import copy, unittest
import author_facility_roofs as a

class RoofContracts(unittest.TestCase):
 def source(self):
  m=a.new_master('fixture',{'slate':'646f73','slate_dark':'4a565c'})
  m['components']=[a.comp('roof',[a.shared.prism('slope',[[0,1.4],[2,3.4],[2,4],[0,2]],-1,1,'slate')])]
  m['instances']=[{'id':'roof','component':'roof'}]
  return m
 def asset(self):return {'master_path':'fixture.json','master_sha256':'fixture','render_path':'fixture.render.json','render_sha256':'fixture','pitch_m':.5,'palette_id_counts':{'wood_brown':1},'slots':{'slate':{'operation_role_counts':{'roof_covering':1}}}}
 def describe(self,m):return a.describe('fixture',self.asset(),m)
 def test_exact_parallel_plane(self):
  d=self.describe(self.source());self.assertEqual(len(d['planes']),1);self.assertEqual(d['planes'][0]['slope'],1);self.assertEqual(d['suppression']['safe_material_groups_when_full_matching_near_resource_ready'],['slate'])
 def test_disjoint_entry_cut_proven(self):
  m=self.source();m['assembly_cuts']=[{'id':'entry','shape':{'kind':'box','min':[-1,-2,-1],'max':[1,0,1]},'selector':{}}]
  d=self.describe(m);self.assertEqual(len(d['planes']),1);self.assertEqual(d['cut_exclusion_proofs'][0]['exclusion'],'strictly_disjoint_transformed_aabb')
 def test_intersecting_cut_blocks(self):
  m=self.source();m['assembly_cuts']=[{'id':'roof_hole','shape':{'kind':'box','min':[0,1,-1],'max':[1,4,1]},'selector':{}}]
  d=self.describe(m);self.assertFalse(d['planes']);self.assertFalse(d['suppression']['safe_material_groups_when_full_matching_near_resource_ready']);self.assertTrue(d['pending'])
 def test_selector_exclusion_not_guessed(self):
  m=self.source();m['assembly_cuts']=[{'id':'other_component','shape':{'kind':'box','min':[0,1,-1],'max':[1,4,1]},'selector':{'component':'wall'}}]
  d=self.describe(m);self.assertEqual(len(d['planes']),1);self.assertEqual(d['cut_exclusion_proofs'][0]['exclusion'],'selector_excludes_roof_operation')
 def test_mixed_nonroof_cap_blocks_whole_group(self):
  m=self.source();m['components'].append(a.comp('window_cap',[a.shared.box('nonroof_cap',[0,0,0],[1,1,1],'slate')]))
  m['instances'].append({'id':'cap','component':'window_cap'});d=self.describe(m)
  self.assertEqual(len(d['planes']),1);self.assertFalse(d['suppression']['safe_material_groups_when_full_matching_near_resource_ready']);self.assertEqual(d['suppression']['unsafe_material_groups'][0]['unhandled_operation_refs'],[('window_cap','nonroof_cap')])
 def test_proper_rotated_operation_preserved(self):
  m=self.source();t={'basis':[[0,0,-1],[0,1,0],[1,0,0]],'translation':[5,2,-3]};m['components'][0]['operations'][0]['transform']=t
  d=self.describe(m);self.assertEqual(d['planes'][0]['operation_transform'],t)
  n=a.make_near(d,m,a.read(a.RULES));a.core.validate_master(n,.05)
 def test_scaling_rejected(self):
  m=self.source();m['instances'][0]['transform']={'basis':[[2,0,0],[0,1,0],[0,0,1]]}
  with self.assertRaises(ValueError):self.describe(m)
 def test_wood_is_distinct_geometry_same_palette(self):
  m=self.source();d=self.describe(m);r=a.read(a.RULES);tile=a.make_near(d,m,r,'roof_tile');wood=a.make_near(d,m,r,'wood_shingle')
  self.assertNotEqual(tile['metadata']['counts'],wood['metadata']['counts']);self.assertEqual(tile['materials'],wood['materials']);self.assertFalse(wood['metadata']['runtime_activation'])
 def test_conical_shape_pending(self):
  m=self.source();m['components'][0]['operations'][0]['shape']={'kind':'lathe','profile':[[0,0],[1,0],[0,3]]};d=self.describe(m)
  self.assertFalse(d['planes']);self.assertTrue(d['pending'])

if __name__=='__main__':unittest.main()
