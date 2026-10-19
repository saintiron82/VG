"""Bounded source/ownership guards; no scene or capsule acceptance."""
import collections,json,math,unittest
from . import height_field as h,public_domain as domain
from ..r17_district_batches import author as a

class TestOuterSources(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.regions,cls.segments,cls.refs=h.fixed_sources();cls.outer=domain.outer_handoff();cls.domains=domain.records()
 def test_exact_outer_segment_coverage(self):
  for r in self.outer['segments']:
   if not r['id'].startswith('RETAINED_JUNCTION:'):continue
   rows=[s for s in self.segments if s['id']==r['id'] or s['id'].startswith(r['id']+':PUBLIC:')]
   self.assertTrue(rows,r['id']);expected=math.dist(*r['xyz_m']);actual=sum(math.dist(*s['xyz_m'])for s in rows)
   self.assertLess(abs(expected-actual),1e-8,r['id'])
 def test_all_extension_masks_identical(self):
  got=[{k:r[k]for k in q}for q in self.outer['junction_extension_masks']for r in self.domains if r['id']==q['id']]
  self.assertEqual(got,self.outer['junction_extension_masks'])
 def test_no_bad_overlap_or_cap_fixed(self):
  self.assertFalse(any(r['id'].startswith('RETAINED_ROAD:')or':CAP:'in r['id']for r in self.regions+self.segments))
 def test_b15_mixed_reference_contract(self):
  d=json.loads((a.CITY/'registered_topography/revisions/r17_district_batches/coherent_b15_r02/fixed_public_seams.json').read_bytes())
  hash_only=[p for r in d['roots']for p in r['retained_public_source_pieces']if'polygon_xz_m'not in p]
  self.assertTrue(hash_only)
  # Shared profiles outside the finite repair domain are deliberately not
  # promoted as unrelated road-height constraints.
  expected=[]
  for r in d['roots']:
   for j,p in enumerate(r['shared_profile_triangles']):
    if any(a.clip(p['polygon_xz_m'],q['polygon_xz_m'])for q in self.domains):expected.append(r['id']+':SHARED:'+str(j)+':PUBLIC:')
  for prefix in expected:self.assertTrue(any(r['id'].startswith(prefix)for r in self.regions),prefix)
  self.assertTrue(all(math.hypot(*r['plane_y_xz_m'][:2])<=.12+1e-8 for r in self.regions))
 def test_pending_common_not_promoted(self):
  self.assertEqual(len(self.outer['pending_common_native_interface']['jumps']),1)
  self.assertFalse(any(r['id'].startswith('R06_COMMON_NATIVE_ENTRY_PUBLIC_EDGE_R01')for r in self.regions+self.segments))
 def test_refs_current(self):
  for r in self.refs:self.assertEqual(a.sha(a.ROOT/r['path']),r['sha256'])
 def test_fixed_profile_report_bound(self):
  r=json.loads((h.HERE/'fixed_profile_review.json').read_bytes());self.assertEqual(r['source_refs'],self.refs);self.assertFalse(r['errors']);self.assertEqual(r['fixed_regions'],len(self.regions));self.assertEqual(r['fixed_segments'],len(self.segments))

if __name__=='__main__':unittest.main()
