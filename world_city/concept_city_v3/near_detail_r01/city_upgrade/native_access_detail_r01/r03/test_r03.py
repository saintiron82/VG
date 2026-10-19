"""Fail-closed fixtures plus exact source-plane/rotated-placement proofs."""
from pathlib import Path
import copy,itertools,json,math,sys,unittest
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import author_r03 as a

class SourceGuard(unittest.TestCase):
 def test_all_24_corner_orders_only_4_upward_perimeters(self):
  q=[[0,0,0],[0,0,1],[1,0,1],[1,0,0]];passed=[];rejected=[]
  for indices in itertools.permutations(range(4)):
   try:a.top_rectangle([q[i] for i in indices]);passed.append(indices)
   except ValueError as e:rejected.append({'order':indices,'reason':str(e)})
  self.assertEqual(set(passed),{tuple(range(i,4))+tuple(range(i)) for i in range(4)});self.assertEqual(len(rejected),20)
  a.save(HERE/'quad_permutation_fixtures.json',{'accepted':passed,'rejected':rejected})
 def test_malformed_and_nonfinite_quads_fail(self):
  q=[[0,0,0],[0,0,1],[1,0,1],[1,0,0]];cases={'bow_tie':[q[i] for i in [0,1,3,2]],'reverse':q[::-1],'duplicate':[q[0],q[1],q[1],q[3]],'three_points':q[:3],'empty':[],'bad_point':[[0,0],*q[1:]]}
  for label,v in [('nan',float('nan')),('inf',float('inf')),('bool',True),('string','0'),('nonplanar',.0125),('nonmicrogrid',.001)]:
   c=copy.deepcopy(q);c[2][1 if label=='nonplanar' else 0]=v;cases[label]=c
  for label,c in cases.items():
   with self.subTest(label=label),self.assertRaises(ValueError):a.top_rectangle(c)
 def test_grid_rejects_real_subcell_gap_accepts_binary_representation(self):
  self.assertEqual(a.strict_grid(10.200000000000001),816)
  for v in [10.20000001,10.20001,.001,float('nan'),True]:
   with self.assertRaises(ValueError):a.strict_grid(v)
 def test_negative_native_grid_face(self):
  q=[[-1.2,1.95,4.8],[-1.2,1.95,6.3],[1.2,1.95,6.3],[1.2,1.95,4.8]]
  self.assertEqual(a.top_rectangle(q),[-96,-504,96,-384])

class ExactUnion(unittest.TestCase):
 def test_two_box_seam(self):
  p=a.union_proof([-96,-504,96,-384],[[-120,-408,120,-384],[-120,-504,120,-408]])
  self.assertTrue(p['supported']);self.assertEqual(p['uncovered_area_cells2'],0);self.assertEqual(p['subject_area_cells2'],23040)
 def test_overlap_does_not_double_count_or_hide_hole(self):
  p=a.union_proof([0,0,80,80],[[0,0,50,80],[30,0,80,80]])
  self.assertTrue(p['supported']);self.assertEqual(p['source_owner_overlap_cells2'],1600)
  q=a.union_proof([0,0,80,80],[[0,0,39,80],[0,0,39,80],[40,0,80,80]])
  self.assertFalse(q['supported']);self.assertEqual(q['uncovered_area_cells2'],80)
 def test_multiple_box_seams_negative_coordinates(self):
  boxes=[[-160,-80,-100,0],[-100,-80,-40,0],[-40,-80,0,0]]
  self.assertTrue(a.union_proof([-160,-80,0,0],boxes)['supported'])
 def test_finite_hole_not_enclosing_aabb(self):
  p=a.union_proof([0,0,80,80],[[0,0,80,39],[0,40,80,80],[0,39,39,40],[40,39,80,40]])
  self.assertFalse(p['supported']);self.assertEqual(p['uncovered_area_cells2'],1)
 def test_wrong_level_and_semantics_do_not_combine(self):
  boxes=[{'semantic_key':['a','bearing','stone','solid'],'top_y_integer_cells':0,'rect_uv_integer_cells':[0,0,40,80]}, {'semantic_key':['a','bearing','stone','rail'],'top_y_integer_cells':0,'rect_uv_integer_cells':[40,0,80,80]}]
  with self.assertRaises(ValueError):a.ownership([0,0,80,80],0,boxes)
  boxes[1]['semantic_key']=boxes[0]['semantic_key'];boxes[1]['top_y_integer_cells']=1
  with self.assertRaises(ValueError):a.ownership([0,0,80,80],0,boxes)
 def test_source_cuts_and_rotated_components_fail_closed(self):
  policy=a.read(a.N/'source_policy.json');old=a.read(a.BASE_PLAN);asset=old['assets'][0];master=a.read(a.R/asset['source_master_path']);rule=policy['assets'][asset['asset_key']]
  bad=copy.deepcopy(master);bad['assembly_cuts']=[{'id':'test_cut'}]
  with self.assertRaises(ValueError):a.source_boxes(bad,rule)
  original=a.previous.source_parts
  try:
   def rotated(m):
    for inst,op,tr in original(m):
     tr=copy.deepcopy(tr);tr['basis']=[[0,0,1],[0,1,0],[-1,0,0]];yield inst,op,tr
   a.previous.source_parts=rotated
   with self.assertRaises(ValueError):a.source_boxes(master,rule)
  finally:a.previous.source_parts=original

