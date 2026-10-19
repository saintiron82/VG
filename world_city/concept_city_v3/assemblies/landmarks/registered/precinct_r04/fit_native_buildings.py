"""Deterministic rigid native modules inside six finite functional compounds."""
from pathlib import Path
from plan_coverage import *
def assets():
 ordinary=load(ORDINARY)['assets'];property=load(CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json')['asset_manifest'];out={}
 for role,key in [('dwelling','ordinary_r2_2fb8f88976f56a'),('lodge','ordinary_r2_357c8088248bad')]:
  r=ordinary[key];out[role]={'asset_key':key,'source':ref(ROOT/r['master_path']),'cache':ref(ROOT/r['render_path']),'bounds':r['bounds']}
 for role,key in [('stone','c3_property_ordinary_r2_fc0efd621519b707'),('store','c3_property_ordinary_r2_2879451e5e6ea01c')]:
  r=property[key];out[role]={'asset_key':key,'source':ref(Path(r['master_path'])),'cache':ref(Path(r['compiled_asset_ref'])),'bounds':r['bounds']}
 for row in load(HERE/'source_preflight.json')['sources']:
  s=load(ROOT/row['source']['path']);out[row['role']]={'asset_key':s['id'],'source':row['source'],'cache':None,'bounds':s['extensions']['local_bounds_m']}
 for role,a in out.items():
  s=load(ROOT/a['source']['path']);m=s.get('metadata',{});ent=m.get('entrance',{});a['doors']=ent.get('all_positions',[ent['position']]if'position'in ent else[e['threshold_local_m']for e in s['extensions']['entrances']]);a['native_door_y_m']=a['doors'][0][1];a['body_bounds']=m.get('body_bounds',a['bounds'])
 return out

def layouts():
 out=dict(SPEC['layouts_local']);canons=[]
 for row,(z,xs)in enumerate([(-18,[-50,-32,-14,4,22,40]),(18,[-50,-30,-10,10,30,50])]):
  for col,x in enumerate(xs):canons.append([f'canon_{row}_{col}',('stone','canon_narrow','canon_wide')[(col+row)%3],[x,z],0 if row==0 else 180])
 canons[5]=['canon_0_5','stone',[48,-3],270];out['CLERGY_CANONS_CLOSE']=canons;return out

def main():
 plan=load(HERE/'coverage_plan.json');catalog=assets();placements=[];failures=[];doors=[];ds=sorted((dx*dx+dz*dz,dx,dz)for dx in range(-8,9)for dz in range(-8,9));layout=layouts()
 for c in plan['compounds']:
  used=[]
  for label,role,local,relative_yaw in layout[c['id']]:
   a=catalog[role];b=a['bounds'];w=b['max'][0]-b['min'][0];d=b['max'][2]-b['min'][2];yaw=c['yaw_degrees']+relative_yaw;angle=math.radians(yaw);found=None
   for _,dx,dz in ds:
    center=world([local[0]+dx,local[1]+dz],c['center_xz_m'],c['yaw_degrees']);foot=rect(center,w,d,angle);clear=rect(center,w+3,d+3,angle)
    if abs(sum(geo.intersection_area(clear,q) for q in c['available_regions_xz_m'])-geo.polygon_area(clear))<1e-5 and not any(geo.positive_area_overlap(clear,p,1e-7)for p in used):found=(center,foot,dx,dz);break
   if not found:failures.append({'compound':c['id'],'label':label,'role':role});continue
   center,foot,dx,dz=found;used.append(foot);id=c['id']+':'+label;origin=[center[0],c['finished_floor_y_m']-a['native_door_y_m'],center[1]];placement={'id':id,'compound_id':c['id'],'site_id':c['site_id'],'function':label,'role':role,'asset_key':a['asset_key'],'source':a['source'],'cache':a['cache'],'position_m':origin,'yaw_rad':angle,'yaw_degrees':yaw,'scale':[1,1,1],'finished_floor_y_m':c['finished_floor_y_m'],'native_door_y_m':a['native_door_y_m'],'outer_footprint_xz_m':foot,'bounded_fit_local_delta_m':[dx,dz],'ground_binding':'Terrain-relative host bench; exact floor/body masking and approaches remain pending.'};placements.append(placement)
   for i,q in enumerate(a['doors']):
    p=world([q[0],q[2]],center,yaw);outward=[math.sin(angle),math.cos(angle)];doors.append({'id':id+':door:'+str(i),'placement_id':id,'compound_id':c['id'],'threshold_xyz_m':[p[0],origin[1]+q[1],p[1]],'outward_xz':outward,'approach_start_xz_m':[p[0]+outward[0]*1.5,p[1]+outward[1]*1.5],'status':'actual_native_threshold; route_pending'})
 report={'schema':'riverstone.precinct.native_fit.v2','coverage_plan':ref(HERE/'coverage_plan.json'),'catalog':catalog,'placements':placements,'doors':doors,'failed_fits':failures,'checks':{'native_scale_all_one':all(p['scale']==[1,1,1]for p in placements),'building_count':len(placements),'asset_family_count':len(catalog),'actual_threshold_count':len(doors)},'actual_placed':False,'actual_viewed':False};write(HERE/'native_building_fit.json',report);print(report['checks']);print('FAILURES',failures);assert not failures
if __name__=='__main__':main()
