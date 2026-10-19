"""Reject stepped seams between active finite walking owners."""
import json,math,time
from .. import author as a
from .source_preflight import HERE,write

def run():
 t=time.monotonic();scene=a.load_scene();d=json.loads((HERE/'composition_report.json').read_bytes());parts=d['rendered_owner_parts'];idx=a.geo._SpatialIndex(16)
 for i,o in enumerate(parts):idx.add(i,o['polygon_xz_m'])
 data=json.loads((HERE/'interfaces.json').read_bytes());old=a.TriangleIndex(scene,[r['edge_xz_m']for r in data['boundary_seams']]);walk={'active_walking','functional_court','shared_public_profile','moved_level_public_entry','level_public_tail'}
 def query(p):
  for i in idx.candidates([p]):
   o=parts[i]
   if a.geo.point_in_convex_polygon(p,o['polygon_xz_m'],1e-10):return dict(id=o['id'],active=o['kind']in walk,kind=o['kind'],plane=o['plane_y_xz_m'])
  for i in old.index.candidates([p]):
   o=old.rows[i]
   if a.geo.point_in_convex_polygon(p,o['polygon_xz_m'],1e-10):return dict(id=str((o['material'],o['triangle_index'])),active=o['material']in('road','alley'),kind='retained_source',plane=o['plane_y_xz_m'])
  return dict(id=None,active=False,kind='native_or_unowned')
 records=[];bad=[]
 for r in data['boundary_seams']:
  if r['maximum_delta_m']<1e-7:continue
  p,q=r['edge_xz_m'];L=math.dist(p,q);n=[-(q[1]-p[1])/L,(q[0]-p[0])/L];m=[(p[k]+q[k])/2 for k in(0,1)];left=query([m[k]+n[k]*1e-5 for k in(0,1)]);right=query([m[k]-n[k]*1e-5 for k in(0,1)]);row=dict(r,left=left,right=right,active_both_sides=left['active']and right['active']);records.append(row)
  if row['active_both_sides']:bad.append(row)
 result=dict(scene_patch_sha256=a.sha(HERE/'candidate_scene_patch.json'),noncontinuous_edges=len(records),active_step_failures=bad,records=records,elapsed_s=time.monotonic()-t,status='PASS'if not bad else'FAILED_ACTIVE_STEP',activation=False);write('walking_seam_review_r01.json',result);print('active steps',len(bad),'edges',len(records),'time',result['elapsed_s'])
if __name__=='__main__':run()
