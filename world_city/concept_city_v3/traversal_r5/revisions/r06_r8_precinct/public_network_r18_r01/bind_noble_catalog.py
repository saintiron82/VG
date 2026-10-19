"""Replace prior noble candidates with the sealed actual fine-entry chains."""
import collections,hashlib,json,math,pathlib,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path[:0]=[str(H),str(ROOT)];import catalog
from world_city.runtime_city.checks import placement as g
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def inside(pt,poly):
 sign=1 if g.signed_polygon_area(poly)>0 else-1
 return all(sign*g._cross(u,v,pt)>=-1e-8*max(math.dist(u,v),1e-12)for u,v in zip(poly,poly[1:]+poly[:1]))
def main():
 base=H/'route_catalog_41_holdings_r02.json';d=read(base);folder=ROOT/'world_city/concept_city_v3/assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/noble_entry_batch_r01';hp=folder/'integration_handoff.json';handoff=read(hp);assert ref(hp)['sha256']=='85b5787f7dfd35ef7aa589b23bb111334dbcba1553ebaf7a27fe5618045239f1';rp=catalog.source(handoff['runtime_routes']);source=read(rp);rows=source['routes'];assert len(rows)==7;lookup={r['id']:r for r in d['routes']};substitutions=[]
 for row in rows:
  owner=row['owner_id'];rid='NOBLE:'+owner+':registered_r1:service_gate';old=lookup[rid];physical_path=catalog.source(row['physical_top']);physical=read(physical_path);points=[]
  for pt in row['polyline_xz_m']:
   hits=[p for p in physical['top_pieces']if inside(pt,p['polygon_xz_m'])]
   if hits:y=math.fsum(p['plane_y_xz_m'][0]*pt[0]+p['plane_y_xz_m'][1]*pt[1]+p['plane_y_xz_m'][2]for p in hits)/len(hits)
   else:
    # This is only a source hint at the fixed public end. The final scene
    # supplies actual standing height; no missing physical floor is created.
    seam=row['source_public_endpoint']['seam_xyz_m'];near=min(seam,key=lambda p:math.hypot(p[0]-pt[0],p[2]-pt[1]));y=near[1]
   points.append([pt[0],y,pt[1]])
  substitutions.append(dict(case_id=rid,old_catalog=ref(base),old_points_xyz_m=old['points_xyz_m'],new_source_route_id=row['id'],new_points_xyz_m=points,reason='Use sealed native fine-entry route and its exact R18 public endpoint instead of the earlier source gate candidate.'))
  contract=next(r['contract']for r in handoff['collision_contracts']if r['owner_id']==owner)
  old.update(points_xyz_m=points,source_width_m=row['width_m'],source_route_id=row['id'],source_road_ids=[row['named_public_road_id']],test_scope='Sealed 2 m noble fine-entry center route and fixed public endpoint, both directions. Continuous native collision envelope and R18 continuation must both be active; no interior or full-width runtime claim.',provenance=[ref(hp),ref(rp),row['physical_top'],contract],resolved_geometry_proof=ref(rp),source_geometry_basis='SEALED_NATIVE_FINE_ENTRY_AND_FIXED_PUBLIC_ENDPOINT',native_fine_id=row['native_fine_id'])
  d['sources']['noble_physical_top_'+owner]=row['physical_top'];d['sources']['noble_contract_'+owner]=contract
 d['sources'].update(prior_41_catalog=ref(base),noble_integration_handoff=ref(hp),noble_runtime_routes=ref(rp),noble_native_pack=handoff['native_pack'],noble_private_route_audit=handoff['private_static_clearance'])
 d['activation_requirements']['native_packs'].append(handoff['native_pack']);d['activation_requirements']['collision_contracts']=[r['contract']for r in handoff['collision_contracts']];d['source_candidate_accounting']['noble_route_substitutions']=substitutions
 d['limits'].append('Seven noble fine-entry centerlines use the sealed source routes and exact native collision envelopes. Static full-width proof and runtime centerline proof remain distinct.')
 expanded=catalog.validate(d);out=H/'route_catalog_41_noble_r03.json';write(out,d);write(H/'catalog_noble_binding_report.json',dict(status='SOURCE_BOUND_AWAITING_EXACT_JOINT_SCENE',catalog=ref(out),expanded_cases=len(expanded),noble_directions=14,native_pack_sets=len(d['activation_requirements']['native_packs']),required_collision_contracts=len(d['activation_requirements']['collision_contracts']),source_route_substitutions=len(substitutions)));print(json.dumps(read(H/'catalog_noble_binding_report.json'),indent=2))
if __name__=='__main__':main()
