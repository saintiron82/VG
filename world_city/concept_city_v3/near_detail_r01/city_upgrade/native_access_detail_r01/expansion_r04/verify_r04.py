"""Independent actual-quad / source-owner / exact-cut / module-envelope proof.
All outputs remain inside expansion_r04; no physics, controller or source edits.
"""
from pathlib import Path
import copy,itertools,json,math,re,resource,struct,sys,time,unittest
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import author_r04 as b
b.limits();a=b.a

def overlap(rects):
 total=0
 for i,(r,y) in enumerate(rects):
  for s,z in rects[i+1:]:
   if y==z:total+=max(0,min(r[2],s[2])-max(r[0],s[0]))*max(0,min(r[3],s[3])-max(r[1],s[1]))
 return total

def module_proof(m,triangle_order):
 render=b.read(b.R/m['render_path']);assert b.sha(b.R/m['render_path'])==m['render_sha256'] and b.sha(b.R/m['master_path'])==m['master_sha256'];w=a.strict_grid(m['trim']['width_m']);h=a.strict_grid(m['trim']['height_m']);wrong=degenerate=triangles=0;quads=0
 for g in render['groups']:
  for q in g['quads']:
   quads+=1
   for p in q:
    # Common render uses origin + integer_cell * pitch. Recover that exact
    # expression rather than re-quantizing cancellation near the crop origin.
    cell=[round((p[i]-render['grid_origin'][i])/P) for i in range(3)]
    assert all(p[i]==render['grid_origin'][i]+cell[i]*P for i in range(3))
    v=[a.strict_grid(render['grid_origin'][i])+cell[i] for i in range(3)]
    assert 0<=v[0]<=w and 0<=v[1]<=h and -3<=v[2]<=0
    assert 0<=p[0]<=m['trim']['width_m'] and 0<=p[1]<=m['trim']['height_m']
   n=a.previous.cross([q[1][i]-q[0][i] for i in range(3)],[q[2][i]-q[0][i] for i in range(3)]);length=math.sqrt(sum(v*v for v in n));assert length>0
   if n[2]/length<-.999:continue # exact same existing common Patch rear-face omission
   for i in range(0,6,3):
    tri=[q[k] for k in triangle_order[i:i+3]];cross=a.previous.cross([tri[1][j]-tri[0][j] for j in range(3)],[tri[2][j]-tri[0][j] for j in range(3)]);dot=sum(x*y for x,y in zip(n,cross));triangles+=1;degenerate+=sum(x*x for x in cross)==0;wrong+=dot>=0
 assert quads==m['quads'] and wrong==0 and degenerate==0
 return {'id':m['id'],'triangles_after_common_rear_omission':triangles,'wrong_clockwise_winding':wrong,'degenerate':degenerate,'outside_trim_vertices':0,'additional_visual_offset_range_m':[0,.0375],'all_pass':True}

