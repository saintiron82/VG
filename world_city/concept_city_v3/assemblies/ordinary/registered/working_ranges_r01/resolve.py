"""Resolve the exact native family unions, masks and exterior door leaves."""
from .design import *
from .ground import ActualGround,geo
from world_city.concept_city_v3.validation.check_landmark_access_candidate import slab_rectangles
from world_city.concept_city_v3.assemblies.property.registered.merchant_block011.coverage import roof_rects

def polys_world(ps,p):return [[xform(q,[p['position_m'][0],p['position_m'][2]],p['yaw_rad'])for q in poly]for poly in ps]
def run():
 selection=load(HERE/'selection.json');report=load(HERE/'compile_report.json');out=[];doors=[];ground=ActualGround();nativeproof=[]
 for p0 in selection['placements']:
  p=copy.deepcopy(p0);a=report['assets'][p['asset_key']];r=load(ROOT/a['render_path']);m=load(ROOT/a['master_path']);assert ref(ROOT/a['render_path'])['sha256']==a['render_sha256'];foundation=slab_rectangles(r,.001,.499);walking=slab_rectangles(r,.51,2.8);roof=roof_rects(r);body=[]
  for module in m['metadata']['modules']:
   lo,hi=module['metadata']['body_bounds']['min'],module['metadata']['body_bounds']['max'];cx,_,cz=module['translation_m'];body.append(rect(lo[0]+cx,lo[2]+cz,hi[0]+cx,hi[2]+cz))
   for di,q in enumerate(module['metadata']['entrance']['all_positions']):
    q=[q[k]+module['translation_m'][k]for k in range(3)];faces=[]
    for gi,g in enumerate(r['groups']):
     if g['material']not in('door','door_dark'):continue
     for qi,quad in enumerate(g['quads']):
      loq=[min(v[k]for v in quad)for k in range(3)];hiq=[max(v[k]for v in quad)for k in range(3)]
      if abs(hiq[2]-loq[2])<1e-8 and loq[0]-1e-7<=q[0]<=hiq[0]+1e-7 and abs(loq[2]-q[2])<=.251 and hiq[1]>=q[1]+1 and loq[1]<=q[1]+.501:faces.append(dict(group_index=gi,quad_index=qi,vertices_local_m=quad,z=loq[2],width_m=hiq[0]-loq[0],bottom_y_m=loq[1],top_y_m=hiq[1]))
    assert faces,(p['id'],module['id'],q);z=max(f['z']for f in faces);faces=[f for f in faces if f['z']==z];actual=[q[0],q[1],z];pt=xform([q[0],z],[p['position_m'][0],p['position_m'][2]],p['yaw_rad']);lip=xform([q[0],r['bounds']['max'][2]],[p['position_m'][0],p['position_m'][2]],p['yaw_rad']);wide=module['params']['style']=='port';doors.append(dict(id=p['id']+':'+module['id']+':DOOR:'+str(di),parcel_id=p['id'],holding_id=p['holding_id'],module_id=module['id'],role='broad_dry_store_handling'if wide else'household_or_craft_front',actual_local_xyz_m=actual,actual_door_xyz_m=[pt[0],p['position_m'][1]+q[1],pt[1]],continuous_source_local_xyz_m=q,native_sampling_delta_m=z-q[2],native_face_evidence=faces,threshold_lip_xz_m=lip,outward_xz=[math.sin(p['yaw_rad']),math.cos(p['yaw_rad'])],exterior_route_width_m=2.5 if wide else 1.8,render_sha256=a['render_sha256'],portal_status='Real closed native leaf; no open/animated door or through-interior access claim',population_or_household_inference=False))
  p.update(body_envelope_polygons_xz_m=polys_world(body,p),body_polygon_definition="Continuous dimension-authored outer wall envelopes; actual native walking-solid masks are supplied separately",native_foundation_polygons_xz_m=polys_world(foundation,p),native_walking_obstacles_xz_m=polys_world(walking,p),native_roof_polygons_xz_m=polys_world(roof,p),actual_door_ids=[d['id']for d in doors if d['parcel_id']==p['id']],foundation_local_polygons_xz_m=foundation,roof_local_polygons_xz_m=roof)
  proof=ground.audit(p['native_foundation_polygons_xz_m']);assert proof['fully_covered']and abs(proof['min_y_m']-2.5)<1e-7 and abs(proof['max_y_m']-2.5)<1e-7,(p['id'],proof);p['area_m2']=dict(native_roof_projection=sum(geo.polygon_area(q)for q in roof),native_foundation_projection=sum(geo.polygon_area(q)for q in foundation),continuous_body_footprint=sum(geo.polygon_area(q)for q in body));out.append(p);nativeproof.append(dict(parcel_id=p['id'],actual_foundation_ground=proof))
 pack=dict(schema='riverstone.working_ranges.resolved_native.v1',status='Staged native family; no city activation',selection=ref(HERE/'selection.json'),compile_report=ref(HERE/'compile_report.json'),assets=report['assets'],placements=out,actual_doors=doors,native_ground_proofs=nativeproof,whole_house_scales=0,cell_edits=0,summary=dict(native_range_groups=len(out),parameter_authored_modules=12,actual_closed_leaf_portals=len(doors),native_roof_projection_m2=sum(p['area_m2']['native_roof_projection']for p in out),native_foundation_projection_m2=sum(p['area_m2']['native_foundation_projection']for p in out),new_common_quads=sum(a['quad_count']for a in report['assets'].values())));write(HERE/'native_geometry.json',pack);print(json.dumps(pack['summary'],indent=2));return pack
if __name__=='__main__':run()
