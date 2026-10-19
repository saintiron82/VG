"""Source/cache, finite ownership and real approach tests for three draw facilities."""
import copy,json,math,unittest
from .build import HERE,CITY,ROOT,ref
from voxel_character.common import coordinate_planes,render_data
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import author as a,side_clearance
from world_city.concept_city_v3.registered_integration.r6 import apply_packs,merge_patches
from world_city.concept_city_v3.registered_integration.r8 import runtime_contracts
from world_city.runtime_city.checks import placement as g
class ServiceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.scene=a.load_scene();cls.pack=json.loads((HERE/'resolved_placements.json').read_text());cls.loc=json.loads((HERE/'locations.json').read_text());cls.patch=json.loads((HERE/'surface_patch.json').read_text());cls.ext=json.loads((HERE/'water_extension.json').read_text());cls.asset=cls.pack['assets'][0];cls.master=json.loads((ROOT/cls.asset['source']['path']).read_text());cls.compiled=coordinate_planes.compile_master(cls.master,{'pitch':.2},max_candidate_cells=400000,max_output_cells=120000);cls.render=render_data.make_render_data(cls.compiled);cls.cells={tuple(c[:3])for c in cls.compiled['cells']}
 def test_native_replay_hashes_and_budget(self):
  self.assertTrue(self.compiled['valid']);self.assertEqual(self.render,json.loads((ROOT/self.asset['cache']['path']).read_text()));self.assertEqual(ref(ROOT/self.asset['source']['path']),self.asset['source']);self.assertEqual(ref(ROOT/self.asset['cache']['path']),self.asset['cache']);self.assertEqual(len(self.pack['placements']),3);self.assertLess(len(self.cells),120000);self.assertEqual(self.render['bounds'],{'min':[-2.,-2.6,-2.],'max':[2.,4.2,2.]})
 def test_three_named_public_continuations(self):
  proof=json.loads((HERE/'public_continuation.json').read_text());expected={'CATHEDRAL_DRAW':'CATHEDRAL_APPROACH','MONASTERY_DRAW':'MARKET_CONTOUR','CASTLE_DRAW':'CASTLE_APPROACH'}
  for row in proof['fixtures']:
   self.assertEqual(row['status'],'PASS');self.assertEqual(row['named_public_road_ids'],[expected[row['fixture_id']]]);self.assertGreater(len(row['continuation_triangle_ids']),1);self.assertTrue(row['named_landing_mask_ids']);self.assertEqual(row['source_profile_sha256'],a.sha(CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json'))
 def test_full_width_source_footing_and_access(self):
  windows=[r['footprint_xz_m']for r in self.loc['drawhouses']]+[p for r in self.loc['drawhouses']for p in r['walk_polygons_xz_m']];ix=a.TriangleIndex(self.scene,windows);owners=[]
  for r in self.loc['drawhouses']:
   ground=a.audit_polygon(ix,r['footprint_xz_m'],r['position_m'][1]);self.assertTrue(ground['passes_existing_surface']);self.assertAlmostEqual(ground['area_m2'],16.)
   for p in r['walk_polygons_xz_m']:
    self.assertLess(g.polygon_area(g.convex_intersection(p,r['footprint_xz_m'])),1e-7)
    audit=a.audit_polygon(ix,p,r['position_m'][1]);self.assertTrue(audit['passes_existing_surface']);owners.extend(dict(id=r['id'],polygon_xz_m=rr['polygon_xz_m'],plane_y_xz_m=rr['plane_y_xz_m'])for rr in audit['source_pieces'])
  self.assertEqual(side_clearance.SideIndex(self.scene,windows).audit(owners)['contacts'],[])
 def test_platform_cardinal_docks_do_not_hit_posts(self):
  for r in self.loc['drawhouses']:
   x,y,z=r['position_m'];axis=r['access_side_local_xz'];self.assertIn(axis,[[1,0],[-1,0],[0,1],[0,-1]])
   for part in self.render['groups']:
    for q in part['quads']:
     qq=[[v[0]+x,v[1]+y,v[2]+z]for v in q]
     for walk in r['walk_polygons_xz_m']:
      clipped=side_clearance.clip_clear_volume(qq,walk,[0,0,y]);self.assertLess(side_clearance.area3d(clipped),1e-7)
 def test_closed_bed_open_shaft_and_nonopaque_water(self):
  def occupied(p):return tuple(math.floor(v/.2+1e-7)for v in p)in self.cells
  self.assertTrue(occupied([0,-2.5,0]));self.assertFalse(occupied([0,-2.,0]));self.assertFalse(any('water'in g['material']for g in self.render['groups']))
  for p in self.pack['placements']:
   self.assertEqual(p['scale'],[1,1,1]);self.assertEqual(p['water_head_y_m'],p['position_m'][1]-2.)
  for v in self.ext['append_vertices_xyz_m']:
   owner=min(self.pack['placements'],key=lambda p:math.dist([v[0],v[2]],[p['position_m'][0],p['position_m'][2]]));local=[v[k]-owner['position_m'][k]for k in range(3)];self.assertFalse(occupied(local));self.assertAlmostEqual(local[1],-2.)
 def test_finite_patch_binds_unchanged_original_water(self):
  merge_patches.merge([self.patch],a.SCENE_SHA256);merge_patches.validate_against_scene(self.scene,self.patch)
  self.assertNotIn('water',self.patch['source_surface_hashes']);self.assertNotIn('water',self.patch['appended_surfaces']);self.assertNotIn('bank',self.patch['source_surface_hashes'])
  for edit in self.patch['surface_edits']:
   original=self.scene['surfaces'][edit['material']][edit['triangle_index']*3:edit['triangle_index']*3+3];self.assertEqual(a.canonical_sha(original),edit['source_triangle_sha256'])
   for tri in edit['replacement_triangles_xyz_m']:self.assertGreater(a.normal_y(tri),0.)
  placed,_=apply_packs.apply_pack(self.scene,self.pack,'registered_services_r01');wet=runtime_contracts.append_water_extensions(placed,self.scene,[self.ext]);old=self.scene['surfaces']['water'];self.assertEqual(wet['surfaces']['water'][:len(old)],old);self.assertEqual(len(wet['surfaces']['water'])-len(old),3*14*3)
 def test_existing_native_masks_stay_clear(self):
  projection=json.loads((CITY/'registered_integration/r8/coverage_plan/native_projection.json').read_text());rows=[];ix=g._SpatialIndex(8)
  for r in projection['instances']:
   for p in r['native_owner_parts_xz_m']:ix.add(len(rows),p);rows.append((r['id'],p))
  for r in self.loc['drawhouses']:
   for p in [r['footprint_xz_m']]+r['walk_polygons_xz_m']:
    for i in ix.candidates(p):self.assertLess(g.polygon_area(g.convex_intersection(p,rows[i][1])),1e-7,(r['id'],rows[i][0]))
if __name__=='__main__':unittest.main(verbosity=2)
