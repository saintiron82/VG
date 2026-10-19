"""Native reusable grounds furniture/boundaries. No output-mesh scaling."""
from build_ledger import *
from world_city.runtime_city.parts.author import Source,make_master,approved_palette,extrusion
from world_city.concept_city_v3.assemblies.landmarks.registered.build_audit import estimate_candidates
from voxel_character.common import core,coordinate_planes,render_data
import copy,resource

def store_source(s,name):
 s['id']='registered_precinct_r06_'+name;s['provenance'].update(author=ref(Path(__file__)),approved_reference=ref(ROOT/'world_city/reference/revision_03/city_social_water_concept.png'),new_engine=False,mesh_scaling=False)
 s['extensions'].update(status='native_source_candidate',actual_viewed=False,whole_city_complete=False)
 (HERE/'masters').mkdir(exist_ok=True);p=HERE/'masters'/f'{s["id"]}.json';p.write_text(json.dumps(s,indent=2)+'\n');return p

def boundary(w,d):
 a=Source(f'ground_boundary_{w}x{d}',[-w/2,-.5,-d/2],[w/2,1.5,d/2])
 for sign in(-1,1):
  z0,z1=((-d/2,-d/2+.5)if sign<0 else(d/2-.5,d/2))
  x0,x1=((-w/2,-w/2+.5)if sign<0 else(w/2-.5,w/2))
  for side,lo,hi in [('zleft',[-w/2,-.5,z0],[-2,1.25,z1]),('zright',[2,-.5,z0],[w/2,1.25,z1]),('xback',[x0,-.5,-d/2],[x1,1.25,-2]),('xfront',[x0,-.5,2],[x1,1.25,d/2])]:a.box(side+str(sign),lo,hi,'stone',component='boundary')
  for q in(-1,1):
   x=q*2.25;z=sign*(d/2-.25);a.box(f'post_z_{sign}_{q}',[x-.25,-.5,z-.25],[x+.25,1.5,z+.25],'timber_dark',component='gate')
   za,zb=sorted([z,z-sign*1.5]);a.box(f'open_leaf_z_{sign}_{q}',[x-.25,.25,za],[x+.25,1.25,zb],'timber',component='gate')
   z=q*2.25;x=sign*(w/2-.25);a.box(f'post_x_{sign}_{q}',[x-.25,-.5,z-.25],[x+.25,1.5,z+.25],'timber_dark',component='gate')
   xa,xb=sorted([x,x-sign*1.5]);a.box(f'open_leaf_x_{sign}_{q}',[xa,.25,z-.25],[xb,1.25,z+.25],'timber',component='gate')
 a.clearance('north_south_clear',[-2,.01,-d/2],[2,2.2,d/2],'4m shared walking/service cross aisle')
 a.clearance('east_west_clear',[-w/2,.01,-2],[w/2,2.2,2],'4m shared walking/service cross aisle')
 s=a.finish();s['extensions'].update(visible_wall_height_m=1.25,soil_embed_m=.5,gates=4,gate_clear_width_m=4,gate_state='static_fully_open',dimensions_m=[w,d]);return s

def shelter(w,d):
 a=Source(f'open_service_shelter_{w}x{d}',[-w/2,-.5,-d/2],[w/2,4,d/2]);eave=3;ridge=4
 for x in(-w/2+.25,w/2-.25):
  for z in(-d/2+.25,d/2-.25):a.box(f'post_{x}_{z}',[x-.25,-.5,z-.25],[x+.25,eave,z+.25],'timber_dark',component='posts')
 for z in(-d/2+.25,d/2-.25):a.box('beam'+str(z),[-w/2,eave-1,z-.25],[w/2,eave-.5,z+.25],'timber',component='beams')
 rot={'basis':[[0,0,-1],[0,1,0],[1,0,0]]}
 for sign in(-1,1):a.op('roof'+str(sign),extrusion([[0,ridge],[sign*d/2,eave],[sign*d/2,eave-.5],[0,ridge-.5]],-w/2,w/2),'slate',component='roof',transform=rot)
 a.clearance('open_work_bay',[-w/2+.75,.01,-d/2+.75],[w/2-.75,2.4,d/2-.75],'Clear storage/shelter work bay')
 return a.finish()

