"""Finite native raster-edge cuts, preserving original packs and old native owners."""
import sys,copy,time,resource,collections
from pathlib import Path
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from plan_coverage import *
from recovered_range_factory import Source,estimate_candidates
from compile_compounds import walk_report,top_faces
from voxel_character.common import coordinate_planes,render_data,core
CONFLICT= CITY/'registered_topography/revisions/r14_precinct_merchant/native_conflicts.json'

def bottom_faces(mesh):
 out=[]
 for g in mesh['groups']:
  for q in g['quads']:
   if not all(abs(v[1]+.5)<1e-7 for v in q):continue
   u=[q[1][j]-q[0][j]for j in range(3)];v=[q[2][j]-q[0][j]for j in range(3)]
   if u[2]*v[0]-u[0]*v[2]<0:out.append([[v[0],v[2]]for v in q])
 return out

def main():
 begin=time.monotonic();pack=load(BASE/'resolved_placements.json');conf=load(CONFLICT);pre=load(BASE/'all_grounds_preflight.json');fit=load(BASE/'native_building_fit.json');rows=[];audits=[];replacements=[];newfloors=[];newbearings=[];access=[]
 for pid in sorted({r['placement_id']for r in conf}):
  a=next(x for x in pack['assets']if x.get('compound_id')==pid);pose=next(x for x in pack['placements']if x['id']==pid);origin=pose['position_m'];s=load(ROOT/a['source']['path']);old=coordinate_planes.compile_master(s,{'pitch':.5},max_candidate_cells=600000,max_output_cells=180000);assert old['valid'];assert render_data.make_render_data(old)==load(ROOT/a['cache']['path']);polys=[r['polygon_xz_m']for r in conf if r['placement_id']==pid];index=geo._SpatialIndex(8)
  for i,p in enumerate(polys):index.add(i,p)
  contacts=[];tags=collections.Counter()
  for cell in old['cells']:
   x,y,z=cell[:3];p=[[origin[0]+x*.5,origin[2]+z*.5],[origin[0]+(x+1)*.5,origin[2]+z*.5],[origin[0]+(x+1)*.5,origin[2]+(z+1)*.5],[origin[0]+x*.5,origin[2]+(z+1)*.5]]
   if any(geo.intersection_area(p,polys[i])>1e-8 for i in index.candidates(p)):
    contacts.append({'cell':cell,'y_range_world_m':[origin[1]+y*.5,origin[1]+(y+1)*.5]});tags[cell[3]]+=1
  print(pid,'actual contact tags',dict(tags),'vertical',min(r['y_range_world_m'][0]for r in contacts),max(r['y_range_world_m'][1]for r in contacts),flush=True)
  assert all(tag in ('court_and_boundary__ground','court_and_boundary__boundary')for tag in tags),tags
  audits.append({'placement_id':pid,'old_source':a['source'],'old_cache':a['cache'],'actual_contact_components':dict(tags),'vertical_min_y_m':min(r['y_range_world_m'][0]for r in contacts),'vertical_max_y_m':max(r['y_range_world_m'][1]for r in contacts),'contacts':contacts,'interpretation':'New court/boundary raster overshoot only; no new dwelling or service-range body is cut.'})
  cutter=Source('finite_raster_edge_cuts',[-100,-.6,-100],[100,2.6,100])
  for i,p in enumerate(polys):
   q=offset(p,-.36);cutter.plan('preserved_owner_clearance_'+str(i),[[x-origin[0],z-origin[2]]for x,z in q],-.6,2.6,component='cutters',action='cut')
  cuts=cutter.components['cutters']['operations'];new=copy.deepcopy(s)
  for comp in new['components']:
   if comp['id']in('court_and_boundary__ground','court_and_boundary__boundary'):comp['operations']+=copy.deepcopy(cuts)
  new['id']=s['id']+'_edge_repair_r01';new['revision']=s.get('revision',1)+1;new['provenance'].update(edge_repair_author=ref(Path(__file__)),immutable_original=a['source'],native_conflict_evidence=ref(CONFLICT));new['extensions']['raster_edge_repair']={'cut_scope':'Ground and boundary only, y−0.6…2.6','cut_expansion_m':.36,'reason':'0.5 m sampled voxel corners must clear preserved native floor masks;0.36 exceeds the half-cell diagonal.','existing_building_components_unchanged':True};sp=OUT/'masters'/f"{new['id']}.json";write(sp,new);est=estimate_candidates(new,.5);rows.append({'placement_id':pid,'source':ref(sp),'estimate':est});write(OUT/'preflight.json',{'sources':rows,'candidate_cap_each':610000,'output_cap_each':180000,'sequential':True,'no_whole_city_compile':True});assert est['candidate_cells_exact_aabb_visits']<610000
  t=time.monotonic();c=coordinate_planes.compile_master(new,{'pitch':.5},max_candidate_cells=610000,max_output_cells=180000);assert c['valid'];mesh=render_data.make_render_data(c);cp=OUT/'cache'/f"{new['id']}.pitch_0.5.render.json";write(cp,mesh)
  removed={tuple(r)for r in old['cells']} - {tuple(r)for r in c['cells']};assert all(r[3]in('court_and_boundary__ground','court_and_boundary__boundary')for r in removed)
  footing=bottom_faces(mesh);hits=[]
  for poly in footing:
   p=[[x+origin[0],z+origin[2]]for x,z in poly]
   for i in index.candidates(p):
    area=geo.intersection_area(p,polys[i])
    if area>1e-8:hits.append(area)
  assert not hits,hits
  row=next(r for r in pre['sources']if r['compound_id']==pid);test=walk_report(c,row,[d for d in fit['doors']if d['compound_id']==pid]);assert test['all_door_starts_reachable'];test['compound_id']=pid;access.append(test)
  asset={**a,'id':new['id'],'source':ref(sp),'cache':ref(cp),'master_hash':core.digest(new),'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells']),'quad_count':mesh['quad_count'],'bounds':mesh['bounds'],'seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'removed_edge_cells':len(removed)}
  replacements.append({'placement_id':pid,'old_asset_key':a['id'],'asset':asset,'placement':{**pose,'asset_key':new['id'],'source':ref(sp),'cache':ref(cp),'actual_cached_bounds_local_m':mesh['bounds']}})
  for i,poly in enumerate(top_faces(mesh)):newfloors.append({'id':pid+':edge_repair_floor:'+str(i),'placement_id':pid,'polygon_xz_m':[[x+origin[0],z+origin[2]]for x,z in poly],'floor_y_m':origin[1],'support_bottom_y_m':origin[1]-.5,'basis':'Actual repaired native upward common quad.'})
  for i,poly in enumerate(footing):newbearings.append({'id':pid+':edge_repair_bearing:'+str(i),'placement_id':pid,'polygon_xz_m':[[x+origin[0],z+origin[2]]for x,z in poly],'bottom_y_m':origin[1]-.5,'finished_floor_y_m':origin[1],'ownership_policy':'Actual repaired native opaque bearing footprint; preserve previous source terrain.'})
  print('REPAIRED',pid,c['candidate_cells'],'removed',len(removed),'doors',len(test['routes']),'gate',test['native_gate_clear_width_sampled_m'],flush=True)
 write(OUT/'vertical_contact_audit.json',{'conflicts':ref(CONFLICT),'rows':audits});write(OUT/'native_access_replay.json',{'compounds':access,'all_pass':True});write(OUT/'replacement_overlay.json',{'schema':'riverstone.precinct.native_edge_repair_overlay.v1','immutable_base':ref(BASE/'resolved_placements.json'),'conflicts':ref(CONFLICT),'replacements':replacements,'replace_floor_and_bearing_placement_ids':[r['placement_id']for r in replacements],'owned_floors':newfloors,'actual_bearing_footprints':newbearings,'removed_all_reported_contact_polygons':True,'native_access_replay':ref(OUT/'native_access_replay.json'),'vertical_contact_audit':ref(OUT/'vertical_contact_audit.json'),'total_seconds':time.monotonic()-begin,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'actual_viewed':False,'independent_full_native_owner_audit':False});print(ref(OUT/'replacement_overlay.json'),flush=True)
if __name__=='__main__':main()
