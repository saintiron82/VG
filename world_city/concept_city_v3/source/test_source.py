"""Fast source-schema and geometry contracts; independent audit owns full collision QA."""
import json,unittest,math
from pathlib import Path
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.source.block_geometry import triangulate,faces
from world_city.concept_city_v3.source.control_streets import ROADS
from world_city.concept_city_v3.source.author import BOUNDARY
HERE=Path(__file__).parent
class SourceTests(unittest.TestCase):
 def setUp(self):self.p=json.loads((HERE/'plan.json').read_text())
 def test_triangles_conserve_concave_area(self):
  p=[[0,0],[5,0],[5,2],[2,2],[2,5],[0,5]];self.assertAlmostEqual(sum(g.polygon_area(t) for t in triangulate(p)),g.polygon_area(p),places=8)
 def test_ids_unique(self):
  for k in ('buildings','plots','paths','roads','blocks','gates','bridges'):
   ids=[v['id'] for v in self.p[k]];self.assertEqual(len(ids),len(set(ids)),k)
 def test_planar_blocks(self):
  for b in self.p['blocks']:
   self.assertAlmostEqual(sum(g.polygon_area(t) for t in b['triangulated_polygon_xz_m']),g.polygon_area(b['polygon_xz_m']),places=5)
 def test_recipe_envelopes(self):
  self.assertEqual(len([r for r in self.p['property_recipe_proxy_report'] if r['plot_id'].startswith('P_NOBLE')]),7)
  self.assertTrue(all(r['checks_valid'] for r in self.p['property_recipe_proxy_report']))
 def test_landmark_contract(self):
  self.assertEqual(len(self.p['landmark_components']),7)
  suppressed=set(self.p['landmark_component_suppressed_building_ids'])
  self.assertIn('B_CATHEDRAL_TOWER_E',suppressed)
  for grp in self.p['landmark_components']:
   self.assertTrue(set(grp['replaces_source_building_ids'])<=suppressed)
   for m in grp['masses']:self.assertEqual(len(m['position_local_xyz_m']),3);self.assertTrue(all(v>0 for v in m['size_xyz_m']))
 def test_finite_water(self):
  w=self.p['water_reservations'];self.assertEqual(w['service_canal_polyline_xz_m'][0][1],420);self.assertEqual(w['service_canal_polyline_xz_m'][-1][1],420);self.assertEqual(w['spring_feeder_polyline_xz_m'][-1],[0,-358])
 def test_density_is_measured(self):
  self.assertTrue(all('density_metrics' in b for b in self.p['blocks']))
  self.assertGreater(self.p['residual_ledger']['residual_before_ground_program_m2'],0)
if __name__=='__main__':unittest.main()
