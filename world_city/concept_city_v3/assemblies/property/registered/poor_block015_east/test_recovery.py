import copy,json,unittest
from pathlib import Path
from .author_density import HERE,ROOT,PLAN,ref
from .route_repair_01.author import apply,digest
from voxel_character.common import core

def read(p):return json.loads((HERE/p).read_text())
class RecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=read('candidate.json');cls.p=read('resolved_placements.json');cls.e=read('route_repair_01/effective_placements.json');cls.a=read('route_repair_01/route_addendum.json');cls.c=read('route_repair_01/checks.json')
 def test_recovered_counts(self):
  self.assertEqual((len(self.p['replaced_placement_ids']),len(self.p['component_placements']),len(self.p['placements']),len(self.p['access_proposals'])),(37,28,10,65));self.assertAlmostEqual(self.p['summary']['after_body_area_m2'],4115);self.assertAlmostEqual(self.p['summary']['after_outer_union_area_m2'],4684)
 def test_lost_bytes_not_claimed_restored(self):
  self.assertFalse(self.p['recovery_provenance']['prior_bytes_restored']);self.assertNotEqual(ref(HERE/'resolved_placements.json')['sha256'],self.p['recovery_provenance']['lost_prior_pack_sha256'])
 def test_hashes(self):
  self.assertEqual(self.a['base_pack'],ref(HERE/'resolved_placements.json'));self.assertEqual(self.a['source_plan'],ref(PLAN));self.assertEqual(self.c['effective_pack'],ref(HERE/'route_repair_01/effective_placements.json'))
  for a in self.p['assets'].values():
   for k in ('master','render'):self.assertEqual(ref(ROOT/a[k+'_path'])['sha256'],a[k+'_sha256'])
 def test_fixed_caps_and_common_results(self):
  p=read('compile_preflight.json');r=read('compile_report.json');self.assertEqual(p['total_predicted_candidate_cells'],359328);self.assertEqual(p['largest_predicted_candidate_cells'],61318);self.assertEqual(p['per_asset_candidate_cap'],65000);self.assertEqual(p['per_asset_output_cap'],60000);self.assertEqual(r['new_union_assets'],7);self.assertEqual(r['total_unique_quads'],12006)
 def test_native_source_operations_preserved(self):
  for key,a in self.p['assets'].items():
   if not key.startswith('attached_native_row_'):continue
   m=json.loads((ROOT/a['master_path']).read_text());cs={c['id']:c for c in m['components']};ins={i['id']:i for i in m['instances']};count=0
   for j,e in enumerate(m['metadata']['native_modules']):
    src=json.loads((ROOT/self.d['assets'][e['asset_key']]['master_path']).read_text());self.assertEqual(m['materials'],src['materials']);prefix=f'H{j:02}_'
    for c in src['components']:q=copy.deepcopy(c);q['id']=prefix+c['id'];self.assertEqual(cs[q['id']],q)
    sis={i['id']:i for i in src['instances']};poses={}
    def local(k):
     if k not in poses:
      q=sis[k];t=core.transform(q.get('transform'));poses[k]=core.compose(local(q['parent']),t) if q.get('parent') else t
     return poses[k]
    for q in src['instances']:
     expected=core.compose({'basis':core.IDENTITY,'translation':e['translation']},local(q['id']));self.assertEqual(ins[prefix+q['id']]['transform'],expected);self.assertEqual(ins[prefix+q['id']]['component'],prefix+q['component']);count+=1
   self.assertEqual(count,len(m['instances']))
 def test_face_bijections(self):
  p=read('actual_geometry_proof.json');self.assertTrue(p['all_face_bijections_pass']);self.assertEqual(p['internal_render_unit_faces'],0);self.assertEqual(p['missing_render_unit_faces'],0)
 def test_actual_doors_and_foundations(self):
  for d in self.p['access_proposals']:self.assertTrue(d['actual_cached_threshold_evidence']);self.assertEqual(d['actual_door_xyz_m'][1],2.5)
  self.assertEqual(sum(len(x['terrain_exclusion_regions_xz_m']) for x in self.p['ownership_masks']),59)
 def test_overlay_only_one_route(self):
  self.assertEqual(apply(self.p,self.a),self.e);self.assertEqual(len(self.a['route_replacements']),1)
  for k in self.a['unchanged_fields']:self.assertEqual(self.p[k],self.e[k])
  with self.assertRaises(AssertionError):apply(self.e,self.a)
 def test_full_width_finite_water_and_native_check(self):
  self.assertEqual(self.c['issues'],[]);self.assertEqual(self.c['counts']['routes'],80);self.assertEqual(self.c['counts']['rounded_joins'],14);self.assertAlmostEqual(self.c['old_water_area_m2'],1.2380150251666409,places=6);self.assertAlmostEqual(self.c['new_route_length_m'],8.01112666630761)
 def test_ground_area_accounting(self):
  g=read('owned_grounds.json');self.assertLess(abs(g['area_accounting_delta_m2']),1e-4);self.assertEqual(len(g['grounds']),13);self.assertEqual(len(g['paths']),13);self.assertFalse(g['unwalkable_narrow_margin_ids']);self.assertGreater(self.c['retained_water_ground_area_m2'],36)
 def test_roof_coverage(self):
  r=read('geometry_review.json');self.assertTrue(r['valid_horizontal_source']);self.assertAlmostEqual(r['projection']['after']['roof_union_inside_block_ratio'],.43104385936850187)
if __name__=='__main__':unittest.main()
