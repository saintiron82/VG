import json,tempfile,unittest
from pathlib import Path
from .terrain_cache import RowCache
class TerrainCacheTests(unittest.TestCase):
 def test_exact_resume(self):
  with tempfile.TemporaryDirectory() as d:
   c=RowCache(d,{'source':'a'});g={'earth':[[0.,1.,0.],[1.,1.,0.],[0.,1.,1.]]};ids={'a'};c.save(0,g,{},ids,set(),2);starts={k:len(v) for k,v in g.items()};prior=set(ids);g['earth'] += [[1.,1.,0.],[1.,1.,1.],[0.,1.,1.]];ids.add('b');c.save(8,g,starts,ids,prior,3)
   n={};s=set();r=RowCache(d,{'source':'a'});self.assertEqual(r.load(0,n,s),2);self.assertEqual(r.load(8,n,s),3);self.assertEqual(n,g);self.assertEqual(s,ids);self.assertEqual(r.hits,2)
 def test_changed_source_is_separate(self):
  with tempfile.TemporaryDirectory() as d:
   a=RowCache(d,{'source':'a'});b=RowCache(d,{'source':'b'});self.assertNotEqual(a.path,b.path);self.assertIsNone(b.load(0,{},set()))
 def test_sequence_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c=RowCache(d,{});c.save(8,{}, {}, {'a'}, {'a'},0)
   with self.assertRaisesRegex(ValueError,'sequence'):c.load(8,{},set())
 def test_corruption_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c=RowCache(d,{});c.save(0,{}, {},set(),set(),0);p=c.filename(0);v=json.loads(p.read_text());v['data']['domains']=100;p.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,'hash'):c.load(0,{},set())
 def test_refuses_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   c=RowCache(d,{});c.save(0,{}, {},set(),set(),0)
   with self.assertRaisesRegex(ValueError,'overwrite'):c.save(0,{}, {},set(),set(),0)
if __name__=='__main__':unittest.main()
