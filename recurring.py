"""Daily 10:00/18:00 Berlin publisher. Exactly three reviewed MANUAL trials per slot."""
import base64,hashlib,json,os,sys,time,urllib.request,urllib.error
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Europe/Berlin');ACCOUNT='17841400862233205';POLICY={'graduation_strategy':'MANUAL'}
def now():return datetime.now(timezone.utc)
def slot_for(t):
 local=t.astimezone(TZ)
 for hour in (10,18):
  target=local.replace(hour=hour,minute=0,second=0,microsecond=0)
  delta=(target-t).total_seconds()
  if -1200<=delta<=3600:return target
 return None
def request(url,token,data=None,method=None):
 req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/vnd.github+json' if 'api.github.com' in url else 'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:
   body=r.read();return json.loads(body) if body else {}
 except urllib.error.HTTPError as e:raise RuntimeError('API HTTP '+str(e.code)) from None

def gh(path,data=None,method=None):return request('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+path,os.environ['GH_TOKEN'],data,method)
def meta(path,data=None):return request('https://graph.instagram.com/v25.0/'+path,os.environ['META_TOKEN'],data)
def readfile(path):
 d=gh('/contents/'+path);return json.loads(base64.b64decode(d['content'])),d['sha']
def save(state):
 _,sha=readfile('recurring-state.json');gh('/contents/recurring-state.json',{'message':'Record recurring Trial Reel progress','sha':sha,'content':base64.b64encode(json.dumps(state,indent=2).encode()).decode()},'PUT')
def validate(q):
 assert q['timezone']=='Europe/Berlin' and q['slots']==['10:00','18:00'] and q['batch_size']==3 and q['trial_params']==POLICY
 seen=set();assigned=set();hashes=set()
 for batch in q['batches']:
  assert batch['id'] not in seen;seen.add(batch['id'])
  target=datetime.fromisoformat(batch['publish_at']);local=target.astimezone(TZ)
  assert target.utcoffset() is not None and local.hour in (10,18) and local.minute==local.second==0
  assert target.timestamp() not in assigned;assigned.add(target.timestamp())
  assert batch['approved'] is True and len(batch['variants'])==3
  assert len({v['id'] for v in batch['variants']})==3
  for v in batch['variants']:
   assert v['review_passed'] is True and len(v['sha256'])==64
   assert v['sha256'] not in hashes,'Duplicate video in queue';hashes.add(v['sha256'])
   assert v['video_url'].startswith('https://github.com/'+os.environ['GITHUB_REPOSITORY']+'/releases/download/')
   assert len(v['caption'])<=2200

def summary(text):
 print(text,flush=True)
 if os.environ.get('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(text+'\n\n')
def run(action,catch_up_batch=""):
 started=now()
 q,_=readfile('recurring-queue.json');validate(q)
 me=meta('me?fields=user_id,username');assert me['user_id']==ACCOUNT and me['username']=='pierreagbeme'
 if action=='validate':summary('Validated account, queue schema and MANUAL trial policy. Queued batches: '+str(len(q['batches']))+'. No publishing performed.');return
 assert action in ('publish','catch-up')
 catchup=action=='catch-up'
 if catchup:
  assert catch_up_batch,'Explicit batch ID required'
  chosen=next((b for b in q['batches'] if b['id']==catch_up_batch),None)
  assert chosen,'Unknown batch'
  target=datetime.fromisoformat(chosen['publish_at'])
  assert target<=started and target.astimezone(TZ).date()==started.astimezone(TZ).date(),'Catch-up limited to a missed slot today'
 else:target=slot_for(now())
 if target is None:summary('Outside 10:00/18:00 Berlin preparation/publication window. No publishing.');return
 key=target.isoformat();state,_=readfile('recurring-state.json');batch=next((b for b in q['batches'] if datetime.fromisoformat(b['publish_at'])==target),None)
 if not batch:
  state.setdefault('slots',{})[key]={'status':'missing_reviewed_batch','checked_at':now().isoformat()};save(state)
  raise RuntimeError('No reviewed batch for '+key+'. Slot skipped; no fallback.')
 if state.get('slots',{}).get(key,{}).get('status')=='missing_reviewed_batch':state['slots'].pop(key)
 record=state.setdefault('slots',{}).setdefault(key,{'batch_id':batch['id'],'variants':{}})
 assert record.get('batch_id')==batch['id'],'Slot already reserved by another batch'
 if record.get('status')=='published_manual_trial':summary('Already published; no duplicate: '+batch['id']);return
 window_end=started+timedelta(minutes=20) if catchup else target+timedelta(minutes=20)
 if catchup:record['authorized_catch_up_started_at']=started.isoformat();save(state)
 for v in batch['variants']:
  r=record['variants'].setdefault(v['id'],{})
  if r.get('published'):continue
  if not r.get('container'):
   assert not r.get('create_attempted'),'Unknown create result; reconcile before any retry'
   # Verify the exact reviewed transfer bytes before asking Meta to ingest them.
   h=hashlib.sha256()
   with urllib.request.urlopen(v['video_url'],timeout=90) as response:
    for block in iter(lambda:response.read(1048576),b''):h.update(block)
   assert h.hexdigest()==v['sha256'],'Transfer hash mismatch'
   r.update(create_attempted=True,trial_params=POLICY);save(state)
   result=meta(ACCOUNT+'/media',{'media_type':'REELS','video_url':v['video_url'],'caption':v['caption'],'share_to_feed':False,'trial_params':POLICY})
   r['container']=result['id'];save(state)
 deadline=min(now()+timedelta(minutes=15),window_end)
 while True:
  ready=True
  for r in record['variants'].values():
   if r.get('published'):continue
   remote=meta(r['container']+'?fields=status_code');r['remote_status']=remote['status_code']
   if remote['status_code']!='FINISHED':ready=False
   assert remote['status_code']!='PUBLISHED','Unknown publish result; reconcile instead of retrying'
  save(state)
  if ready:break
  if now()>=deadline:raise RuntimeError('Meta ingestion not ready; no replacement containers and no partial new batch.')
  time.sleep(60)
 while now()<target:time.sleep(min(30,(target-now()).total_seconds()))
 for v in batch['variants']:
  r=record['variants'][v['id']]
  if r.get('published'):continue
  assert not r.get('publish_attempted'),'Unknown publication result; reconcile before retry'
  assert target<=now()<=window_end,'Publication window closed'
  assert r['trial_params']==POLICY
  r['publish_attempted']=True;save(state)
  result=meta(ACCOUNT+'/media_publish',{'creation_id':r['container']})
  r.update(published=True,media_id=result['id']);save(state)
  r['media']=meta(result['id']+'?fields=id,permalink,timestamp');save(state)
  summary(v['id']+': '+r['media']['permalink'])
 for r in record['variants'].values():assert meta(r['container']+'?fields=status_code')['status_code']=='PUBLISHED'
 record['status']='published_manual_trial';record['verified_at']=now().isoformat();save(state)
 summary('Batch verified: three MANUAL Trial Reels. Automatic graduation disabled.')
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'validate',os.environ.get('CATCH_UP_BATCH',''))
