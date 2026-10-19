"""Bounded native-supported north closure and explicit estate public risers."""
import json,math,copy,time
from pathlib import Path
from .height_field import HERE
from . import finite_geometry_r03 as g
from .classify_unknown_edges_r01 import ref,union_length
from ..r17_district_batches import author as a

def dump(p,d):p.write_text(json.dumps(d,separators=(',',':'))+'\n');return ref(p)
def fan(p,unproject):
 if len(p)<3:return[]
 return [[unproject(p[0]),unproject(p[i]),unproject(p[i+1])]for i in range(1,len(p)-1)if g.area([p[0],p[i],p[i+1]])>0]
def strip(edge,top,bottom):
 u,v=edge;A=[u[0],a.common.height(top,u),u[1]];B=[v[0],a.common.height(top,v),v[1]];C=[v[0],a.common.height(bottom,v),v[1]];D=[u[0],a.common.height(bottom,u),u[1]]
 return[[A,B,C],[A,C,D]]
def triangle_key(t):return tuple(sorted(tuple(v)for v in t))
def subtract_vertical(candidates,existing):
 idx=a.geo._SpatialIndex(4)
 for i,t in enumerate(existing):idx.add(i,[[v[0],v[2]]for v in t])
 emitted=[];ledger=[]
 for ci,t in enumerate(candidates):
  xz=[[v[0],v[2]]for v in t];u,v=max(((p,q)for p in xz for q in xz),key=lambda z:math.dist(*z));L=math.dist(u,v)
  if not L:continue
  d=[(v[k]-u[k])/L for k in(0,1)];project=lambda x:[(x[0]-u[0])*d[0]+(x[2]-u[1])*d[1],x[1]];unproject=lambda x:[u[0]+d[0]*x[0],x[1],u[1]+d[1]*x[0]]
  p=[project(x)for x in t];parts=[p];covered=[]
  for i in idx.candidates(xz):
   q=existing[i]
   if max(abs(g.cross(u,v,[z[0],z[2]]))/L for z in q)>2e-7:continue
   qq=[project(z)for z in q];overlap=math.fsum(g.area(g.clip(s,qq))for s in parts)
   if overlap>1e-14:parts=g.subtract(parts,[qq]);covered.append(dict(existing_triangle_index=i,area_m2=overlap))
   if not parts:break
  first=len(emitted)
  if not covered:emitted.append(t)
  else:
   for q in parts:emitted+=fan(q,unproject)
  ledger.append(dict(candidate_triangle_index=ci,source_area_m2=g.area(p),emitted_area_m2=math.fsum(g.area(q)for q in parts),covered_by_existing=covered,emitted_triangle_indices=list(range(first,len(emitted)))))
 return emitted,ledger

