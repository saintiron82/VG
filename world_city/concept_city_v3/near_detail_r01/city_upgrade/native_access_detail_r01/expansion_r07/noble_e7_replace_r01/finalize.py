"""Seal one E7 replacement and a compact runtime projection. No production writes."""
from pathlib import Path
import collections,copy,gzip,hashlib,importlib.util,json,math,os,resource,shutil,subprocess,sys,time
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent
s=importlib.util.spec_from_location if False else importlib.util.spec_from_file_location('e7_frozen_author',H/'author_r03.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
q=m.q;p=m.p;a=m.a;R=m.R;N=m.N;P=m.P

def limit():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2);resource.setrlimit(resource.RLIMIT_CPU,(90,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))

def seal():
 start=time.monotonic();limit();masks,demands,requests,cachedeps=m.specification();oldplan=q.read(q.PLAN);old=next(v for v in oldplan['assets']if v['asset_key']==q.KEY);source=q.read(R/old['source_render_path']);diagnosis=q.read(N/'expansion_r06/noble_e7_audit_r01/diagnosis.json');assert all(q.sha(R/f)==v for f,v in masks['source_dependencies'].items());assert all(q.sha(R/f)==v for f,v in cachedeps.items())
 modules={};excluded=[];records=[];footprints={};proofs=[]
 for ident,d in demands.items():
  ep=H/'excluded_modules'/(ident+'.json')
  if ep.exists():
   ex=q.read(ep);assert ex['mask_sha256']==d['mask_sha256'];excluded.append({'module_key':ident,**ex});continue
  if d['cached']:row=copy.deepcopy(d['cached'])
  else:
   rp=H/'module_records'/(ident+'.json');record=q.read(rp);assert record['all_pass'] and record['mask_sha256']==d['mask_sha256'];assert record['closed_boundary']['all_pass'];row=record['module'];records.append(q.ref(rp))
  for kind in ['master','render']:
   path=R/row[kind+'_path'];assert q.sha(path)==row[kind+'_sha256']
   if str(path).endswith('.gz'):assert hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()==row['decoded_'+kind+'_sha256']
  modules[ident]=row;render=m.read(R/row['render_path']);xy=set()
  # Backing is continuous through stone joints; its exact exported footprint is
  # the whole visual support mask, including concavities and holes.
  for group in render['groups']:
   for face in group['quads']:
    if not all(abs(v[2]+.0375)<1e-12 for v in face):continue
    ix=[round(v[0]/P)for v in face];iy=[round(v[1]/P)for v in face]
    for y in range(min(iy),max(iy)):
     for x in range(min(ix),max(ix)):
      assert (x,y)not in xy;xy.add((x,y))
  assert xy;footprints[ident]=xy
 placements=[];gridrows={};visibility=[];cached_source_replays=0
 pose=old['actual_instances'][0]['instance'];capture=q.read(q.audit6.CAPTURE);observer=capture['observer'];observer=observer['position']if isinstance(observer,dict)else observer
 localobs=a.polygons.inverse_transform_point_m(observer,pose['position_m'],pose.get('yaw_rad',0));ou,ov=localobs[0],-localobs[2];vertical=max(0,localobs[1]-.0375,-localobs[1])
 for req in requests:
  ident=req['module_key'];g=req['grid'];gx,gy=g['grid_xy_m'];assert (gx,gy)not in gridrows
  if ident not in modules:continue
  ox,oy=req['module_offset_xy_m'];dx,dy=round(ox/P),round(oy/P);actual={(x+dx,y+dy)for x,y in footprints[ident]};expected=p.expand(g['allowed_cell_runs_xy']);assert actual==expected
  if demands[ident]['cached']:proof=m.validate_source_runs(g,old);cached_source_replays+=1
  else:proof=q.read(H/'module_records'/(ident+'.json'))['source_proof']
  rows=[0]*80
  for x,y in actual:rows[y]|=1<<x
  gridrows[(gx,gy)]=rows
  # Reuse the existing common footprint partition at integer scale. Geometry
  # stays unchanged; this only makes an exact compact visibility footprint.
  spec={'pitch_m':1,'trim':{'width_m':80,'height_m':80},'holes':[{'rect':r}for r in g['forbidden_cell_runs_xy']]}
  compact=a.common.allowed_rectangles(spec);assert p.expand(compact)==actual
  rects=[[r[0]*P-ox,r[1]*P-oy,r[2]*P-ox,r[3]*P-oy]for r in compact]
  translation=[gx+ox,.0375,-gy-oy];basis=[[1,0,0],[0,0,1],[0,-1,0]];assert a.common.validate_placement(translation,basis)
  bounds=[gx+g['bbox_cells_xy'][0]*P,gy+g['bbox_cells_xy'][1]*P,gx+g['bbox_cells_xy'][2]*P,gy+g['bbox_cells_xy'][3]*P]
  refs=[{'ref':ref,'quad_sha256':q.digest(source['groups'][ref[0]]['quads'][ref[1]])}for ref in g['source_face_refs']]
  pl={'module_key':ident,'transform':{'basis':basis,'translation':translation},'bounds_uv_m':bounds,'grid_xy_m':[gx,gy],'source_plane_y_m':0,'source_face_refs':refs,'source_owner_operation_ids':g['source_owner_ids'],'source_support_mask_sha256':g['mask_sha256'],'visibility_footprint_rects_xy_m':rects,'visibility_local_z_bounds_m':[-.0375,0],'collision_changed':False}
  placements.append(pl);proofs.append({'grid_xy_m':[gx,gy],'module_key':ident,'source_proof':proof,'original_actual_quad_hashes':refs,'exact_common_footprint_rectangles':len(compact),'compiled_mask_matches_source_mask':True})
  min2=math.inf;corner2=math.inf;max2=0
  for x,y,z,w in compact:
   lo=[gx+x*P,gy+y*P];hi=[gx+z*P,gy+w*P];du=max(lo[0]-ou,0,ou-hi[0]);dv=max(lo[1]-ov,0,ov-hi[1]);min2=min(min2,du*du+dv*dv+vertical*vertical)
   ds=[(u-ou)**2+(v-ov)**2+vertical*vertical for u in [lo[0],hi[0]]for v in [lo[1],hi[1]]];corner2=min(corner2,*ds);max2=max(max2,*ds)
  center=[gx+.5,.0375,-gy-.5];center2=sum((center[i]-localobs[i])**2for i in range(3));visibility.append({'placement_index':len(placements)-1,'grid_xy_m':[gx,gy],'minimum_footprint_distance_m':math.sqrt(min2),'minimum_cell_or_partition_corner_distance_m':math.sqrt(corner2),'maximum_corner_distance_m':math.sqrt(max2),'center_distance_m':math.sqrt(center2),'visible_before_fade7':min2<49})
  assert time.monotonic()-start<80,'Source/projection validation exceeded its separate 90s bound'
 # Exact integer row coverage preserves every previously accepted fine cell.
 old_cells=0
 for prev in old['placements']:
  x0,y0,x1,y1=[round(v/P)for v in prev['bounds_uv_m']]
  for yy in range(y0,y1):
   for xx in range(x0,x1):
    gx,ix=divmod(xx,80);gy,iy=divmod(yy,80);assert (gx,gy)in gridrows and gridrows[gx,gy][iy]>>ix&1;old_cells+=1
 assert old_cells==718400
 total=sum(bits.bit_count()for rows in gridrows.values()for bits in rows);assert total==masks['summary']['safe_cells']-sum(ex['safe_cell_count']for ex in excluded)
 visible=sorted((v for v in visibility if v['visible_before_fade7']),key=lambda v:(v['minimum_footprint_distance_m'],v['center_distance_m'],v['placement_index']));selected=visible[:120];selected_ids={v['placement_index']for v in selected};grid_to_index={tuple(pl['grid_xy_m']):i for i,pl in enumerate(placements)}
 points=[]
 for i,point in enumerate(diagnosis['image_gap_diagnostics']):
  u,v=point['local_uv_m'];gx,gy=math.floor(u),math.floor(v);ix,iy=math.floor((u-gx)/P),math.floor((v-gy)/P);covered=(gx,gy)in gridrows and bool(gridrows[gx,gy][iy]>>ix&1);selected_here=grid_to_index.get((gx,gy))in selected_ids
  if i<4:assert covered and selected_here
  if i==4:assert not covered
  if i==5:assert covered and selected_here
  points.append({'image_pixel_xy':point['image_pixel_xy'],'local_uv_m':[u,v],'covered_by_safe_cell':covered,'selected_with_cap120':selected_here,'prior_classification':point['actual_source_patch_hits'][0]['classification']if point['actual_source_patch_hits']else None})
 missing_domains=[v for v in diagnosis['consistent_grid_demands']if tuple(v['grid_xy'])not in {tuple(g['grid_xy_m'])for g in masks['grids']}];assert len(missing_domains)==2
 source_area=diagnosis['areas']['allowed_source_domain_m2'];safe_area=total*P*P;area={'original_actual_quad_area_m2':480,'original_walk_cut_allowed_domain_m2':source_area,'previous_detail_m2':112.25,'candidate_safe_detail_m2':safe_area,'recovered_area_m2':safe_area-112.25,'preserved_previous_cells':old_cells,'lost_previous_cells':0,'preflight_safe_mask_area_m2':masks['summary']['safe_area_m2'],'fine_grid_loss_including_empty_domains_m2':source_area-masks['summary']['safe_area_m2'],'joint_only_unsupported_tip_loss_m2':sum(ex['safe_area_m2']for ex in excluded),'total_original_allowed_not_detailed_m2':source_area-safe_area,'source_domains_with_zero_whole_safe_cells':missing_domains,'outside_source_area_m2':0,'positive_cut_overlap_m2':0,'duplicate_area_m2':0}
 stats={'all_pass':True,'source_mask_preparation':q.ref(H/'prepared_masks.json'),'source_dependencies_unchanged':True,'geometry_modules':len(modules),'new_geometry_modules':len(records),'cached_unique_modules':len(modules)-len(records),'cached_placements':cached_source_replays,'placements':len(placements),'horizontal_cells':total,'entire_exported_cell_footprints_inside_original_support':True,'outside_source_cells':0,'duplicate_footprint_cells':0,'new_colliders':0,'area_accounting':area,'unsupported':excluded,'per_placement_source_proofs':proofs,'new_module_closed_boundary_proofs':records,'new_geometry_bytes':m.geometry_bytes(),'address_space_limit_bytes':256*1024*1024,'verification_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 q.save(H/'validation/source_geometry_report.json',stats)
 vis={'all_pass':all(pt['covered_by_safe_cell']and pt['selected_with_cap120']for pt in points[:4]),'actual_observer_m':observer,'owner_local_observer_m':localobs,'fade_start_m':4,'fade_end_m':7,'max_active_modules':120,'visible_footprint_count':len(visible),'selected_count':len(selected),'truncated_count':max(0,len(visible)-120),'all_visible_modules_fit_cap120':len(visible)<=120,'selection_policy':'Exact supported footprint rectangles, clamp observer onto each rectangle and local Z envelope; minimum 3D distance ascending, stable center-distance/index tie breaks. Fully faded modules at >=7m do not compete. Corner bounds include peripheral cells; module center alone is not a visibility proof.','pixel_diagnostic_scope':'Fixed original capture camera plane projection only; no new actual GUI or walking test.','original_four_large_gap_points_now_covered':True,'forbidden_control_still_uncovered':True,'image_point_checks':points,'ordered_visible_modules':visible,'all_placements':visibility,'production_runtime_changed':False}
 q.save(H/'validation/visibility_report.json',vis)
 asset={k:copy.deepcopy(v)for k,v in old.items()if k not in ['placements','faces','excluded','status']};asset.update({'placements':placements,'status':'SOURCE_SAFE_PARTIAL_CELL_REPLACEMENT_CANDIDATE','source_support_proof':q.ref(H/'prepared_masks.json'),'geometry_validation':q.ref(H/'validation/source_geometry_report.json'),'area_accounting':area,'unsupported':excluded,'replacement':{'old_plan':q.ref(q.PLAN),'old_asset_key':q.KEY,'old_placement_count':len(old['placements']),'atomic_whole_asset_replace':True,'do_not_stack_old_and_new':True}})
 plan={'schema':oldplan['schema'],'revision':'r07_noble_e7_atomic_source_safe_cells_r01','source_city_index_sha256':oldplan['source_city_index_sha256'],'maximum_additional_visual_offset_from_source_m':.0375,'assets':[asset],'runtime_activation':False,'whole_city_upgrade_complete':False,'provenance':{'author':q.ref(Path(__file__)),'frozen_mask_author':q.ref(H/'prepare.py'),'source_masks':q.ref(H/'prepared_masks.json'),'build_records':records,'source_dependencies':masks['source_dependencies'],'cached_catalog_dependencies':cachedeps,'unchanged_common_mesh_and_source':True}}
 pp=H/'source_plan.json';cp=H/'modules/catalog.json';q.save(pp,plan);q.save(cp,{'schema':'riverstone.native_access_detail.module_catalog.v1','revision':plan['revision'],'source_plan_sha256':q.sha(pp),'modules':list(modules.values()),'original_collision_unchanged':True,'runtime_activation':False,'source_dependencies':masks['source_dependencies']})
 keep=['asset_key','source_master_path','source_master_sha256','source_render_path','source_render_sha256','source_pitch_m','existing_collision_unchanged','rule','placements','actual_instances','source_collision_baseline'];projected={k:copy.deepcopy(asset[k])for k in keep};projected['full_source_proof']={'asset_key':q.KEY,**q.ref(pp)};projected['geometry_validation']=q.ref(H/'validation/source_geometry_report.json')
 projection={k:copy.deepcopy(plan[k])for k in ['schema','revision','source_city_index_sha256','maximum_additional_visual_offset_from_source_m','whole_city_upgrade_complete']};projection.update({'runtime_projection':True,'assets':[projected],'projection_contract':'Exact selected asset fields and all placements copied; full author proof remains SHA-bound for streaming verification.'});rp=H/'runtime_projection/source_plan.json';rc=H/'runtime_projection/modules.json';q.save(rp,projection);rcdata=q.read(cp);rcdata['source_plan_sha256']=q.sha(rp);q.save(rc,rcdata)
 assert all(projected[k]==asset[k]for k in keep)and projected['placements']==asset['placements'];q.save(H/'runtime_projection/validation.json',{'all_pass':True,'full_source_plan':q.ref(pp),'runtime_projection':q.ref(rp),'full_module_catalog':q.ref(cp),'runtime_module_catalog':q.ref(rc),'modules_exactly_equal':rcdata['modules']==q.read(cp)['modules'],'copied_asset_fields':keep,'placement_count':len(placements),'omitted_placements':0,'duplicated_placements':0,'altered_copied_fields':0,'production_binding_changed':False})
 q.save(H/'runtime_projection/delta.json',{'schema':'riverstone.native_access.atomic_candidate_delta.v1','asset_key':q.KEY,'operation':'replace_exactly_one_asset_row_and_resolve_module_refs','replace_source_master_sha256':asset['source_master_sha256'],'replace_source_render_sha256':asset['source_render_sha256'],'source_plan':q.ref(rp),'module_catalog':q.ref(rc),'full_proof_plan':q.ref(pp),'old_placement_count':170,'new_placement_count':len(placements),'other_assets_unchanged':True,'max_active_modules':120,'requires_footprint_fade_aware_visibility':True,'visibility_contract':q.ref(H/'validation/visibility_report.json'),'runtime_binding_performed':False})
 print(json.dumps({'source_checks_pass':True,'area':area,'new_modules':len(records),'placements':len(placements),'visible_footprints':len(visible),'new_geometry_bytes':m.geometry_bytes(),'verification_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)

if __name__=='__main__':seal()
