"""Exact finite cell-footprint coverage, support and actual native gate clearance."""
import json,math,time
from .author import HERE,ROOT,read,old
from .profile import a
from .audit_native import cols
from .prepare_patch import rectangles
from voxel_character.common import coordinate_planes,render_data

def run():
 start=time.monotonic();p=read(HERE/'profile.json');pack=read(HERE/'resolved_placements.json');ds=[read(ROOT/r['compiled']['path'])for r in pack['assets']];cs=[cols(d)for d in ds];fine=ds[2]['pitch'];profiles=[];ix=old.geo._SpatialIndex(4)
 for i,r in enumerate(p['triangles']):
  poly=[[v[0],v[2]]for v in r['triangle_local_xyz_m']];profiles.append((poly,old.plane(r['triangle_local_xyz_m'])));ix.add(i,poly)
 low,high=999,-999;pieces=0;supportgap=0;bad=[]
 for (x,z),(bottom,top)in cs[2].items():
  poly=[[x*fine,z*fine],[(x+1)*fine,z*fine],[(x+1)*fine,(z+1)*fine],[x*fine,(z+1)*fine]]
  inside=[]
  for i in ix.candidates(poly):
   q=a.clip(poly,profiles[i][0])
   if not q:continue
   inside.append(q);plane=profiles[i][1];ys=[a.common.height(plane,v)for v in q];low=min(low,top-max(ys));high=max(high,top-min(ys));pieces+=1
  if not inside:continue
  supports=[]
  for cc,d in zip(cs[:2],ds[:2]):
   pitch=d['pitch']
   for xx in range(math.floor(poly[0][0]/pitch)-1,math.floor(poly[2][0]/pitch)+1):
    for zz in range(math.floor(poly[0][1]/pitch)-1,math.floor(poly[2][1]/pitch)+1):
     rr=cc.get((xx,zz))
     if rr and rr[0]<=bottom+1e-8 and rr[1]>=bottom-1e-8:supports.append([[xx*pitch,zz*pitch],[(xx+1)*pitch,zz*pitch],[(xx+1)*pitch,(zz+1)*pitch],[xx*pitch,(zz+1)*pitch]])
  residual=a.common.subtract(inside,supports);gap=sum(old.area(q)for q in residual);supportgap+=gap
  if gap>1e-8:bad.append(dict(cell=[x,z],gap_m2=gap))
 fine_masks=rectangles(cs[2],fine);missing=sum(old.area(q)for poly,plane in profiles for q in a.common.subtract([poly],fine_masks))
 s=a.load_scene();gate=next(r for r in s['common_instances']if r['id']==p['main_gate_id']);asset=s['common_assets'][gate['asset_key']];gc=coordinate_planes.compile_master(read(ROOT/asset['master_path']),dict(pitch=asset['pitch_m']),max_candidate_cells=100000,max_output_cells=30000);gr=render_data.make_render_data(gc);original=read(ROOT/asset['render_path']);assert gr['groups']==original['groups'] and gr['bounds']==original['bounds']
 yaw=gate['yaw_rad'];co,si=math.cos(yaw),math.sin(yaw);gp=gate['position_m'];frame=p['bridge_frame'];b,t=frame['basis'],frame['translation'];local=lambda v:[sum(b[j][i]*(v[j]-t[j])for j in range(3))for i in range(3)];conflicts=[];pitch=gc['pitch'];clearance=3.1
 for cell in gc['cells']:
  x,y,z=cell[:3];y0=gp[1]+y*pitch;y1=y0+pitch
  if y0>6 or y1<1:continue
  pp=[]
  for xx,zz in[(x,z),(x+1,z),(x+1,z+1),(x,z+1)]:
   q=local([gp[0]+co*xx*pitch+si*zz*pitch,0,gp[2]-si*xx*pitch+co*zz*pitch]);pp.append([q[0],q[2]])
  for i in ix.candidates(pp):
   q=a.clip(pp,profiles[i][0])
   if not q:continue
   ys=[a.common.height(profiles[i][1],v)for v in q]
   if y0<max(ys)+clearance-1e-8 and y1>min(ys)+.01:conflicts.append(dict(cell=cell[:3],overlap_area_m2=old.area(q),height_interval=[y0,y1],floor_range=[min(ys),max(ys)]))
 result=dict(status='PASS'if missing<1e-7 and supportgap<1e-7 and not bad and low>=-.1 and high<=.1 and not conflicts else'FAIL',finite_profile_pieces=pieces,physical_profile_uncovered_area_m2=missing,unsupported_profile_under_native_cover_m2=supportgap,visible_top_error_range_m=[low,high],native_gate_recompiled_exact=True,gate_clear_height_m=clearance,gate_cell_conflicts=conflicts,support_failures=bad,seconds=time.monotonic()-start,limits=['Gate volume and exact finite cell coverage proof; actual composed-scene controller replay remains required.','No structural certification; native causeway visibly owns the approach volume.'])
 (HERE/'full_cell_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('gate_cell_conflicts','support_failures')},indent=2));assert result['status']=='PASS'
if __name__=='__main__':run()