def smallbed():
 # Same native raised-bed grammar, newly dimension-authored3×2m variant.
 a=Source('compact_medicinal_bed',[-1.5,-.5,-1],[1.5,1.5,1]);a.box('raised_stone_bed',[-1.5,-.5,-1],[1.5,.5,1],'stone',component='bed');a.box('planted_herbs',[-1,.5,-.5],[1,1.5,.5],'timber_light',component='crop');return a.finish()
def fuel():
 a=Source('seasoned_fuel_stack',[-1.5,-.5,-1],[1.5,1.5,1]);a.box('sleepers',[-1.5,-.5,-1],[1.5,0,1],'timber_dark',component='sleepers')
 for j in range(3):
  for k in range(4-j%2):a.box(f'fuel_{j}_{k}',[-1.5,j*.5,-1+k*.5],[1.5,(j+1)*.5,-.6+k*.5],'timber'if j%2 else'timber_light',component='fuel')
 return a.finish()

def author():
 p=load(HERE/'grounds_plan.json');rows=[]
 sources=[('boundary_'+str(w)+'x'+str(d),boundary(w,d),.25)for w,d in sorted({tuple(u['dimensions_m'])for u in p['units']})]
 sources += [('shelter_8x6',shelter(8,6),.5),('shelter_4x3',shelter(4,3),.25),('compact_bed',smallbed(),.5),('fuel_stack',fuel(),.25),('park_bench',make_master('park_bench'),.1),('cargo_crate',make_master('cargo_crate'),.25)]
 for key,s,pitch in sources:
  path=store_source(s,key);e=estimate_candidates(s,pitch);assert e['candidate_cells_exact_aabb_visits']<300000,(key,e);rows.append({'role':key,'source':ref(path),'pitch_m':pitch,'estimate':e})
 write('native_preflight.json',{'sources':rows,'summary':{'new_sources':len(rows),'candidate_cell_visits':sum(r['estimate']['candidate_cells_exact_aabb_visits']for r in rows),'candidate_cap_each':300000,'output_cap_each':150000},'source_dependencies':[ref(ROOT/'world_city/runtime_city/parts/author.py'),ref(ROOT/'voxel_character/common/core.py'),ref(ROOT/'voxel_character/common/coordinate_planes.py'),ref(ROOT/'voxel_character/common/render_data.py')],'whole_terrain_compile':False,'mesh_scaling':False});print(load(HERE/'native_preflight.json')['summary'])

def compile_all():
 pre=load(HERE/'native_preflight.json');out=[];start=time.monotonic();(HERE/'cache').mkdir(exist_ok=True)
 for a in pre['sources']:
  s=load(ROOT/a['source']['path']);t=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':a['pitch_m']},max_candidate_cells=300000,max_output_cells=150000);assert c['valid'],c.get('constraints');mesh=render_data.make_render_data(c);path=HERE/'cache'/f'{s["id"]}.pitch_{a["pitch_m"]}.render.json';path.write_text(json.dumps(mesh,separators=(',',':'))+'\n');out.append(dict(a,id=s['id'],cache=ref(path),bounds=mesh['bounds'],candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),quad_count=mesh['quad_count'],constraints=c['constraints'],seconds=time.monotonic()-t,master_hash=core.digest(s)));print('compiled',a['role'],c['candidate_cells'],len(c['cells']),flush=True)
 write('compiled_assets.json',{'assets':out,'summary':{'assets':len(out),'candidate_cells':sum(a['candidate_cells']for a in out),'output_cells':sum(a['output_cells']for a in out),'seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'common_unchanged':True})
if __name__=='__main__':
 if '--compile'in sys.argv:compile_all()
 else:author()
