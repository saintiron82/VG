"""Bounded southern road cover through unchanged common compiler.

The physical profile is continuous; the visible cover is sampled at 5 cm.
Only derived coarse road-cap cuts change. Original bridge inputs stay frozen.
"""
import copy,hashlib,json,math,pathlib,sys,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3';BASE=HERE.parent
from voxel_character.common import coordinate_planes,render_data
from world_city.runtime_city.checks import placement as geo
from world_city.runtime_city.parts.author import extrusion
PITCH=.05;THICKNESS=.4;GUARD=.05
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def ref(p):return {'path':str(pathlib.Path(p).relative_to(ROOT)),'sha256':sha(p)}
def write(p,d):
 with pathlib.Path(p).open('x') as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
def area(p):return geo.polygon_area(p)
def hull(ps):
 ps=sorted(set(map(tuple,ps)));cross=lambda a,b,c:(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);lo=[];hi=[]
 for p in ps:
  while len(lo)>1 and cross(lo[-2],lo[-1],p)<=0:lo.pop()
  lo.append(p)
 for p in reversed(ps):
  while len(hi)>1 and cross(hi[-2],hi[-1],p)<=0:hi.pop()
  hi.append(p)
 return [list(p) for p in lo[:-1]+hi[:-1]]
def plane(tri):
 a,b,c=tri;dx1,dz1=b[0]-a[0],b[2]-a[2];dx2,dz2=c[0]-a[0],c[2]-a[2];dy1,dy2=b[1]-a[1],c[1]-a[1];den=dx1*dz2-dx2*dz1;gx=(dy1*dz2-dy2*dz1)/den;gz=(dx1*dy2-dx2*dy1)/den;return gx,gz,a[1]-gx*a[0]-gz*a[2]
def profile():
 pack=read(BASE/'drawbridge_candidate/resolved_placements.json');frame=pack['bridge_to_world'];b=frame['basis'];t=frame['translation']
 world=lambda p:[t[i]+sum(b[i][j]*p[j] for j in range(3)) for i in range(3)]
 local=lambda p:[sum(b[j][i]*(p[j]-t[j]) for j in range(3)) for i in range(3)]
 south=read(CITY/'registered_topography/road_extensions/south_country_r1/contract.json');L=math.dist(south['centerline_xyz_m'][0],south['centerline_xyz_m'][1]);f=2.5/L
 end=[[south['cross_sections_xyz_m'][0][j][k]*(1-f)+south['cross_sections_xyz_m'][1][j][k]*f for k in range(3)] for j in range(2)]
 # Native Z=-3.5 is the first side in the source terminal cross-section.
 y72=1.5-.25/3.5
 sections=[[[x,y,-3.5],[x,y,3.5]] for x,y in [(64,2),(67.5,1.75),(71,1.5),(72,y72)]]+[list(map(local,end))]
 triangles=[]
 for i,(a,c) in enumerate(zip(sections,sections[1:])):
  for j,tri in enumerate([[a[0],c[0],c[1]],[a[0],c[1],a[1]]]):
   coeff=plane(tri);assert math.hypot(*coeff[:2])<=.1+1e-9
   triangles.append({'id':f'SOUTH_GRADED_COVER:{i}:{j}','triangle_local_xyz_m':tri,'triangle_xyz_m':list(map(world,tri)),'plane_local_y':list(coeff),'maximum_grade':math.hypot(*coeff[:2]),'polygon_local_xz_m':[[p[0],p[2]] for p in tri]})
 return dict(schema='riverstone.southern_cover_profile.v1',status='bounded_candidate_pending_native_and_capsule_checks',frame=frame,sections_local_xyz_m=sections,sections_world_xyz_m=[[world(v) for v in s] for s in sections],triangles=triangles,width_m=7,source_area_m2=sum(area(r['polygon_local_xz_m']) for r in triangles),native_cut_extent_local_xz_m=[64,-3.55,72,3.55],country_road_extension_station_m=2.5,coarse_recess_below_profile_m=.2,visible_pitch_m=PITCH,cover_thickness_m=THICKNESS,visual_support_apron_m=GUARD,maximum_grade=max(r['maximum_grade'] for r in triangles),sources={'bridge_pack':ref(BASE/'drawbridge_candidate/resolved_placements.json'),'original_native_master':ref(BASE/'drawbridge_candidate/masters/stone_approaches.json'),'original_native_render':ref(ROOT/pack['assets']['stone_approaches']['render_path']),'south_road':ref(CITY/'registered_topography/road_extensions/south_country_r1/contract.json')},limits=['New continuous main-road cap, not step-up behavior or an authored stair replacement.','The central moving span and all original master files remain unchanged.','Native visual cover has measured sampling error relative to declared collision profile; no invisible support-only ramp.','No full-city terrain regeneration or gameplay release.'])
def coarse_master(p):
 m=read(BASE/'drawbridge_candidate/masters/stone_approaches.json');m['id']='registered_south_approach_r02_recessed_fixed';m['revision']=2
 for i,(a,b) in enumerate(zip(p['sections_local_xyz_m'][:3],p['sections_local_xyz_m'][1:4])):
  x0,y0=a[0][:2];x1,y1=b[0][:2];m['assembly_cuts'].append({'id':f'south_lane_finite_cap_recess_{i}','selector':{},'action':'cut','shape':extrusion([[x0,y0-.2],[x1,y1-.2],[x1,2.5],[x0,2.5]],-3.55,3.55)})
 m['provenance']['southern_cover_r02']={'original':p['sources']['original_native_master'],'profile':ref(HERE/'profile.json'),'scope':'Three finite source cap cuts inside X64..72, Z±3.55, all below new supported graded cover; no edited occupied cells.'}
 return m

