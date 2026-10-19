"""Measure actual persisted native cells/tops, then resolve a new recovered pack."""
import copy,json,math
from . import author as a
from .recovery_support import author as prior
HERE=a.HERE;geo=a.geo

def columns(asset):
 c=json.loads(open(asset['compiled_cells_path']).read());p=c['pitch'];o=c['grid_origin'];out={}
 for row in c['cells']:
  i,j,k=row[:3];key=(i,k)
  if key not in out:out[key]=[j,j]
  else:out[key]=[min(out[key][0],j),max(out[key][1],j)]
 return [dict(i=i,k=k,polygon_xz_m=[[a.ORIGIN[0]+o[0]+p*x,a.ORIGIN[2]+o[2]+p*z] for x,z in ((i,k),(i+1,k),(i+1,k+1),(i,k+1))],top_y_m=a.ORIGIN[1]+o[1]+p*(hi+1),bottom_y_m=a.ORIGIN[1]+o[1]+p*lo) for (i,k),(lo,hi) in sorted(out.items())]

def run():
 manifest=json.loads((HERE/'cache/manifest.json').read_bytes());assets=manifest['assets'];old=copy.deepcopy(a.PACK);native=[];alltops=[];allcolumns={}
 for role in ('coarse','fine'):
  key=manifest[role+'_asset'];asset=assets[key];r=json.loads(open(asset['compiled_asset_ref']).read());fs=a.tops(r);cols=columns(asset);allcolumns[role]=cols;alltops+=fs;owner='TRAIN:r09:'+role
  native.append(dict(id=owner,asset_key=key,role='reconstructed_training_'+role,position_m=a.ORIGIN,yaw_rad=0,scale=[1,1,1],compiled_asset_ref=asset['compiled_asset_ref'],render_sha256=asset['render_sha256'],surface_owner=owner,surface_ownership=dict(owner_id=owner,kind='finite_native_training_'+role,floor_y_m=18,compiled_upward_faces=fs,terrain_exclusion_regions_xz_m=[f['polygon_xz_m'] for f in fs],render_sha256=asset['render_sha256'],policy='Exact persisted native top union; genuine sampled tread geometry. No capsule or cart claim.')))
 index=geo._SpatialIndex(4)
 for i,f in enumerate(alltops):index.add(i,f['polygon_xz_m'])
 uncovered=0.
 for p in a.SURFACE['polygon_regions_xz_m']:
  parts=[p]
  for i in sorted(index.candidates(p)):
   parts=[q for p0 in parts for c in geo.convex_difference(p0,alltops[i]['polygon_xz_m']) if(q:=a.clean(c))]
  uncovered+=sum(geo.polygon_area(q) for q in parts)
 coarse_faces=native[0]['surface_ownership']['compiled_upward_faces'];fine_faces=native[1]['surface_ownership']['compiled_upward_faces'];ci=geo._SpatialIndex(4)
 for i,f in enumerate(coarse_faces):ci.add(i,f['polygon_xz_m'])
 overlap=sum(geo.polygon_area(geo.convex_intersection(f['polygon_xz_m'],coarse_faces[i]['polygon_xz_m'])) for f in fine_faces for i in ci.candidates(f['polygon_xz_m']))
 finecolumns=allcolumns['fine'];lookup={(c['i'],c['k']):c for c in finecolumns};risers=[];burial=[]
 for c in finecolumns:
  for d in ((1,0),(0,1)):
   n=lookup.get((c['i']+d[0],c['k']+d[1]))
   if n:risers.append(abs(c['top_y_m']-n['top_y_m']))
  p=c['polygon_xz_m'];samples=p+[[sum(q[j] for q in p)/4 for j in (0,1)]]
  burial.extend(prior.prior.land_height_at(*q)-c['bottom_y_m'] for q in samples)
 public=[];roads=[r for r in prior.prior._owners() if r['kind']=='road'];road_index=geo._SpatialIndex(16)
 for i,r in enumerate(roads):road_index.add(i,r['polygon_xz_m'])
 for fi,f in enumerate(alltops):
  for i in sorted(road_index.candidates(f['polygon_xz_m'])):
   road=roads[i];q=a.clean(geo.convex_intersection(f['polygon_xz_m'],road['polygon_xz_m']))
   if q:
    assert road['road_id']=='CASTLE_APPROACH';public.append(dict(owner_id='TRAIN:r09:native_public',compiled_face_index=fi,road_id=road['road_id'],road_owner_id=road['owner_id'],polygon_xz_m=q,actual_compiled_top_y_m=f['y_m'],status='finite_native_tread_owner; public boundary step remains measured'))
 edges=[]
 for c in finecolumns:
  p=c['polygon_xz_m']
  for d,j in (((0,-1),0),((1,0),1),((0,1),2),((-1,0),3)):
   if (c['i']+d[0],c['k']+d[1]) in lookup:continue
   u,v=p[j],p[(j+1)%4];m=[(u[k]+v[k])/2 for k in (0,1)]
   r=prior.prior.owner_at(*m)
   if r['kind']=='road' and r.get('road_id')=='CASTLE_APPROACH':
    samples=[[(1-t)*u[k]+t*v[k] for k in (0,1)] for t in (0,.25,.5,.75,1)]
    edges.append(dict(segment_xz_m=[u,v],native_top_y_m=c['top_y_m'],samples=[dict(xz_m=q,road_y_m=prior.prior.road_height_at('CASTLE_APPROACH',*q),step_m=c['top_y_m']-prior.prior.road_height_at('CASTLE_APPROACH',*q)) for q in samples]))
 report=dict(status='bounded_reconstruction_audit',source_coverage_gap_m2=uncovered,coarse_fine_top_overlap_m2=overlap,coarse_top_faces=len(coarse_faces),fine_top_faces=len(fine_faces),fine_columns=len(finecolumns),fine_owned_area_m2=len(finecolumns)*a.PITCH**2,actual_public_clips=len(public),max_interior_riser_m=max(risers),minimum_buried_overlap_m=min(burial),minimum_native_depth_m=min(c['top_y_m']-c['bottom_y_m'] for c in finecolumns),native_top_levels_m=sorted(set(c['top_y_m'] for c in finecolumns)),public_boundary_segments=edges,maximum_public_boundary_step_m=max(abs(s['step_m']) for e in edges for s in e['samples']),source_maximum_triangle_grade=a.SURFACE['maximum_triangle_grade'],traversal_status='unverified; native125mm interior risers and measured exterior step remain discrete',double_internal_side_removal_claim=False)
 assert uncovered<1e-7 and overlap<1e-7 and max(risers)<=a.PITCH+1e-8 and min(burial)>=.25-1e-7,report
 a.write(HERE/'native_audit.json',report);a.write(HERE/'native_columns.json',allcolumns)
 old['placements']=[p for p in old['placements'] if p['id']!='TRAIN:owned_ground']+native;old['ownership_masks']=[m for m in old['ownership_masks'] if m['owner_id']!='TRAIN:owned_ground']+[p['surface_ownership'] for p in native];old['actual_public_surface_overrides']=public;old['asset_manifest'].update(assets);old['reconstruction']=dict(reason='Executor reset lost the former r09 bytes; reconstructed from verified version5 training source.',source_pack_sha256=a.sha(a.PACK_PATH),original_training_source_sha256=a.sha(a.SOURCE),historical_lost_pack_sha256='92fb6fc8069dfefe652b98d92f2c050cdc24b6d18cd521993d7f75529703abcf',hash_equivalence_claim=False);old['replacement_native_placement_ids']=['TRAIN:owned_ground'];old['native_audit_sha256']=a.sha(HERE/'native_audit.json');old['status']='reconstructed_native_candidate_pending_independent_check';old['runtime_ready']=False;old['applied_to_scene']=False;old['metrics'].update(placements=len(old['placements']),r09_fine_owned_area_m2=report['fine_owned_area_m2']);a.write(HERE/'resolved_placements.json',old);print(json.dumps({k:v for k,v in report.items() if k!='public_boundary_segments'}),flush=True)
if __name__=='__main__':run()
