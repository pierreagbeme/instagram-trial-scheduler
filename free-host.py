"""Free, temporary Meta transfer server. Only explicitly staged MP4s are served."""
import argparse,json,re,secrets,subprocess,sys,time,urllib.request,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
B=Path(__file__).resolve().parent
STATE=B/'hosting'; STATE.mkdir(exist_ok=True)
MANIFEST=STATE/'files.json'
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_HEAD(self):self.transfer(False)
 def do_GET(self):self.transfer(True)
 def transfer(self,body):
  files=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
  value=files.get(self.path)
  if not value:self.send_error(404);return
  p=Path(value);size=p.stat().st_size;start,end=0,size-1
  requested=self.headers.get('Range')
  if requested:
   m=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
   if not m or not any(m.groups()):self.send_error(416);return
   if not m[1]:start=max(0,size-int(m[2]))
   else:start=int(m[1]);end=min(size-1,int(m[2])) if m[2] else size-1
   if start>end or start>=size:self.send_error(416);return
  self.send_response(206 if requested else 200)
  for k,v in {'Content-Type':'video/mp4','Content-Length':str(end-start+1),'Accept-Ranges':'bytes','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}.items():self.send_header(k,v)
  if requested:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers()
  if body:
   try:
    with p.open('rb') as f:
     f.seek(start);remaining=end-start+1
     while remaining:
      chunk=f.read(min(1024*1024,remaining))
      if not chunk:break
      self.wfile.write(chunk);remaining-=len(chunk)
   except (BrokenPipeError,ConnectionResetError):pass

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['serve','start','stage']);ap.add_argument('file',nargs='?');a=ap.parse_args()
 if a.action=='serve':ThreadingHTTPServer(('127.0.0.1',8766),Handler).serve_forever()
 elif a.action=='stage':
  p=Path(a.file).resolve();assert p.is_file() and p.suffix=='.mp4'
  rows=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
  key=next((k for k,v in rows.items() if v==str(p)),None) or '/'+secrets.token_urlsafe(24)+'.mp4'
  rows[key]=str(p);MANIFEST.write_text(json.dumps(rows,indent=2));print((STATE/'public-url.txt').read_text().strip()+key)
 else:
  if (STATE/'pids.json').exists():
   alive=[]
   for pid in json.loads((STATE/'pids.json').read_text()).values():
    try:os.kill(pid,0);alive.append(pid)
    except ProcessLookupError:pass
   if alive:
    print('Existing hosting processes active; reuse current URL.');return
   (STATE/'pids.json').unlink()
  server=subprocess.Popen([sys.executable,__file__,'serve'],stdout=(STATE/'server.log').open('a'),stderr=subprocess.STDOUT,start_new_session=True)
  tunnel=subprocess.Popen(['/usr/local/bin/cloudflared','tunnel','--url','http://127.0.0.1:8766','--no-autoupdate'],stdout=(STATE/'tunnel.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
  (STATE/'pids.json').write_text(json.dumps({'server':server.pid,'tunnel':tunnel.pid}))
  for _ in range(60):
   text=(STATE/'tunnel.log').read_text()
   m=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',text)
   if m:(STATE/'public-url.txt').write_text(m[0]);print('Free temporary HTTPS tunnel ready');return
   if tunnel.poll() is not None:raise SystemExit('Tunnel failed; inspect tunnel.log')
   time.sleep(1)
  raise SystemExit('Tunnel not ready yet; inspect tunnel.log')
if __name__=='__main__':main()