def run_geometry():
 start=time.perf_counter();p=b.read(b.PLAN);c=b.read(b.CAT);rep=b.read(H/'build_report.json');ledger=b.read(b.LEDGER);old=b.read(a.CAT);oldrows={m['id']:m for m in old['modules']};mods={m['id']:m for m in c['modules']};assert b.sha(b.PLAN)==c['source_plan_sha256'];assert all(b.sha(b.R/path)==s for path,s in rep['frozen_dependencies'].items())
 source=b.R/'world_city/concept_city_v3/playable_detail_r01/RenderData.gd';match=re.search(r'const TRIANGLE_ORDER := (\[[^\]]+\])',source.read_text());order=json.loads(match[1]);assert order==[0,2,1,0,3,2]
 module_rows=[module_proof(m,order) for m in c['modules']];reused=sum(m['id'] in oldrows for m in c['modules']);assert reused==21 and all(m==oldrows[m['id']] for m in c['modules'] if m['id'] in oldrows)
 asset_rows=[];rotations=0;max_roundtrip=0
 for row in p['assets']:
  original=b.read(b.R/row['source_render_path']);master=b.read(b.R/row['source_master_path']);assert b.sha(b.R/row['source_render_path'])==row['source_render_sha256'] and b.sha(b.R/row['source_master_path'])==row['source_master_sha256'];boxes,cuts=b.source_owners_and_cuts(master,row['rule'],row['source_pitch_m']);faces={(f['group_index'],f['quad_index']):f for f in row['faces']};patchrects=[];source_area=patch_area=0
  for f in row['faces']:
   q=original['groups'][f['group_index']]['quads'][f['quad_index']];assert q==f['quad'] and b.digest(q)==f['quad_sha256'];r=a.top_rectangle(q);assert r==f['rect_uv_integer_cells'];own=a.ownership(r,a.strict_grid(q[0][1]),boxes);assert own['owners']==f['operation_owners'] and own['proof']==f['semantic_owner_union'];assert b.cut_exclusion(q,cuts)==f['cut_exclusion_proofs'];source_area+=(r[2]-r[0])*(r[3]-r[1])
  assert overlap([(f['rect_uv_integer_cells'],a.strict_grid(f['plane_y_m'])) for f in row['faces']])==0
  for placement in row['placements']:
   f=faces[tuple(placement['source_face_ref'])];m=mods[placement['module_key']];bounds=[a.strict_grid(v) for v in placement['bounds_uv_m']];tr=placement['transform'];assert tr['basis']==[[1,0,0],[0,0,1],[0,-1,0]];assert placement['source_face_sha256']==f['quad_sha256'];assert a.strict_grid(tr['translation'][0])==bounds[0] and a.strict_grid(-tr['translation'][2])==bounds[1];assert abs(tr['translation'][1]-.0375-f['plane_y_m'])<=1e-15
   assert a.strict_grid(m['trim']['width_m'])==bounds[2]-bounds[0] and a.strict_grid(m['trim']['height_m'])==bounds[3]-bounds[1]
   assert a.union_proof(bounds,[f['rect_uv_integer_cells']])['uncovered_area_cells2']==0
   assert a.union_proof(bounds,[o['rect_uv_integer_cells'] for o in f['operation_owners']])['uncovered_area_cells2']==0
   patchrects.append((bounds,a.strict_grid(f['plane_y_m'])));patch_area+=(bounds[2]-bounds[0])*(bounds[3]-bounds[1])
   corners=[[x*P,f['plane_y_m'],-v*P] for x,v in [(bounds[0],bounds[1]),(bounds[2],bounds[1]),(bounds[2],bounds[3]),(bounds[0],bounds[3])]]
   pose=row['actual_instances'][0]['instance'];assert pose.get('scale',[1,1,1])==[1,1,1]
   for pos,yaw in [(pose['position_m'],pose.get('yaw_rad',0)),([-123.5,8.1,-291.75],.37),([-123.5,8.1,-291.75],-2.194336547087899),([-123.5,8.1,-291.75],math.pi/2),([-123.5,8.1,-291.75],math.pi)]:
    for q in corners:
     world=a.polygons.transform_point_m(q,pos,yaw);local=a.polygons.inverse_transform_point_m(world,pos,yaw);err=max(abs(local[i]-q[i]) for i in range(3));max_roundtrip=max(max_roundtrip,err);assert err<1e-12;rotations+=1
    subject=[[a.polygons.transform_point_m(q,pos,yaw)[i] for i in [0,2]] for q in corners];worldface=[[a.polygons.transform_point_m(q,pos,yaw)[i] for i in [0,2]] for q in f['quad']];assert a.polygons.uncovered_area_by_union(subject,[worldface],0)<=1e-10
  assert overlap(patchrects)==0 and source_area==patch_area
  centers=[[(s[0]+s[2])*P/2,(s[1]+s[3])*P/2] for s,y in patchrects];counts=[sum((q[0]-o[0])**2+(q[1]-o[1])**2<=64 for q in centers) for o in centers];peak=max(counts)
  asset_rows.append({'asset_key':row['asset_key'],'faces':len(faces),'placements':len(row['placements']),'supported_projected_area_m2':source_area*P*P,'uncovered_actual_face_area_cells2':0,'uncovered_semantic_union_area_cells2':0,'overlap_area_cells2':0,'cuts_proven_disjoint':len(cuts),'source_collision_baseline':row['source_collision_baseline']['kind'],'observed_max_centers_within_8m_at_module_centers':peak,'sampled_budget_probe_is_not_global_maximum':True,'potential_truncation_at_existing_cap_120':peak>120,'budget_configuration_changed':False,'all_pass':True})
 assert len(ledger['assets'])==26 and sum(x['category']=='native_paving_access' for x in ledger['assets'])==21 and sum(x['category']=='small_bridges' for x in ledger['assets'])==5
 assert len(mods)==82 and sum(len(x['placements']) for x in p['assets'])==426
 result={'all_pass':True,'plan':b.ref(b.PLAN),'module_catalog':b.ref(b.CAT),'ledger':b.ref(b.LEDGER),'unchanged_dependencies':len(rep['frozen_dependencies']),'existing_module_rows_exactly_reused':reused,'modules':module_rows,'assets':asset_rows,'rotated_and_actual_pose_corners_checked':rotations,'maximum_roundtrip_error_m':max_roundtrip,'world_union_numeric_area_verification_bound_m2':1e-10,'exact_local_support_tolerance_m':0,'clockwise_order_read_from_unchanged_runtime':b.ref(source),'new_colliders':0,'runtime_integration_or_walk_test_claimed':False,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 output=H/'candidate_geometry.json'
 if output.exists():
  prior=b.read(output);ignore={'elapsed_seconds','peak_rss_kib'}
  assert {k:v for k,v in prior.items() if k not in ignore}=={k:v for k,v in result.items() if k not in ignore},'Replay changed a geometric proof; existing evidence remains untouched'
 else:b.save(output,result)
 print(json.dumps({k:v for k,v in result.items() if k!='modules'}));return result

P=b.P
class Guards(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=b.read(b.PLAN);cls.asset=cls.plan['assets'][-1];cls.master=b.read(b.R/cls.asset['source_master_path']);cls.rule=cls.asset['rule'];cls.boxes,cls.cuts=b.source_owners_and_cuts(cls.master,cls.rule,.2);cls.quad=cls.asset['faces'][0]['quad']
 def test_actual_cut_below_deck_by_point_65(self):
  proof=b.cut_exclusion(self.quad,self.cuts);self.assertEqual(proof[0]['separating_intervals'],[{'axis':1,'cut_side':'below','positive_gap_m':.65}])
 def test_cut_touching_top_rejected(self):
  c=copy.deepcopy(self.cuts);c[0]['max'][1]=0
  with self.assertRaisesRegex(ValueError,'cut_intersects'):b.cut_exclusion(self.quad,c)
 def test_finite_hole_inside_quad_rejected_even_if_corners_clear(self):
  c=copy.deepcopy(self.cuts);c[0]['min']=[-.1,-1,-.1];c[0]['max']=[.1,1,.1]
  with self.assertRaisesRegex(ValueError,'cut_intersects'):b.cut_exclusion(self.quad,c)
 def test_strict_lateral_disjoint_cut_accepted(self):
  c=copy.deepcopy(self.cuts);c[0]['min']=[9,-1,-.1];c[0]['max']=[10,1,.1];self.assertTrue(b.cut_exclusion(self.quad,c)[0]['strict_disjoint'])
 def test_assembly_cut_not_ignored(self):
  m=copy.deepcopy(self.master);m['assembly_cuts']=[{'id':'hole'}]
  with self.assertRaisesRegex(ValueError,'assembly_cut'):b.source_owners_and_cuts(m,self.rule,.2)
 def test_rotated_source_paint_not_approximated_by_aabb(self):
  m=copy.deepcopy(self.master);m['components'][0]['operations'][0]['transform']={'basis':[[0,0,1],[0,1,0],[-1,0,0]]}
  with self.assertRaisesRegex(ValueError,'rotated_source'):b.source_owners_and_cuts(m,self.rule,.2)
 def test_nonbox_paint_rejected(self):
  m=copy.deepcopy(self.master);m['components'][0]['operations'][0]['shape']={'kind':'extrusion','polygon':[[0,0],[1,0],[1,1]],'z_min':-1,'z_max':0}
  with self.assertRaisesRegex(ValueError,'paint_operation'):b.source_owners_and_cuts(m,self.rule,.2)
 def test_dynamic_part_rejected(self):
  m=copy.deepcopy(self.master);m['components'][0]['parts'][0]['dynamic']=True
  with self.assertRaisesRegex(ValueError,'dynamic_part'):b.source_owners_and_cuts(m,self.rule,.2)
 def test_pitch_dependent_minimum_rejected(self):
  m=copy.deepcopy(self.master);m['components'][0]['operations'][0]['shape']['minimum_cells']=[1000,0,0]
  with self.assertRaisesRegex(ValueError,'pitch_dependent'):b.source_owners_and_cuts(m,self.rule,.2)
 def test_all_24_quad_permutations_only_four_correct(self):
  good=bad=0
  for order in itertools.permutations(range(4)):
   try:a.top_rectangle([self.quad[i] for i in order]);good+=1
   except ValueError:bad+=1
  self.assertEqual((good,bad),(4,20))
 def test_uncovered_union_hole_and_seams(self):
  self.assertTrue(a.union_proof([-160,-80,0,0],[[-160,-80,-80,0],[-80,-80,0,0]])['supported'])
  self.assertFalse(a.union_proof([0,0,80,80],[[0,0,80,39],[0,40,80,80],[0,39,39,40],[40,39,80,40]])['supported'])
 def test_different_semantics_not_joined(self):
  boxes=[{'semantic_key':['i','c','m','floor'],'top_y_integer_cells':0,'rect_uv_integer_cells':[0,0,40,80]},{'semantic_key':['i','c','m','rail'],'top_y_integer_cells':0,'rect_uv_integer_cells':[40,0,80,80]}]
  with self.assertRaises(ValueError):a.ownership([0,0,80,80],0,boxes)
 def test_missing_original_quad_does_not_become_box_support(self):
  original=b.read(b.R/self.asset['source_render_path']);self.assertNotEqual(self.asset['faces'][0]['quad_sha256'],b.digest([]))
  with self.assertRaises(ValueError):a.top_rectangle([])
 def test_duplicate_retained_top_faces_detected(self):
  r=a.top_rectangle(self.quad);self.assertGreater(overlap([(r,0),(r,0)]),0)
 def test_wrong_box_level_rejected(self):
  with self.assertRaises(ValueError):a.ownership(a.top_rectangle(self.quad),1,self.boxes)

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Guards);result=unittest.TextTestRunner(verbosity=2).run(suite);b.save(H/'fixture_results.json',{'all_pass':result.wasSuccessful(),'tests_run':result.testsRun,'failures':[str(x) for x in result.failures],'errors':[str(x) for x in result.errors]});assert result.wasSuccessful();run_geometry();assert b.output_bytes()<b.LIMIT
