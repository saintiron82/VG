"""Retire obsolete same-plane paint only under canonical final23 ownership."""
import json,copy,time,collections
from pathlib import Path
from .. import author as a
from ..coherent_final24_r02.prepare import ref,load
from ..final_profile_audit_r01 import exact_clip as e
from ..final23_float32_review_r01.classify import area
from ..final23_precision_continuation_r01.runtime_winding import f32,normal
from .....assemblies.waterworks.registered_bridge.port_approach_r01.normalized import normalized,NORMALIZATION
HERE=Path(__file__).resolve().parent
BINDING=a.CITY/'registered_integration/r8/final_exterior_candidate_r01/port_atomic_activation_r02/activation_binding.json'
REPORT=a.CITY/'registered_integration/r8/final_exterior_candidate_r01/final23_shared_source_conflicts_r01.json'
def write(n,d):
 p=HERE/n;assert not p.exists(),str(p);p.write_text(json.dumps(d,separators=(',',':'),allow_nan=False)+'\n')
def emit(p,plane,tag):
 p=normalized(p,tag)
 if not p:return[]
 return list(a.fan_upward([[x,a.common.height(plane,[x,z]),z]for x,z in p]))
def run():
 start=time.monotonic();binding=json.loads(BINDING.read_bytes());report=json.loads(REPORT.read_bytes());assert a.sha(BINDING)==report['binding']['sha256'];oldref=binding['patches'][13];old=load(oldref);topref=binding['patches'][24];top=load(topref);assert old['id']=='R8_SAME_PLANE_FUNCTIONAL_BACKLANDS'and top['id']=='R17_COMPLETE_FINAL24_TOPS'
 oldrows={(r['material'],r['triangle_index']):r for r in old['surface_edits']};newrows={(r['material'],r['triangle_index']):r for r in top['surface_edits']};scene=a.load_scene();rowupdates={};masks=[];rowledger=[]
 for case in report['errors']:
  key=case['material'],case['triangle_index'];assert {r['id']for r in case['producers']}=={old['id'],top['id']};s=scene['surfaces'][key[0]][key[1]*3:key[1]*3+3];p=[[v[0],v[2]]for v in s];plane=a.common.plane(s);orr=oldrows[key];nr=newrows[key]
  oldremoved=a.common.subtract([p],[[[v[0],v[2]]for v in t]for t in orr['replacement_triangles_xyz_m']]);newremoved=a.common.subtract([p],[[[v[0],v[2]]for v in t]for t in nr['replacement_triangles_xyz_m']]);overlap=[]
  for u in oldremoved:
   for v in newremoved:
    q=e.clip(u,v)
    if area(q)>0:overlap.append(q)
  tris=[t for j,q in enumerate(overlap)for t in emit(q,plane,str(key)+':RESTORED_SOURCE:'+str(j))];updated=dict(orr,replacement_triangles_xyz_m=orr['replacement_triangles_xyz_m']+tris);rowupdates[key]=updated;masks.extend(overlap);rowledger.append(dict(material=key[0],triangle_index=key[1],original_producer=oldref,source_original_triangle_sha256=orr['source_triangle_sha256'],source_original_vertices_xyz_m=s,old_backland_row=orr,canonical_final23_row=nr,overlap_polygons_xz_m=overlap,overlap_area_m2=sum(area(q)for q in overlap),replacement_backland_row=updated,policy='Restore the original plane only to the backland producer remainder so final23 owns its sole source cut; old backland paint is retired over the exact same intersection.'))
 print('Source rows',len(rowupdates),'overlap area',sum(r['overlap_area_m2']for r in rowledger),flush=True);idx=a.geo._SpatialIndex(8)
 for i,p in enumerate(masks):idx.add(i,p)
 updated=copy.deepcopy(old);updated['surface_edits']=[rowupdates.get((r['material'],r['triangle_index']),r)for r in old['surface_edits']];appendledger=[];appended={};precision=[]
 for material,vs in old['appended_surfaces'].items():
  new=[]
  for i in range(len(vs)//3):
   t=vs[3*i:3*i+3];p=[[v[0],v[2]]for v in t];candidates=[j for j in sorted(idx.candidates(p))if area(e.clip(p,masks[j]))>0]
   if not candidates:new.extend(t);continue
   parts=[p]
   for j in candidates:parts=[r for q in parts for r in e.difference(q,masks[j])]
   removed=area(p)-sum(area(q)for q in parts)
   if removed<=0:new.extend(t);continue
   plane=a.common.plane(t);tris=[q for k,r in enumerate(parts)for q in emit(r,plane,material+':'+str(i)+':'+str(k))];startindex=len(new)//3;new.extend(v for q in tris for v in q);appendledger.append(dict(material=material,source_appended_triangle_index=i,source_triangle_sha256=a.canonical_sha(t),source_vertices_xyz_m=t,replacement_triangles_xyz_m=tris,derived_first_triangle_index=startindex,removed_area_m2=removed,remaining_area_m2=sum(a.normal_y(q)/2 for q in tris),canonical_mask_indices=candidates))
   for k,q in enumerate(tris):
    f=[[f32(x)for x in v]for v in q];n=normal(f)
    if n[1]<0:precision.append(dict(material=material,derived_appended_triangle_index=startindex+k,vertices_xyz_m=q,float32_vertices_xyz_m=f,float32_normal_xyz=n))
  appended[material]=new
 updated['appended_surfaces']=appended;updated['final23_same_plane_supersession']=dict(source_producer=oldref,source_main_binding=ref(BINDING),canonical_final23_top=topref,ledger_path=str((HERE/'ownership_ledger.json').relative_to(a.ROOT)),scope='Only same-plane backland paint within exact final23 source-cut intersections. All exterior backland source planes, native uses and unrelated producer fields remain unchanged.');write('backland_producer.json',updated);write('ownership_ledger.json',dict(source_main_binding=ref(BINDING),failed_source_report=ref(REPORT),source_backland_producer=oldref,canonical_final23_top=topref,source_rows=rowledger,appended_rows=appendledger,normalization=NORMALIZATION,new_float32_inversions=precision,summary=dict(source_rows=len(rowledger),appended_rows=len(appendledger),removed_backland_area_m2=sum(r['removed_area_m2']for r in appendledger),source_cut_overlap_m2=sum(r['overlap_area_m2']for r in rowledger),normalization_absolute_area_delta_m2=sum(abs(r['area_delta_m2'])for r in NORMALIZATION),float32_inversions=len(precision),elapsed_s=time.monotonic()-start),activation=False));binding['patches'][13]=ref(HERE/'backland_producer.json');binding['patches'][24]=ref(HERE.parent/'final23_precision_continuation_r01/top_scene_patch.json');binding['final23_backland_supersession']=dict(ledger=ref(HERE/'ownership_ledger.json'),source_main_binding=ref(BINDING));write('activation_binding.json',binding);print('COMPLETE',len(appendledger),'paint rows, precision holds',len(precision),flush=True)
if __name__=='__main__':run()
