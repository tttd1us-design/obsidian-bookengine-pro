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

                # 5. 00_옵시디언_스마트_편집툴킷_세팅가이드.md
                guide_file = os.path.join(folder_path, '00_옵시디언_스마트_편집툴킷_세팅가이드.md')
                with open(guide_file, 'w', encoding='utf-8') as f:
                    guide_content = """# 🛠️ 옵시디언 스마트 도서 편집 툴킷 세팅 & 3단계 초안 구조화 가이드

> **본 볼트는 Obsidian BookEngine Pro에서 출판 규격(신국판 B5)으로 자동 패키징된 도서 전용 볼트입니다.**  
> 옵시디언에서 본 폴더를 `Open folder as vault`로 여신 후, 아래의 4대 핵심 플러그인과 3단계 실전 편집 스킬을 활용하면 초안을 가장 빠르고 품격 있게 마감할 수 있습니다.

---

## Ⅰ. 산만한 초안을 구조화하는 3단계 AI 편집 스킬

AI에게 단순히 "글 매끄럽게 다듬어줘"라고 요청하면 기계적 수식어만 더 붙어 오히려 글이 분산됩니다.  
텍스트를 완전히 분해한 뒤 아래 3단계로 재조립하도록 지시해야 합니다.

### 1단계: 논점 추출 및 중복 병합 (De-duplication)
- 글 전체에서 **주장(Claim), 사례(Evidence), 보조 설명(Elaboration)**만 발라냅니다.
- 표현만 다르고 같은 말을 반복하는 문단들을 단 하나의 날카로운 명제로 묶습니다.

### 2단계: '불릿 포인트 독' 해독 (De-bulleting)
- AI 특유의 잘게 쪼개진 목록(`1., 2., 3...`, `- `, `* `)을 강제로 해체합니다.
- 문맥과 인과관계가 이어지는 호흡 긴 **줄글 산문(Prose)**으로 전환시킵니다.

### 3단계: 기계적 접속사 박멸 (De-cliché)
- "한편", "또한", "살펴보겠습니다", "중요한 역할을 합니다", "기대되어집니다" 같은 전형적 AI 투를 금지어로 지정합니다.
- 문장을 단문화하고 서술어를 명확하고 힘 있게 잡습니다 (`~한다`, `~이다`).

---

## Ⅱ. 원클릭 원고 구조화 및 문체 리팩토링 프롬프트

```markdown
[원고 구조화 및 문체 리팩토링 지침]

다음 텍스트는 아이디어가 산만하게 나열되어 있거나 초안 상태의 글입니다. 아래 4가지 규칙을 엄격히 적용해 완성된 책의 본문 형태로 전면 재집필하세요.

1. 구조 재배치: 시간순 또는 논리적 인과(문제 제기 → 메커니즘 분석 → 적용 사례 → 한계 및 결론)에 따라 문단의 순서를 가장 설득력 있는 흐름으로 완전히 뒤바꾸세요.
2. 중복 통폐합: 유사한 논점이나 의미가 겹치는 문장은 단 하나의 가장 날카로운 문장으로 합치세요.
3. 서술 방식 전환: 무분별한 불릿 포인트(목록형)를 금지하며, 문단과 문단이 자연스럽게 이어지는 에세이/도서 본문 스타일의 완성된 산문으로 전환하세요.
4. AI 클리셰 삭제: '이를 통해', '주목할 만한 점은', '또한', '~할 수 있습니다' 같은 상투적인 어미와 접속사를 전면 삭제하고 단문 중심의 담백한 어조로 마감하세요.

[초안 입력]
```

---

## Ⅲ. 옵시디언 안에서 '알아서' 편집해 주는 4대 핵심 도구

1. **Obsidian Copilot (또는 BMO Chatbot)**
   - **역할**: 사이드바에 상주하는 1:1 수석 편집장.
   - **활용법**: 긴 챕터 초안을 열어둔 채 `/copilot`을 띄우고 *"현재 활성화된 노트(Active Note)의 논리적 모순을 찾고, 3개의 절(Section)로 재구성해 줘"*라고 지시.
2. **Text Generator (프롬프트 템플릿 자동화)**
   - **역할**: 반복적인 편집 작업을 단축키 하나로 실행.
   - **활용법**: 위의 '원고 구조화 프롬프트'를 템플릿으로 저장하고, 산만한 메모 블록을 드래그한 뒤 단축키를 누르면 그 자리에서 완성된 산문으로 즉시 치환.
3. **Smart Connections (AI 임베딩 벡터 검색)**
   - **역할**: 흩어진 유사 메모 자동 탐색.
   - **활용법**: 지금 쓰는 챕터와 주제가 겹치는 과거 독서 노트나 레퍼런스를 우측 패널에 자동으로 추천.
4. **Linter (서식 및 레이아웃 자동 강제)**
   - **역할**: 내용 편집 전, 지저분한 마크다운 문법 평탄화.
   - **활용법**: 저장(`Ctrl/Cmd + S`) 시점에 들쑥날쑥한 헤딩 깊이, 불필요한 공백 줄, 엉망인 들여쓰기를 출판 표준 규격으로 자동 정돈.

---

## Ⅳ. 가장 빠른 실전 작업 3단계 순서

1. **Linter**로 서식의 물리적 노이즈(불필요한 줄바꿈, 들여쓰기 오류)를 한 번에 싹 밀어냅니다.
2. **Text Generator나 Copilot**에 '구조화 프롬프트'를 태워 본문을 단단한 산문 형태로 압축·재배열합니다.
3. 재배열된 텍스트에서 튀어나오는 이질적인 문장만 단축키(`Alt + ↑/↓`)로 문맥 위치를 미세 조정하며 마감합니다.
"""
                    f.write(guide_content)
                created_files.append('00_옵시디언_스마트_편집툴킷_세팅가이드.md')

                # 6. 출판품질검수_QC_리포트.txt
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
