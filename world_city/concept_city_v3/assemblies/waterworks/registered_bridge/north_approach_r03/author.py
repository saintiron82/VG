"""Supported north road connector through existing common master/compiler.

Source geometry is continuous; pitches are independent sampling choices. The
road collision contract is a measured continuous top with bounded visible
sampling error, never a controller step-up or an unsupported collision ramp.
"""
import copy,json,math,time
from pathlib import Path
from .profile import HERE,ROOT,CITY
from ..south_approach_r02 import author as old
from voxel_character.common import coordinate_planes,render_data
from world_city.runtime_city.parts.author import extrusion,box
PITCH=.1;THICKNESS=.4;GUARD=.05
ref=old.ref;read=old.read

def write(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def source_base(name):
 original=read(HERE.parent/'drawbridge_candidate/masters/stone_approaches.json')
 return dict(schema='riverstone.voxel.master.v1',id=name,revision=3,axes=original['axes'],grid_origin=[0,0,0],materials=original['materials'],coordinate_planes=[],components=[],instances=[],constraints=[dict(id='present',kind='nonempty',selector={}),dict(id='connected',kind='connected',selector={})],provenance=dict(profile=ref(HERE/'profile.json'),author=ref(__file__),common_only=True,new_mesher=False,cell_edits=False))
def cover(p,coarse=False):
 m=source_base('registered_north_approach_r03_'+('supported_causeway'if coarse else'visible_road'))
 for i,r in enumerate(p['triangles']):
  tri=r['triangle_local_xyz_m']
  if coarse and min(v[0]for v in tri)>=-72-1e-8:continue
  poly=[[v[0],v[2]]for v in tri];gx,gz,c=old.plane(tri);g=math.hypot(gx,gz);u=[gx/g,gz/g]if g>1e-10 else[1,0];v=[-u[1],u[0]];a=tri[0]
  apron=.35 if coarse else GUARD
  expanded=old.hull([[x+dx,z+dz]for x,z in poly for dx in[-apron,apron]for dz in[-apron,apron]])
  us=[(q[0]-a[0])*u[0]+(q[1]-a[2])*u[1]for q in expanded];vs=[(q[0]-a[0])*v[0]+(q[1]-a[2])*v[1]for q in expanded];lo,hi=min(us),max(us);vl,vh=min(vs),max(vs)
  hull=old.hull([[a[0]+s*u[0]+t*v[0],a[2]+s*u[1]+t*v[1]]for s in[lo,hi]for t in[vl,vh]])
  lower=lambda s:-4.5-a[1]if coarse else g*s-THICKNESS
  top=lambda s:g*s-(.175 if coarse else 0)
  ops=[dict(id='supported_volume',part='solid',action='paint',material='stone',shape=extrusion([[lo,lower(lo)],[hi,lower(hi)],[hi,top(hi)],[lo,top(lo)]],vl,vh),transform=dict(basis=[[u[0],0,v[0]],[0,1,0],[u[1],0,v[1]]],translation=a))]
  for j,outside in enumerate(old.geo.convex_difference(hull,expanded)):
   if old.area(outside)<1e-10:continue
   ops.append(dict(id=f'clip_{j}',part='solid',action='cut',shape=extrusion([[x,-z]for x,z in outside],-5 if coarse else min(q[1]for q in tri)-THICKNESS-.2,max(q[1]for q in tri)+.2),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
  name=f'section_{i}';m['components'].append(dict(id=name,parts=[dict(id='solid',pivot=[0,0,0])],operations=ops));m['instances'].append(dict(id=name,component=name))
 # Exact endpoint stops avoid aprons overlapping retained native/terrain tops.
 m['assembly_cuts']=[dict(id='north_seam_stop',selector={},action='cut',shape=box([-108,-6,-6],[-106,4,6])),dict(id='bridge_stop',selector={},action='cut',shape=box([-64,-6,-6],[-62,4,6]))]
 if coarse:
  # A bounded bearing-course cap closes the measured 0.30 m old-deck gap.
  m['components'].append(dict(id='north_bearing_course',parts=[dict(id='solid',pivot=[0,0,0])],operations=[dict(id='bearing_course',part='solid',action='paint',material='stone',shape=box([-72,1,-3.125],[-64,1.5,3.125]))]))
  m['instances'].append(dict(id='north_bearing_course',component='north_bearing_course'))
 m['provenance'].update(clear_width_m=6,visual_pitch_m=.25 if coarse else PITCH,thickness_m=None if coarse else THICKNESS,bed_bottom_y_m=-4.5 if coarse else None,central_navigation_untouched_local_x_greater_than=-64)
 return m

def fixed(p):
 src=HERE.parent/'south_approach_r02/sources/registered_south_approach_r02_recessed_fixed.json';m=read(src);m['id']='registered_north_approach_r03_recessed_fixed';m['revision']=3
 m['assembly_cuts'].append(dict(id='north_road_finite_cap_recess',selector={},action='cut',shape=box([-72,1.3,-3.15],[-64,2.2,3.15])))
 m['provenance']['north_r03']=dict(source=ref(src),profile=ref(HERE/'profile.json'),scope='Only local X[-72,-64], Z+-3.15, Y[1.3,2.2] road-cap recess. Existing southern approach and central mechanism source unchanged.')
 return m

def compile_one(m,pitch,cap=4000000,outcap=900000):
 name=m['id'];mp=HERE/'sources'/(name+'.json');write(mp,m);start=time.monotonic();c=coordinate_planes.compile_master(m,dict(pitch=pitch),max_candidate_cells=cap,max_output_cells=outcap);assert c['valid'],c.get('constraints');r=render_data.make_render_data(c);cp=HERE/'cache'/(name+'.compiled.json');rp=HERE/'cache'/(name+'.render.json');write(cp,c);write(rp,r)
 result=dict(id=name,source=ref(mp),cache=ref(rp),compiled=ref(cp),pitch_m=pitch,bounds=r['bounds'],candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=r['quad_count'],seconds=time.monotonic()-start);write(HERE/(name+'.record.json'),result);print(json.dumps(result),flush=True);return result

def main():
 p=read(HERE/'profile.json');assert p['maximum_grade']<=.12
 rows=[compile_one(fixed(p),.25),compile_one(cover(p,True),.25),compile_one(cover(p),PITCH)]
 f=p['bridge_frame'];yaw=math.atan2(f['basis'][0][2],f['basis'][0][0]);ids=['BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED','BRIDGE_MAIN_RIVER:NORTH_SUPPORTED_CAUSEWAY','BRIDGE_MAIN_RIVER:NORTH_VISIBLE_ROAD']
 pack=dict(schema='riverstone.r8.north_connector.native.v1',status='NATIVE_COMPILED_PENDING_FINITE_OWNERSHIP_AND_CAPSULE_REPLAY',assets=rows,placements=[dict(id=pid,asset_key=r['id'],position_m=f['translation'],yaw_rad=yaw,palette_id='native_bridge',palette_override={},scale=[1,1,1])for pid,r in zip(ids,rows)],replaced_placement_ids=[ids[0]],source_refs=[ref(HERE/'profile.json')],limits=['Continuous collision override and precise original terrain clipping required before promotion.','No central leaf, chain, vessel or guarded interlock change.'])
 write(HERE/'resolved_placements.json',pack)
if __name__=='__main__':main()
