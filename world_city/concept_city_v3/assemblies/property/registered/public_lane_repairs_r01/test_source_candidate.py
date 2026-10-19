"""Read-only source-cut guards; no native compile or acceptance assertion."""
import copy,hashlib,json,pathlib,unittest
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class SourceCandidate(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.candidate=read(H/'source_candidates.json');cls.columns=read(H/'baseline/cap_columns.json')
 def test_hash_bindings(self):
  for r in self.candidate['records']:
   for k in ['source_master','original_master','original_render','original_cell_snapshot']:
    self.assertEqual(sha(ROOT/r[k]['path']),r[k]['sha256'])
 def test_only_appended_operations(self):
  for r in self.candidate['records']:
   old=read(ROOT/r['original_master']['path']);new=read(ROOT/r['source_master']['path']);n=r['original_operation_count']
   self.assertEqual(new['components'][0]['operations'][:n],old['components'][0]['operations'])
   self.assertEqual(len(new['components'][0]['operations'])-n,r['appended_cut_count'])
   new['components'][0]['operations']=new['components'][0]['operations'][:n]
   for k in ['id','revision','metadata']:old.pop(k,None);new.pop(k,None)
   self.assertEqual(old,new)
 def test_selected_actual_cells_exact(self):
  for r in self.candidate['records']:
   master=read(ROOT/r['source_master']['path']);cells=read(ROOT/r['original_cell_snapshot']['path'])['cells'];ops=master['components'][0]['operations'][r['original_operation_count']:];hits=set()
   for o in ops:
    self.assertEqual(o['action'],'cut');self.assertEqual(o['shape']['kind'],'box');self.assertEqual(set(o['selector']),{'feature'})
    self.assertTrue(all(f.startswith('r1_access_skin_')for f in o['selector']['feature']))
    lo=o['shape']['min'];hi=o['shape']['max']
    for c in cells:
     center=[(c[i]+.5)*.5 for i in range(3)]
     if c[6]in o['selector']['feature'] and all(lo[i]<=center[i]<hi[i]for i in range(3)):hits.add(tuple(c[:3]))
   self.assertEqual(hits,{tuple(v)for v in r['expected_removed_grid_cells']})
 def test_finite_columns_and_traffic_accounted(self):
  counts={'E1':(44,44),'E2':(57,58)}
  for r in self.columns['records']:
   columns=r['candidate_columns'];self.assertEqual((len(columns),sum(len(c['cells'])for c in columns)),counts[r['property_id']])
   self.assertTrue(all(0<c['traffic_area_m2']<=.2500000001 for c in columns))
   self.assertAlmostEqual(sum(c['traffic_area_m2']for c in columns)+r['outside_traffic_cell_fraction_area_m2'],len(columns)*.25,places=9)
   self.assertEqual(r['non_access_skin_features'],[])
 def test_budget_and_hold(self):
  self.assertEqual(self.candidate['status'],'SOURCE_CANDIDATE_NOT_COMPILED_OR_ACTIVATED')
  for r in self.candidate['records']:
   self.assertLess(r['candidate_budget']['exact_candidate_visits_without_cell_sampling'],300000)
   self.assertEqual(r['preserve_sampling_pitch_m'],.5);self.assertTrue(r['preserve_pose'])
if __name__=='__main__':unittest.main(verbosity=2)
