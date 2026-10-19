"""Exact exported-vertex/translation and negative regression checks; no sampling."""
from pathlib import Path
from fractions import Fraction as F
import copy,importlib.util,json,math,resource,time
H=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('frozen_author',H/'author_r03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);q=m.q;p=m.p;a=m.a
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
start=time.monotonic();plan=q.read(H/'source_plan.json');asset=plan['assets'][0];modules={r['id']:r for r in q.read(H/'modules/catalog.json')['modules']};masks={tuple(g['grid_xy_m']):g for g in q.read(H/'prepared_masks.json')['grids']};source=q.read(q.R/asset['source_render_path']);walk=[q.e.fp(o['polygon_uv_m'])for o in asset['source_polygon_owners']];cuts=[q.e.fp(c['polygon_uv_m'])for c in asset['source_component_cuts']];actual=[q.e.fp([[v[0],-v[2]]for v in source['groups'][f['source_face_ref'][0]]['quads'][f['source_face_ref'][1]]])for f in q.read(H/'prepared_masks.json')['actual_faces']]
backs=vertices=cached=0;maxroundtrip=0;unique_export_vertices=0
print('start',flush=True)
for placement in asset['placements']:
 row=modules[placement['module_key']];render=m.read(q.R/row['render_path']);gx,gy=placement['grid_xy_m'];tx,ty,tz=placement['transform']['translation'];offset=[F(tx)-gx,-F(tz)-gy];isnew=row.get('transport')=='existing_gzip_json'
 g=masks[gx,gy];localwalk=[q.e.fp(o['polygon_uv_m'])for o in asset['source_polygon_owners']if o['operation']in g['source_owner_ids']];localactual=[q.e.fp([[v[0],-v[2]]for v in source['groups'][gi]['quads'][qi]])for gi,qi in g['source_face_refs']];seen=set()
 for group in render['groups']:
  for quad in group['quads']:
   vertices+=len(quad)
   for v in quad:
    if tuple(v[:2])in seen:continue
    seen.add(tuple(v[:2]));unique_export_vertices+=1
    # Exact source-local placement uses the actual exported binary64 vertex;
    # no rounding or snapping is accepted as the safety proof.
    for axis,anchor,off in [(0,gx,offset[0]),(1,gy,offset[1])]:
     index=round(float(F(v[axis])+off)/m.P);target=F(index*m.P);value=F(v[axis])+off
     if isnew:assert value==target
   if not all(abs(v[2]+.0375)<1e-12 for v in quad):continue
   backs+=1
   if not isnew:
    poly=[[F(tx)+F(v[0]),-F(tz)+F(v[1])]for v in quad];rect=[min(v[0]for v in poly),min(v[1]for v in poly),max(v[0]for v in poly),max(v[1]for v in poly)];poly=p.rectpoly(rect)
    assert any(p.rect_in(rect,p.lines(o))for o in localwalk)or q.e.exact_union(poly,localwalk)==0
    assert q.e.exact_union(poly,localactual)==0 and all(q.ad.intersection_area(poly,c)==0 for c in cuts);cached+=1
 # The same proper owner transform maps source and detail together; four
 # negative-coordinate/yaw diagnostics check composition, not source tolerances.
 for origin,yaw in [(asset['actual_instances'][0]['instance']['position_m'],0),([-213.5,14.1,-321.75],.37),([-213.5,14.1,-321.75],-2.194336547087899),([-213.5,14.1,-321.75],math.pi/2)]:
  local=[tx,0,tz];world=a.polygons.transform_point_m(local,origin,yaw);back=a.polygons.inverse_transform_point_m(world,origin,yaw);err=max(abs(x-y)for x,y in zip(back,local));assert err<1e-12;maxroundtrip=max(maxroundtrip,err)
print('exported vertices and cached source footprints passed',flush=True)
fixtures=m.crop.fixtures();q.save(H/'validation/common_crop_fixtures.json',fixtures)
# Explicitly mutate support masks, using a known original-cut cell and an
# outside-walk cell; original geometry and prepared source data remain intact.
negative=[]
for kind in ['walk','cut','quad']:
 found=False
 for g in masks.values():
  gx,gy=g['grid_xy_m'];xx=q.coords(gx)[0];yy=q.coords(gy)[0]
  for x,y,z,w in g['forbidden_cell_runs_xy']:
   rect=[xx[x],yy[y],xx[x+1],yy[y+1]];poly=p.rectpoly(rect)
   condition={'walk':lambda:q.e.exact_union(poly,walk)>0,'cut':lambda:any(q.ad.intersection_area(poly,c)>0 for c in cuts),'quad':lambda:q.e.exact_union(poly,actual)>0}[kind]
   if not condition():continue
   altered=copy.deepcopy(g);altered['allowed_cell_runs_xy']=[[x,y,x+1,y+1]]
   rejected=False
   try:m.validate_source_runs(altered,asset)
   except AssertionError:rejected=True
   assert rejected;negative.append({'case':'reject_positive_'+kind+'_violation','grid_xy_m':[gx,gy],'cell_xy':[x,y],'pass':True});found=True;break
  if found:break
 assert found,kind
out={'all_pass':True,'source_plan':q.ref(H/'source_plan.json'),'exported_vertices_checked':vertices,'backing_quads':backs,'cached_actual_exported_backing_quads_exactly_inside_source':cached,'new_exported_vertices_exactly_match_proved_binary64_grid':True,'unique_exported_xy_vertices_checked':unique_export_vertices,'source_local_support_tolerance_m':0,'source_local_placement_rounding_used':False,'proper_owner_pose_diagnostics':4*len(asset['placements']),'maximum_double_roundtrip_error_m':maxroundtrip,'rigid_transform_support_argument':'Apply the same proper source-owner transform to both the exact source domain and every proved detail footprint. No source support is expanded; floating roundtrip is diagnostic only.','negative_source_mutations':negative,'common_crop_fixtures':q.ref(H/'validation/common_crop_fixtures.json'),'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
q.save(H/'validation/transforms_r02_report.json',out);print(json.dumps(out))
