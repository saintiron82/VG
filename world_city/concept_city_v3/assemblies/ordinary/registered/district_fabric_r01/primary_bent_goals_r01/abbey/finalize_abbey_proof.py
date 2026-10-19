"""Verify source hashes and all retained explicit scene boxes; no scene mutation."""
from search_abbey import *
def main():
 d=load(O/'abbey_bent_route_proof.json');scene=load(SC);assert ref(SC)['sha256']==d['scene']['sha256']=='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
 refs=[]
 for p in d['native_bindings']:
  for k in('source','cache'):
   actual=ref(ROOT/p[k]['path']);assert actual==p[k],(p['id'],k,actual,p[k]);refs.append(dict(native_id=p['id'],kind=k,**actual,verified=True))
 contacts=[];near=[]
 for box in scene['boxes']:
  x,y,z=box['position_m'];w,h,l=box['size_m'];poly=b.xform(b.rect(-w/2,-l/2,w/2,l/2),box);lo=y-h/2;hi=y+h/2
  touched=False
  for part in d['support_checks']:
   if geo.intersection_area(poly,part['polygon_xz_m'])<=1e-8:continue
   touched=True
   for r in part['source_pieces']:
    q=geo.convex_intersection(poly,r['polygon_xz_m'])
    if not q or geo.polygon_area(q)<=1e-8:continue
    ys=[terrain.common.height(r['plane_y_xz_m'],v)for v in q]
    if hi>min(ys)+.01+1e-8 and lo<max(ys)+2.2-1e-8:contacts.append(dict(box_id=box['id'],ribbon_piece_id=part['id'],intersection_polygon_xz_m=q,box_y_interval_m=[lo,hi],walking_y_interval_m=[min(ys),max(ys)]))
  if touched:near.append(box)
 fmin=min(r['min_y_m']for c in d['support_checks']for r in c['source_pieces']);fmax=max(r['max_y_m']for c in d['support_checks']for r in c['source_pieces']);meshes={};candidates=[]
 for placement in scene['common_instances']:
  asset=scene['common_assets'][placement['asset_key']];bb=asset.get('bounds');py=placement['position_m'][1]
  if bb is None:
   if asset['render_path']not in meshes:meshes[asset['render_path']]=load(ROOT/asset['render_path'])
   bb=meshes[asset['render_path']]['bounds']
  if bb['max'][1]+py<=fmin+.01 or bb['min'][1]+py>=fmax+2.2:continue
  poly=b.xform(b.rect(bb['min'][0],bb['min'][2],bb['max'][0],bb['max'][2]),placement)
  if any(geo.intersection_area(poly,c['polygon_xz_m'])>1e-8 for c in d['support_checks']):candidates.append(placement['id'])
 missing=sorted(set(candidates)-{p['id']for p in d['native_bindings']})
 d['whole_scene_native_candidate_check']=dict(total_instances=len(scene['common_instances']),walking_floor_y_interval_m=[fmin,fmax],possible_native_colliders=candidates,unverified_ids=missing,passed=not missing)
 d['native_reference_verification']=refs;d['explicit_box_clearance']=dict(total_scene_boxes=len(scene['boxes']),projected_near_route_boxes=near,contacts=contacts,passed=not contacts)
 d['summary']['explicit_box_contacts']=len(contacts);d['summary']['native_source_hashes_verified']=len(refs)
 d['summary']['unverified_native_candidate_count']=len(missing)
 d['summary']['passed']=d['summary']['passed']and not contacts and not missing
 d['summary']['status']='FINITE_RIBBON_PASS_RUNTIME_UNTESTED'if d['summary']['passed']else'FINITE_RIBBON_BLOCKED'
 write('abbey_bent_route_proof.json',d)
 write('abbey_bent_route_summary.json',{k:v for k,v in d.items()if k not in('support_checks','native_floor_source_refs','terrain_side_checks','native_contacts','upper_actual_surface_conflicts')})
 p=ref(O/'abbey_bent_route_proof.json');print(json.dumps(dict(proof=p,summary=d['summary'],boxes=near)),flush=True)
 (O/'README.md').write_text('# Existing-geometry abbey main-entry route\n\n'+json.dumps(d['summary'],indent=2)+'\n\nScene: '+d['scene']['path']+'\nSHA256: '+d['scene']['sha256']+'\n\nProof: abbey_bent_route_proof.json\nProof SHA256: '+p['sha256']+'\n\nThe full market chain is not included. Splice the recorded exact ROAD:WEST_MONASTERY_EDGE source cut into the original public chain. The route ends at the actual exterior standing point with a separately audited continuation to the church door threshold. No native/terrain geometry, placement, controller, renderer, or scene was changed.\n\nRun search_abbey.py, then audit_abbey.py, then finalize_abbey_proof.py with python -B. The screening raster is only a search heuristic; the final finite source intersections, source hashes, swept-width caps/joins, native-solid clearance, retained banks and explicit scene boxes are the proof. Controller replay and visual scene review remain untested.\n')
if __name__=='__main__':main()
