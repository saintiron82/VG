"""Replace fitting ordinary spatial masses with immutable common house cache assets.
No whole-house scaling. Exact fit, source design provenance and height deltas are
recorded per source mass; unresolved/landmark masses remain explicitly visible.
"""
from pathlib import Path
import copy,hashlib,json,math,sys,collections
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
from world_city.runtime_city.assemble_city import write,sha
from world_city.concept_city_v3.topography.author import height_at
ROOFS={'clay_red':['a16b51','ac775c','80523f','b18a6c'],'wood_brown':['80664a','8c7355','624f3d','9c8568'],'slate_gray':['646f73','748085','4a565c','879096']}
def seed(s):return int(hashlib.sha256(s.encode()).hexdigest()[:10],16)
def xform(p,x,z,yaw):return [p[0]+math.cos(yaw)*x+math.sin(yaw)*z,p[1]-math.sin(yaw)*x+math.cos(yaw)*z]
def main():
 plan=json.loads((HERE/'source/plan.json').read_text());block=json.loads((HERE/'generated/blockout.scene.json').read_text());oldpath=ROOT/'world_city/runtime_city/generated/r2/scene.flat_property.json';old=json.loads(oldpath.read_text());oldids={x['id']:x for x in old['instances']};pboxes={b['id']:b for b in block['boxes']}
 catalog=[]
 for k,s in old['asset_specs'].items():
  if s['family']!='ordinary_r2':continue
  a=old['assets'][k]['coarse'];bb=a['bounds'];w=bb['max'][0]-bb['min'][0];d=bb['max'][2]-bb['min'][2]
  catalog.append((k,s,a,w,d))
 placed=[];assets={};unresolved=[];records=[]
 for b in plan['buildings']:
  function=b.get('function','');district=b['district_id'];p=b['position_xz_m'];yaw=b.get('yaw_rad',0);protected=oldids.get(b.get('source_design_id',''));choices=[]
  if protected:
   key=protected['asset_key'];spec=old['asset_specs'][key];asset=old['assets'][key].get('fine',old['assets'][key]['coarse']);override=protected['palette_override'];palette=protected['palette_id'];reason='approved seven-building design and palette reused'
  else:
   if any(t in function for t in ['castle','cathedral','monastery','town_hall','grain_hall','noble_main','barrack','warehouse','tower']):unresolved.append({'id':b['id'],'reason':'dedicated common facility/property assembly staged separately'});continue
   desired='poor_row' if district=='D_POOR' else 'regular_house';style='merchant' if 'MERCHANT' in district or district=='D_CIVIC' else 'artisan' if 'CRAFT' in district else 'old_timber'
   for key,spec,asset,w,d in catalog:
    if w>b['width_m']+.01 or d>b['depth_m']+.01:continue
    if spec.get('assembly_class') not in [desired,'regular_house','servant_lodge']:continue
    cover=w*d/(b['width_m']*b['depth_m'])
    if cover<.5:continue
    score=(1-cover)*12+abs(spec['floors']-b.get('floors',2))*3+(0 if spec.get('style')==style else 2)+(0 if spec.get('assembly_class')==desired else 3)
    choices.append((score+(seed(b['id']+key)%1000)/10000,key,spec,asset))
   if not choices:unresolved.append({'id':b['id'],'reason':'no fitting cached common body; new authored module required'});continue
   _,key,spec,asset=min(choices,key=lambda x:x[0]);reason='immutable cached common master, no scale';roof=b.get('roof_material','clay_red');roof={'red_clay':'clay_red','gray_slate':'slate_gray','brown_shingle':'wood_brown','brown_wood':'wood_brown'}.get(roof,roof)
   if roof not in ROOFS:roof='wood_brown' if district=='D_POOR' else 'clay_red'
   override=dict(zip(['slate','slate_light','slate_dark','slate_worn'],ROOFS[roof]));palette=roof
  bb=asset['bounds'];corners=[xform(p,x,z,yaw) for x,z in [(bb['min'][0],bb['min'][2]),(bb['max'][0],bb['min'][2]),(bb['max'][0],bb['max'][2]),(bb['min'][0],bb['max'][2])]]
  base=max(height_at(*q) for q in corners+[p]);meta=asset.get('author_metadata',{});ent=meta.get('entrance',{});local=ent.get('all_positions',[])
  if not local:local=[ent.get('position',[0,0,spec['depth_m']/2])]
  entries=[[*xform(p,e[0],e[2],yaw),e[1]] for e in local]
  worldentries=[[q[0],base+q[2],q[1]] for q in entries]
  placed.append({'id':b['id'],'asset_key':key,'position_m':[p[0],base,p[1]],'yaw_rad':yaw,'palette_id':palette,'palette_override':override,'source_mass_id':b['id'],'source_design_id':b.get('source_design_id'),'actual_entrances_m':worldentries,'scale':[1,1,1]})
  assets[key]=asset;records.append({'source_mass_id':b['id'],'asset_key':key,'master_sha256':asset['master_sha256'],'render_sha256':asset['render_sha256'],'reason':reason,'source_mass_size_m':[b['width_m'],b['height_m'],b['depth_m']],'actual_local_bounds':bb,'height_delta_m':round(bb['max'][1]-bb['min'][1]-b['height_m'],3),'source_entrance_xz_m':b['entrance_xz_m'],'actual_entrances_m':worldentries,'threshold_height_deltas_m':[round(e[1]-height_at(e[0],e[2]),4) for e in worldentries],'actual_footprint_xz_m':corners,'footprint_validation':'candidate pending independent actual-bound review'})
 replaced={p['id'] for p in placed};block['boxes']=[b for b in block['boxes'] if b['id'] not in replaced];block['common_instances']=placed;block['common_assets']=assets;block['status']='partial_common_exterior_candidate_not_final';block['reuse_provenance']={'source_catalog':str(oldpath.relative_to(ROOT)),'sha256':sha(oldpath),'new_compilation_count':0,'geometry_scaling':False}
 write(HERE/'generated/common_houses.scene.json',block);write(HERE/'evidence/common_house_reuse.json',{'source_plan_sha256':sha(HERE/'source/plan.json'),'replaced_count':len(placed),'unique_assets':len(assets),'unresolved':unresolved,'records':records,'validation_status':'needs clearance/threshold and actual visual review'})
 print(json.dumps({'common_instances':len(placed),'unique_assets':len(assets),'unresolved':len(unresolved)},indent=2))
if __name__=='__main__':main()
