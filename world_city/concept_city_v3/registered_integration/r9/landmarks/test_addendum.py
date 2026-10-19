"""Focused integration/geometry invariants; not a substitute for runtime review."""
import copy, importlib.util, json, math, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r9_landmark_author',HERE/'build_addendum.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
from voxel_character.common import coordinate_planes,core,render_data

class AddendumTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.pack=json.loads((HERE/'pack.json').read_text());cls.ledger=json.loads((HERE/'attachment_ledger.json').read_text())['rows'];cls.ctx=json.loads((HERE/'base_instance_context.json').read_text());cls.native={p['id']:p for p in cls.ctx['common_instances']};cls.p={p['id']:p for p in cls.pack['add_instances']}
 def test_sealed_base_unchanged(self):self.assertEqual(b.sha(b.BASE),b.BASE_SHA)
 def test_contract_and_no_retirements(self):
  self.assertEqual(self.pack['schema'],'riverstone.city.visual_addendum.v1');self.assertEqual(self.pack['base_scene_sha256'],b.BASE_SHA);self.assertEqual(self.pack['remove_instance_ids'],[])
  self.assertEqual(len(self.p),len(self.pack['add_instances']));self.assertFalse(self.p.keys()&self.native.keys());self.assertEqual(len(self.ledger),len(self.p))
 def test_unit_scale_finite_transforms_and_new_paths(self):
  for p in self.p.values():
   self.assertEqual(p['scale'],[1,1,1]);self.assertTrue(all(math.isfinite(x)for x in p['position_m']+[p['yaw_rad']]));self.assertIn(p['asset_key'],self.pack['common_assets'])
  for a in self.pack['common_assets'].values():
   for kind in ['master','render']:
    path=b.ROOT/a[kind+'_path'];self.assertTrue(path.is_relative_to(HERE));self.assertEqual(b.sha(path),a[kind+'_sha256'])
 def test_native_parent_sources_and_caches_untouched(self):
  for parent in {r['native_parent_id']for r in self.ledger}:
   a=self.ctx['common_assets'][self.native[parent]['asset_key']]
   for kind in ['master','render']:self.assertEqual(b.sha(b.ROOT/a[kind+'_path']),a[kind+'_sha256'])
 def test_all_attachments_leave_ground_player_band_empty(self):
  for row in self.ledger:
   self.assertGreaterEqual(row['minimum_clearance_above_native_ground_m'],5.5-1e-8)
   self.assertGreater(row['world_bounds_m']['min'][1],row['native_ground_datum_m']+3)
   self.assertFalse(row['ground_route_encroachment'])
 def test_actual_cached_bboxes_overlap_declared_native_support(self):
  for row in self.ledger:
   p=self.native[row['native_parent_id']];a=self.ctx['common_assets'][p['asset_key']];local=json.loads((b.ROOT/a['render_path']).read_text())['bounds'];parent=b.bounds_world(local,p);child=row['world_bounds_m']
   for axis in range(3):self.assertLessEqual(max(child['min'][axis],parent['min'][axis]),min(child['max'][axis],parent['max'][axis])+1e-8,(row['id'],axis))
 def test_cathedral_four_faces_and_native_spire_preserved(self):
  faces=[p for p in self.p.values() if p['asset_key']=='r9_cathedral_gothic_face'];self.assertEqual(len(faces),4)
  yaw=sorted(round((p['yaw_rad']-faces[0]['yaw_rad'])%(2*math.pi),6)for p in faces)
  self.assertEqual(yaw,[0,round(math.pi/2,6),round(math.pi,6),round(math.pi*1.5,6)])
  for p in faces:self.assertEqual(p['position_m'][1],42)
  self.assertNotIn('cathedral_registered:single_bell_tower',self.pack['remove_instance_ids'])
 def test_common_independent_recompile_is_deterministic(self):
  for key,a in self.pack['common_assets'].items():
   m=json.loads((b.ROOT/a['master_path']).read_text());rd=json.loads((b.ROOT/a['render_path']).read_text());saved=core.digest(m)
   c=coordinate_planes.compile_master(m,{'pitch':.5},max_candidate_cells=250000,max_output_cells=100000)
   self.assertTrue(c['valid']);self.assertEqual(saved,core.digest(m));self.assertEqual(render_data.make_render_data(c),rd);self.assertLess(c['candidate_cells'],15000)
 def test_city_watch_turret_roots_are_on_native_walls(self):
  rows=[r for r in self.ledger if ':WATCH:' in r['id']];self.assertEqual(len(rows),18)
  for r in rows:self.assertEqual(r['native_parent_asset'],'registered_curtain16_h14');self.assertEqual(r['local_attachment_offset_m'],[0,10.5,0])

if __name__=='__main__':unittest.main(verbosity=2)