class CurrentSource(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan,cls.changes=a.plan()
 def test_only_two_source_faces_added_and_old_placements_identical(self):
  self.assertEqual([(v['faces']-v['previous_faces'],v['placements']-v['previous_placements']) for v in self.changes],[(2,24),(0,0)])
  self.assertTrue(all(c['previous_placements_sha256']==c['preserved_placements_sha256'] for c in self.changes))
  for c in self.changes:
   for f in c['new_faces']:
    self.assertEqual(len(f['operation_owners']),2);self.assertEqual(f['semantic_owner_union']['uncovered_area_cells2'],0)
 def test_every_patch_stays_inside_actual_face_and_semantic_union(self):
  for asset in self.plan['assets']:
   faces={(f['group_index'],f['quad_index']):f for f in asset['faces']}
   for p in asset['placements']:
    r=[a.strict_grid(v) for v in p['bounds_uv_m']];f=faces[tuple(p['source_face_ref'])]
    self.assertTrue(a.union_proof(r,[f['rect_uv_integer_cells']])['supported'])
    self.assertTrue(a.union_proof(r,[b['rect_uv_integer_cells'] for b in f['operation_owners']])['supported'])
 def test_all_patch_corners_under_arbitrary_rigid_instance_yaw(self):
  # Transform already-proved source patches and source polygons together via the
  # existing shared placement helper. No rotated component-box approximation.
  tested=0
  for asset in self.plan['assets']:
   faces={(f['group_index'],f['quad_index']):f for f in asset['faces']}
   for p in asset['placements']:
    f=faces[tuple(p['source_face_ref'])];b=p['bounds_uv_m'];corners=[[x,f['plane_y_m'],-v] for x,v in [(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]]
    for yaw in [0,.37,-2.194336547087899,math.pi/2,math.pi]:
     pos=[-123.5,8.1,-291.75]
     for c in corners:
      world=a.polygons.transform_point_m(c,pos,yaw);local=a.polygons.inverse_transform_point_m(world,pos,yaw)
      self.assertLess(max(abs(local[i]-c[i]) for i in range(3)),1e-12);tested+=1
     world_subject=[[a.polygons.transform_point_m(c,pos,yaw)[i] for i in (0,2)] for c in corners]
     world_face=[[a.polygons.transform_point_m(c,pos,yaw)[i] for i in (0,2)] for c in f['quad']]
     self.assertLessEqual(a.polygons.uncovered_area_by_union(world_subject,[world_face],0),1e-10)
  a.save(HERE/'rotated_placement_proof.json',{'patches':226,'yaw_variants':5,'transformed_corners_checked':tested,'exact_local_uncovered_area_cells2':0,'rigid_roundtrip_max_bound_m':1e-12,'common_world_union_numeric_area_bound_m2':1e-10,'world_geometry_generated':False})

if __name__=='__main__':unittest.main(verbosity=2)
