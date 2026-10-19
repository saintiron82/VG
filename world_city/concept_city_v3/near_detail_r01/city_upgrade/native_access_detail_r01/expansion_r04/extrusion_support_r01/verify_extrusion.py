from pathlib import Path
from fractions import Fraction as F
import copy,itertools,json,math,re,resource,sys,time,unittest
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import author_extrusion as e
b=e.b;a=e.a;b.limits();sys.path.insert(0,str(H.parent));import verify_r04 as prior

class ExactSource(unittest.TestCase):
 def test_two_triangles_shared_diagonal(self):
  s=e.fp([[0,0],[1,0],[1,1],[0,1]]);self.assertEqual(e.exact_union(s,[s[:3],[s[0],s[2],s[3]]]),0)
 def test_negative_coordinate_multi_polygon_seam(self):
  s=e.fp([[-2,-1],[0,-1],[0,0],[-2,0]]);covers=e.fp([[-2,-1],[-1,-1],[-1,0],[-2,0]]),e.fp([[-1,-1],[0,-1],[0,0],[-1,0]])
  self.assertEqual(e.exact_union(s,list(covers)),0)
 def test_sub_epsilon_hole_remains_positive(self):
  s=e.fp([[0,0],[1,0],[1,1],[0,1]]);x=F(1,2);gap=F(1,10**12)
  covers=[[[F(0),F(0)],[x,F(0)],[x,F(1)],[F(0),F(1)]],[[x+gap,F(0)],[F(1),F(0)],[F(1),F(1)],[x+gap,F(1)]]]
  self.assertEqual(e.exact_union(s,covers),gap)
 def test_duplicate_overlap_does_not_fill_missing_gap(self):
  s=e.fp([[0,0],[1,0],[1,1],[0,1]]);cover=e.fp([[0,0],[.5,0],[.5,1],[0,1]])
  self.assertEqual(e.exact_union(s,[cover,cover]),F(1,2))
 def test_internal_hole_not_filled_by_outer_aabb(self):
  s=e.fp([[0,0],[3,0],[3,3],[0,3]]);covers=[e.fp(p) for p in [[[0,0],[3,0],[3,1],[0,1]],[[0,2],[3,2],[3,3],[0,3]],[[0,1],[1,1],[1,2],[0,2]],[[2,1],[3,1],[3,2],[2,2]]]]
  self.assertEqual(e.exact_union(s,covers),1)
 def test_concave_bowtie_duplicate_polygons_rejected(self):
  for p in [[[0,0],[1,1],[0,1],[1,0]],[[0,0],[2,0],[1,.5],[2,1],[0,1]],[[0,0],[1,0],[1,0],[0,1]]]:self.assertFalse(e.convex(e.fp(p)))
 def test_polygon_orientation_does_not_change_union(self):
  s=e.fp([[0,0],[1,0],[1,1],[0,1]]);self.assertEqual(e.exact_union(s,[s[::-1]]),0)
 @classmethod
 def setUpClass(cls):
  cls.plan=e.read(e.PLAN);cls.asset=cls.plan['assets'][0];cls.master=e.read(e.R/cls.asset['source_master_path']);cls.rule=cls.asset['rule']
 def test_source_cuts_rejected_without_shape_guess(self):
  for assembly in [True,False]:
   m=copy.deepcopy(self.master)
   if assembly:m['assembly_cuts']=[{'id':'cut'}]
   else:m['components'][0]['operations'].append({'id':'cut','action':'cut'})
   with self.assertRaises(ValueError):e.source_caps(m,self.rule)
 def test_source_nonaxis_cap_rejected(self):
  m=copy.deepcopy(self.master);op=next(o for o in m['components'][0]['operations'] if o['id'] in self.rule['operation_ids']);op['transform']['basis']=[[math.cos(.2),-math.sin(.2),0],[0,0,1],[-math.sin(.2),-math.cos(.2),0]]
  with self.assertRaises(ValueError):e.source_caps(m,self.rule)
 def test_missing_path_metadata_owner_rejected(self):
  r=copy.deepcopy(self.rule);r['operation_ids'].append('imaginary_path')
  with self.assertRaises(ValueError):e.source_caps(self.master,r)
 def test_material_does_not_override_semantic_metadata(self):
  m=copy.deepcopy(self.master);r=next(x for x in m['metadata']['owned_floor_regions'] if x['id'] in self.rule['operation_ids']);r['material']='earth'
  with self.assertRaises(ValueError):e.source_caps(m,self.rule)
 def test_wrong_height_not_a_supported_surface(self):
  owners=e.source_caps(self.master,self.rule);proof=e.semantic_proof([-55.5,15,-55,16],1,owners);self.assertFalse(proof['supported'])
 def test_all_24_source_quad_permutations(self):
  q=self.asset['faces'][0]['quad'];accepted=0
  for order in itertools.permutations(range(4)):
   try:a.top_rectangle([q[i]for i in order]);accepted+=1
   except ValueError:pass
  self.assertEqual(accepted,4)

