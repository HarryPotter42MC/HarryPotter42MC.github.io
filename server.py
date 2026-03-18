"""
Live-reload dev server.
Serves files with an injected <script> that polls for changes and auto-refreshes.
"""
import http.server, os, time, threading, hashlib

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

def file_hash(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""

def dir_snapshot():
    snap = {}
    for root, _, files in os.walk(DIRECTORY):
        for fname in files:
            if fname == "server.py":
                continue
            p = os.path.join(root, fname)
            snap[p] = file_hash(p)
    return snap

CHANGED = {"v": 0}
_last = dir_snapshot()

def watcher():
    global _last
    while True:
        time.sleep(0.5)
        cur = dir_snapshot()
        if cur != _last:
            _last = cur
            CHANGED["v"] += 1

threading.Thread(target=watcher, daemon=True).start()

INJECT = b"""
<script>
(function(){
  var v = null;
  setInterval(function(){
    fetch('/__livereload__').then(r=>r.text()).then(function(t){
      if(v===null){v=t;return;}
      if(t!==v){location.reload();}
    }).catch(()=>{});
  }, 500);
})();
</script>
"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIRECTORY, **kw)

    def do_GET(self):
        if self.path == "/__livereload__":
            body = str(CHANGED["v"]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
            return
        # serve normally, inject live-reload into HTML
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if path.endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as f:
                data = f.read()
            data = data.replace(b"</body>", INJECT + b"</body>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        pass  # silence request logs

print(f"Live server running at http://localhost:{PORT}")
print("Open that URL in your browser — the page auto-refreshes on any file change.")
print("Press Ctrl+C to stop.\n")
http.server.HTTPServer(("", PORT), Handler).serve_forever()
