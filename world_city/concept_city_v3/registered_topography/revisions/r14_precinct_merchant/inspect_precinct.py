"""Bounded native support and route diagnosis; no source grade edits."""
import json,math,collections
from pathlib import Path
from ..r13_precinct_interfaces import materials as t
HERE=Path(__file__).resolve().parent;PATH=t.CITY/'assemblies/landmarks/registered/precinct_r04/resolved_placements.json';ACCESS=PATH.parent/'exterior_access_proposal.json'
pack=json.loads(PATH.read_bytes());access=json.loads(ACCESS.read_bytes())
route_reports=[]
for r in access['routes']:
 ps=r['polyline_xz_m'];samples=[];bad=[];owners=collections.Counter()
 for si,(a,b) in enumerate(zip(ps,ps[1:])):
  L=math.dist(a,b);nx=-(b[1]-a[1])/L*r['width_m']/2;nz=(b[0]-a[0])/L*r['width_m']/2;n=max(1,math.ceil(L/1))
  for i in range(n+1):
   u=i/n
   for side in [-1,0,1]:
    x=a[0]+u*(b[0]-a[0])+side*nx;z=a[1]+u*(b[1]-a[1])+side*nz
    h=t.land_height_at(x,z);o=t.owner_at(x,z);samples.append(h);owners[o['kind']]+=1
    if abs(h-r['gate_y_m'])>1e-6:bad.append(dict(point_xyz_m=[x,h,z],segment_index=si,fraction=u,width_side=side,owner_id=o['owner_id'],kind=o['kind']))
 for ji,p in enumerate(r['join_polygons_xz_m']):
  for x,z in p:
   h=t.land_height_at(x,z);samples.append(h)
   if abs(h-r['gate_y_m'])>1e-6:
    o=t.owner_at(x,z);bad.append(dict(point_xyz_m=[x,h,z],join_index=ji,owner_id=o['owner_id'],kind=o['kind']))
 route_reports.append(dict(id=r['id'],gate_y_m=r['gate_y_m'],sample_count=len(samples),min_y_m=min(samples),max_y_m=max(samples),nonlevel_samples=bad,owners=dict(owners)))
 print(r['id'],len(bad),flush=True)
gaps=[r for r in pack['actual_bearing_footprints'] if r['maximum_vertex_gap_m']>1e-6]
report=dict(schema='riverstone.precinct_bounded_support_diagnosis.v1',source_pack_sha256=t.R04.sha(PATH),source_access_sha256=t.R04.sha(ACCESS),terrain_module_sha256=t.R04.sha(Path(t.__file__)),gapped_bearings=gaps,gapped_bearing_total_projected_area_m2=sum(t.geo.polygon_area(r['polygon_xz_m']) for r in gaps),maximum_bearing_vertex_gap_m=max((r['maximum_vertex_gap_m'] for r in gaps),default=0),routes=route_reports)
(HERE/'precinct_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print('gaps',len(gaps),report['gapped_bearing_total_projected_area_m2'])
