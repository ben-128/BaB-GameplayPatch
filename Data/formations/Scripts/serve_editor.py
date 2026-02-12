"""
Local HTTP server for the Formation Editor.
Serves editor.html and provides a REST API for listing, loading, and saving area JSONs.

Usage:  py -3 Data/formations/serve_editor.py
Then open http://localhost:8000 in a browser.
"""

import http.server
import json
import os
import sys

PORT = 8000
# BASE_DIR should be formations root (parent of Scripts/), where editor.html lives
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/':
            self.path = '/editor.html'
            return super().do_GET()

        if self.path == '/api/files':
            return self._list_files()

        if self.path.startswith('/api/load/'):
            rel = self.path[len('/api/load/'):]
            return self._load_file(rel)

        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/save/'):
            rel = self.path[len('/api/save/'):]
            return self._save_file(rel)
        self._json_error(404, 'Not found')

    def _list_files(self):
        files = []
        for dirpath, _dirs, filenames in os.walk(BASE_DIR):
            for fn in sorted(filenames):
                if not fn.endswith('.json'):
                    continue
                # Skip vanilla reference files (read-only, not for editing)
                if fn.endswith('_vanilla.json'):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, BASE_DIR).replace('\\', '/')
                # Only include files inside subdirectories (level/area.json)
                if '/' not in rel:
                    continue
                label = rel.replace('/', ' / ').replace('.json', '')
                files.append({'path': rel, 'label': label})
        files.sort(key=lambda f: f['path'])
        self._json_response(files)

    def _load_file(self, rel):
        safe = self._safe_path(rel)
        if safe is None:
            return self._json_error(403, 'Invalid path')
        if not os.path.isfile(safe):
            return self._json_error(404, 'File not found')
        with open(safe, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._json_response(data)

    def _save_file(self, rel):
        safe = self._safe_path(rel)
        if safe is None:
            return self._json_error(403, 'Invalid path')
        if not os.path.isfile(safe):
            return self._json_error(404, 'File not found (will not create new files)')

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            return self._json_error(400, 'Invalid JSON: ' + str(e))

        with open(safe, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')

        self._json_response({'ok': True, 'path': rel})

    def _safe_path(self, rel):
        """Resolve relative path and ensure it stays inside BASE_DIR."""
        rel = rel.replace('\\', '/')
        full = os.path.normpath(os.path.join(BASE_DIR, rel))
        if not full.startswith(BASE_DIR):
            return None
        if not full.endswith('.json'):
            return None
        return full

    def _json_response(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, code, msg):
        self._json_response({'error': msg}, code)

    def log_message(self, fmt, *args):
        # Quieter logging: skip static file requests
        if args and isinstance(args[0], str) and args[0].startswith('GET /api'):
            pass  # still log API calls
        sys.stderr.write('[editor] %s\n' % (fmt % args))


if __name__ == '__main__':
    print(f'Formation Editor server starting on http://localhost:{PORT}')
    print(f'Serving files from: {BASE_DIR}')
    print('Press Ctrl+C to stop.\n')
    server = http.server.HTTPServer(('localhost', PORT), EditorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
