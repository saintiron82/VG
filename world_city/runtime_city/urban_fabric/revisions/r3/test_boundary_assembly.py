import copy,json,unittest
from .boundary_assembly import *
from .author_overlay import apply_revision_overlay

class BoundaryAssemblyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=json.loads((HERE/'generated/overlay.json').read_text());cls.scene=json.loads((ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json').read_text());base=json.loads((ROOT/'world_city/runtime_city/revisions/r3/urban_fabric.access_repaired.json').read_text());cls.access=apply_revision_overlay(base,cls.data)['access_reservations']
 def sample(self,m):return compile_master(m,{'pitch':.5},max_candidate_cells=250000,max_output_cells=100000)
 def test_all_three_union_masters_clear_and_connected(self):
  for p in self.data['property_records']:
   m=make_boundary_assembly(self.data,p['id']);r=self.sample(m);a=audit_sampled_boundary(m,r,self.scene,self.access)
   self.assertTrue(a['valid'],a['errors']);self.assertEqual(a['expected_wall_arcs'],3);self.assertEqual(len(a['sampled_3d_connected_solid_sizes']),3);self.assertTrue(a['one_cell_owner']);self.assertTrue(a['single_solid_part']);self.assertTrue(a['single_instance']);self.assertLess(a['candidate_cells'],30000)
 def test_short_source_module_provenance_complete(self):
  for p in self.data['property_records']:
   m=make_boundary_assembly(self.data,p['id']);meta=m['metadata'];self.assertEqual(set(meta['source_placement_ids']),set(p['wall_placement_ids']));self.assertEqual({q['source_placement_id'] for q in meta['source_operation_ledger']},set(p['wall_placement_ids']))
   self.assertTrue(meta['clearance_cut_ledger']);self.assertTrue(all(c['source_placement_id'] in p['wall_placement_ids'] for c in meta['clearance_cut_ledger']))
   self.assertEqual(m,make_boundary_assembly(self.data,p['id']))
 def test_projected_short_supports_remain_nonflat_and_connected(self):
  pid='UF_ESTATE_03';ids=set(next(p for p in self.data['property_records'] if p['id']==pid)['wall_placement_ids']);heights={p['id']:7.3+.12*(p['position_m'][0]+165) for p in self.data['placements'] if p['id'] in ids};m=make_boundary_assembly(self.data,pid,heights);r=self.sample(m);a=audit_sampled_boundary(m,r,self.scene,self.access)
  self.assertTrue(a['valid'],a['errors']);self.assertTrue(m['metadata']['terrain_y_preprojected']);self.assertGreater(max(heights.values())-min(heights.values()),3)
  source={p['id']:p for p in self.data['placements']}
  for q in m['metadata']['source_operation_ledger']:
   p=source[q['source_placement_id']];self.assertEqual(q['world_position_m'][::2],p['position_m'][::2]);self.assertEqual(q['world_position_m'][1],heights[p['id']])
 def test_gate_plug_is_rejected(self):
  m=make_boundary_assembly(self.data,'UF_ESTATE_01');g=m['metadata']['gates'][0];pos=m['metadata']['placement_position_m'];x,z=g['center_xz_m'];m['components'][0]['operations'].append({'id':'negative_test_gate_plug','part':'boundary_solid','action':'paint','material':'stone','shape':{'kind':'box','min':[x-pos[0]-.5,0,z-pos[2]-.5],'max':[x-pos[0]+.5,2,z-pos[2]+.5]}});a=audit_sampled_boundary(m,self.sample(m),self.scene,self.access)
  self.assertFalse(a['valid']);self.assertIn('sampled_gate_full_width_obstruction',{e['check'] for e in a['errors']})
 def test_unknown_projection_id_rejected(self):
  with self.assertRaises(ValueError):make_boundary_assembly(self.data,'UF_ESTATE_01',{'missing_id':0})
if __name__=='__main__':unittest.main()
