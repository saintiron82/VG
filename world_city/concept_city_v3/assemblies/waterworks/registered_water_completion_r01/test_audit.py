"""Integrity gates for the actual-city water audit and explicit limits."""
import unittest
from .audit import *
from world_city.concept_city_v3.registered_integration.r8.runtime_contracts import append_water_extensions
class AuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.scene=a.load_scene()
 def test_all_actual_beds_and_native_asset_bindings(self):
  r=json.loads((HERE/'actual_geometry_audit.json').read_text());self.assertEqual(len(r['water_triangles']),143)
  for x in r['water_triangles']:
   self.assertLess(x['bed_missing_area_m2'],1e-7);j=x['water_triangle_index'];self.assertEqual(a.canonical_sha(self.scene['surfaces']['water'][3*j:3*j+3]),x['source_triangle_sha256'])
  for x in r['native_assets']:
   for key in['source','cache']:self.assertEqual(ref(ROOT/x[key]['path']),x[key])
 def test_actual_canal_banks_continuous(self):
  r=json.loads((HERE/'bank_continuity.json').read_text());self.assertEqual(len(r['banks']),613);self.assertEqual(len(r['zero_length_contract_bank_indices']),26)
  for x in r['banks']:
   self.assertLess(x['missing_area_m2'],1e-7)
   for owner in x['actual_bank_owners']:
    j=owner['triangle_index'];self.assertEqual(a.canonical_sha(self.scene['surfaces']['bank'][3*j:3*j+3]),owner['source_triangle_sha256'])
 def test_harbor_graph_and_static_vessel_domains(self):
  r=json.loads((HERE/'harbor_interfaces.json').read_text());ids={n['id']for n in r['nodes']};seen={next(iter(ids))}
  while True:
   nxt=seen|{e['b']for e in r['edges']if e['a']in seen}|{e['a']for e in r['edges']if e['b']in seen}
   if nxt==seen:break
   seen=nxt
  self.assertEqual(seen,ids);self.assertEqual(len(ids),7);self.assertEqual(len(r['vessels']),4)
  for v in r['vessels']:self.assertLess(v['missing_water_below_projection_m2'],1e-7)
  b=json.loads((HERE/'main_bridge_interfaces.json').read_text());self.assertLess(b['with_actual_moving_leaves_gap_m2'],1e-7);self.assertGreater(b['static_only_gap_m2'],98.);self.assertLess(b['static_only_gap_m2'],98.01)
 def test_head_graph_limits_and_castle_independence(self):
  r=json.loads((HERE/'head_graph_and_asset_associations.json').read_text());self.assertEqual(len(r['graph_nodes']),26);self.assertFalse(r['issues']);self.assertTrue(all(r['industrial_nodes_reach_outfall'].values()));self.assertEqual(r['node_source_roots']['CASTLE_DRAW'],['CASTLE_CISTERN']);self.assertNotIn('RAW_SPRING',r['node_source_roots']['CASTLE_DRAW']);self.assertEqual(len(r['warnings']),1);self.assertAlmostEqual(r['warnings'][0]['maximum_delta_m'],.015136756930591577)
  castle=next(x for x in r['asset_associations']if x.get('node_id')=='CASTLE_DRAW');self.assertEqual(castle['actual_position_m'][1],24);self.assertEqual(castle['local_stored_head_y_m'],22)
 def test_stored_water_extension_and_old_seals(self):
  e=json.loads((HERE/'water_extension.json').read_text());out=append_water_extensions(self.scene,self.scene,[e]);old=self.scene['surfaces']['water'];self.assertEqual(out['surfaces']['water'][:len(old)],old);self.assertEqual(e['owner_ids'],['RESERVOIR_DRAWPOINT']);self.assertFalse(e['collision']);self.assertTrue(all(v[1]==15.5 for v in e['append_vertices_xyz_m']))
  for dirname in['registered_services_r01','registered_mill_r01']:
   root=HERE.parent/dirname;manifest=json.loads((root/'freeze_manifest.json').read_text())
   for path,h in manifest['owned_files'].items():self.assertEqual(a.sha(root/path),h,(dirname,path))
if __name__=='__main__':unittest.main(verbosity=2)
