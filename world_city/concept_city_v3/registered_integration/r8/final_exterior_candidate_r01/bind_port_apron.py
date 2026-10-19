"""Bind compiled port apron ownership to its exact untouched R7 source rows."""
import pathlib,json,numpy as np
from world_city.concept_city_v3.registered_integration.r6 import apply_packs as a,merge_patches as m
from world_city.concept_city_v3.registered_integration.r7 import surface_guard
D=pathlib.Path(__file__).resolve().parent

def ref(p):return dict(path=a.rel(p),sha256=a.sha(p))
def read(r):return a.load(a.ROOT/r['path'],r['sha256'])
def main():
 bp=a.CITY/'registered_topography/revisions/public_corridors_r18/causeway_side_joins_r01/final23_joined_r01/activation_binding.json';b=a.load(bp);lp=D/'port_source_location_r03.json';loc=a.load(lp);requests=read(loc['requests']);base=read(b['base_scene']);out=D/'port_atomic_activation_r02';assert not out.exists();out.mkdir();edits=[]
 assert loc['unique']==59 and not loc['missing']and not loc['ambiguous']
 for r,q in zip(loc['rows'],requests['current_top_retirement_requests']):
  x=r['locations'][0];assert x['kind']=='base'and x['source']==b['base_scene'];assert r['triangle_sha256']==q['source_triangle_sha256'];edits.append(dict(material=x['material'],triangle_index=x['triangle_index'],source_triangle_sha256=q['source_triangle_sha256'],replacement_triangles_xyz_m=q['replacement_triangles_xyz_m']))
 mats={e['material']for e in edits};patch=dict(schema='riverstone.finite_native_ownership.v1',id='R8_PORT_NATIVE_APRON_TOP_OWNERSHIP_R01',base_scene_sha256=b['base_scene']['sha256'],status='source_verified_runtime_pending',source_surface_hashes={k:m.canonical_sha(base['surfaces'][k])for k in mats},surface_edits=edits,appended_surfaces={},removed_foundation_proxy_ids=[],source_references=[loc['requests'],ref(lp)],policy='Retire only exact source-plane area beneath measured new coarse/fine native tops. Preserve all other source plane pieces and native bridge geometry.')
 m.validate_against_scene(base,patch);guard=surface_guard.audit_patch(patch);keys={(r['material'],r['triangle_index'])for r in edits};overlap=[]
 for pi,r in enumerate(b['patches']):
  p=read(r)
  for row in p['surface_edits']:
   if(row['material'],row['triangle_index'])in keys:overlap.append([pi,row['material'],row['triangle_index']])
 assert not overlap,overlap
 ts=np.asarray([t for r in edits for t in r['replacement_triangles_xyz_m']],dtype=np.float64);qt=ts.astype(np.float32);cross=np.cross(qt[:,1]-qt[:,0],qt[:,2]-qt[:,0]);assert not np.any(cross[:,1]<0);assert not np.any((cross[:,1]==0)&np.any(cross!=0,axis=1))
 pp=out/'scene_patch.json';pp.write_text(json.dumps(patch,separators=(',',':'))+'\n');b['patches'].append(ref(pp));pack=read(requests['native_pack'])
 for v in (pack['assets'].values() if isinstance(pack['assets'],dict) else pack['assets']):a.asset_record(v)
 b['packs'].append(dict(requests['native_pack'],name='compiled_port_side_apron'))
 cp=a.CITY/'assemblies/waterworks/registered_bridge/port_approach_r01/collision_contract_r02.json';b['collision_contracts'].append(ref(cp));b['evidence'] += [loc['requests'],ref(lp)]
 review=dict(status='PASS_EXACT_SOURCE_AND_FLOAT32_TOP_BINDING_RUNTIME_PENDING',source_binding=ref(bp),requests=loc['requests'],source_triangles=len(edits),retained_triangles=len(ts),float32_exact_zero_faces=int(np.all(cross==0,axis=1).sum()),nonzero_downward_or_vertical_faces=0,prior_patch_overlap=overlap,source_guard=guard,retired_area_m2=requests['removed_current_top_area_m2'],native_pack=requests['native_pack'],collision_contract=ref(cp))
 p=out/'review.json';p.write_text(json.dumps(review,indent=2)+'\n');b['evidence'].append(ref(p));b['source_stage']='Integrated110 holdings with compiled port apron and both causeway side approaches. Thirteen final23 microscopic top-emission cases remain a declared candidate hold; full composed review is pending.'
 p=out/'activation_binding.json';p.write_text(json.dumps(b,indent=2)+'\n');print(ref(p),len(b['patches']),len(b['packs']),len(b['collision_contracts']),flush=True)
if __name__=='__main__':main()
