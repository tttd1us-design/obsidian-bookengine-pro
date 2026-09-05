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
