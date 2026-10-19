"""Bounded check of the actual 8 m preview fan, separate from analytic grades."""
import json, math, time
from . import author as a
from world_city.concept_city_v3.review_geometry import fan, prune_collinear_xyz

def grade(t):
 p,q,r=t; ux,uz=q[0]-p[0],q[2]-p[2];vx,vz=r[0]-p[0],r[2]-p[2]
 det=ux*vz-uz*vx
 if abs(det)<=1e-10:return None
 dy,dv=q[1]-p[1],r[1]-p[1]
 return math.hypot((dy*vz-dv*uz)/det,(ux*dv-vx*dy)/det)

def run(output_name='preview_audit_repaired.json'):
 start=time.monotonic();b=a.COLLAR_BOUNDS;stats={};bad=[];tile_count=0
 for x in range(math.floor(b[0]/8)*8,math.ceil(b[2]/8)*8,8):
  for z in range(math.floor(b[1]/8)*8,math.ceil(b[3]/8)*8,8):
   tile_count+=1
   for r in a.surface_domains([x,z,x+8,z+8]):
    if not r.get('render_land',True) or not r['kind'].startswith('r14_'):continue
    pts=prune_collinear_xyz([[p[0],a.surface_height_at(r,*p),p[1]] for p in r['polygon_xz_m']])
    for t in fan(pts):
     g=grade(t)
     if g is None:continue
     key=r['kind'];s=stats.setdefault(key,dict(triangle_count=0,maximum_grade=0.,steeper_than_12pct=0,maximum_sampled_analytic_departure_m=0.));s['triangle_count']+=1;s['maximum_grade']=max(s['maximum_grade'],g)
     if key=='r14_public_profile':
      for p in t+[[sum(v[k] for v in t)/3 for k in range(3)]]:s['maximum_sampled_analytic_departure_m']=max(s['maximum_sampled_analytic_departure_m'],abs(p[1]-a.source_surface_height_at(r,p[0],p[2])))
     if g>.12000001:
      s['steeper_than_12pct']+=1
      if len(bad)<100:bad.append(dict(tile=[x,z,x+8,z+8],owner_id=r['owner_id'],road_id=r.get('road_id'),grade=g,vertices_xyz_m=t))
 result=dict(schema='riverstone.r14_preview_fan_audit.v1',author_sha256=a.R04.sha(a.HERE/'author.py'),bounds_xz_m=b,tile_count=tile_count,stats=stats,failures=bad,seconds=time.monotonic()-start,limitations=['Matches current vertex sampling/pruning/fan before additional integration floor masks.','Material-plane subdivision preserves these triangle gradients.','No capsule or final common terrain approval.'])
 (a.HERE/output_name).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='failures'},indent=2));return result
if __name__=='__main__':run()
