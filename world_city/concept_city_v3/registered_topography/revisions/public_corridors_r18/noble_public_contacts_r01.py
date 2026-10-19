"""Local exact two-sided estate/public contacts. All R07 top data is unchanged."""
import json,math,itertools,collections
from .height_field import HERE
from . import finite_geometry_r03 as g
from .audit_tjunctions_r01 import contains
from .classify_unknown_edges_r01 import ref
from ..r17_district_batches import author as a

def shared_edges(p,q):
 out=[]
 for u,v in zip(p,p[1:]+p[:1]):
  L=math.dist(u,v)
  if L<1e-9:continue
  for x,y in zip(q,q[1:]+q[:1]):
   if math.dist(x,y)<1e-9:continue
   distance=max(abs(g.cross(u,v,w))/L for w in(x,y))
   if distance>1e-9:continue
   tt=[sum((w[k]-u[k])*(v[k]-u[k])for k in(0,1))/(L*L)for w in(x,y)];lo=max(0,min(tt));hi=min(1,max(tt))
   if (hi-lo)*L<1e-9:continue
   out.append(dict(edge_xz_m=[[u[k]+t*(v[k]-u[k])for k in(0,1)]for t in(lo,hi)],maximum_collinear_roundoff_m=distance))
 return out

def main():
 fp=HERE/'finite_field_candidate_r07_native_bound.json';pub=json.loads(fp.read_bytes());by={r['id']:r for r in pub['records']};directory=a.CITY/'registered_topography/revisions/r17_district_batches/noble_terminal_assist_r03';rows=[];segments={};sources=[ref(fp)]
 for path in sorted(directory.glob('E*_proposal.json')):
  d=json.loads(path.read_bytes());sources.append(ref(path));local={r['id']:r for r in d['fixed_regions']}
  for c in d['result'].get('conflicts',[]):
   p=c['point_xz_m'];matches=[]
   for id in c['fixed_region_ids']:
    r=by.get(id,local[id]);inside=contains(p,r['polygon_xz_m']);matches.append(dict(id=id,finite_contains=inside,height_m=a.common.height(r['plane_y_xz_m'],p),polygon_xz_m=r['polygon_xz_m'],plane_y_xz_m=r['plane_y_xz_m']))
   matched=[r for r in matches if r['finite_contains']];related=[]
   for x,y in itertools.combinations(matched,2):
    if abs(x['height_m']-y['height_m'])<1e-7:continue
    for edge in shared_edges(x['polygon_xz_m'],y['polygon_xz_m']):
     u,v=edge['edge_xz_m'];L=math.dist(u,v);t=sum((p[k]-u[k])*(v[k]-u[k])for k in(0,1))/(L*L)
     if not -1e-8<=t<=1+1e-8 or abs(g.cross(u,v,p))/L>1e-9:continue
     key=(tuple(sorted([x['id'],y['id']])),tuple(tuple(z)for z in edge['edge_xz_m']));sid='NOBLE_PUBLIC_RISER:'+str(len(segments))
     if key in segments:sid=segments[key]['id']
     else:
      dy=[a.common.height(x['plane_y_xz_m'],w)-a.common.height(y['plane_y_xz_m'],w)for w in(u,v)];breaks=[0,1]
      if dy[0]*dy[1]<0:breaks.insert(1,dy[0]/(dy[0]-dy[1]))
      triangles=[]
      for lo,hi in zip(breaks,breaks[1:]):
       ep=[[u[k]+tt*(v[k]-u[k])for k in(0,1)]for tt in(lo,hi)];mid=[(ep[0][k]+ep[1][k])/2 for k in(0,1)];high,low=(x,y)if a.common.height(x['plane_y_xz_m'],mid)>a.common.height(y['plane_y_xz_m'],mid)else(y,x)
       # Orient the side outward from the higher polygon's interior.
       center=[sum(w[k]for w in high['polygon_xz_m'])/len(high['polygon_xz_m'])for k in(0,1)]
       if g.cross(ep[0],ep[1],center)<0:ep.reverse()
       A,B=[[w[0],a.common.height(high['plane_y_xz_m'],w),w[1]]for w in ep];C,D=[[w[0],a.common.height(low['plane_y_xz_m'],w),w[1]]for w in reversed(ep)]
       for tri in [[A,B,C],[A,C,D]]:
        v1=[tri[1][k]-tri[0][k]for k in range(3)];v2=[tri[2][k]-tri[0][k]for k in range(3)];cross=[v1[1]*v2[2]-v1[2]*v2[1],v1[2]*v2[0]-v1[0]*v2[2],v1[0]*v2[1]-v1[1]*v2[0]]
        if math.hypot(*cross)>1e-14:triangles.append(tri)
      segments[key]=dict(id=sid,estate_ids=[d['owner_id']],owner_ids=[x['id'],y['id']],edge_xz_m=edge['edge_xz_m'],plane_y_xz_m_by_owner={x['id']:x['plane_y_xz_m'],y['id']:y['plane_y_xz_m']},maximum_height_jump_m=max(map(abs,dy)),endpoint_signed_height_differences_m=dy,triangles_xyz_m=triangles,maximum_collinear_roundoff_m=edge['maximum_collinear_roundoff_m'],classification='ACCIDENTAL_INTERPOLATION_JOIN_REPRESENTED_AS_EXPLICIT_RISER_CANDIDATE',runtime_acceptance='PENDING_UNCHANGED_CAPSULE_BOTH_DIRECTIONS',within_parent_0_04m_bound=max(map(abs,dy))<=.04)
     related.append(sid)
   spread=max((r['height_m']for r in matched),default=0)-min((r['height_m']for r in matched),default=0)
   rows.append(dict(estate_id=d['owner_id'],point_xz_m=p,reported_ids=c['fixed_region_ids'],matches=matches,finite_height_spread_m=spread,paired_segment_ids=sorted(set(related)),classification='EXACT_TWO_SIDED_PUBLIC_CONTACT'if related else('POINT_ONLY_PUBLIC_HEIGHT_SPLIT'if spread>1e-7 else'REJECTED_REMOTE_TINY_POLYGON_MATCH')))
 out=dict(schema='riverstone.r18.noble_public_two_sided_contacts.v1',status='FINITE_CONTACT_CANDIDATE_PENDING_COMPOSED_COLLISION',sources=sources,rows=rows,segments=list(segments.values()),public_top_mutation_count=0,policy=['All R07 public polygons, planes and rendered triangles are preserved verbatim.','At a paired segment, preserve both plane-specific boundary knots. A single-valued private field must partition along the riser continuation rather than average heights.','These are accidental interpolation seams made explicit as candidate risers, not original authored stair semantics.','Each riser needs actual unchanged-controller traversal both ways. Segments above 0.04 m remain explicit holds.','Public ownership remains canonical; no private cap may cover it.'])
 op=HERE/'noble_public_two_sided_contacts_r01.json';op.write_text(json.dumps(out,separators=(',',':'))+'\n');print(ref(op));print(collections.Counter(r['classification']for r in rows));print('segments',len(segments),'max',max(r['maximum_height_jump_m']for r in segments.values()),'over4cm',[(r['estate_ids'],r['owner_ids'],r['maximum_height_jump_m'])for r in segments.values()if not r['within_parent_0_04m_bound']])
if __name__=='__main__':main()
