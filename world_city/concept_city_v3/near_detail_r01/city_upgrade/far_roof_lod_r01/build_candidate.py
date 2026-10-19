"""Bounded, non-mutating source-backed far-roof LOD candidate orchestration."""
from __future__ import annotations
import argparse,copy,gzip,hashlib,json,resource,sys,time
from pathlib import Path
H=Path(__file__).resolve().parent;U=H.parent;R=H.parents[4];C=U.parents[1]
sys.path[:0]=[str(R),str(U),str(U/'facility_roofs')]
from voxel_character.common import core
from build_near_catalog import source_parts
import author_facility_roofs as roofs
import source_surface_adapter as surface

def load(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(Path(p).relative_to(R)),sha256=sha(p))
def write(p,d):
 raw=(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
 if p.suffix=='.gz':raw=gzip.compress(raw,compresslevel=9,mtime=0)
 p.write_bytes(raw)
def fingerprint(d):return dict(sha256=core.digest(d),canonical_json_bytes=len(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()))

def main(key):
 started=time.monotonic()
 resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
 source=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'][key]
 entry=load(C/'playable_detail_r01/near_catalog.json')['assets'][key]
 master_path=R/source['master_path'];master=load(master_path)
 assert sha(master_path)==source['master_sha256']==entry['source_master_sha256']
 old_far_path=R/entry['far_visual_render_path'];old=load(old_far_path);assert sha(old_far_path)==entry['far_visual_render_sha256']
 revision=entry['source_revision'];revised=load(R/revision['revised_master_path']);assert sha(R/revision['revised_master_path'])==revision['revised_master_sha256']
 proxy_path=R/entry['shadow_proxy_path'];proxy=load(proxy_path);assert sha(proxy_path)==entry['shadow_proxy_sha256'] and proxy['source_master_sha256']==source['master_sha256']
 mapping=load(U/'surface_mapping/material_surface_map.v1.json')['assets'][key]
 descriptor=roofs.describe(key,mapping,master)
 assert not descriptor['pending'] and not descriptor['preserved_terminal_component_cuts'] and not master.get('assembly_cuts')
 materials=descriptor['suppression']['safe_material_groups_when_full_matching_near_resource_ready']
 assert materials and not descriptor['suppression']['unsafe_material_groups']
 raw_records=[];proof=[];priority={}
 for idx,(ins,op,tr) in enumerate(source_parts(master)):
  if op.get('material')not in materials:continue
  assert op['action']=='paint' and (ins['component']=='roof' or ins['component'].endswith('_roof'))
  priority[(ins['component'],op['id'])]=idx
  rec=dict(id=ins['id']+'/'+op['id'],material=op['material'],shape=op['shape'],transform=tr,priority=idx)
  raw_records.append(rec);proof.append(dict(instance=ins['id'],component=ins['component'],operation=op['id'],operation_sha256=core.digest(op),transform_sha256=core.digest(tr)))
 assert len(raw_records)==len(proxy['extrusions'])==len(proxy['source_operations'])
 for rec,p,source_op in zip(raw_records,proxy['extrusions'],proxy['source_operations']):
  shape=rec['shape']
  if shape['kind']=='box':
   lo,hi=shape['min'],shape['max'];shape=dict(kind='extrusion',polygon=[[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]],z_min=lo[2],z_max=hi[2])
  assert all(shape[k]==p[k]for k in ['polygon','z_min','z_max']) and rec['transform']==p['transform']
 assert [p['operation_sha256']for p in proof]==[p['operation_sha256']for p in proxy['source_operations']]
 original_components={c['id']:c for c in master['components']};revised_components={c['id']:c for c in revised['components']}
 for component in set(p['component']for p in proof):assert original_components[component]==revised_components[component]
 canonical=[]
 for p in descriptor['planes']:
  # Existing descriptor merges only exactly adjoining, matching source bands.
  aa,bb=p['x_min'],p['x_max'];ya,yb=p['y_at_x_min'],p['y_at_x_max'];th=p['vertical_skin_thickness_m']
  shape=dict(kind='extrusion',polygon=[[aa,ya-th],[bb,yb-th],[bb,yb],[aa,ya]],z_min=p['z_min'],z_max=p['z_max'])
  for ins in p['component_instances']:
   canonical.append(dict(id=ins['id']+'/'+p['id'],material=p['material'],shape=shape,transform=core.compose(ins['transform'],p['operation_transform']),priority=max(priority[(p['component'],op)]for op in p['source_operations']),source_operations=p['source_operations']))
 for p in descriptor['retained_ridge_boxes']:
  op=p['operation']
  for ins in p['component_instances']:
   canonical.append(dict(id=ins['id']+'/'+op['id'],material=op['material'],shape=op['shape'],transform=core.compose(ins['transform'],core.transform(op.get('transform'))),priority=priority[(p['component'],op['id'])],source_operations=[op['id']]))
 canonical.sort(key=lambda p:p['priority'])
 solids=[surface.solid(r)for r in canonical];raw_solids=[surface.solid(r)for r in raw_records]
 regions,stats=surface.regions(solids);raw_regions,raw_stats=surface.regions(raw_solids)
 groups,quad_records=surface.quads(regions)
 audit=surface.audit_boundary(quad_records,raw_solids)
 difference=dict(canonical_missing_from_raw_m2=surface.compare_boundaries(regions,raw_regions),raw_missing_from_canonical_m2=surface.compare_boundaries(raw_regions,regions))
 nonroof=[copy.deepcopy(g)for g in old['groups']if g['material']not in materials]
 output=copy.deepcopy(old);output['groups']=sorted(nonroof+groups,key=lambda g:g['material']);output['quad_count']=sum(len(g['quads'])for g in output['groups'])
 vertices=[v for g in output['groups']for q in g['quads']for v in q]
 output['bounds']={'min':[min(v[i]for v in vertices)for i in range(3)],'max':[max(v[i]for v in vertices)for i in range(3)]}
 output.pop('cell_count',None);output.pop('payload_hash',None)
 output['geometry']='Hybrid visual-only LOD: unchanged common .5m nonroof quads plus exact continuous authored roof union boundary. Not a new fine voxel source or compiled occupancy.'
 output['provenance']={'base_far_render':ref(old_far_path),'source_roof_master':ref(master_path),'source_shadow_proxy':ref(proxy_path),'source_surface_adapter':ref(H/'source_surface_adapter.py'),'builder':ref(Path(__file__)),'common_render_interface':'riverstone.voxel.render.v1','runtime_renderer':'unchanged RenderData.gd / CityWorld._native_mesh','inherited_nonroof_sampling_pitch_m':old['pitch'],'roof_geometry_sampling_pitch_m':None}
 output['source_surface_lod']={'schema':'riverstone.source_surface_lod.v1','source_solid_union':True,'source_pitch_metadata_applies_to_retained_nonroof_only':True,'high_resolution_voxel_source':False,'collision_reference_changed':False}
 roof_path=H/'roof_union_boundary.render.json';roof=copy.deepcopy(output);roof['groups']=groups;roof['quad_count']=sum(len(g['quads'])for g in groups);rv=[v for g in groups for q in g['quads']for v in q];roof['bounds']={'min':[min(v[i]for v in rv)for i in range(3)],'max':[max(v[i]for v in rv)for i in range(3)]}
 out_path=H/'candidate.render.json.gz';write(out_path,output);write(roof_path,roof)
 write(H/'canonical_source_solids.json',{'schema':'riverstone.source_surface_solids.v1','asset_key':key,'solids':canonical,'source_operations':proof,'original_operation_count':len(raw_records),'canonical_solids':len(canonical),'source_master':ref(master_path),'shadow_proxy':ref(proxy_path)})
 kept_proofs=[{'material':g['material'],'quad_count':len(g['quads']),'before':fingerprint(g),'after':fingerprint(next(x for x in output['groups']if x['material']==g['material']))}for g in nonroof]
 removed=[{'material':g['material'],'quad_count':len(g['quads']),**fingerprint(g)}for g in old['groups']if g['material']in materials]
 tests={'source_hashes_match':True,'shadow_proxy_matches_original_source_solids':True,'revised_source_roof_component_unchanged':True,'only_source_owned_roof_groups_removed':True,'nonroof_groups_canonical_json_exact':all(p['before']==p['after']for p in kept_proofs),'palette_exact':output['materials']==old['materials'],'source_union_domains_equal':max(difference.values())<1e-6,'no_interior_roof_surface':audit['interior_surface_area_m2']<1e-6,'no_duplicate_roof_surface':audit['coincident_surface_overlap_m2']<1e-6,'outward_normal_probes_pass':audit['normal_probe_errors']==0,'no_open_or_nonmanifold_roof_boundary':audit['open_or_nonmanifold_edge_segments']==0,'edge_winding_pass':audit['edge_winding_errors']==0,'within_existing_near_source_aabb':all(output['bounds']['min'][i]>=entry['visual_bounds']['min'][i]-1e-7 and output['bounds']['max'][i]<=entry['visual_bounds']['max'][i]+1e-7 for i in range(3)),'runtime_unchanged':True,'collision_reference_unchanged':True}
 report={'schema':'riverstone.source_roof_far_lod_candidate.v1','asset_key':key,'all_geometry_tests_pass':all(tests.values()),'tests':tests,'render':ref(out_path),'roof_only_render':ref(roof_path),'canonical_source_solids':ref(H/'canonical_source_solids.json'),'base_far_render':ref(old_far_path),'base_far_contract':ref(R/entry['far_visual_contract_path']),'source_master':ref(master_path),'source_revision':ref(R/entry['source_revision_path']),'revised_master':ref(R/revision['revised_master_path']),'source_shadow_proxy':ref(proxy_path),'original_roof_solids':len(raw_records),'canonical_roof_solids':len(solids),'roof_quad_count':roof['quad_count'],'output_quad_count':output['quad_count'],'removed_roof_groups':removed,'unchanged_nonroof_groups':kept_proofs,'geometry_audit':audit,'raw_vs_canonical_boundary_difference':difference,'canonical_boundary_stats':stats,'raw_boundary_stats':raw_stats,'bounds':output['bounds'],'source_bounds_contract':entry['bounds_contract'],'integration_status':'CANDIDATE_ONLY_PARENT_ACTUAL_RENDER_AND_NEW_EXPLICIT_FAR_CONTRACT_REQUIRED','current_revised_far_validator_compatible':False,'blocker':'Exact authored y40 roof exceeds old coarse y39.5 envelope. Use a distinct source-bounded continuous far LOD contract; do not silently weaken old validator.','is_new_highres_voxel_source':False,'changed_source_master':False,'changed_runtime':False,'changed_collision':False,'actual_city_visual_reviewed':False,'existing_helpers':[ref(Path(roofs.__file__)),ref(Path(surface.clip.__file__)),ref(R/'voxel_character/tools/mesh.py'),ref(R/'voxel_character/common/core.py'),ref(C/'playable_detail_r01/RenderData.gd')],'seconds':time.monotonic()-started,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 write(H/'candidate.provenance.json',report)
 print(json.dumps({k:report[k]for k in ['all_geometry_tests_pass','roof_quad_count','output_quad_count','geometry_audit','raw_vs_canonical_boundary_difference','seconds','max_rss_kib']}),flush=True)
 assert report['seconds']<=30 and report['max_rss_kib']<256*1024
 assert sum(p.stat().st_size for p in H.rglob('*')if p.is_file())<10*1024*1024
 assert report['all_geometry_tests_pass'],tests
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--asset',default='registered_cathedral_nave_aisles_transept');a=p.parse_args();main(a.asset)