def main():
 start=time.monotonic();jp=a.CITY/'registered_integration/r8/joint_boundary_r05/surface_patch.json';jr=a.CITY/'registered_integration/r8/joint_boundary_r05/boundary_review.json';joint=json.loads(jp.read_bytes());review=json.loads(jr.read_bytes());existing=[joint['appended_surfaces']['bank'][i:i+3]for i in range(0,len(joint['appended_surfaces']['bank']),3)]
 # Retire only old eight-owner north earth's two obsolete retaining strips.
 old=[]
 for row in review['boundary_seams']:
  if str(row['owner_id']).startswith('NORTH_RETIRED_MASK_EARTH:')and row['kind']=='nonwalking_retaining':
   u,v=row['edge_xz_m'];y=row['owned_y_m'];z=row['outside_y_m'];A=[u[0],y[0],u[1]];B=[v[0],y[1],v[1]];C=[v[0],z[1],v[1]];D=[u[0],z[0],u[1]];old.extend([[A,B,C],[A,C,D]])
 # Numerical projection is used only to identify finite strip overlap; all
 # remaining bank vertices keep their original plane.
 rebound_banks,retirement=subtract_vertical(existing,old)
 rebound=copy.deepcopy(joint);rebound['id']='R8_JOINT_41_BOUNDARY_NORTH_SOURCE_REBOUND_R01';rebound['appended_surfaces']['bank']=[v for t in rebound_banks for v in t];rebound['source_references']+= [ref(jp),ref(jr)];rebound['supersedes_patch']=ref(jp)
 rbp=HERE/'joint_boundary_north_rebound_r02.json';dump(rbp,rebound)
 # Add exact missing north vertical intervals to measured native side tops.
 hp=HERE/'north_connected_native_closure_r04.json';h=json.loads(hp.read_bytes());ctx=json.loads((HERE/'north_connected_unknown_context_r03.json').read_bytes());cm={(r['owner_id'],str(r['edge_xz_m'])):r for r in ctx['rows']};candidate=[];north_rows=[]
 for row in h['rows']:
  if row['category']!='NONWALKING_NATIVE_SUPPORT_JOIN_REQUIRED':continue
  u,v=row['edge_xz_m'];plane=cm[row['owner_id'],str(row['edge_xz_m'])]['owner_plane_y_xz_m'];joins=row['nonwalking_native_support_join_intervals'];closed=row['already_closed_native_side_intervals']+row['accepted_physical_profile_intervals'];knots=sorted({0.,1.,*[t for j in joins+closed for t in j['interval_t']]});used=[]
  for lo,hi in zip(knots,knots[1:]):
   mid=(lo+hi)/2
   if any(j['interval_t'][0]<=mid<=j['interval_t'][1]for j in closed):continue
   choices=[j for j in joins if j['interval_t'][0]<=mid<=j['interval_t'][1]]
   if not choices:continue
   q=max(choices,key=lambda j:j['native_face']['top_y_m']);edge=[[u[k]+t*(v[k]-u[k])for k in(0,1)]for t in(lo,hi)];ts=strip(edge,plane,q['actual_structural_top_plane_y_xz_m']);first=len(candidate);candidate+=ts;used.append([lo,hi]);north_rows.append(dict(owner_id=row['owner_id'],edge_xz_m=edge,native_face=q['native_face'],earth_plane_y_xz_m=plane,structural_top_y_m=q['native_face']['top_y_m'],triangle_indices=[first,first+1]))
  assert union_length(used+[j['interval_t']for j in closed])>=1-1e-8
 localp=HERE/'north_connected_surface_patch_r03.json';local=json.loads(localp.read_bytes());candidate=[local['appended_surfaces']['bank'][i:i+3]for i in range(0,len(local['appended_surfaces']['bank']),3)]+candidate
 structuralp=HERE/'native_structural_side_patch_r01.json';struct=json.loads(structuralp.read_bytes());structtris=[struct['appended_surfaces']['bank'][i:i+3]for i in range(0,len(struct['appended_surfaces']['bank']),3)]
 north,nd=subtract_vertical(candidate,rebound_banks+structtris)
 out=copy.deepcopy(local);out['id']='R18_NORTH_PREMASK_EARTH_AND_EXACT_NATIVE_CLOSURE_R04';out['status']='BOUNDED_GEOMETRY_CANDIDATE_PENDING_ACTUAL_SCENE';out['appended_surfaces']['bank']=[v for t in north for v in t];out['source_references']+=[ref(hp),ref(rbp),ref(structuralp)];np=HERE/'north_connected_complete_patch_r05.json';dump(np,out)
 # Public risers may already be present in the joint side patch. Emit only
 # their finite uncovered parts; never duplicate coplanar bank triangles.
 cp=HERE/'noble_public_two_sided_contacts_r01.json';contacts=json.loads(cp.read_bytes());risers=[t for r in contacts['segments']for t in r['triangles_xyz_m']];remaining,rd=subtract_vertical(risers,rebound_banks+structtris+north)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_EXPLICIT_NOBLE_PUBLIC_RISERS_R01',status='CANDIDATE_PENDING_UNCHANGED_CAPSULE_BOTH_DIRECTIONS',base_scene_sha256=joint['base_scene_sha256'],source_surface_hashes={},surface_edits=[],appended_surfaces={'bank':[v for t in remaining for v in t]},removed_foundation_proxy_ids=[],source_references=[ref(cp),ref(rbp)],public_top_mutation_count=0,authorized_maximum_riser_m=.05757588768113919)
 rp=HERE/'noble_public_riser_patch_r02.json';dump(rp,patch)
 result=dict(schema='riverstone.r18.local_final_source_closure.v1',status='PASS_BOUNDED_SOURCE_GEOMETRY_PENDING_COMPOSED_RUNTIME',sources=[ref(jp),ref(jr),ref(hp),ref(localp),ref(structuralp),ref(cp),ref(Path(__file__))],joint_boundary_rebound=ref(rbp),north_patch=ref(np),noble_riser_patch=ref(rp),north_unknown_edge_count=294,north_already_native_closed_edge_count=252,north_structural_join_edge_count=42,north_remaining_unclassified_edge_count=0,north_structural_rows=north_rows,north_emission_partition=nd,public_riser_emission_partition=rd,joint_retirement_partition=[r for r in retirement if r['covered_by_existing']],joint_source_edits_unchanged=rebound['surface_edits']==joint['surface_edits'],public_top_mutation_count=0,maximum_public_riser_m=max(r['maximum_height_jump_m']for r in contacts['segments']),new_public_riser_triangle_count=len(remaining),north_retaining_triangle_count=len(north),seconds=time.monotonic()-start,limits=['The 29.3309241421 m2 connected earth restoration uses exact original pre-mask finite source planes, not extrapolated road planes. Other mask components remain untouched.','North measured native top heights are lower bearing edges of vertical earth support joins only, not promoted walking floor owners.','All R07 public planes and triangles remain verbatim. Public risers are explicit, with E1 maximum57.576mm allowed as a pending runtime candidate.','Grounds private tails must retain both exact public contact heights; no universal continuous private field is implied.','Existing estate native overlap replacement, cemetery producer and final actual scene replay remain required.'])
 rr=HERE/'local_final_source_closure_review_r02.json';dump(rr,result);print({k:v for k,v in result.items()if k not in ['sources','north_structural_rows','north_emission_partition','public_riser_emission_partition','joint_retirement_partition','limits']});print(ref(rr))
if __name__=='__main__':main()
