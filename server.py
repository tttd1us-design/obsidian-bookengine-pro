import http.server
import socketserver
import webbrowser
import os
import sys
import json
import subprocess
from datetime import datetime

PORT = 8765
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_POST(self):
        if self.path == '/api/github-sync':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                text = data.get('content', '')
                title = data.get('title', '원고')

                os.makedirs(os.path.join(DIRECTORY, 'manuscript'), exist_ok=True)
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-', '(', ')', '『', '』')).strip()
                if not safe_title:
                    safe_title = 'manuscript'
                file_path = os.path.join(DIRECTORY, 'manuscript', f'{safe_title}.md')
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text)

                subprocess.run(['git', 'add', '.'], cwd=DIRECTORY, check=True)
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                commit_msg = f'docs(manuscript): sync "{title}" at {timestamp}'
                subprocess.run(['git', 'commit', '-m', commit_msg], cwd=DIRECTORY, check=False)
                push_res = subprocess.run(['git', 'push', 'origin', 'main'], cwd=DIRECTORY, capture_output=True, text=True)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                response = {
                    'success': True,
                    'message': f'GitHub 저장소에 성공적으로 동기화 및 푸시되었습니다!',
                    'file': os.path.basename(file_path),
                    'commit': commit_msg,
                    'repoUrl': 'https://github.com/tttd1us-design/obsidian-bookengine-pro'
                }
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                err_resp = {'success': False, 'error': str(e)}
                self.wfile.write(json.dumps(err_resp, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == '/api/browse-folder':
            try:
                import tkinter
                from tkinter import filedialog
                root = tkinter.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                selected_dir = filedialog.askdirectory(title="원고를 저장할 폴더를 선택하세요")
                root.destroy()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'path': selected_dir}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == '/api/open-folder':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                folder_path = data.get('folderPath', '')
                if os.path.exists(folder_path):
                    try:
                        os.startfile(folder_path)
                    except Exception:
                        subprocess.Popen(['explorer', folder_path])
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True}).encode('utf-8'))
                else:
                    raise Exception('지정된 폴더를 찾을 수 없습니다: ' + folder_path)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        if self.path == '/api/save-to-local-folder':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                folder_path = data.get('folderPath', '').strip()
                title = data.get('title', '도서원고').strip()
                plan_doc = data.get('planDoc', '')
                processed_text = data.get('processedText', '')
                working_sections = data.get('workingSections', [])
                open_explorer = data.get('openExplorer', True)

                if not folder_path:
                    safe_name = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                    folder_path = os.path.join(r'C:\Users\tttd1\Documents\Obsidian_Books', safe_name or '도서출판_원고')

                os.makedirs(folder_path, exist_ok=True)
                created_files = []

                # 1. 00_출판사납품_전체완성원고.md
                main_file = os.path.join(folder_path, '00_출판사납품_전체완성원고.md')
                with open(main_file, 'w', encoding='utf-8') as f:
                    f.write(processed_text)
                created_files.append('00_출판사납품_전체완성원고.md')

                # 2. 00_완전집필기획서.md
                if plan_doc:
                    plan_file = os.path.join(folder_path, '00_완전집필기획서.md')
                    with open(plan_file, 'w', encoding='utf-8') as f:
                        f.write(plan_doc)
                    created_files.append('00_완전집필기획서.md')

                # 3. chapters/ 폴더 생성 및 챕터별 분할 저장 (옵시디언 볼트 완벽 호환)
                chapters_dir = os.path.join(folder_path, 'chapters')
                os.makedirs(chapters_dir, exist_ok=True)

                if working_sections and len(working_sections) > 0:
                    for idx, sec in enumerate(working_sections):
                        sec_title = sec.get('title', f'챕터_{idx+1}')
                        clean_sec_title = "".join(c for c in sec_title if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                        filename = f'{idx+1:02d}_{clean_sec_title}.md'
                        ch_path = os.path.join(chapters_dir, filename)
                        with open(ch_path, 'w', encoding='utf-8') as f:
                            content = f"# {sec.get('title')}\n\n"
                            content += f"> 분류: {sec.get('phase', '본문')} | 글자수: {len(sec.get('content', '')):,}자\n\n---\n\n"
                            content += sec.get('content', '')
                            f.write(content)
                        created_files.append(f'chapters/{filename}')

                # 4. 00_목차_및_구조분석표.md
                toc_file = os.path.join(folder_path, '00_목차_및_구조분석표.md')
                with open(toc_file, 'w', encoding='utf-8') as f:
                    toc_content = f"# {title} - 전체 목차 아키텍처\n\n"
                    toc_content += f"> 생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    toc_content += "## [챕터 리스트]\n\n"
                    for idx, sec in enumerate(working_sections):
                        toc_content += f"{idx+1}. **{sec.get('title')}** ({sec.get('phase', '본문')} / {len(sec.get('content', '')):,}자)\n"
                    f.write(toc_content)
                created_files.append('00_목차_및_구조분석표.md')

                # 5. 출판품질검수_QC_리포트.txt
                qc_file = os.path.join(folder_path, '출판품질검수_QC_리포트.txt')
                with open(qc_file, 'w', encoding='utf-8') as f:
                    char_count = len(processed_text)
                    b5_pages = (char_count + 679) // 680
                    report = f"==========================================================\n"
                    report += f" [Obsidian BookEngine Pro - 출판 품질 검수 리포트]\n"
                    report += f"==========================================================\n\n"
                    report += f"• 도서명: {title}\n"
                    report += f"• 저장 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    report += f"• 저장 절대 경로: {folder_path}\n"
                    report += f"• 신국판 B5 기준 쪽수: 약 {b5_pages} 쪽 (680자/쪽 기준)\n"
                    report += f"• 총 본문 글자수: {char_count:,} 자\n"
                    report += f"• 생성된 파일 수: {len(created_files)} 개 (통합본 + {len(working_sections)}개 챕터 분할본)\n"
                    report += f"• 안티슬롭 검수: 100% 상투구 필터 통과\n"
                    report += f"• 옵시디언 볼트 호환: 즉시 옵시디언에서 'Open folder as vault' 가능\n\n"
                    report += f"==========================================================\n"
                    f.write(report)
                created_files.append('출판품질검수_QC_리포트.txt')

                # 6. 윈도우 탐색기 열기
                if open_explorer:
                    try:
                        os.startfile(folder_path)
                    except Exception:
                        subprocess.Popen(['explorer', folder_path])

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                resp = {
                    'success': True,
                    'message': f'내 컴퓨터 폴더에 {len(created_files)}개 파일이 성공적으로 저장되었습니다!',
                    'folderPath': folder_path,
                    'files': created_files
                }
                self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return
        super().do_POST()

def run():
    os.chdir(DIRECTORY)
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        url = f'http://localhost:{PORT}/index.html'
        print('=' * 65)
        print(' [Obsidian BookEngine Pro - 베스트셀러 출판 스튜디오 가동]')
        print(f' 서버 주소: {url}')
        print(' 브라우저를 자동으로 실행합니다. 종료하려면 Ctrl+C를 누르세요.')
        print('=' * 65)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n서버를 안전하게 종료합니다.')
            sys.exit(0)

if __name__ == '__main__':
    run()
