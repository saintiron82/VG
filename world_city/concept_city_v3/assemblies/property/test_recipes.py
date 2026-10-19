"""Small source/real-sampler tests, deliberately no old-city scene or GUI."""
import copy,json,math,unittest
from .recipes import *
from voxel_character.common.coordinate_planes import compile_master

class PropertyRecipeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.recipes={f:build_property_recipe(example_plot(f)) for f in FAMILIES}
 def test_all_three_recipes_have_exact_door_routes(self):
  for f,r in self.recipes.items():self.assertTrue(r['checks']['valid'],r['checks']['errors']);self.assertEqual(r['checks']['building_doors'],r['checks']['routed_doors']);self.assertTrue(r['no_old_city_inputs'])
  self.assertEqual(self.recipes['poor_block']['metrics']['dwelling_units'],18)
 def test_social_geometry_differences(self):
  n,m,p=(self.recipes[f]['metrics'] for f in ('noble_estate','merchant_court','poor_block'))
  self.assertLess(n['building_coverage_fraction'],.22);self.assertGreater(p['building_coverage_fraction'],.45);self.assertGreater(m['building_coverage_fraction'],.38);self.assertGreater(n['garden_orchard_area_m2'],800);self.assertEqual(p['garden_orchard_area_m2'],0)
  for r in self.recipes.values():self.assertGreater(r['metrics']['court_area_m2'],100)
 def test_cache_identity_ignores_plot_id_world_pose_and_pad(self):
  for f,r in self.recipes.items():
   p=example_plot(f);p.update(id='ANOTHER_PLOT',origin_xz_m=[-200,80],yaw_rad=.71,pad_y_m=7);p['gate_position_xz_m']=world_point([0,p['depth_m']/2],p['origin_xz_m'],p['yaw_rad']);p['polygon_xz_m']=world_polygon(rect([0,0],p['width_m'],p['depth_m']),p['origin_xz_m'],p['yaw_rad']);s=build_property_recipe(p)
   self.assertEqual(r['cache_specs'],s['cache_specs']);self.assertTrue(s['checks']['valid']);self.assertTrue(all(q['position_m'][1]==7 for q in s['placements']))
 def test_three_noble_mainhouse_shapes_are_distinct(self):
  classes=set();cache={}
  for v in range(3):
   r=build_property_recipe(example_plot('noble_estate',v));self.assertTrue(r['checks']['valid']);main=next(p for p in r['placements'] if p['role']=='main_residence');classes.add(main['assembly_class']);cache.update(r['cache_specs'])
  self.assertEqual(classes,{'older_stone_manor','merchant_palazzo','timber_courtyard_house'});self.assertLessEqual(len(cache),11)
 def test_floor_ownership_is_explicit_and_collision_enabled(self):
  for r in self.recipes.values():
   self.assertTrue(r['surface_ownership']['exclusive']);self.assertTrue(r['surface_ownership']['city_terrain_must_exclude_this_footprint']);self.assertTrue(r['surface_ownership']['floor_collision_required']);p=next(p for p in r['placements'] if p['role']=='owned_surface');self.assertEqual(p['collision_policy'],'walkable_floor');self.assertTrue(p['collision_enabled'])
 def test_missing_floor_owner_is_rejected(self):
  r=copy.deepcopy(self.recipes['noble_estate']);r['surface_ownership']['exclusive']=False;self.assertIn('invalid_exclusive_floor_ownership',{e['check'] for e in validate_recipe(r)['errors']})
 def test_pose_change_without_clearance_update_rejected(self):
  r=copy.deepcopy(self.recipes['poor_block']);r['placements'][0]['local_position_m'][0]+=2;self.assertIn('stale_local_footprint',{e['check'] for e in validate_recipe(r)['errors']})
 def test_sampled_owned_floor_under_every_door_route(self):
  for r in self.recipes.values():
   floor=next(p for p in r['placements'] if p['role']=='owned_surface');c=compile_master(make_asset_master(r['cache_specs'][floor['asset_key']]),{'pitch':.5},max_candidate_cells=100000,max_output_cells=30000);cells={(p[0],p[2]) for p in c['cells']}
   for a in r['entrance_routes']:
    for start,end in zip(a['polyline_local_xz_m'],a['polyline_local_xz_m'][1:]):
     for j in range(1,10):
      t=j/10;x=start[0]+t*(end[0]-start[0]);z=start[1]+t*(end[1]-start[1]);self.assertIn((math.floor(x/.5),math.floor(z/.5)),cells,a['id'])
 def test_contradictory_gate_or_small_plot_rejected(self):
  p=example_plot('noble_estate');p['width_m']=40
  with self.assertRaises(ValueError):build_property_recipe(p)
  p=example_plot('poor_block');p['gate_position_xz_m']=[10,18]
  with self.assertRaises(ValueError):build_property_recipe(p)
 def test_intruding_prop_is_rejected(self):
  r=copy.deepcopy(self.recipes['poor_block']);well=next(p for p in r['placements'] if p['role']=='communal_well');h=next(p for p in r['placements'] if p['source_provider']=='ordinary_r2');well['footprint_local_xz_m']=copy.deepcopy(h['footprint_local_xz_m']);self.assertFalse(validate_recipe(r)['valid'])
 def test_missing_door_route_is_rejected(self):
  r=copy.deepcopy(self.recipes['poor_block']);r['entrance_routes'].pop();self.assertIn('missing_door_routes',{e['check'] for e in validate_recipe(r)['errors']})
 def test_real_common_sampler_one_estate_one_poor_block(self):
  reports=[]
  for f in ('noble_estate','poor_block'):
   r=self.recipes[f]
   for key,s in r['cache_specs'].items():
    pitch=resource_for(s)['pitch'];m=make_asset_master(s);c=compile_master(m,{'pitch':pitch},max_candidate_cells=300000,max_output_cells=100000);self.assertTrue(c['valid']);self.assertTrue(c['cells']);bounds,meta=describe_asset(s)
    lo=[min(row[a] for row in c['cells'])*pitch for a in range(3)];hi=[(max(row[a] for row in c['cells'])+1)*pitch for a in range(3)]
    for a in (0,2):self.assertGreaterEqual(lo[a]+1e-5,bounds['min'][a]);self.assertLessEqual(hi[a]-1e-5,bounds['max'][a])
    reports.append({'property_type':f,'asset_key':key,'provider':s['provider'],'role':s['params'].get('assembly_class',s['params'].get('kind')),'pitch_m':pitch,'valid':c['valid'],'occupied_cells':len(c['cells']),'candidate_cells':c['candidate_cells'],'sampled_bounds':{'min':lo,'max':hi},'payload_hash':c['payload_hash']})
  (HERE/'generated/sampling_report.json').write_text(json.dumps(reports,indent=2)+'\n')
 def test_actual_sampled_boundary_gates_and_connections(self):
  for family,r in self.recipes.items():
   p=next(p for p in r['placements'] if p['role']=='boundary');m=make_asset_master(r['cache_specs'][p['asset_key']]);c=compile_master(m,{'pitch':.5},max_candidate_cells=100000,max_output_cells=30000);self.assertEqual(len(m['components'][0]['parts']),1);self.assertEqual(len({tuple(q[:3]) for q in c['cells']}),len(c['cells']));points={(q[0],q[2]) for q in c['cells']}
   for x,z in points:
    poly=rect([(x+.5)*.5,(z+.5)*.5],.5,.5)
    for a in r['entrance_routes']:self.assertFalse(any(positive_area_overlap(poly,q,.002) for q in a['ribbon_polygons_local_xz_m']),a['id'])
    for h in r['placements']:
     if h['role'] not in ('boundary','owned_surface'):self.assertFalse(positive_area_overlap(poly,h['footprint_local_xz_m'],.002),h['id'])
   groups=[]
   while points:
    queue=[points.pop()];n=0
    while queue:
     x,z=queue.pop();n+=1
     for q in ((x+1,z),(x-1,z),(x,z+1),(x,z-1)):
      if q in points:points.remove(q);queue.append(q)
    groups.append(n)
   self.assertEqual(len(groups),2 if family=='noble_estate' else 1)
 def test_boundary_has_short_projection_supports(self):
  for r in self.recipes.values():
   p=next(p for p in r['placements'] if p['role']=='boundary');s=r['cache_specs'][p['asset_key']]['params']
   self.assertTrue(all(math.dist(q['a'],q['b'])<=6.0001 for q in s['segments']))
if __name__=='__main__':unittest.main()
