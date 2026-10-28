"""Stage exactly three reviewed videos and reserve one Berlin slot. No publishing."""
from pathlib import Path
import sys,json,subprocess,base64,re,hashlib,tempfile
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
REPO='pierreagbeme/instagram-trial-scheduler'
def cmd(*args):return subprocess.check_output(['gh',*args],text=True)
def replacement_guard(old,m,target,state,at):
 assert old and old['id']==m['id'] and datetime.fromisoformat(old['publish_at'])==target,'Exact existing batch and slot required'
 assert target-at>=timedelta(hours=1),'Replacement requires at least one hour lead'
 assert not any(datetime.fromisoformat(key)==target for key in state.get('slots',{})),'Publisher has started this slot; replacement forbidden'
def main():
 m=json.loads(Path(sys.argv[1]).read_text());assert re.fullmatch(r'[a-z0-9-]{5,80}',m['id']);assert m['account']=='pierreagbeme';target=datetime.fromisoformat(m['publish_at']);local=target.astimezone(ZoneInfo('Europe/Berlin'));assert target>datetime.now(timezone.utc) and local.hour in (10,18) and local.minute==local.second==0
 variants=m['variants'];assert len(variants)==3 and len({v['id'] for v in variants})==3
 data=json.loads(cmd('api',f'repos/{REPO}/contents/recurring-queue.json'));q=json.loads(base64.b64decode(data['content']))
 old=next((b for b in q['batches'] if b['id']==m['id'] or datetime.fromisoformat(b['publish_at'])==target),None)
 replace='--replace-unstarted' in sys.argv[2:]
 if replace:
  state=json.loads(base64.b64decode(json.loads(cmd('api',f'repos/{REPO}/contents/recurring-state.json'))['content']));replacement_guard(old,m,target,state,datetime.now(timezone.utc))
 elif old:raise RuntimeError('Batch or slot already exists; inspect existing queue instead of overwriting')
 files=[];records=[]
 for v in variants:
  f=Path(v['file']).resolve();review=json.loads(Path(v['review_file']).read_text());digest=hashlib.sha256(f.read_bytes()).hexdigest()
  assert f.suffix=='.mp4' and review['passed'] is True and review['publication_allowed'] is True and digest==review['sha256'];assert 0<len(v['caption'])<=2200
  assert not any(x['sha256']==digest for b in q['batches'] if not (replace and b['id']==m['id']) for x in b['variants']),'Already queued video'
  files.append(str(f));records.append({'id':v['id'],'sha256':digest,'review_passed':True,'caption':v['caption'],'filename':f.name})
 assert len(set(files))==3 and len({Path(f).name for f in files})==3
 tag='batch-'+m['id']+('-revision-'+hashlib.sha256(''.join(r['sha256'] for r in records).encode()).hexdigest()[:10] if replace else '')
 cmd('release','create',tag,'--repo',REPO,'--prerelease','--title',m['id'],'--notes','Reviewed MANUAL Instagram Trial Reel transfer batch.',*files)
 assets=json.loads(cmd('release','view',tag,'--repo',REPO,'--json','assets'))['assets'];urls={a['name']:a['url'] for a in assets}
 for r in records:r['video_url']=urls[r.pop('filename')]
 # Read again after upload, so another producer cannot silently overwrite a slot.
 data=json.loads(cmd('api',f'repos/{REPO}/contents/recurring-queue.json'));q=json.loads(base64.b64decode(data['content']))
 if replace:
  current=next((b for b in q['batches'] if b['id']==m['id']),None);assert current==old,'Batch changed during upload'
  state=json.loads(base64.b64decode(json.loads(cmd('api',f'repos/{REPO}/contents/recurring-state.json'))['content']));replacement_guard(current,m,target,state,datetime.now(timezone.utc))
  q['batches']=[b for b in q['batches'] if b['id']!=m['id']]
 else:assert not any(b['id']==m['id'] or datetime.fromisoformat(b['publish_at'])==target for b in q['batches'])
 q['batches'].append({'id':m['id'],'publish_at':target.isoformat(),'approved':True,'variants':records,'release_tag':tag})
 payload={'message':'Queue reviewed Trial Reel batch '+m['id'],'sha':data['sha'],'content':base64.b64encode(json.dumps(q,indent=2,ensure_ascii=False).encode()).decode()}
 with tempfile.NamedTemporaryFile(mode='w',suffix='.json') as f:
  json.dump(payload,f);f.flush();cmd('api',f'repos/{REPO}/contents/recurring-queue.json','--method','PUT','--input',f.name)
 print('Queued',m['id'],'for',target.isoformat(),'; three reviewed MANUAL Trial Reels. No publishing now.')
if __name__=='__main__':main()
