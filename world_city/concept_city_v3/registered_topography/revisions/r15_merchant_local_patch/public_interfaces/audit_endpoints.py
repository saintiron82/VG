"""All19 endpoints split against exact frozen R5 triangles, not nine anchors."""
from inspect_extents import *
from solve_interfaces import distance

def endpoint_report(g,num):
 p,q=g['polygon_xz_m'][3],g['polygon_xz_m'][2];rows=[];knots=[0.,1.]
 for mat,i,t,poly in candidates([p,q]):
  interval=a.segment_mask_interval(p,q,poly)
  if interval:
   plane=a.affine_plane(t);rows.append(dict(material=mat,triangle_index=i,interval_t=interval,plane_y_xz_m=plane,vertices_xyz_m=t));knots.extend(interval)
 knots=sorted(set(round(max(0.,min(1.,v)),12) for v in knots));pieces=[];maximum=0.;uncovered=0.;multivalued=0.
 ep=g['endpoint_profile']
 def proposed(t):
  u=t*(len(ep)-1);k=min(len(ep)-2,int(u));u-=k;return ep[k]['y_m']*(1-u)+ep[k+1]['y_m']*u
 for lo,hi in zip(knots,knots[1:]):
  if hi-lo<1e-11:continue
  mid=(lo+hi)/2;active=[r for r in rows if r['interval_t'][0]<=mid+1e-10 and r['interval_t'][1]>=mid-1e-10];span=[[(1-t)*p[k]+t*q[k] for k in(0,1)] for t in(lo,hi)];hits=[]
  for r in active:
   yy=[a.plane_height(r['plane_y_xz_m'],*v) for v in span];delta=max(abs(y-proposed(t)) for y,t in zip(yy,(lo,hi)));maximum=max(maximum,delta);hits.append(dict(material=r['material'],triangle_index=r['triangle_index'],vertices_xyz_m=r['vertices_xyz_m'],plane_y_xz_m=r['plane_y_xz_m'],endpoint_xyz_m=[[v[0],y,v[1]] for v,y in zip(span,yy)],nine_anchor_max_error_on_segment_m=delta))
  if not hits:uncovered+=math.dist(*span)
  if hits:
   spread=max(max(h['endpoint_xyz_m'][k][1] for h in hits)-min(h['endpoint_xyz_m'][k][1] for h in hits) for k in(0,1));multivalued=max(multivalued,spread)
  pieces.append(dict(t_interval=[lo,hi],segment_xz_m=span,source_triangles=hits))
 return dict(index=num,gate_id=g['id'],property_id=g['property_id'],terminal_segment_xz_m=[p,q],width_m=math.dist(p,q),actual_frozen_segments=pieces,maximum_nine_anchor_vs_actual_triangle_error_m=maximum,uncovered_terminal_length_m=uncovered,maximum_same_segment_frozen_height_spread_m=multivalued)

def run():
 reports=[endpoint_report(g,n) for n,g in enumerate(C['gate_profiles'])]
 output=dict(schema='riverstone.r15_actual_frozen_endpoint_proof.v1',source_contract_sha256=a.sha(HERE.parent/'source_contract.json'),source_scene_sha256=a.sha(SCENE),frozen_reference_sha256=a.sha(HERE.parent/'frozen_local_reference.json'),gate_count=len(reports),reports=reports,limits=['Input endpoint binding only. A proposed nine-anchor endpoint is not promoted by this report.','Accepted joint fields may move the old terminal within a finite shared collar; their final exterior seams remain fixed.'])
 (HERE/'all19_frozen_endpoint_proof.json').write_text(json.dumps(output,indent=2)+'\n')
 print([(r['index'],r['maximum_nine_anchor_vs_actual_triangle_error_m'],r['uncovered_terminal_length_m'],r['maximum_same_segment_frozen_height_spread_m']) for r in reports],flush=True)
if __name__=='__main__':run()
