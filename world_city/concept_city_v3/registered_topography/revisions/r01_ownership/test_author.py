import math,random,unittest
from . import author as a
from world_city.runtime_city.checks import placement as g

class OwnershipTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  a.snapshot_check();a._source_owners()
  regions={r['id']:r for r in a.base.terrace_regions()}
  points=[regions[k]['polygon_xz_m'][0] for k in ['CASTLE','TRAIN','MONASTERY','E3','E6','E7']]
  points += [p['actual_body_footprint_xz_m'][0] for p in a.ORDINARY['placements'][::90]]
  points += [a.base.WATER_BY_ID['SPRING_VISIBLE']['polyline_xz_m'][2],a.base.WATER_BY_ID['CRAFT_CANAL_VISIBLE']['polyline_xz_m'][2]]
  cls.patches=[]
  for p in points:
   x,z=4*math.floor(p[0]/4),4*math.floor(p[1]/4);b=[x-4,z-4,x+4,z+4]
   cls.patches.append((b,a.surface_domains(b)))
 def test_frozen_snapshot(self):a.snapshot_check()
 def test_complete_disjoint_convex_partition(self):
  for b,rs in self.patches:
   self.assertAlmostEqual(sum(g.polygon_area(r['polygon_xz_m']) for r in rs),(b[2]-b[0])*(b[3]-b[1]),places=6)
   for i,r in enumerate(rs):
    p=r['polygon_xz_m'];self.assertTrue(g.is_convex_polygon(p),(r['owner_id'],p))
    for q in rs[:i]:self.assertLess(g.polygon_area(g.convex_intersection(p,q['polygon_xz_m'])),1e-7)
 def test_dry_domain_excludes_water(self):
  wet=a.base.finite_water_polygons()
  for _,rs in self.patches:
   for r in rs:
    if not r['render_land']:continue
    for w in wet:
     if a.base._overlap(a.base._bounds(r['polygon_xz_m']),a.base._bounds(w['polygon_xz_m'])):
      self.assertLess(g.polygon_area(g.convex_intersection(r['polygon_xz_m'],w['polygon_xz_m'])),1e-7)
 def test_owner_specific_bench_height(self):
  count=0
  for _,rs in self.patches:
   for r in rs:
    if r['kind'] in ('terrace','door_landing','building_body_hole'):
     count+=1
     for p in r['polygon_xz_m']:self.assertEqual(a.surface_height_at(r,*p),r['floor_y_m'])
  self.assertGreater(count,10)
 def test_road_surface_unchanged_and_shoulders_protected(self):
  for r in a.base.REGISTERED_PLAN['roads']:
   ps=r['polyline_xz_m'];p=ps[len(ps)//2]
   owner=a.owner_at(*p)
   if owner['kind']=='water_hole':continue
   self.assertIn(owner['kind'],('road','road_shoulder'))
   self.assertEqual(a.surface_height_at(owner,*p),a.base.dry_height_at(*p))
 def test_retaining_faces_have_both_real_owner_heights(self):
  count=0
  for b,rs in self.patches:
   for edge in a.retaining_interfaces(b,rs):
    count+=1
    self.assertEqual(len(edge['vertices_xyz_m']),4)
    self.assertGreater(max(abs(edge['left_y_m'][i]-edge['right_y_m'][i]) for i in(0,1)),1e-6)
  self.assertGreater(count,10)
 def test_adjacent_tile_boundary_crossings_conform(self):
  # No corner is discarded where an owner partition reaches a neighboring tile.
  p=a.ORDINARY['placements'][0]['actual_body_footprint_xz_m'][0];x=4*math.floor(p[0]/4);z=4*math.floor(p[1]/4)
  left=a.surface_domains([x-4,z,x,z+4]);right=a.surface_domains([x,z,x+4,z+4])
  def points(rs):return sorted(set(round(q[1],6) for r in rs for q in r['polygon_xz_m'] if abs(q[0]-x)<1e-7))
  for zz in sorted(set(points(left)+points(right))):
   l=[r for r in left if g.point_in_convex_polygon([x,zz],r['polygon_xz_m'],1e-6)]
   r=[r for r in right if g.point_in_convex_polygon([x,zz],r['polygon_xz_m'],1e-6)]
   for ll in l:
    for rr in r:
     if ll['owner_id']==rr['owner_id']:
      self.assertAlmostEqual(a.surface_height_at(ll,x,zz),a.surface_height_at(rr,x,zz),places=9)
 def test_finished_floor_not_origin_plus_half_metre(self):
  for p in a.ORDINARY['placements']:
   self.assertAlmostEqual(p['position_m'][1]+p['cached_primary_door_local_y_m'],p['pad_floor_y_m'])
 def test_water_network_terminal_reaches_receiver(self):
  c=a.build_contract();self.assertTrue(any(e['source']=='EAST_CHANNEL_VISIBLE:8' and e['target']=='RIVER_OUTFALL' for e in c['water_graph']['edges']))
 def test_actual_bodies_clear_traffic_and_own_support_aprons(self):
  owners=a._source_owners();index=g._SpatialIndex(32);lanes=[]
  for o in owners:
   if o['kind'] in ('road','water_hole'):index.add(len(lanes),o['polygon_xz_m']);lanes.append(o)
  for body in a.ORDINARY['placements']:
   poly=body['actual_body_footprint_xz_m']
   for i in index.candidates(poly):self.assertLess(g.polygon_area(g.convex_intersection(poly,lanes[i]['polygon_xz_m'])),1e-6)
  for id in ['B_REG_0524','B_REG_0525']:
   body=next(p for p in a.ORDINARY['placements'] if p['id']==id)
   self.assertEqual(a.owner_at(*a.centroid(body['actual_body_footprint_xz_m']))['owner_id'],id+':BODY')
 def test_query_is_bounded(self):
  with self.assertRaises(ValueError):a.surface_domains([0,0,33,4])
if __name__=='__main__':unittest.main()
