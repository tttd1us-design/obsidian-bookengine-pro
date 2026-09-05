import http.server
import socketserver
import webbrowser
import os
import sys

PORT = 8765
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

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
