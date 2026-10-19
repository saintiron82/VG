"""Read-only assertions and meaningful low-cell/pose negative controls."""
import unittest
from .author_roofs import *
from .audit_roofs import envelope,overlaps
class RoofTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=load(HERE/'pack.json');cls.proof=load(HERE/'proof.json');cls.scene=load(BASE);cls.audit=load(HERE/'audit.json');cls.original={p['id']:p for p in cls.scene['common_instances']}
 def test_base_and_all_bound_sources(self):
  self.assertEqual(sha(BASE),BASE_SHA)
  for a in self.proof['assets']:
   for k in ['source_master','source_render','source_compiled','new_master','new_render','new_compiled']:
    self.assertEqual(ref(ROOT/a[k]['path']),a[k])
  for r in self.proof['common_sources']:self.assertEqual(ref(ROOT/r['path']),r)
 def test_all_thirty_ids_poses_palettes_and_proofs(self):
  rows=self.pack['replace_instances'];self.assertEqual(len(rows),30);self.assertEqual({r['id']for r in rows},{p['id']for p in self.scene['common_instances']if relevant(p)})
  for r in rows:
   p=self.original[r['id']];self.assertEqual(r['expected_asset_key'],p['asset_key']);self.assertEqual(r['expected_position_m'],p['position_m']);self.assertEqual(r['expected_yaw_rad'],p['yaw_rad']);self.assertEqual(r['palette_override'],p['palette_override']);self.assertEqual(r['palette_id'],p['palette_id']);self.assertEqual(r['proof_sha256'],sha(ROOT/r['proof_path']));self.assertEqual(p['scale'],[1,1,1])
  self.assertFalse(self.pack['add_instances']);self.assertFalse(self.pack['remove_instance_ids'])
 def test_native_cache_payload_and_common_face_bijection(self):
  for a in self.proof['assets']:
   n=load(ROOT/a['new_compiled']['path']);r=load(ROOT/a['new_render']['path']);self.assertTrue(n['valid']);self.assertEqual(core.digest(n['cells']),n['payload_hash']);self.assertEqual(render_data.make_render_data(n),r);self.assertEqual(face_bijection(n,r),a['face_bijection'])
 def test_protected_cells_and_physical_entrances(self):
  for a in self.proof['assets']:
   o=load(ROOT/a['source_compiled']['path']);n=load(ROOT/a['new_compiled']['path']);self.assertEqual(low(o),low(n));self.assertEqual(o['materials'],n['materials']);self.assertEqual(canonical(low(n)),a['new_low_cells_sha256'])
   for m in a['module_records']:self.assertEqual(m['original_entrances'],m['new_entrances'])
 def test_low_cell_negative_control(self):
  a=self.proof['assets'][0];o=load(ROOT/a['source_compiled']['path']);n=load(ROOT/a['new_compiled']['path']);n['cells'].remove(next(r for r in n['cells']if r[1]*n['pitch']<CUTOFF));self.assertNotEqual(low(o),low(n))
 def test_shared_architecture_and_native_envelopes(self):
  self.assertEqual(len(self.pack['common_assets']),8);self.assertGreaterEqual(min(self.proof['shared_variant_counts'].values()),2)
  for a in self.proof['assets']:
   before=a['old_bounds'];after=a['new_bounds'];self.assertLessEqual(after['max'][1],before['max'][1]);self.assertEqual(after['min'],before['min'])
   for k in (0,2):self.assertEqual(after['max'][k],before['max'][k])
   o=load(ROOT/a['source_compiled']['path']);n=load(ROOT/a['new_compiled']['path']);self.assertEqual({(r[0],r[2])for r in o['cells']},{(r[0],r[2])for r in n['cells']});self.assertNotEqual(o['payload_hash'],n['payload_hash'])
 def test_adjacent_and_route_differential_audit(self):
  self.assertEqual(self.audit['pack'],ref(HERE/'pack.json'));self.assertEqual(self.audit['proof'],ref(HERE/'proof.json'));self.assertFalse(self.audit['introduced_envelope_intersections']);self.assertFalse(self.audit['excluded_instances_without_render_bounds']);self.assertGreater(self.audit['compared_adjacent_pairs'],150000)
  for r in self.audit['original_and_unchanged_route_envelope_contacts']:self.assertEqual(r['original_envelope_overlap_m2'],r['new_envelope_overlap_m2'])
  self.assertEqual(self.audit['protected_runtime_contracts_sha256'],canonical(self.scene['collision_contracts']));self.assertEqual(self.audit['protected_surfaces_sha256'],canonical(self.scene['surfaces']))
 def test_pose_and_envelope_negative_controls(self):
  r=self.pack['replace_instances'][0];p=self.original[r['id']];bad=copy.deepcopy(p);bad['position_m'][0]+=.5;self.assertNotEqual(bad['position_m'],r['expected_position_m']);self.assertNotEqual(envelope(self.pack['common_assets'][r['asset_key']],bad)[0],envelope(self.pack['common_assets'][r['asset_key']],p)[0])
 def test_comparison_sheet_and_camera_scope(self):
  self.assertTrue((HERE/'native_roof_comparison.png').stat().st_size>50000);self.assertEqual(len(self.pack['inspection_cameras']),2);self.assertTrue(all('ortho_size_m'in c for c in self.pack['inspection_cameras'].values()))
if __name__=='__main__':unittest.main(verbosity=2)
