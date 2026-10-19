"""Cache-local native solid masks and exterior-only actual source doors."""
from .design import *
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
from world_city.concept_city_v3.assemblies.property.registered.merchant_block011.coverage import roof_rects
from world_city.runtime_city.checks import placement as geo

def local_for(key,a):
 r=load(ROOT/a['render_path']);m=load(ROOT/a['master_path']);assert ref(ROOT/a['render_path'])['sha256']==a['render_sha256']
 lo=r['bounds']['min'][1];foundation=slab_rectangles(r,lo+.001,lo+min(.124,a['pitch_m']-.001));walking=slab_rectangles(r,.51,2.8);roof=roof_rects(r);doors=[];occluded=[]
 for mod in m.get('metadata',{}).get('modules',[]):
  yaw=mod.get('yaw_rad',0);tr=mod['translation_m'];n=[math.sin(yaw),math.cos(yaw)];t=[math.cos(yaw),-math.sin(yaw)]
  for di,raw in enumerate(mod['metadata']['entrance']['all_positions']):
   qxz=xform([raw[0],raw[2]],[tr[0],tr[2]],yaw);q=[qxz[0],raw[1]+tr[1],qxz[1]];qplane=sum(q[k*2]*n[k]for k in(0,1));qtan=sum(q[k*2]*t[k]for k in(0,1));faces=[]
   for gi,g in enumerate(r['groups']):
    if g['material']not in('door','door_dark'):continue
    for qi,quad in enumerate(g['quads']):
     plane=[v[0]*n[0]+v[2]*n[1]for v in quad];tan=[v[0]*t[0]+v[2]*t[1]for v in quad];ys=[v[1]for v in quad]
     if max(plane)-min(plane)>1e-6 or abs(plane[0]-qplane)>.251 or not(min(tan)-1e-6<=qtan<=max(tan)+1e-6)or min(ys)>q[1]+.501 or max(ys)<q[1]+1:continue
     faces.append(dict(group_index=gi,quad_index=qi,vertices_local_m=quad,plane=plane[0],width_m=max(tan)-min(tan),bottom_y_m=min(ys),top_y_m=max(ys)))
   if not faces:occluded.append(dict(module_id=mod['id'],door_index=di,continuous_source_xyz_m=q,reason='Closed source portal is internal to attached native union; not an exterior entrance.'));continue
   plane=max(f['plane']for f in faces);faces=[f for f in faces if abs(f['plane']-plane)<1e-8];tans=[v[0]*t[0]+v[2]*t[1]for f in faces for v in f['vertices_local_m']];native_tan=(min(tans)+max(tans))/2
   actual=[q[0]+n[0]*(plane-qplane)+t[0]*(native_tan-qtan),q[1],q[2]+n[1]*(plane-qplane)+t[1]*(native_tan-qtan)]
   # Continuous union may leave a material leaf behind a perpendicular return.
   # Require a clear one-metre point immediately in its outward half-plane.
   approach=[actual[0]+n[0]*1.25,actual[2]+n[1]*1.25]
   if any(geo.point_in_convex_polygon(approach,p)for p in walking):
    occluded.append(dict(module_id=mod['id'],door_index=di,continuous_source_xyz_m=q,reason='Native outward approach obstructed by attached return; not an exterior entrance.'));continue
   wide=mod['params']['style']=='port';doors.append(dict(id=mod['id']+':DOOR:'+str(di),module_id=mod['id'],source_position_local_xyz_m=q,actual_local_xyz_m=actual,outward_local_xz=n,threshold_lip_local_xz_m=[actual[0]+n[0]*.5,actual[2]+n[1]*.5],exterior_route_width_m=2.5 if wide else 1.8,native_face_evidence=faces,role='dry_store_handling'if wide else'domestic_or_craft',status='Actual closed native exterior leaf; interior traversal unimplemented'))
 return dict(key=key,asset=a,foundation_local_polygons_xz_m=foundation,walking_local_polygons_xz_m=walking,roof_local_polygons_xz_m=roof,doors=doors,occluded_internal_source_doors=occluded,court_local_polygon_xz_m=m.get('metadata',{}).get('court_local_polygon_xz_m'),native_bottom_local_y_m=lo,finished_floor_local_y_m=.5,roof_area_m2=sum(geo.polygon_area(p)for p in roof),foundation_area_m2=sum(geo.polygon_area(p)for p in foundation))

def run():
 assets=load(HERE/'compile_report.json')['assets'];old=load(CITY/'assemblies/ordinary/registered/working_ranges_r01/compile_report.json')['assets'];assets.update(old)
 out={key:local_for(key,a)for key,a in assets.items()if key!='district_r01_boundary_2m'}
 d=dict(schema='riverstone.district_fabric.native_local.v1',compile_report=ref(HERE/'compile_report.json'),assets=out);write(HERE/'native_local.json',d)
 print(json.dumps({k:dict(doors=len(v['doors']),internal_doors=len(v['occluded_internal_source_doors']),roof_area=v['roof_area_m2'],foundation_parts=len(v['foundation_local_polygons_xz_m']))for k,v in out.items()},indent=2));return d
if __name__=='__main__':run()
