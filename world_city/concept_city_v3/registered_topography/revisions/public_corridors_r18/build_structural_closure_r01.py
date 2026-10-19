"""Add only exposed vertical joins to measured native access/support solids."""
import json,math,collections,time
from .height_field import HERE
from . import finite_geometry_r03 as g
from .classify_unknown_edges_r01 import ref,union_length
from ..r17_district_batches import author as a

def lerp(u,v,t):return [u[k]+t*(v[k]-u[k]) for k in (0,1)]
def main():
 start=time.monotonic();hp=HERE/'boundary_closure_handoff_r05_native.json';cp=HERE/'unknown_boundary_classification_r05_context.json';jp=a.CITY/'registered_integration/r8/joint_boundary_r05/surface_patch.json';h=json.loads(hp.read_bytes());ctx=json.loads(cp.read_bytes());joint=json.loads(jp.read_bytes());cm={(r['owner_id'],str(r['edge_xz_m'])):r for r in ctx['rows']};rows=[];tris=[];partial=[]
 for r in h['rows']:
  if r['category'] not in ['NONWALKING_NATIVE_SUPPORT_JOIN_REQUIRED','PARTIAL_OR_UNRESOLVED']:continue
  c=cm[r['owner_id'],str(r['edge_xz_m'])];u,v=r['edge_xz_m'];plane=c['owner_plane_y_xz_m'];joins=list(r['nonwalking_native_support_join_intervals']);closed=r['already_closed_native_side_intervals']+r['accepted_physical_profile_intervals']
  # Native fine access skin is a known ground support; projected tops are used
  # only as the LOWER bearing edge of a vertical connector, never walk owners.
  if r['category']=='PARTIAL_OR_UNRESOLVED' and 'COMMON' in r['owner_id']:
   for hit in c['native_and_contract_intervals']:
    s=hit['surface']
    if s.get('native_instance_id')!='R06_COMMON_R02:fine_access':continue
    if max(hit['delta_y_range_m'])>1e-8:continue
    joins.append(dict(interval_t=hit['interval_t'],actual_structural_top_plane_y_xz_m=s['plane_y_xz_m'],native_upface=s,semantics='nonwalking vertical bearing join to exact native access-skin upper face'))
  knots=sorted({0.,1.,*[t for j in joins+closed for t in j['interval_t']]});used=[]
  for lo,hi in zip(knots,knots[1:]):
   if hi<=lo:continue
   mid=(lo+hi)/2
   if any(j['interval_t'][0]<=mid<=j['interval_t'][1]for j in closed):continue
   candidates=[j for j in joins if j['interval_t'][0]<=mid<=j['interval_t'][1]]
   if not candidates:continue
   # All candidate planes here are exact horizontal native top planes.
   q=max(candidates,key=lambda j:a.common.height(j['actual_structural_top_plane_y_xz_m'],lerp(u,v,mid)));ep=[lerp(u,v,t)for t in(lo,hi)];top=[a.common.height(plane,p)for p in ep];bottom=[a.common.height(q['actual_structural_top_plane_y_xz_m'],p)for p in ep];assert min(y-z for y,z in zip(top,bottom))>=-1e-8
   xyz=[[ep[0][0],top[0],ep[0][1]],[ep[1][0],top[1],ep[1][1]],[ep[1][0],bottom[1],ep[1][1]],[ep[0][0],bottom[0],ep[0][1]]];ts=[[xyz[0],xyz[1],xyz[2]],[xyz[0],xyz[2],xyz[3]]]
   ts=[t for t in ts if math.dist(t[0],t[1])*abs(t[2][1]-t[1][1])>0 or math.dist(t[1],t[2])*abs(t[0][1]-t[2][1])>0]
   if not ts:continue
   first=len(tris);tris.extend(ts);used.append([lo,hi]);rows.append(dict(owner_id=r['owner_id'],source_edge_xz_m=[u,v],interval_t=[lo,hi],edge_xz_m=ep,public_plane_y_xz_m=plane,structural_top_plane_y_xz_m=q['actual_structural_top_plane_y_xz_m'],native_evidence=q,triangle_indices=list(range(first,len(tris))),height_interval_m=[min(y-z for y,z in zip(top,bottom)),max(y-z for y,z in zip(top,bottom))]))
  if union_length(used+[j['interval_t']for j in closed])<1-1e-8:partial.append(dict(owner_id=r['owner_id'],edge_xz_m=[u,v],remaining_fraction=1-union_length(used+[j['interval_t']for j in closed])))
 # Check candidate faces against already emitted joint-bank faces in their own
 # finite vertical plane. Positive-area overlap is rejected, not waved away.
 flat=joint['appended_surfaces']['bank'];existing=[flat[i:i+3]for i in range(0,len(flat),3)];idx=a.geo._SpatialIndex(4)
 for i,t in enumerate(existing):idx.add(i,[[v[0],v[2]]for v in t])
 duplicates=[];maxdistance=0.
 for row in rows:
  u,v=row['edge_xz_m'];L=math.dist(u,v);d=[(v[k]-u[k])/L for k in(0,1)];project=lambda p:[(p[0]-u[0])*d[0]+(p[2]-u[1])*d[1],p[1]]
  for k in row['triangle_indices']:
   t=tris[k];p=[project(x)for x in t]
   for j in idx.candidates([u,v]):
    e=existing[j];distance=max(abs(g.cross(u,v,[x[0],x[2]]))/L for x in e)
    if distance>2e-7:continue
    q=g.clip(p,[project(x)for x in e]);ar=g.area(q)
    if ar>1e-10:duplicates.append(dict(new_triangle=k,joint_triangle=j,overlap_area_m2=ar))
 assert not duplicates,duplicates[:5]
 assert all(a.normal_y(t)==0 or abs(a.normal_y(t))<1e-10 for t in tris)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_EXACT_NATIVE_STRUCTURAL_SIDE_JOIN_R01',status='BOUNDED_VERTICAL_ONLY_PENDING_COMPOSED_REVIEW',base_scene_sha256=joint['base_scene_sha256'],source_surface_hashes={},surface_edits=[],appended_surfaces={'bank':[v for t in tris for v in t]},removed_foundation_proxy_ids=[],source_references=[ref(hp),ref(cp),ref(jp),ref(__import__('pathlib').Path(__file__))])
 out=HERE/'native_structural_side_patch_r01.json';out.write_text(json.dumps(patch,separators=(',',':'))+'\n');report=dict(schema='riverstone.r18.native_structural_side_closure.v1',status='PASS_BOUNDED_VERTICAL_NATIVE_JOIN_GEOMETRY',sources=patch['source_references'],patch=ref(out),rows=rows,triangle_count=len(tris),owner_edge_count=len({(r['owner_id'],str(r['source_edge_xz_m']))for r in rows}),new_walking_top_count=0,positive_area_overlap_with_joint_retaining_faces=duplicates,remaining_partial_edges=partial,maximum_fill_height_m=max((r['height_interval_m'][1]for r in rows),default=0),seconds=time.monotonic()-start,limits=['Only exact support-side or access-skin bearing is used as the lower edge of vertical joins. No roof or structural top becomes a walking owner.','Existing r05 native-closed intervals are not duplicated.','Remaining noble revisions, cemetery producer side closure and unknown tiny fragments are separate ledger entries.','Full composed mesh and controller verification remain required.']);rp=HERE/'native_structural_side_review_r01.json';rp.write_text(json.dumps(report,separators=(',',':'))+'\n');print({k:v for k,v in report.items() if k not in ['rows','sources']});print(ref(rp))
if __name__=='__main__':main()
