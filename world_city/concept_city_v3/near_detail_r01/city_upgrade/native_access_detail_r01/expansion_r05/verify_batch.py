from pathlib import Path
from fractions import Fraction as F
import argparse,copy,json,re,sys,math,time,resource,unittest
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE));import author_batch as p
ad=p.adapter;e=ad.e;b=e.b;a=e.a
sys.path.insert(0,str(p.OLD));import verify_r04 as prior
H=None
class CutProof(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=p.read(p.PLAN);cls.asset=cls.plan['assets'][0];cls.master=p.read(p.R/cls.asset['source_master_path']);cls.rule=cls.asset['rule']
 def test_exact_internal_hole_overlap(self):
  self.assertEqual(ad.intersection_area(e.fp([[0,0],[3,0],[3,3],[0,3]]),e.fp([[1,1],[2,1],[2,2],[1,2]])),1)
 def test_sub_epsilon_overlap_not_discarded(self):
  delta=F(1,10**12);subject=e.fp([[0,0],[1,0],[1,1],[0,1]]);cut=[[1-delta,F(0)],[F(2),F(0)],[F(2),F(1)],[1-delta,F(1)]];self.assertEqual(ad.intersection_area(subject,cut),delta)
 def test_shared_edge_has_zero_area(self):
  self.assertEqual(ad.intersection_area(e.fp([[0,0],[1,0],[1,1],[0,1]]),e.fp([[1,0],[2,0],[2,1],[1,1]])),0)
 def test_cut_part_label_does_not_limit_instance_cut(self):
  m=copy.deepcopy(self.master);m['components'][0]['parts'].append({'id':'other','pivot':[0,0,0]});cut=next(o for o in m['components'][0]['operations']if o['action']=='cut');cut['part']='other';owners,cuts=ad.source_contract(m,self.rule,.5);self.assertEqual(len(cuts),len(self.asset['source_component_cuts']));self.assertEqual(cuts[0]['part'],'other')
 def test_selector_is_preserved_and_conservatively_considered(self):
  m=copy.deepcopy(self.master);cut=next(o for o in m['components'][0]['operations']if o['action']=='cut');cut['selector']={'part':'solid'};owners,cuts=ad.source_contract(m,self.rule,.5);self.assertEqual(cuts[0]['selector'],{'part':'solid'})
 def test_assembly_cut_rejected(self):
  m=copy.deepcopy(self.master);m['assembly_cuts']=[{'id':'hole'}]
  with self.assertRaises(ValueError):ad.source_contract(m,self.rule,.5)
 def test_dynamic_source_rejected(self):
  m=copy.deepcopy(self.master);m['components'][0]['parts'][0]['dynamic']=True
  with self.assertRaises(ValueError):ad.source_contract(m,self.rule,.5)
 def test_nonaxis_and_nonconvex_cut_rejected(self):
  for malformed in ['rotation','polygon']:
   m=copy.deepcopy(self.master);cut=next(o for o in m['components'][0]['operations']if o['action']=='cut')
   if malformed=='rotation':cut['transform']['basis']=[[math.cos(.1),-math.sin(.1),0],[0,0,1],[-math.sin(.1),-math.cos(.1),0]]
   else:cut['shape']['polygon']=[[0,0],[1,1],[0,1],[1,0]]
   with self.assertRaises(ValueError):ad.source_contract(m,self.rule,.5)
 def test_grass_not_authorized_by_path_rule(self):
  rule=copy.deepcopy(self.rule);rule['operation_ids'].append('owned_floor_0')
  with self.assertRaises(ValueError):ad.source_contract(self.master,rule,.5)
 def test_height_and_visual_offset_cut_scope(self):
  owners=[{'operation':'path','semantic_key':['i','c','stone','solid'],'top_y_m':0,'bounds_uv_m':[0,0,1,1],'polygon_uv_m':[[0,0],[1,0],[1,1],[0,1]]}]
  cut={'operation':'gate','operation_sha256':'x','polygon_sha256':'x','polygon_uv_m':[[0,0],[1,0],[1,1],[0,1]],'y_interval_m':[0,3]}
  self.assertFalse(ad.patch_proof([0,0,1,1],0,owners,[cut])['supported'])
  cut['y_interval_m']=[.0375,3];self.assertFalse(ad.patch_proof([0,0,1,1],0,owners,[cut])['supported'])
  cut['y_interval_m']=[.1,3];self.assertTrue(ad.patch_proof([0,0,1,1],0,owners,[cut])['supported'])
 def test_negative_coordinate_cut_projection(self):
  s=e.fp([[-3,-3],[-1,-3],[-1,-1],[-3,-1]]);cut=e.fp([[-2,-2],[0,-2],[0,0],[-2,0]]);self.assertEqual(ad.intersection_area(s,cut),1)

def verify():
 start=time.perf_counter();plan=p.read(p.PLAN);cat=p.read(p.CAT);build=p.read(H/'build_report.json');audit=p.read(H/'source_application_audit.json');assert cat['source_plan_sha256']==p.sha(p.PLAN);assert all(p.sha(p.R/path)==s for path,s in build['source_dependencies'].items());mods={r['id']:r for r in cat['modules']};order=json.loads(re.search(r'const TRIANGLE_ORDER := (\[[^\]]+\])',(b.C/'playable_detail_r01/RenderData.gd').read_text())[1]);module_rows=[prior.module_proof(m,order)for m in cat['modules']];assets=[];checked=0;maxerror=0
 for row in plan['assets']:
  src=p.read(p.R/row['source_render_path']);master=p.read(p.R/row['source_master_path']);owners,cuts=ad.source_contract(master,row['rule'],row['source_pitch_m']);assert owners==row['source_polygon_owners'] and cuts==row['source_component_cuts'];assert len({tuple(o['semantic_key'])for o in owners})==1,'Mixed semantic source groups are unsupported in this bounded candidate';faces={(f['group_index'],f['quad_index']):f for f in row['faces']};rects=[];area=0;actual=row['actual_instances'][0]['instance'];assert actual.get('scale',[1,1,1])==[1,1,1]
  for f in row['faces']:
   q=src['groups'][f['group_index']]['quads'][f['quad_index']];assert q==f['quad'] and p.digest(q)==f['quad_sha256'] and a.top_rectangle(q)==f['rect_uv_integer_cells']
  for placement in row['placements']:
   f=faces[tuple(placement['source_face_ref'])];bounds=placement['bounds_uv_m'];rect=[a.strict_grid(v)for v in bounds];proof=ad.patch_proof(bounds,placement['source_plane_y_m'],owners,cuts);assert proof==placement['source_semantic_cut_proof'] and proof['supported'];assert a.union_proof(rect,[f['rect_uv_integer_cells']])['uncovered_area_cells2']==0
   assert all(x['exact_overlap_area_ratio']==[0,1]for x in proof['cut_exclusion']);m=mods[placement['module_key']];assert a.strict_grid(m['trim']['width_m'])==rect[2]-rect[0] and a.strict_grid(m['trim']['height_m'])==rect[3]-rect[1];assert placement['transform']=={'basis':[[1,0,0],[0,0,1],[0,-1,0]],'translation':[bounds[0],f['plane_y_m']+.0375,-bounds[1]]};assert placement['source_face_sha256']==f['quad_sha256'];rects.append((rect,a.strict_grid(f['plane_y_m'])));area+=(rect[2]-rect[0])*(rect[3]-rect[1])*p.P*p.P
   corners=[[x,f['plane_y_m'],-y]for x,y in [(bounds[0],bounds[1]),(bounds[2],bounds[1]),(bounds[2],bounds[3]),(bounds[0],bounds[3])]]
   for pos,yaw in [(actual['position_m'],actual.get('yaw_rad',0)),([-213.5,14.1,-321.75],.37),([-213.5,14.1,-321.75],-2.194336547087899),([-213.5,14.1,-321.75],math.pi/2),([-213.5,14.1,-321.75],math.pi)]:
    for point in corners:
     world=a.polygons.transform_point_m(point,pos,yaw);back=a.polygons.inverse_transform_point_m(world,pos,yaw);error=max(abs(back[i]-point[i])for i in range(3));maxerror=max(maxerror,error);assert error<1e-12;checked+=1
  assert prior.overlap(rects)==0;bad=[x for x in audit['rejected_patches']if x['asset_key']==row['asset_key']];positive=gate=0
  for r in bad:
   proof=ad.patch_proof(r['bounds_uv_m'],r['source_plane_y_m'],owners,cuts);assert proof==r['proof'] and not proof['supported'];outside=proof['source_cap_union']['exact_uncovered_area_ratio'][0]>0;cut_overlap=any(c['exact_overlap_area_ratio'][0]>0 for c in proof['cut_exclusion']);assert outside or cut_overlap;positive+=1;gate+=not outside and cut_overlap
  centers=[[(r[0]+r[2])*p.P/2,(r[1]+r[3])*p.P/2]for r,y in rects];peak=max(sum((x[0]-y[0])**2+(x[1]-y[1])**2<=64 for y in centers)for x in centers)
  assets.append({'asset_key':row['asset_key'],'actual_faces':len(faces),'placements':len(rects),'source_owners':len(owners),'source_cuts':len(cuts),'source_supported_area_m2':area,'actual_source_uncovered_area_m2':0,'exact_path_union_uncovered_area_m2':0,'exact_original_cut_overlap_area_m2':0,'coplanar_overlap_area_m2':0,'rejected_positive_area_patches':positive,'fully_path_supported_but_cut_overlapping_rejected_patches':gate,'radius8_center_probe_max':peak,'probe_is_not_global_maximum':True,'potential_truncation_at_cap120':peak>120,'original_render_groups_sha256':{g['material']:p.digest(g['quads'])for g in src['groups']},'existing_collision_kind':row['source_collision_baseline']['kind']})
 result={'all_pass':True,'source_plan':b.ref(p.PLAN),'module_catalog':b.ref(p.CAT),'assets':assets,'modules':module_rows,'transformed_actual_and_rotated_corners':checked,'maximum_roundtrip_error_m':maxerror,'geometric_support_tolerance_m':0,'new_colliders':0,'production_binding_changed':False,'new_walking_route_claimed':False,'elapsed_seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};out=H/'candidate_geometry.json'
 if out.exists():
  old=p.read(out);skip={'elapsed_seconds','peak_rss_kib'};assert {k:v for k,v in old.items()if k not in skip}=={k:v for k,v in result.items()if k not in skip}
 else:p.save(out,result)
 print(json.dumps({k:v for k,v in result.items()if k!='modules'}));assert p.output_bytes()<p.LIMIT

if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(min(120,resource.getrlimit(resource.RLIMIT_CPU)[1]),)*2)
 ap=argparse.ArgumentParser();ap.add_argument('--revision',required=True,choices=list(p.BATCHES));args=ap.parse_args();H=BASE/args.revision;p.PLAN=H/'source_plan.json';p.CAT=H/'modules/catalog.json'
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CutProof));p.save(H/'fixture_results.json',{'all_pass':r.wasSuccessful(),'tests':r.testsRun,'failures':[str(x)for x in r.failures],'errors':[str(x)for x in r.errors]});assert r.wasSuccessful();verify()