def fine_master(p):
 original=read(BASE/'drawbridge_candidate/masters/stone_approaches.json');m={'schema':'riverstone.voxel.master.v1','id':'registered_south_approach_r02_visible_cover','revision':2,'axes':original['axes'],'grid_origin':[0,0,0],'materials':original['materials'],'coordinate_planes':[],'components':[],'instances':[],'constraints':[{'id':'cover_present','kind':'nonempty','selector':{}},{'id':'cover_connected','kind':'connected','selector':{}}],'provenance':{'profile':ref(HERE/'profile.json'),'author':ref(__file__),'common_only':True,'new_mesher':False,'cell_edits':False}}
 for i,r in enumerate(p['triangles']):
  tri=r['triangle_local_xyz_m'];poly=r['polygon_local_xz_m'];gx,gz,c=r['plane_local_y'];g=math.hypot(gx,gz);u=[gx/g,gz/g];v=[-u[1],u[0]];a=tri[0];expanded=hull([[x+dx,z+dz] for x,z in poly for dx in [-GUARD,GUARD] for dz in [-GUARD,GUARD]])
  us=[(q[0]-a[0])*u[0]+(q[1]-a[2])*u[1] for q in expanded];vs=[(q[0]-a[0])*v[0]+(q[1]-a[2])*v[1] for q in expanded];lo,hi=min(us),max(us);vl,vh=min(vs),max(vs);cover=hull([[a[0]+s*u[0]+t*v[0],a[2]+s*u[1]+t*v[1]] for s in [lo,hi] for t in [vl,vh]])
  ops=[{'id':'slope','part':'solid','action':'paint','material':'stone','shape':extrusion([[lo,g*lo-THICKNESS],[hi,g*hi-THICKNESS],[hi,g*hi],[lo,g*lo]],vl,vh),'transform':{'basis':[[u[0],0,v[0]],[0,1,0],[u[1],0,v[1]]],'translation':a}}]
  for j,outside in enumerate(geo.convex_difference(cover,expanded)):
   if area(outside)<1e-10:continue
   ops.append({'id':f'clip_{j}','part':'solid','action':'cut','shape':extrusion([[x,-z] for x,z in outside],a[1]+g*lo-THICKNESS-PITCH,a[1]+g*hi+PITCH),'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
  name=f'cover_{i}';m['components'].append({'id':name,'parts':[{'id':'solid','pivot':[0,0,0]}],'operations':ops});m['instances'].append({'id':name,'component':name})
 m['assembly_cuts']=[]
 for j,poly in enumerate([[[63.9,-4],[64,-4],[64,4],[63.9,4]],[[64,-4],[72,-4],[72,-3.5],[64,-3.5]],[[64,3.5],[72,3.5],[72,4],[64,4]]]):
  m['assembly_cuts'].append({'id':f'trim_optional_bridge_apron_{j}','selector':{},'action':'cut','shape':extrusion([[x,-z] for x,z in poly],.5,2.1),'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
 m['provenance']['apron_trim']='Remove only optional 5 cm apron at X<64 and bridge Z outside +-3.5 for X64..72. Exact 7 m physical profile remains fully covered; avoids coplanar old native top overlap.'
 return m

def compile_one(m,pitch,cap,outcap):
 name=m['id'];mp=HERE/'sources'/(name+'.json');write(mp,m);started=time.monotonic();c=coordinate_planes.compile_master(m,{'pitch':pitch},max_candidate_cells=cap,max_output_cells=outcap);assert c['valid'],c.get('constraints');r=render_data.make_render_data(c);cp=HERE/'cache'/(name+'.compiled.json');rp=HERE/'cache'/(name+'.render.json');write(cp,c);write(rp,r);record={'id':name,'master':ref(mp),'compiled':ref(cp),'render':ref(rp),'bounds':r['bounds'],'pitch_m':pitch,'candidate_cells':c['candidate_cells'],'cell_count':len(c['cells']),'quad_count':r['quad_count'],'seconds':time.monotonic()-started};print(json.dumps(record),flush=True);return record

def main():
 p=profile();write(HERE/'profile.json',p);print('PROFILE',p['source_area_m2'],p['maximum_grade'],flush=True)
 coarse=compile_one(coarse_master(p),.25,4000000,900000);fine=compile_one(fine_master(p),PITCH,2000000,700000)
 write(HERE/'resolved_placements.json',{'schema':'riverstone.south_approach_r02.native_candidate.v1','status':'compiled_pending_support_and_capsule_checks','profile':ref(HERE/'profile.json'),'assets':{'recessed_fixed':coarse,'visible_cover':fine},'placements':[{'id':'BRIDGE_MAIN_RIVER:SOUTH_RECESSED_FIXED','asset_key':'recessed_fixed','position_m':p['frame']['translation'],'transform':p['frame']},{'id':'BRIDGE_MAIN_RIVER:SOUTH_VISIBLE_GRADED_COVER','asset_key':'visible_cover','position_m':p['frame']['translation'],'transform':p['frame']}],'replaces_only':['BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED'],'floor_ownership':'Finite source triangles own the continuous collision top; native cap is visual and support volume. Exact cover cells and actual spill margins require ledger.','controller_unchanged':True})
if __name__=='__main__':main()
