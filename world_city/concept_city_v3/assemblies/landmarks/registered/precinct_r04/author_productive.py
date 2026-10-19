"""Coherent fenced productive frames with reused native orchard/bed modules."""
from author_grounds import *
def main():
 frames=load(HERE/'productive_frames.json')['frames'];gardens=load(GARDEN);catalog=gardens['asset_manifest'];rows=[];placements=[];assets={};contracts=[]
 for f in frames:
  p=f['polygon_xz_m'];c={**f,'available_regions_xz_m':[p],'requested_frame_xz_m':p};loops=[p];gate=choose_gate(c,loops,[],load(SOURCE)['roads']);ground=floor_source(c,loops,gate)
  # Plantable earth is a material role from the existing garden source, not a new color.
  bed=catalog['c3_property_fabric_r3_b8fc7a975a10ec9f'];bsource=load(Path(bed['master_path']));green=next((v for k,v in bsource['materials'].items()if 'grass'in k or 'earth'in k or 'soil'in k),None)
  if green:
   ground['materials']['productive_ground']=green
   for component in ground['components']:
    if component['id']=='ground':
     for op in component['operations']:op['material']='productive_ground'
  ground['id']='registered_precinct_productive_'+f['id'].lower();ground['extensions'].update(real_gate=gate,world_anchor_xz_m=f['center_xz_m'],host_bench_y_m=f['finished_floor_y_m'],productive_function=f['function']);path=HERE/'masters'/f"{ground['id']}.json";write(path,ground);estimate=estimate_candidates(ground,.5);assert estimate['candidate_cells_exact_aabb_visits']<600000;rows.append({'id':ground['id'],'compound_id':f['id'],'source':ref(path),'estimate':estimate,'position_m':[f['center_xz_m'][0],f['finished_floor_y_m'],f['center_xz_m'][1]],'gate':gate})
  orchard=f['function']=='orchard';key='c3_property_fabric_r3_05a88415aae614ab' if orchard else 'c3_property_fabric_r3_b8fc7a975a10ec9f';asset=catalog[key];assets[key]=asset;bounds=asset['bounds'];w=f['width_m'];d=f['depth_m'];count=0
  if orchard:
   xs=[x for x in range(-int(w/2),int(w/2)+1,10) if abs(x)>=5 and abs(x)<=w/2-5.5]
   xs=[-w/4,w/4] if len(xs)<2 else xs
   zs=[(i-(max(1,int((d-11)/10)+1)-1)/2)*10 for i in range(max(1,int((d-11)/10)+1))]
  else:
   positive=[4.5+8*i for i in range(10) if 4.5+8*i<=w/2-4.5];xs=[-x for x in reversed(positive)]+positive;nz=max(1,int((d-6)/5)+1);zs=[(i-(nz-1)/2)*5 for i in range(nz)]
  for x in xs:
   for z in zs:
    center=world([x,z],f['center_xz_m'],f['yaw_degrees']);foot=geo.transformed_aabb_xz_m(bounds,[center[0],f['finished_floor_y_m'],center[1]],math.radians(f['yaw_degrees']));inner=offset(p,1.5)
    if abs(geo.intersection_area(foot,inner)-geo.polygon_area(foot))>1e-6:continue
    corridor=geo.road_ribbon(gate['center_xz_m'],gate['inside_xz_m'],4)
    if geo.positive_area_overlap(foot,corridor,0):continue
    if any(geo.positive_area_overlap(foot,q['footprint_xz_m'],0)for q in placements if q['site_id']==f['id']):continue
    placements.append({'id':f['id']+':'+('fruit_tree' if orchard else 'productive_bed')+':'+str(count),'site_id':f['id'],'asset_key':key,'role':'orchard' if orchard else 'kitchen_bed','position_m':[center[0],f['finished_floor_y_m'],center[1]],'yaw_rad':math.radians(f['yaw_degrees']),'scale':[1,1,1],'footprint_xz_m':foot,'ground_anchor':{'datum_y_m':f['finished_floor_y_m'],'embed_m':1 if orchard else .5}});count+=1
  contracts.append({'id':f['id'],'site_id':f['site_id'],'function':f['function'],'floor_y_m':f['finished_floor_y_m'],'logical_owned_floor_regions_xz_m':[p],'gate':gate,'native_prop_count':count,'working_aisle':'Unplanted central3m minimum; actual cache crown/bed footprints remain disjoint.'})
 pre=load(HERE/'compound_preflight.json');pre['sources']+=rows;write(HERE/'all_grounds_preflight.json',pre);write(HERE/'productive_placements.source.json',{'frames':contracts,'placements':placements,'asset_manifest':assets,'source_plan':ref(SOURCE),'existing_gardens_unchanged':ref(GARDEN),'actual_placed':False,'actual_viewed':False});print([(r['compound_id'],r['estimate']['candidate_cells_exact_aabb_visits'])for r in rows]);print('productive props',len(placements))
if __name__=='__main__':main()
