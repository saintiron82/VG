"""Native workyard fixtures reserved wholly inside existing non-walk ownership."""
import json,hashlib,math,time,collections
from pathlib import Path
from world_city.runtime_city.parts.author import Source,extrusion
from world_city.runtime_city.checks import placement as geo
from voxel_character.common.coordinate_planes import compile_master
from voxel_character.common.render_data import make_render_data
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[3];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rel(p):return str(Path(p).relative_to(ROOT))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def masters():
 a=Source('b13_cooper_bench',[-1.5,-.25,-1],[1.5,1.5,1]);a.box('top',[-1.5,.75,-.75],[1.5,1,0],'timber');a.box('shelf',[-1.3,.15,-.65],[1.3,.35,-.1],'timber_dark')
 for i,(x,z) in enumerate(( (x,z) for x in (-1.25,1.25) for z in (-.6,-.15))):a.box('leg'+str(i),[x-.15,-.25,z-.15],[x+.15,.9,z+.15],'timber_dark')
 for i in range(4):a.box('stave'+str(i),[-1.2+i*.5,1,-.5],[-1.05+i*.5,1.125,.9],'timber_light')
 yield 'cooper_bench',a
 a=Source('b13_drying_frame',[-2.5,-.25,-1],[2.5,2.75,1])
 for i,x in enumerate((-2.25,2.25)):
  a.box('post'+str(i),[x-.125,-.25,-.125],[x+.125,2.75,.125],'timber');a.box('foot'+str(i),[x-.35,-.125,-.75],[x+.35,.25,.75],'timber_dark')
 a.box('beam',[-2.5,2.5,-.125],[2.5,2.75,.125],'timber');a.box('linen',[-1.75,.75,-.0625],[.6,2.5,.0625],'stone_light');a.box('canvas',[.9,1.25,-.0625],[1.9,2.5,.0625],'stone')
 yield 'drying_frame',a
 a=Source('b13_wood_stack',[-1.5,-.25,-1],[1.5,1.5,1])
 for i,z in enumerate((-.75,.5)):a.box('skid'+str(i),[-1.5,-.25,z],[1.5,.25,z+.25],'timber_dark')
 for r in range(3):
  for c in range(4):a.box('beam%d_%d'%(r,c),[-1.4,.25+r*.3,-.9+c*.5],[1.4,.5+r*.3,-.65+c*.5],'timber_light' if (r+c)%2 else 'timber')
 yield 'wood_stack',a
 a=Source('b13_privy_shed',[-1.25,-.25,-1.5],[1.25,3,1.5]);a.box('base',[-1.125,-.25,-1.375],[1.125,0,1.375],'stone_dark');a.box('boards',[-1,0,-1.25],[1,2.5,1.25],'timber');a.box('hollow',[-.75,0,-1],[.75,2.25,1.251],action='cut');a.box('frontleft',[-1,0,1],[0,2.5,1.25],'timber_dark');a.box('door',[0,0,1],[.75,1.9,1.25],'timber_light');a.op('leanroof',extrusion([[-1.25,2.5],[1.25,2.75],[1.25,3],[-1.25,2.75]],-1.5,1.5),'timber_dark');a.box('vent',[-.5,2,-1.251],[.25,2.25,-.75],action='cut')
 yield 'privy_shed',a

def rect(bounds,pos,yaw,margin=0):
 lo,hi=bounds['min'],bounds['max'];c,s=math.cos(yaw),math.sin(yaw)
 return [[pos[0]+c*x+s*z,pos[1]-s*x+c*z] for x,z in [(lo[0]-margin,lo[2]-margin),(hi[0]+margin,lo[2]-margin),(hi[0]+margin,hi[2]+margin),(lo[0]-margin,hi[2]+margin)]]
