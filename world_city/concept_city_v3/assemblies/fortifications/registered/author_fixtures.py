"""Bounded native fortification fixtures, no wall-path or city placement mutation."""
import sys,json,math,time,resource
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered'))
from build_audit import ref,write,estimate_candidates,source_bounds
from author_assemblies import make_hip_tower,finish
from world_city.runtime_city.landmarks.author import _Author,_extrusion,_box
from world_city.runtime_city.infrastructure.author import make_master
from world_city.runtime_city.parts.author import Source,approved_palette
from voxel_character.common import core,coordinate_planes,render_data

def gateway(name,width,clear,spring,eave,ridge,depth=6):
 half=depth/2
 a=_Author({'asset_id':name,'kind':'wall_tower','width_m':width,'depth_m':depth,'height_m':ridge})
 a.box('masonry','gate_mass',[-width/2,-2,-half],[width/2,eave,half],'stone')
 radius=clear/2;curve=[[radius*math.cos(i*math.pi/24),spring+radius*math.sin(i*math.pi/24)] for i in range(25)]
 opening=[[-radius,-3],[radius,-3]]+curve+[[-radius,-3]]
 a.assembly_cuts.append({'id':'barrel_passage','selector':{},'shape':_extrusion(opening,-half-.01,half+.01)})
 a.roof('gate_roof',-width/2,width/2,-half,half,eave,ridge,across_x=False)
 a.empty_regions.append({'id':'walking_throat','kind':'empty_region','selector':{},'shape':_box([-clear/2,.1,-half],[clear/2,min(spring,3.5),half])})
 a.portals=[{'id':'gate_throat','threshold_local_m':[0,0,half],'forward_into_asset':[0,0,-1],'clear_width_m':clear,'clear_height_m':spring,'through_passage':True,'interior_status':'continuous road must own the sloped floor; no flat source floor'}]
 v=finish(a,'native_gate_header','clay_red',0);v['extensions']['foundation_footprints_local_xz_m']=[[-width/2,-half,-clear/2,half],[clear/2,-half,width/2,half]]
 v['extensions']['design_dimensions_m']={'outer_width':width,'clear_width':clear,'depth':depth,'jamb_each':(width-clear)/2}
 v['extensions']['road_floor_policy']='No floor in source; bind exact continuous road datum and preserve longitudinal grade through the arch.'
 return v

def fixtures():
 out=[]
 for h in (14,18,22):
  s=make_master({'kind':'wall_panel','width_m':16,'depth_m':3,'height_m':h,'battlements':True,'battlement_height_m':1,'battlement_spacing_m':2});s['id']='registered_curtain16_h'+str(h);out.append(s)
 for w,h in ((10,34),(12,42)):out.append(make_hip_tower('registered_fort_tower_'+str(w)+'x'+str(h),w,w,h-7,h,1))
 out.append(gateway('registered_main_gate_header',9.047511073905033,8,4.5,11.5,16))
 out.append(gateway('registered_service_gate_header',6.4,4.8,3.5,8,11.5,2))
 for length,depth in ((16,.5),(16,1),(2,.5)):
  a=Source('fort_footing_'+str(length)+'x'+str(depth),[-length/2,-depth,-2],[length/2,0,2]);a.box('bearing',[-length/2,-depth,-2],[length/2,0,2],'stone_dark');s=a.finish();s['id']='registered_'+a.kind;out.append(s)
 for s in out:
  s['materials'].update({k:v for k,v in approved_palette().items() if k in s['materials'] and not k.startswith('slate')})
  s.setdefault('provenance',{})['fortification_author']=ref(Path(__file__));s['provenance']['registered_preflight']=ref(HERE/'preflight.json');s.setdefault('extensions',{}).update(city_placement=None,actual_scene_loaded=False,actual_visual_review=False,local_bounds_m=source_bounds(s),status='reusable_native_fixture_height_assignment_pending')
 return out

def main():
 rows=[]
 for s in fixtures():
  sp=HERE/'masters'/f"{s['id']}.json";write(sp,s);expected=estimate_candidates(s,.5)['candidate_cells_exact_aabb_visits'];assert expected<2000000;before=core.digest(s);start=time.monotonic();c=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=2000000,max_output_cells=400000);assert c['candidate_cells']==expected;assert core.digest(s)==before
  row={'id':s['id'],'source':ref(sp),'master_hash':before,'valid':c['valid'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'constraints':c['constraints'],'seconds':round(time.monotonic()-start,3),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
  if c['valid']:
   rd=render_data.make_render_data(c);cp=HERE/'cache'/f"{s['id']}.pitch_0.5.render.json";write(cp,rd);row.update(cache=ref(cp),quads=rd['quad_count'],bounds=rd['bounds'])
  rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('constraints','source','cache')}),flush=True)
 report={'schema':'riverstone.city.registered_fortification_fixtures.v1','status':'pass' if all(r['valid'] for r in rows) else 'fail','sources':rows,'source_plan':ref(ROOT/'world_city/concept_city_v3/registered_source/plan.json'),'preflight':ref(HERE/'preflight.json'),'compile_policy':'Sequential independent0.5m common cache fixtures; no city/wall compilation.','placements':[],'actual_scene_loaded':False,'actual_visual_review':False,'remaining':['Exact end closures and per-chunk foundations','Observed tower placement anchors and paired-face fit','Main gate oblique corridor/collision proof and real floor profile','Source-bound proxy replacement ledger','Independent roads/buildings/water and support audit']};write(HERE/'fixture_manifest.json',report);assert report['status']=='pass'
if __name__=='__main__':main()
