import json,math,collections
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write,index
from ..bounded_profile_r01.finite import inside
from ..noble_terminal_assist_r02.solve import point_distance
from ..incident_risers_r02.solve import interval
from .gradient_links import solve_field
HERE=Path(__file__).resolve().parent
D=a.HERE/'noble_terminal_diagnosis_r01/E1_proposal.json';d=json.loads(D.read_bytes());design=json.loads((HERE/'cut_design_boundary.json').read_bytes());p=design['points'];tris=design['original_triangles'];path=design['vertex_path'];original_p=[q[:]for q in p];original_t=[t[:]for t in tris];fixed={int(k):v for k,v in design['fixed_heights'].items()};sector=design['start_sector'];copies=sector['copies'];fixed.pop(copies[1]);parts=design['component_triangles'];assert len(parts)==2
anchors={int(k):v for k,v in sector['sector_anchors'].items()};ci=[]
for part in parts:
 clusters={anchors[k]for k in part if k in anchors};assert len(clusters)==1,clusters;ci.append(clusters.pop())
assert set(ci)=={0,1}
low=ci.index(0);high=ci.index(1);duplicate={}
for v in path:duplicate[v]=len(p);p.append(p[v][:])
for j in parts[high]:tris[j]=[duplicate.get(i,i)for i in tris[j]]
for v in path:
 if v in fixed:fixed[duplicate[v]]=fixed[v]
start=path[0];fixed[start]=sector['clusters'][0]['y'];fixed[duplicate[start]]=sector['clusters'][1]['y'];delta=fixed[duplicate[start]]-fixed[start];station=[0.]
for u,v in zip(path,path[1:]):station.append(station[-1]+math.dist(p[u],p[v]))
end_at=next(station[j]for j,v in enumerate(path)if j and v in fixed);equalities=[(v,duplicate[v],delta*max(0.,1-st/end_at))for st,v in zip(station,path)]
old=json.loads((a.ROOT/d['target_source']['path']).read_bytes())['top_pieces'];ix=index(old);fallback=[]
def target(q):
 matches=[r for i in ix.candidates([q])if inside(q,(r:=old[i])['polygon_xz_m'])]
 if matches:return a.common.height(matches[0]['plane_y_xz_m'],q)
 i,dist=min(((i,point_distance(q,r['polygon_xz_m']))for i,r in enumerate(old)),key=lambda t:t[1]);fallback.append(dict(point_xz_m=q,distance_m=dist,source_piece_index=i));return a.common.height(old[i]['plane_y_xz_m'],q)
ys=[fixed.get(i,target(q))for i,q in enumerate(p)];result=solve_field(p,tris,fixed,ys,.12,equalities);out=dict(owner_id='E1',source=d['source'],target_source=d['target_source'],private_domain_polygons_xz_m=d['private_domain_polygons_xz_m'],fixed_public_regions=d['fixed_public_regions'],fixed_inner_regions=d['fixed_inner_regions'],cut_design=dict(path=str((HERE/'cut_design_boundary.json').relative_to(a.ROOT)),sha256=a.sha(HERE/'cut_design_boundary.json')),result=result,extrapolated_soft_targets=fallback,activation=False)
if result['status']=='PASSED_FINITE_TRIANGLE_GRADE':
 ys=result['heights_m'];risers=[];errors=[]
 for u,v in zip(path,path[1:]):
  low_y=[ys[u],ys[v]];high_y=[ys[duplicate[u]],ys[duplicate[v]]];q=[p[u],p[v]];quad=[[q[0][0],low_y[0],q[0][1]],[q[1][0],low_y[1],q[1][1]],[q[1][0],high_y[1],q[1][1]],[q[0][0],high_y[0],q[0][1]]];emitted=[]
  edgeowners=[j for j in parts[low]if u in original_t[j]and v in original_t[j]];assert len(edgeowners)==1;centroid=[sum(original_p[k][ax]for k in original_t[edgeowners[0]])/3 for ax in[0,1]];mid=[(q[0][ax]+q[1][ax])/2 for ax in[0,1]]
  for tri in [[quad[0],quad[1],quad[2]],[quad[0],quad[2],quad[3]]]:
   b=[tri[1][k]-tri[0][k]for k in range(3)];c=[tri[2][k]-tri[0][k]for k in range(3)];n=[b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0]]
   if math.sqrt(sum(w*w for w in n))<1e-12:continue
   if n[0]*(centroid[0]-mid[0])+n[2]*(centroid[1]-mid[1])<0:tri=[tri[0],tri[2],tri[1]]
   emitted.append(tri)
  if emitted:risers.append(dict(edge_xz_m=q,left_heights_m=low_y,right_heights_m=high_y,triangles_xyz_m=emitted,maximum_step_m=max(abs(high_y[k]-low_y[k])for k in[0,1]),material='bank',walking_surface=False))
 edges=collections.defaultdict(list)
 for j,t in enumerate(original_t):
  for u,v in zip(t,t[1:]+t[:1]):edges[tuple(sorted([u,v]))].append(j)
 fixedregions=d['fixed_public_regions']+d['fixed_inner_regions'];fi=index(fixedregions)
 for (u,v),owners in edges.items():
  if len(owners)!=1:continue
  j=owners[0];mapping=dict(zip(original_t[j],tris[j]));q=[original_p[u],original_p[v]];y=[ys[mapping[u]],ys[mapping[v]]]
  for k in fi.candidates(q):
   r=fixedregions[k];span=interval(*q,r['polygon_xz_m'])
   if not span or(span[1]-span[0])*math.dist(*q)<=1e-7:continue
   err=max(abs((1-t)*y[0]+t*y[1]-a.common.height(r['plane_y_xz_m'],[(1-t)*q[0][ax]+t*q[1][ax]for ax in[0,1]]))for t in span)
   if err>1e-7:errors.append(dict(edge_xz_m=q,source_id=r['id'],error_m=err))
 expected=sum(a.geo.polygon_area(q)for q in d['private_domain_polygons_xz_m']);area=sum(a.geo.polygon_area(t['polygon_xz_m'])for t in result['triangles']);out['result']=dict(status='PASSED_FINITE_PROFILE_WITH_DECLARED_INCIDENT_RISERS'if not errors and abs(area-expected)<1e-7 else'HELD_BOUNDARY_OR_COVERAGE',result=result,vertical_risers=risers,boundary_errors=errors,domain_area_m2=expected,triangulated_area_m2=area,maximum_step_m=max(r['maximum_step_m']for r in risers),linear_taper_equalities=equalities)
write(HERE/'E1_proposal.json',out);print(out['result']['status'],out['result'].get('result',{}).get('maximum_gradient'),out['result'].get('maximum_step_m'))
