"""All native exterior leaves receive finite full-width shared-court routes."""
from .geometry import *

def run():
 layout=load(HERE/'selected_layout.json');holds={h['id']:h for h in layout['holdings']};placements={p['id']:p for p in layout['placements']};allobstacles=[q for p in layout['placements']for q in p['native_walking_obstacles_xz_m']];obstacles=raster(allobstacles,True);routes=[];failed=[]
 for d in layout['actual_doors']:
  h=holds[d['holding_id']];w=d['exterior_route_width_m'];allowed=raster([h['holding_polygon_xz_m']]+h['external_route_polygons_xz_m']);free=allowed&~obstacles;clear=ndimage.distance_transform_edt(free)*GRID>=w/2+.2;n=d['outward_xz'];lip=d['threshold_lip_xz_m'];approach=[lip[k]+n[k]*(w/2+1.0)for k in(0,1)];start=nearest(clear,approach,2.5);end=nearest(clear,h['gate_position_xz_m'],3);goals=np.zeros(SHAPE,bool)
  if end:goals[end]=True
  line=astar(clear,start,goals)if start and end else None
  if not line:failed.append(dict(door_id=d['id'],reason='No full-width native-obstacle-clear path through the holding to its gate'));continue
  line=line+[h['gate_position_xz_m']];line=[q for j,q in enumerate(line)if j==0 or math.dist(q,line[j-1])>1e-7];portal_width=min(w,min(f['width_m']for f in d['native_face_evidence'])-.125);neck=[lip[k]+n[k]*(portal_width/2+.4)for k in(0,1)];portal=[lip,neck,line[0]];ps=ribbons(portal,portal_width,caps=False)+ribbons(line,w,caps=True);hits=[]
  for i,p in enumerate(ps):
   for j,q in enumerate(allobstacles):
    a=geo.intersection_area(p,q)
    if a>1e-6:hits.append(dict(route_piece=i,obstacle=j,area_m2=a))
  if hits:failed.append(dict(door_id=d['id'],reason='Exact native walking collision in complete ribbon/join geometry',overlaps=hits));continue
  routes.append(dict(id=d['id']+':COURT_LINK',door_id=d['id'],holding_id=d['holding_id'],parcel_id=d['parcel_id'],floor_y_m=h['floor_y_m'],width_m=w,polyline_xz_m=[lip,neck]+line,polyline_xyz_m=[[q[0],h['floor_y_m'],q[1]]for q in [lip,neck]+line],polygons_xz_m=ps,native_door_threshold_neck=dict(width_m=portal_width,polyline_xz_m=portal,policy='The finite threshold neck matches the actual native leaf width, then joins the wider courtyard lane. No broad cart-through-door claim.'),length_m=sum(math.dist(a,b)for a,b in zip(portal,portal[1:]))+sum(math.dist(a,b)for a,b in zip(line,line[1:])),native_walking_overlap_area_m2=0,joins_gate_xz_m=h['gate_position_xz_m'],status='Exact native walking masks clear; source terrain and final capsule review pending'))
 out=dict(schema='riverstone.district_fabric.access.v1',layout=ref(HERE/'selected_layout.json'),routes=routes,unresolved_doors=failed,summary=dict(actual_native_exterior_doors=len(layout['actual_doors']),finite_full_width_door_links=len(routes),unresolved_doors=len(failed),shared_backbone_routes=len(layout['shared_private_routes'])),limits=['Closed native door leaves are interaction anchors; no interior or NPC navigation claim.','Threshold routes meet the exterior leaf approach without a rounded cap extending backwards into the wall.','All interior bends have full circumscribed joins; roof overhangs are not walking obstructions.']);write(HERE/'access_handoff.json',out);print(json.dumps(out['summary'],indent=2));print(json.dumps(failed,indent=2)[:2500]);return out
if __name__=='__main__':run()
