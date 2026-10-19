import unittest,json,math
from . import author as a,review as r
class Tests(unittest.TestCase):
 def test_original_pack(self):self.assertEqual(a.sha(a.PACK_PATH),'9eb840f6710d24c028e61f66718689a04db00290d094c878d9a5dab0fa5035b8')
 def test_source_removal_only(self):
  old=a.SOURCE_MASTER['components'][0]['operations'];m=json.loads((a.HERE/'sources/registered_training_r09_recovered_coarse.master.json').read_bytes());self.assertEqual(m['components'][0]['operations'],[x for x in old if not x['id'].startswith('r1_access_skin_')])
 def test_native_audit(self):
  d=json.loads((a.HERE/'native_audit.json').read_bytes());self.assertLess(d['source_coverage_gap_m2'],1e-7);self.assertLess(d['coarse_fine_top_overlap_m2'],1e-7);self.assertLessEqual(d['max_interior_riser_m'],.125);self.assertGreaterEqual(d['minimum_buried_overlap_m'],.25);self.assertNotIn(18.5,d['native_top_levels_m'])
 def test_fine_owners(self):
  cs=json.loads((a.HERE/'native_columns.json').read_bytes())['fine']
  for c in cs:
   p=c['polygon_xz_m'];x,z=[sum(q[k] for q in p)/4 for k in (0,1)];self.assertAlmostEqual(r.height_at(x,z),c['top_y_m'],places=8)
 def test_native_public(self):
  for f in r.DATA['actual_public_surface_overrides']:
   p=f['polygon_xz_m'];x,z=[sum(q[k] for q in p)/len(p) for k in (0,1)];self.assertAlmostEqual(r.height_at(x,z),f['actual_compiled_top_y_m'],places=8)
 def test_contract_inheritance(self):
  c=r.build_contract();self.assertEqual(len(c['water_surfaces']),6);self.assertEqual(len(r.finite_water_polygons()),80);self.assertEqual(len(c['ordinary_foundations']),616);self.assertIn('recovery_support',c)
 def test_partition(self):
  box=[-272,-155,-254,-149];rs=r.surface_domains(box,False);self.assertAlmostEqual(sum(a.geo.polygon_area(x['polygon_xz_m']) for x in rs),108,places=6);self.assertFalse(any(r.stale(x) for x in rs))
if __name__=='__main__':unittest.main()
