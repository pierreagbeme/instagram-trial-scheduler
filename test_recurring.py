import os,unittest,copy
from datetime import datetime
import recurring as r
os.environ['GITHUB_REPOSITORY']='pierreagbeme/instagram-trial-scheduler'
class Guards(unittest.TestCase):
 def test_dst_and_slots(self):
  for utc,hour in [('2026-10-28T08:17:00+00:00',10),('2027-07-01T07:17:00+00:00',10),('2026-10-28T16:17:00+00:00',18),('2027-07-01T15:17:00+00:00',18)]:self.assertEqual(r.slot_for(datetime.fromisoformat(utc)).hour,hour)
 def test_closed_window(self):
  for t in ['2026-10-28T06:00:00+00:00','2026-10-28T09:21:00+00:00','2026-10-28T20:00:00+00:00']:self.assertIsNone(r.slot_for(datetime.fromisoformat(t)))
 def test_empty_queue_safe(self):r.validate({'timezone':'Europe/Berlin','slots':['10:00','18:00'],'batch_size':3,'trial_params':r.POLICY,'batches':[]})
 def test_regular_or_auto_rejected(self):
  with self.assertRaises(AssertionError):r.validate({'timezone':'Europe/Berlin','slots':['10:00','18:00'],'batch_size':3,'trial_params':{'graduation_strategy':'SS_PERFORMANCE'},'batches':[]})
if __name__=='__main__':unittest.main()

from unittest.mock import patch
import io
class PublishingGuards(unittest.TestCase):
 def setup_case(self):
  raw=[b'a',b'b',b'c'];vs=[{'id':str(i),'review_passed':True,'sha256':r.hashlib.sha256(raw[i]).hexdigest(),'video_url':'https://github.com/pierreagbeme/instagram-trial-scheduler/releases/download/t/'+str(i),'caption':'Test'} for i in range(3)]
  q={'timezone':'Europe/Berlin','slots':['10:00','18:00'],'batch_size':3,'trial_params':r.POLICY,'batches':[{'id':'test-batch','approved':True,'publish_at':'2026-10-28T10:00:00+01:00','variants':vs}]};state={'slots':{}};calls=[];published=set()
  def meta(path,data=None):
   if path.startswith('me?'):return {'user_id':r.ACCOUNT,'username':'pierreagbeme'}
   if data is not None:
    calls.append((path,data))
    if path.endswith('/media'):return {'id':'cid'+str(len([x for x in calls if x[0].endswith('/media')]))}
    published.add(data['creation_id']);return {'id':'media'+data['creation_id']}
   if path.startswith('media'):return {'permalink':'https://instagram.com/reel/test','id':path.split('?')[0]}
   return {'status_code':'PUBLISHED' if path.split('?')[0] in published else 'FINISHED'}
  return q,state,calls,published,meta,raw
 def test_publish_exactly_three_then_no_duplicates(self):
  q,s,c,p,m,raw=self.setup_case()
  with patch.object(r,'now',return_value=datetime.fromisoformat('2026-10-28T09:00:00+00:00')),patch.object(r,'readfile',side_effect=lambda name:(q if name=='recurring-queue.json' else s,'sha')),patch.object(r,'save'),patch.object(r,'meta',side_effect=m),patch.object(r.urllib.request,'urlopen',side_effect=lambda url,**kw:io.BytesIO(raw[int(url[-1])])):
   r.run('publish');r.run('publish')
  creates=[data for path,data in c if path.endswith('/media')];pubs=[data for path,data in c if path.endswith('/media_publish')]
  self.assertEqual(len(creates),3);self.assertEqual(len(pubs),3)
  self.assertTrue(all(x['trial_params']==r.POLICY and x['share_to_feed'] is False for x in creates))
 def test_unknown_publish_is_never_retried(self):
  q,s,c,p,m,raw=self.setup_case();s['slots']['2026-10-28T10:00:00+01:00']={'batch_id':'test-batch','variants':{str(i):{'container':'cid'+str(i),'trial_params':r.POLICY,'publish_attempted':True} for i in range(3)}}
  with patch.object(r,'now',return_value=datetime.fromisoformat('2026-10-28T09:00:00+00:00')),patch.object(r,'readfile',side_effect=lambda name:(q if name=='recurring-queue.json' else s,'sha')),patch.object(r,'save'),patch.object(r,'meta',side_effect=m):
   with self.assertRaisesRegex(AssertionError,'Unknown publication'):r.run('publish')
  self.assertEqual(c,[])
