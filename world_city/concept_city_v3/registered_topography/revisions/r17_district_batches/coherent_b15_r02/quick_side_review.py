import json,math,time
from .. import author as a,side_clearance
from .source_preflight import HERE,write

def run():
 t=time.monotonic();d=json.loads((HERE/'composition_report.json').read_bytes());owners=[x for x in d['rendered_owner_parts']if x['kind']in('active_walking','shared_public_profile','moved_level_public_entry','level_public_tail','functional_court')];s=json.loads((HERE/'interfaces.json').read_bytes());scene=dict(surfaces=dict(bank=[v for tri in s['appended_retaining_triangles_xyz_m']for v in tri]));result=side_clearance.SideIndex(scene).audit(owners);contacts=[];boundary=[];lookup={}
 for o in owners:lookup.setdefault(o['id'],[]).append(o)
 for r in result['contacts']:
  # A side exactly on a closed walking polygon boundary has no interior
  # occupation. Keep this as explicit retaining-edge evidence.
  polys=lookup[r['owner_id']];touch=False
  for o in polys:
   p=o['polygon_xz_m'];sign=1 if a.geo.signed_polygon_area(p)>0 else-1
   if any(all(abs(a.geo._cross(u,v,[q[0],q[2]]))<=1e-7*max(math.dist(u,v),1.)for q in r['intersection_vertices_xyz_m'])for u,v in zip(p,p[1:]+p[:1])):touch=True;break
  (boundary if touch else contacts).append(r)
 result.update(interior_contacts=contacts,boundary_only_contacts=boundary,elapsed_s=time.monotonic()-t);write('new_side_review_r01.json',result);print('interior',len(contacts),'boundary',len(boundary),'elapsed',result['elapsed_s'],flush=True)
if __name__=='__main__':run()
