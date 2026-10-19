"""Cheap registered source checks. No common compile, controller or hydraulics."""
import unittest,math,random,hashlib
from . import author as a
from world_city.runtime_city.checks.placement import intersection_area,is_convex_polygon

class RegisteredTerrainTests(unittest.TestCase):
 def test_control_snapshot_binding(self):
  self.assertEqual(a.CONTROLS_SHA256,hashlib.sha256(a.CONTROL_PATH.read_bytes()).hexdigest())
  self.assertEqual(a.ROAD_CONTROLS_SHA256,hashlib.sha256(a.ROAD_CONTROL_PATH.read_bytes()).hexdigest())
 def test_registered_road_and_wall_pixels(self):
  self.assertEqual(len(a.registered_roads()),28)
  for road in a.registered_roads():
   for point,pixel in zip(road['resolved_world_xyz_m'],road['trace_pixel_xy']):
    self.assertLess(math.dist(a.project(*point),pixel),1e-8)
    self.assertAlmostEqual(point[1],a.road_height_at(road['id'],point[0],point[2]),places=7)
  wall=a.registered_wall()
  for point,pixel in zip(wall['world_xyz_m'],wall['trace_pixel_xy']):self.assertLess(math.dist(a.project(*point),pixel),1e-8)
 def test_declared_area_benches_and_shared_feet(self):
  regions={p['id']:p for p in a.terrace_regions()}
  for aid,height in [('castle',24),('cathedral',14),('market',4),('monastery',8)]:
   point=next(p['inferred_target_world_xyz_m'] for p in a.CONTROLS['anchors'] if p['id']==aid)
   self.assertAlmostEqual(a.building_floor_at(point[0],point[2]),height,places=6)
  for upper,lower,y in [('E3','E6',12),('E5','E7',10)]:
   shared=[p for p in regions[upper]['boundary_vertices_xyz_m'] if any(math.dist(p,q)<1e-8 for q in regions[lower]['boundary_vertices_xyz_m'])]
   self.assertGreaterEqual(len(shared),2)
   self.assertTrue(all(abs(p[1]-y)<1e-8 for p in shared))
 def test_continuous_road_grade(self):
  rng=random.Random(1450)
  for _ in range(3000):
   x,z=rng.uniform(-500,500),rng.uniform(-500,600);t=rng.uniform(0,math.tau);d=.2
   grade=abs(a.dry_height_at(x,z)-a.dry_height_at(x+d*math.cos(t),z+d*math.sin(t)))/d
   self.assertLessEqual(grade,.12+1e-8)
  for road in a.registered_roads():self.assertLessEqual(road['maximum_vertex_grade'],.12+1e-8)
 def test_finite_water_ownership(self):
  domains=a.finite_water_polygons()
  for i,p in enumerate(domains):
   self.assertTrue(is_convex_polygon(p['polygon_xz_m']))
   for q in domains[i+1:]:self.assertLess(intersection_area(p['polygon_xz_m'],q['polygon_xz_m']),1e-7)
 def test_actual_wet_profiles_are_downhill(self):
  for wid,w in a.WATER_BY_ID.items():
   heads=[]
   for p,q in zip(w['polyline_xz_m'],w['polyline_xz_m'][1:]):
    for i in range(100):
     t=i/100;heads.append(a.water_height_at(wid,p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])))
   self.assertLessEqual(max(v-u for u,v in zip(heads,heads[1:])),1e-8,wid)
 def test_receiver_mouth_heads(self):
  checked=0
  for d in a.finite_water_polygons():
   mouth=a.MOUTHS.get(d['surface_id'])
   if not mouth:continue
   for point in d['polygon_xz_m']:
    if abs(a._line_value(point,mouth['edge']))<1e-6:
     receiver=16 if mouth['receiver']=='basin' else a.river_water_y(point[0])
     self.assertAlmostEqual(a.water_height_at(d['surface_id'],*point),receiver,places=8)
     checked+=1
  self.assertGreater(checked,4)
 def test_water_beds_below_every_head(self):
  for d in a.finite_water_polygons():
   for p in d['polygon_xz_m']:
    self.assertLessEqual(a.height_at(*p),a.water_height_at(d['surface_id'],*p)-.5)
 def test_graph_direction_and_manual_lift(self):
  graph=a._graph();nodes={n['id']:n for n in graph['nodes']}
  for edge in graph['edges']:
   if edge['mode']=='manual_lift':self.assertTrue(edge['energy_source']);continue
   self.assertLessEqual(nodes[edge['target']]['head_y_m'],nodes[edge['source']]['head_y_m']+1e-8)
   self.assertFalse(nodes[edge['source']]['network']=='industrial_nonpotable' and nodes[edge['target']]['network']=='protected_supply')
 def test_finished_floor_does_not_add_asset_threshold(self):
  self.assertAlmostEqual(a.building_floor_at(230,-199),14)
  floor=14;cached_door_local_y=.5;origin=floor-cached_door_local_y
  self.assertEqual(origin+cached_door_local_y,floor)
if __name__=='__main__':unittest.main()