def main():
 t=time.monotonic();assets={};stats=[]
 for kind,a in masters():
  m=a.finish();m['provenance'].update(author={'path':rel(Path(__file__)),'sha256':sha(__file__)},reconstruction='New bytes from retained design after workspace reset; revision02 prompt reference is a recovery notice, not original prompt.')
  key='b13_workyard_'+kind;mp=HERE/'masters'/f'{key}.json';write(mp,m);comp=compile_master(m,{'pitch':.125},max_candidate_cells=100000,max_output_cells=30000);assert comp['valid'];rp=HERE/'cache'/f'{key}.render.json';rd=make_render_data(comp);write(rp,rd)
  assets[key]=dict(master_path=rel(mp),master_sha256=sha(mp),render_path=rel(rp),render_sha256=sha(rp),bounds=rd['bounds'],pitch_m=.125,quad_count=rd['quad_count']);stats.append(dict(kind=kind,cells=len(comp['cells']),quads=rd['quad_count']))
 lp=CITY/'assemblies/landscape/registered/resolved_placements.json';land=json.loads(lp.read_bytes());key='c3_property_fabric_r3_b8fc7a975a10ec9f';a=land['asset_manifest'][key];assets['productive_bed']=dict(master_path=rel(a['master_path']),master_sha256=a['master_file_sha256'],render_path=rel(a['compiled_asset_ref']),render_sha256=a['render_sha256'],bounds=a['bounds'],pitch_m=.5,quad_count=a['quad_count'])
 gp=CITY/'assemblies/ordinary/registered/r1/owned_grounds.json';ground=json.loads(gp.read_bytes());dp=CITY/'assemblies/ordinary/registered/r1/resolved_placements.json';density=json.loads(dp.read_bytes());yaws={p['id']:p['yaw_rad'] for p in density['placements']};placements=[];unplaced=[];reserved=[]
 for gi,g in enumerate(ground['grounds']):
  role=g['role'];kinds=['productive_bed']*6 if 'productive' in role else ['privy_shed']*2 if 'privy' in role else ['wood_stack','wood_stack','cooper_bench'] if 'stockyard' in role else [('drying_frame','cooper_bench'),('wood_stack','cooper_bench'),('drying_frame','wood_stack')][gi%3]
  yaw=yaws.get(g['id'].split(':')[0],0);regions=g['polygons_xz_m'];points=[p for q in regions for p in q];cx=sum(p[0] for p in points)/len(points);cz=sum(p[1] for p in points)/len(points)
  candidates=sorted(((x,z) for x in range(math.ceil(min(p[0] for p in points)),math.floor(max(p[0] for p in points))+1) for z in range(math.ceil(min(p[1] for p in points)),math.floor(max(p[1] for p in points))+1)),key=lambda p:((p[0]-cx)**2+(p[1]-cz)**2,p))
  for ki,kind in enumerate(kinds):
   key=kind if kind=='productive_bed' else 'b13_workyard_'+kind;a=assets[key];found=None
   for x,z in candidates:
    poly=rect(a['bounds'],[x,z],yaw,.875);area=geo.polygon_area(poly);covered=sum(geo.polygon_area(geo.convex_intersection(poly,p)) for p in regions)
    if covered<area-1e-6:continue
    if any(geo.polygon_area(geo.convex_intersection(poly,p))>1e-7 for p in reserved):continue
    found=(x,z,poly);break
   if found is None:unplaced.append(dict(ground_id=g['id'],kind=kind,reason='No native bounds plus 0.875 m working margin fits reserved nonwalk ground.'));continue
   x,z,poly=found;reserved.append(poly);placements.append(dict(id=f'B13_YARD_{gi:02d}_{ki}',asset_key=key,position_m=[x,2.5,z],yaw_rad=yaw,scale=[1,1,1],ground_id=g['id'],role=kind,footprint_xz_m=rect(a['bounds'],[x,z],yaw),reserved_working_polygon_xz_m=poly,footing_embed_m=-a['bounds']['min'][1],floor_y_m=2.5,palette_id='native_b13_workyard',palette_override={}))
 out=dict(schema='riverstone.b13_workyard.native.v1',status='native_placement_candidate_support_and_visual_review_pending',source_plan_sha256=sha(CITY/'registered_source/plan.json'),inputs=[dict(path=rel(p),sha256=sha(p)) for p in (gp,dp,lp)],assets=assets,placements=placements,unplaced=unplaced,no_floor_geometry_added=True,all_new_prototypes_same_common_engine=True,geometry_tests=dict(reserved_inside_disjoint_owned_nonwalk=True,working_margin_m=.875,reserved_overlap_count=0),compile_stats=stats,wall_seconds=time.monotonic()-t)
 write(HERE/'resolved_placements.json',out);print(json.dumps(dict(placements=len(placements),roles=dict(collections.Counter(p['role'] for p in placements)),unplaced=len(unplaced),wall_seconds=out['wall_seconds'],sha256=sha(HERE/'resolved_placements.json'))))
if __name__=='__main__':main()
