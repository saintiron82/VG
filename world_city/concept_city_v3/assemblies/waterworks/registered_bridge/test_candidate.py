"""Source geometry, datum and ownership checks. Never invokes a compiler."""
import hashlib,json,math,unittest
from .author import HERE,ROOT,PLAN,BASE,TERRAIN,WIDTH,CART,WALK,PARAPET,Axis,bounds,overlaps,surface_y,sha,cambered_height_at
from voxel_character.common import core
from world_city.runtime_city.checks import placement as geo
from world_city.concept_city_v3.registered_topography import author as terrain

def read(path):return json.loads(path.read_text())

class BridgeCandidateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=read(HERE/'candidate.json');cls.plan=read(PLAN)
 def test_bound_inputs_unchanged(self):
  for key in ('source_plan','terrain_author','registration_controls','source_master','author'):
   r=self.p[key];self.assertEqual(sha(ROOT/r['path']),r['sha256'])
  self.assertEqual(self.p['source_plan']['sha256'],'685592393dd5b3bffa189d497db8bff14ba4d893d5d81089a66427bd5a6b588c')
 def test_native_master_source_schema(self):
  for r in self.p['sources']:
   path=ROOT/r['path'];self.assertEqual(sha(path),r['sha256']);core.validate_master(read(path),.2)
  m=read(HERE/'masters/stone_arch_bay_16x14.json');ops=[o for c in m['components'] for o in c['operations']];body=next(o for o in ops if o['id']=='stone_bay');cut=next(o for o in ops if o['id']=='barrel_opening')
  self.assertEqual(body['shape']['min'],[-8,-5.5,-7.]);self.assertEqual(body['shape']['max'],[8,0,7.]);self.assertEqual(cut['action'],'cut');self.assertEqual((cut['shape']['z_min'],cut['shape']['z_max']),(-7.01,7.01))
  base=read(BASE);original=next(o for c in base['components'] for o in c['operations'] if o['id']=='barrel_opening');self.assertEqual(cut['shape']['polygon'],original['shape']['polygon'])
 def test_native_rigid_repeat_no_scale(self):
  self.assertEqual(len(self.p['bays']),9)
  for b in self.p['bays']:
   self.assertEqual(b['scale_xyz'],[1,1,1]);self.assertAlmostEqual(math.dist(*b['endpoints_xz_m']),16,places=8)
   basis=b['transform']['basis'];cols=list(zip(*basis))
   for i,c in enumerate(cols):
    self.assertAlmostEqual(sum(x*x for x in c),1,places=10)
    for d in cols[:i]:self.assertAlmostEqual(sum(x*y for x,y in zip(c,d)),0,places=10)
 def test_width_and_gate_reconciliation(self):
  w=self.p['width_reconciliation'];self.assertEqual(w['original_road_width_m'],7);self.assertEqual(w['original_bridge_record_width_m'],8)
  self.assertEqual(CART+2*WALK+2*PARAPET,WIDTH);self.assertEqual(w['width_at_gate_m'],7)
  self.assertGreater(w['north_taper_begins_station_m'],w['gate_station_m']);self.assertLess(w['width_at_gate_m'],w['gate_opening_width_m'])
  for b in self.p['bays']:
   self.assertAlmostEqual(geo.polygon_area(b['footprint_xz_m']),16*14,places=8);self.assertAlmostEqual(geo.polygon_area(b['cart_lane_polygon_xz_m']),16*8,places=8)
 def test_exact_road_datum_and_bounded_interpolation(self):
  axis=Axis(next(r for r in self.plan["roads"] if r["id"]=="MAIN_BRIDGE"))
  for b in self.p['bays']:
   for p in b['deck_profile']:self.assertAlmostEqual(p['deck_y_m'],cambered_height_at(*p['xz_m'],axis,self.p['camber_overlay']),places=10)
   for a,c in zip(b['deck_profile'],b['deck_profile'][1:]):self.assertLessEqual(abs(c['deck_y_m']-a['deck_y_m'])/math.dist(a['xz_m'],c['xz_m']),.100000001)
  self.assertLessEqual(self.p['checks']['maximum_half_sample_deck_error_m'],.0125)
 def test_cap_is_explicit_profile_not_flat_control_labels(self):
  self.assertEqual(self.p['source_four_control_level_labels_m'],[2.2,2.4,2.4,2.2]);self.assertEqual(self.p['source_resolved_deck_range_y_m'][0],1.)
  for b in self.p['bays']:
   m=read(ROOT/b['cap_source']['path']);op=next(o for c in m['components'] for o in c['operations'] if o['id']=='profiled_deck_spandrel');top=list(reversed(op['shape']['polygon'][2:]));self.assertEqual(len(top),65)
   for v,p in zip(top,b['deck_profile']):self.assertAlmostEqual(v[1]+b['arch_top_y_m'],p['deck_y_m'],places=10)
 def test_cart_lane_and_walks_open_above_finished_deck(self):
  for b in self.p['bays']:
   cap=read(ROOT/b['cap_source']['path'])
   for c in cap['components']:
    for op in c['operations']:
     if c['id']=='parapets':self.assertGreaterEqual(min(abs(op['shape']['z_min']),abs(op['shape']['z_max'])),6.4-1e-9)
 def test_disjoint_owned_polygons_and_profile_vertices(self):
  for label in ('deck_regions','approach_regions'):
   rs=self.p[label]
   for i,r in enumerate(rs):
    self.assertGreater(r['area_m2'],0);self.assertEqual(len(r['polygon_xz_m']),len(r['vertex_y_m']))
    for p,y in zip(r['polygon_xz_m'],r['vertex_y_m']):self.assertAlmostEqual(y,surface_y(r['surface_profile'],p),places=9)
    for q in rs[:i]:
     if overlaps(bounds(r['polygon_xz_m']),bounds(q['polygon_xz_m'])):self.assertLess(geo.polygon_area(geo.convex_intersection(r['polygon_xz_m'],q['polygon_xz_m'])),1e-6)
 def test_complete_full_width_wet_crossing(self):
  road=next(r for r in self.plan['roads'] if r['id']=='MAIN_BRIDGE');axis=Axis(road);owned=self.p['deck_regions'];wet_count=0
  for i in range(int(axis.length*2)+1):
   s=i*.5;p=axis.at(s);a=axis.at(max(0,s-.1));b=axis.at(min(axis.length,s+.1));t=[(b[j]-a[j])/math.dist(a,b) for j in (0,1)]
   for offset in (-3.5,0,3.5):
    q=[p[0]-t[1]*offset,p[1]+t[0]*offset]
    if any(w['surface_id']=='MAIN_RIVER' for w in terrain.water_samples_at(*q)):
     wet_count+=1;self.assertTrue(any(geo.point_in_convex_polygon(q,r['polygon_xz_m'],1e-7) for r in owned),q)
  self.assertGreater(wet_count,600)
  # The new full 14 m deck follows its declared native-chord axis. Its <=0.49 px
  # axis refinement is explicit; the original 7 m road above remains covered.
  for bay in self.p["bays"]:
   a,b=bay["endpoints_xz_m"];t=[(b[j]-a[j])/16 for j in (0,1)]
   for i in range(1,32):
    p=[a[j]+t[j]*i*.5 for j in (0,1)]
    for off in (-6.999,-4,0,4,6.999):
     q=[p[0]-t[1]*off,p[1]+t[0]*off]
     self.assertTrue(any(geo.point_in_convex_polygon(q,r["polygon_xz_m"],1e-7) for r in owned),q)
 def test_dry_abutments_and_bed_reaching_foundations(self):
  self.assertEqual(len(self.p['abutments']),2)
  for a in self.p['abutments']:self.assertLess(a['water_overlap_area_m2'],1e-7)
  for b in self.p['bays']:
   for s in b['foundation_samples']:
    self.assertAlmostEqual(s['bearing_ground_y_m'],terrain.height_at(*s['xz_m']),places=9);self.assertGreaterEqual(s['embed_m'],.5)
  self.assertTrue(self.p['checks']['abutments_dry'])
 def test_image_axis_and_adjacency(self):
  self.assertLess(self.p['checks']['maximum_centerline_registration_change_px'],.5)
  self.assertEqual(self.p['trace_pixel_xy'],[[950,810],[958,854],[971,904],[983,969]])
  self.assertFalse(self.p['checks']['new_building_conflicts'])
 def test_limits_not_promoted_to_placement_or_navigation(self):
  self.assertEqual(self.p['compile_invocations'],0);self.assertEqual(self.p['actual_scene_placements'],0)
  self.assertIn('source_only',self.p['status']);self.assertGreaterEqual(self.p['navigation_channel']['normal_water_clearance_min_m'],3)
  self.assertTrue(any('masted' in s for s in self.p['remaining_limits']))
  self.assertLessEqual(self.p['checks']['maximum_approach_grade'],.12000001)

 def test_camber_endpoints_lift_and_original_evidence(self):
  axis=Axis(next(r for r in self.plan['roads'] if r['id']=='MAIN_BRIDGE'));c=self.p['camber_overlay']
  for s in (0,c['start_station_m'],c['end_station_m'],axis.length):
   p=axis.at(s);self.assertAlmostEqual(cambered_height_at(*p,axis,c),terrain.road_height_at('MAIN_BRIDGE',*p),places=8)
  old=self.p['original_low_field_candidate'];self.assertEqual(sha(ROOT/old['path']),old['sha256'])
  self.assertLessEqual(self.p['checks']['maximum_authored_deck_grade'],.10000001)
  self.assertLess(self.p['checks']['maximum_camber_image_delta_px'],4.2)
  self.assertLessEqual(self.p['checks']['maximum_camber_lift_m'],3.01)
 def test_navigation_channel_actual_full_width_clearance(self):
  b=next(b for b in self.p['bays'] if b['id']==self.p['navigation_channel']['bay_id']);t=b['transform'];B=t['basis'];C=t['translation']
  for x in (-3,-2.5,-2,-1,0,1,2,2.5,3):
   soffit=(-.65-.075*abs(x)) if abs(x)<=2 else (-.8-.25*(abs(x)-2))
   for z in (-7,-3.5,0,3.5,7):
    wx=C[0]+B[0][0]*x+B[0][2]*z;wz=C[2]+B[2][0]*x+B[2][2]*z
    self.assertTrue(any(w['surface_id']=='MAIN_RIVER' for w in terrain.water_samples_at(wx,wz)))
    self.assertGreaterEqual(C[1]+soffit-terrain.river_water_y(wx),3)
  self.assertGreater(self.p['checks']['maximum_pier_extension_m'],0)

if __name__=='__main__':unittest.main(verbosity=2)