def verify():
 start=time.perf_counter();plan=e.read(e.PLAN);cat=e.read(e.CAT);audit=e.read(H/'source_application_audit.json');build=e.read(H/'build_report.json');asset=plan['assets'][0];src=e.read(e.R/asset['source_render_path']);master=e.read(e.R/asset['source_master_path']);owners=e.source_caps(master,asset['rule']);assert owners==asset['source_polygon_owners'];assert cat['source_plan_sha256']==e.sha(e.PLAN);assert all(e.sha(e.R/p)==s for p,s in build['source_dependencies'].items());mods={m['id']:m for m in cat['modules']}
 rd=b.C/'playable_detail_r01/RenderData.gd';order=json.loads(re.search(r'const TRIANGLE_ORDER := (\[[^\]]+\])',rd.read_text())[1]);module_rows=[prior.module_proof(m,order) for m in cat['modules']];faces={(f['group_index'],f['quad_index']):f for f in asset['faces']};rects=[];checked=0;maxerror=0;rejected_positive=0;totalarea=0
 for f in asset['faces']:
  q=src['groups'][f['group_index']]['quads'][f['quad_index']];assert q==f['quad'] and e.digest(q)==f['quad_sha256'] and a.top_rectangle(q)==f['rect_uv_integer_cells'];assert e.semantic_proof([x*e.P for x in f['rect_uv_integer_cells']],f['plane_y_m'],owners)==f['full_face_semantic_proof']
 for p in asset['placements']:
  f=faces[tuple(p['source_face_ref'])];r=[a.strict_grid(v)for v in p['bounds_uv_m']];m=mods[p['module_key']];assert a.union_proof(r,[f['rect_uv_integer_cells']])['uncovered_area_cells2']==0;proof=e.semantic_proof(p['bounds_uv_m'],p['source_plane_y_m'],owners);assert proof==p['source_semantic_proof'] and proof['supported'] and proof['exact_uncovered_area_ratio']==[0,1];assert p['source_face_sha256']==f['quad_sha256']
  assert p['transform']['basis']==[[1,0,0],[0,0,1],[0,-1,0]];assert p['transform']['translation']==[p['bounds_uv_m'][0],f['plane_y_m']+.0375,-p['bounds_uv_m'][1]];assert a.strict_grid(m['trim']['width_m'])==r[2]-r[0] and a.strict_grid(m['trim']['height_m'])==r[3]-r[1]
  rects.append((r,a.strict_grid(f['plane_y_m'])));totalarea+=(r[2]-r[0])*(r[3]-r[1])*e.P*e.P
  corners=[[x*e.P,f['plane_y_m'],-y*e.P] for x,y in [(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])]];actual=asset['actual_instances'][0]['instance'];assert actual.get('scale',[1,1,1])==[1,1,1]
  for pos,yaw in [(actual['position_m'],actual.get('yaw_rad',0)),([-213.5,14.1,-321.75],.37),([-213.5,14.1,-321.75],-2.194336547087899),([-213.5,14.1,-321.75],math.pi/2),([-213.5,14.1,-321.75],math.pi)]:
   for q in corners:
    world=a.polygons.transform_point_m(q,pos,yaw);back=a.polygons.inverse_transform_point_m(world,pos,yaw);error=max(abs(back[i]-q[i])for i in range(3));maxerror=max(maxerror,error);assert error<1e-12;checked+=1
 assert prior.overlap(rects)==0 and totalarea==audit['supported_area_m2']
 for row in audit['rejected_patches']:
  plane=src['groups'][row['source_face_ref'][0]]['quads'][row['source_face_ref'][1]][0][1];proof=e.semantic_proof(row['bounds_uv_m'],plane,owners);assert proof==row['proof'] and not proof['supported'];rejected_positive+=proof['exact_uncovered_area_ratio'][0]>0
 assert rejected_positive==len(audit['rejected_patches'])==397
 # Radius probe uses supported module centers only; original world may have other owners.
 centers=[[(r[0]+r[2])*e.P/2,(r[1]+r[3])*e.P/2] for r,y in rects];peak=max(sum((x[0]-y[0])**2+(x[1]-y[1])**2<=64 for y in centers)for x in centers)
 result={'all_pass':True,'source_plan':b.ref(e.PLAN),'module_catalog':b.ref(e.CAT),'actual_source_faces':len(faces),'placements':len(rects),'source_polygon_owners':len(owners),'source_support_area_m2':totalarea,'uncovered_actual_source_area_m2':0,'uncovered_exact_semantic_union_area_m2':0,'coplanar_overlap_area_m2':0,'rejected_patches_with_proven_positive_uncovered_area':rejected_positive,'original_earth_boundary_and_unsupported_path_edges_unchanged':True,'source_group_geometry_sha256':{g['material']:e.digest(g['quads']) for g in src['groups']},'rotated_actual_and_negative_coordinate_corners':checked,'maximum_roundtrip_error_m':maxerror,'radius8_module_center_probe_max':peak,'probe_is_not_global_maximum':True,'potential_truncation_at_cap120':peak>120,'module_results':module_rows,'new_colliders':0,'runtime_binding_changed':False,'no_new_walk_route_claim':True,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 out=H/'candidate_geometry.json'
 if out.exists():
  old=e.read(out);skip={'elapsed_seconds','peak_rss_kib'};assert {k:v for k,v in old.items()if k not in skip}=={k:v for k,v in result.items()if k not in skip}
 else:e.save(out,result)
 print(json.dumps({k:v for k,v in result.items()if k!='module_results'}));return result
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ExactSource);r=unittest.TextTestRunner(verbosity=2).run(suite);e.save(H/'fixture_results.json',{'all_pass':r.wasSuccessful(),'tests':r.testsRun,'failures':[str(x)for x in r.failures],'errors':[str(x)for x in r.errors]});assert r.wasSuccessful();verify();assert b.output_bytes()<b.LIMIT
