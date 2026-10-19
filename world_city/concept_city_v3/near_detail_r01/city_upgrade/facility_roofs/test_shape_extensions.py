import copy,math,unittest
import author_facility_roofs as a
import finish_roofs as f
import extend_roof_shapes as x
import select_variants as variants
class ShapeExtensionContracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rules=a.read(x.RULES);cls.bundle=f.layers.load_master(f.OUT/'shape_support_descriptors.v2.json.gz')['assets']
 def source(self,key):
  d=self.bundle[key];return d,a.read(a.ROOT/d['source_master_path'])
 def hip(self):
  d,s=self.source('registered_castle_rear_square_tower');c=next(c for c in s['components'] if c['id']=='roof');return c['operations'][0],c['operations'][1:]
 def test_actual_hip_source_immutable(self):
  op,cuts=self.hip();before=copy.deepcopy((op,cuts));new,r=x.hip_detail(op,cuts,self.rules['shape_types']['solid_square_hip'],.2);self.assertEqual((op,cuts),before);self.assertTrue(all(o['action']=='cut' for o in new));self.assertEqual(r['parameters']['apex_y_m'],64)
 def test_hip_requires_exact_orthogonal_original_cuts(self):
  op,cuts=self.hip();cuts[0]['shape']['z_max']+=.001
  with self.assertRaises(ValueError):x.hip_parameters(op,cuts)
 def test_non_square_hip_is_rejected(self):
  op,cuts=self.hip();op['shape']['z_max']-=.1
  with self.assertRaises(ValueError):x.hip_parameters(op,cuts)
 def test_all_four_hip_cap_frames_face_outward(self):
  op,cuts=self.hip();new,r=x.hip_detail(op,cuts,self.rules['shape_types']['solid_square_hip'],.2);caps=[o for o in new if o['metadata']['detail_role']=='segmented_dihedral_hip_cap'];self.assertTrue(caps)
  for q in caps:
   t=q['transform'];self.assertGreater(t['basis'][1][1],0);p=t['translation'];self.assertAlmostEqual(p[1],64-(11/7)*max(abs(p[0]),abs(p[2])),places=10)
 def test_hip_flatten_preserves_unmodified_source_cut_metadata(self):
  d,s=self.source('registered_castle_rear_square_tower');before=copy.deepcopy(s);m,_,proof=x.build_one(d['asset_key'],d,s,'roof_tile',self.rules);self.assertEqual(s,before);self.assertEqual(m['components'][0]['metadata']['source_cuts'],s['components'][1]['operations'][1:] if s['components'][1]['id']=='roof' else next(c for c in s['components'] if c['id']=='roof')['operations'][1:]);self.assertTrue(proof[0]['subset_holds_for_continuous_shapes_and_every_sampling_pitch'])
 def test_cone_uses_curved_headlaps_and_original_profile(self):
  d,s=self.source('cathedral_bell_tower_128m_r02');op=next(o for c in s['components'] for o in c['operations'] if o['id']=='bell_tower_spire');before=copy.deepcopy(op);new,r=x.cone_detail(op,self.rules['shape_types']['conical_spire'],.2);self.assertEqual(op,before);self.assertEqual(r['parameters']['original_lathe_profile'],op['shape']['profile']);self.assertTrue(any(q['shape']['kind']=='lathe' for q in new));self.assertTrue(all(q['action']=='cut' for q in new));self.assertLess(r['cap_starts_y_m'],128)
 def test_unsupported_spire_profile_rejected(self):
  op={'shape':{'kind':'lathe','profile':[[1,0],[.2,4],[0,3],[.8,0]]}}
  with self.assertRaises(ValueError):x.cone_parameters(op)
 def test_flat_depth_is_bounded_by_original_slab(self):
  op={'id':'slate_cap','part':'solid','shape':x.box([0,1,0],[.6,1.1,.6])};new,r=x.flat_detail(op,{},self.rules['shape_types']['flat_cover'],.2);self.assertLessEqual(r['parameters']['joint_depth_m'],.0500000001);self.assertTrue(all(q['action']=='cut' for q in new))
 def test_wood_shingles_use_different_geometry_parameters(self):
  base=self.rules['shape_types']['flat_cover'];wood={**base,**self.rules['covering_overrides']['wood_shingle']['flat_cover']};op={'id':'gallery_roof','part':'solid','shape':x.box([-2,1,-1],[2,1.4,1])};tile,_=x.flat_detail(op,{},base,.2);shingle,_=x.flat_detail(op,{},wood,.2);self.assertNotEqual(tile,shingle);self.assertLess(wood['tile_width_m'],base['tile_width_m']);self.assertGreater(wood['course_run_m'],base['course_run_m'])
 def test_flat_wood_detail_survives_five_centimetre_sampling(self):
  cfg={**self.rules['shape_types']['flat_cover'],**self.rules['covering_overrides']['wood_shingle']['flat_cover']};op={'id':'gallery_roof','part':'solid','action':'paint','material':'slate','shape':x.box([0,1,0],[1,1.4,1])};cuts,_=x.flat_detail(op,{},cfg,.2);m=a.new_master('flat_wood_fixture',{'slate':'646f73'});m['components']=[a.comp('roof',[op]+cuts)];m['instances']=[{'id':'roof','component':'roof'}];original=copy.deepcopy(m);original['components'][0]['operations']=[op];opts={'max_candidate_cells':150000,'max_output_cells':50000,'cell_bounds':{'min':[0,20,0],'max':[20,28,20]}};near=a.core.compile_master(m,{'pitch':.05},**opts);old=a.core.compile_master(original,{'pitch':.05},**opts);n={tuple(r[:3]) for r in near['cells']};o={tuple(r[:3]) for r in old['cells']};self.assertTrue(n);self.assertTrue(n<o)
 def test_generic_slate_policy_has_no_native_fallback(self):
  d,s=self.source('registered_castle_stable');covering,evidence=variants.native_semantics(d,s);self.assertIsNone(covering);self.assertEqual(evidence['reason'],'generic_slate_slots_require_missing_external_semantics')
 def test_port_original_semantics_selects_tile_without_rgb(self):
  d,s=self.source('registered_port_long_loading_shed');s['materials']={k:'ff00ff' for k in s['materials']};covering,evidence=variants.native_semantics(d,s);self.assertEqual(covering,'roof_tile');self.assertIn('source_roof_operation_provenance',evidence['basis'])
 def test_union_roof_family_is_explicit_not_rgb(self):
  key='registered_precinct_union_clergy_school_service_edge_repair_r01_principal_frame_r01_corner_repair_r01';d,s=self.source(key);covering,evidence=variants.native_semantics(d,s);self.assertEqual(covering,'roof_tile');self.assertTrue(all(v['roof_family'] in ['slate_gray','clay_red'] for v in evidence['component_rules']))
if __name__=='__main__':unittest.main()
