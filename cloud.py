import os,json,sys,time,base64,hashlib,io,zipfile,subprocess,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime,timezone,timedelta
from cryptography.fernet import Fernet
B=Path(__file__).resolve().parent
ACCOUNT='17841400862233205'
TARGET=datetime(2026,10,24,8,tzinfo=timezone.utc)
def now():return datetime.now(timezone.utc)
def api(url,token,data=None,method=None):
 req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/vnd.github+json' if 'api.github.com' in url else 'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:
   body=r.read();return json.loads(body) if body else {}
 except urllib.error.HTTPError as e:
  raise RuntimeError('API request failed: HTTP '+str(e.code)) from None
GH='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']
def gh(path,data=None,method=None):return api(GH+path,os.environ['GH_TOKEN'],data,method)
def meta(path,data=None):return api('https://graph.instagram.com/v25.0/'+path,os.environ['META_TOKEN'],data)
def loadstate():
 d=gh('/contents/state.json');return json.loads(base64.b64decode(d['content'])),d['sha']
def save(state):
 _,sha=loadstate();gh('/contents/state.json',{'message':'Record batch progress','sha':sha,'content':base64.b64encode(json.dumps(state,indent=2).encode()).decode()},'PUT')
def unpack():
 z=zipfile.ZipFile(io.BytesIO(Fernet(os.environ['PACKAGE_KEY'].encode()).decrypt((B/'batch.enc').read_bytes())))
 for n in z.namelist():
  assert not n.startswith('/') and '..' not in Path(n).parts
 z.extractall(B);m=json.loads((B/'batch.json').read_text())
 assert m['account']=='pierreagbeme' and m['trial_params']=={'graduation_strategy':'MANUAL'}
 assert datetime.fromisoformat(m['publish_not_before'])==TARGET
 for v in m['variants']:assert hashlib.sha256((B/v['file']).read_bytes()).hexdigest()==v['sha256']
 return m
def verify_account():
 me=meta('me?fields=user_id,username');assert me['user_id']==ACCOUNT and me['username']=='pierreagbeme'
def guard(action,t):
 if action=='prepare':assert TARGET-timedelta(hours=20)<=t<TARGET,'Outside preparation window'
 if action=='publish':assert TARGET-timedelta(minutes=60)<=t<=TARGET+timedelta(minutes=30),'Outside publishing window'
def command(*args):return subprocess.check_output([sys.executable,str(B/'free-host.py'),*args],text=True).strip()
def transfer_ready(url):
 for attempt in range(18):
  try:
   with urllib.request.urlopen(urllib.request.Request(url,method='HEAD'),timeout=10) as r:
    if r.status==200 and int(r.headers.get('Content-Length','0'))>1000:return
  except Exception:pass
  time.sleep(5)
 raise RuntimeError('Temporary cloud transfer URL unavailable; no Meta creation attempted')
def ready(cid):
 for _ in range(40):
  s=meta(cid+'?fields=status_code')['status_code']
  if s=='FINISHED':return
  if s in ['ERROR','EXPIRED']:raise RuntimeError('Meta container '+s)
  time.sleep(15)
 raise RuntimeError('Meta processing timeout')
def stophost():
 p=B/'hosting/pids.json'
 if p.exists():
  import signal
  for pid in json.loads(p.read_text()).values():
   try:os.kill(pid,signal.SIGTERM)
   except ProcessLookupError:pass

def main():
 action=sys.argv[1];assert action in ['validate','prepare','publish'];m=unpack();verify_account()
 if action=='validate':print('Cloud validation passed: account, encrypted videos, hashes, MANUAL trial policy.');return
 guard(action,now());state,_=loadstate()
 if action=='prepare':
  try:
   print(command('start'))
   for v in m['variants']:
    name=v['style'];r=state.get(name,{})
    if not r.get('container'):
     assert not r.get('create_attempted'),'Unknown creation outcome: reconcile before retry'
     u=command('stage',str(B/v['file']));print('::add-mask::'+u,flush=True);transfer_ready(u)
     r={'create_attempted':True,'trial_params':{'graduation_strategy':'MANUAL'}};state[name]=r;save(state)
     result=meta(ACCOUNT+'/media',{'media_type':'REELS','video_url':u,'caption':v['caption'],'share_to_feed':False,'trial_params':r['trial_params']})
     r['container']=result['id'];save(state)
    ready(r['container']);r['ready']=True;save(state);print(name,'ingested by Meta as MANUAL Trial Reel',flush=True)
  finally:stophost()
 else:
  assert set(state)=={v['style'] for v in m['variants']}
  for r in state.values():
   assert r['trial_params']=={'graduation_strategy':'MANUAL'} and r.get('ready')
   if not r.get('published'):ready(r['container'])
  while now()<TARGET:time.sleep(min(30,(TARGET-now()).total_seconds()))
  for name,r in state.items():
   if r.get('published'):print(name,'already published');continue
   assert not r.get('publish_attempted'),'Unknown publication outcome: reconcile before retry'
   assert TARGET<=now()<=TARGET+timedelta(minutes=30),'Publication window closed'
   r['publish_attempted']=True;save(state)
   result=meta(ACCOUNT+'/media_publish',{'creation_id':r['container']})
   r.update(published=True,media_id=result['id'],published_at=now().isoformat());save(state)
   r['media']=meta(result['id']+'?fields=id,permalink,timestamp');save(state);print(name,r['media']['permalink'],flush=True)
  gh('/actions/workflows/publish.yml/disable',{},'PUT')
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## Batch status\n\n'+ '\n'.join('- '+k+': '+(v.get('media',{}).get('permalink') or ('Meta ingestion complete' if v.get('ready') else 'Pending')) for k,v in state.items()))
if __name__=='__main__':main()
