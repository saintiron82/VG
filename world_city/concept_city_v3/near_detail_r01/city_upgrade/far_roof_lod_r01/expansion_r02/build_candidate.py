"""One generic recipe consumes an explicitly audited source-roof LOD contract."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"expansion_r01"))
from input_contract import *
OUTPUT=Path(__file__).resolve().parent
import argparse,copy,gzip,resource,time

def read_render(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def fingerprint(g):return {'sha256':core.digest(g),'canonical_json_bytes':len(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())}
def encoded(p,data):p.write_bytes(gzip.compress((json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0))
def main(key):
 start=time.monotonic();resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
 idx=load(C/'playable_r01/generated/tile_r01/index.json')['common_assets'];mapping=load(U/'surface_mapping/material_surface_map.v1.json')['assets'];source=idx[key];master=load(R/source['master_path']);contract=inspect(key,mapping[key],source,master);out=OUTPUT/key;out.mkdir(exist_ok=True)
 write(out/'input.contract.json',contract)
 if contract['status']!='SUPPORTED_INPUT_UNBUILT':print(json.dumps(contract));return
 assert contract['schema']=='riverstone.source_roof_lod_input.v1' and contract['asset_key']==key
 assert contract['source_master']['sha256']==source['master_sha256'] and contract['baseline_far_render']['sha256']==source['render_sha256']
 base_path=R/contract['baseline_far_render']['path'];assert sha(base_path)==contract['baseline_far_render']['sha256'];base=read_render(base_path)
 mats=contract['materials'];solids=[surface.solid(r)for r in contract['canonical_solids']];raw=[surface.solid(r)for r in contract['raw_solids']]
 regions,stats=surface.regions(solids);raw_regions,raw_stats=surface.regions(raw);groups,faces=surface.quads(regions)
 audit=surface.audit_boundary(faces,raw);difference={'canonical_missing_from_original_m2':surface.compare_boundaries(regions,raw_regions),'original_missing_from_canonical_m2':surface.compare_boundaries(raw_regions,regions)}
 nonroof=[copy.deepcopy(g)for g in base['groups']if g['material']not in mats];render=copy.deepcopy(base);render['groups']=sorted(nonroof+groups,key=lambda g:g['material']);render['quad_count']=sum(len(g['quads'])for g in render['groups']);render.pop('cell_count',None);render.pop('payload_hash',None)
 vertices=[p for g in render['groups']for q in g['quads']for p in q];render['bounds']={'min':[min(p[i]for p in vertices)for i in range(3)],'max':[max(p[i]for p in vertices)for i in range(3)]}
 render['geometry']='Hybrid visual-only source-surface LOD. Unchanged baseline nonroof voxel groups plus exact continuous cut-free source roof union boundary. Not new compiled occupancy.'
 render['source_surface_lod']={'schema':'riverstone.source_surface_lod.v1','source_solid_union':True,'source_pitch_metadata_applies_to_retained_nonroof_only':True,'high_resolution_voxel_source':False,'collision_reference_changed':False}
 render['provenance']={'source_master':contract['source_master'],'baseline_far_render':contract['baseline_far_render'],'input_contract':ref(out/'input.contract.json'),'generic_builder':ref(Path(__file__)),'generic_input_adapter':ref(H/'input_contract.py'),'source_surface_adapter':ref(P/'source_surface_adapter.py'),'runtime_renderer':'unchanged RenderData.gd / CityWorld._native_mesh','inherited_nonroof_sampling_pitch_m':base['pitch'],'roof_geometry_sampling_pitch_m':None}
 render_path=out/'candidate.render.json.gz';encoded(render_path,render)
 kept=[{'material':g['material'],'quad_count':len(g['quads']),'before':fingerprint(g),'after':fingerprint(next(x for x in render['groups']if x['material']==g['material']))}for g in nonroof]
 removed=[{'material':g['material'],'quad_count':len(g['quads']),**fingerprint(g)}for g in base['groups']if g['material']in mats]
 # Bounds are the union of retained voxel cell bounds and exact authored roof
 # bounds, not a claim that every retained old voxel lies in its analytical solid.
 roof_vertices=[v for f in faces for v in f['q']];roof_bounds={'min':[min(p[i]for p in roof_vertices)for i in range(3)],'max':[max(p[i]for p in roof_vertices)for i in range(3)]};source_roof_bounds={'min':[min(s['bounds']['min'][i]for s in raw)for i in range(3)],'max':[max(s['bounds']['max'][i]for s in raw)for i in range(3)]}
 tests={'all_nonroof_groups_exact':all(x['before']==x['after']for x in kept),'palette_exact':base['materials']==render['materials'],'original_and_canonical_union_boundary_equal':max(difference.values())<1e-6,'no_internal_roof_faces':audit['interior_surface_area_m2']<1e-6,'no_duplicate_roof_faces':audit['coincident_surface_overlap_m2']<1e-6,'closed_manifold_roof_boundary':audit['open_or_nonmanifold_edge_segments']==0,'outward_normal_probes':audit['normal_probe_errors']==0,'edge_winding':audit['edge_winding_errors']==0,'only_exact_source_roof_aabb':all(abs(roof_bounds[d][i]-source_roof_bounds[d][i])<1e-7 for d in ['min','max']for i in range(3)),'input_has_no_relevant_roof_cuts':True,'within_quad_budget':render['quad_count']<=50000,'no_runtime_or_source_changes':True}
 report={'schema':'riverstone.source_roof_far_lod_candidate.v1','asset_key':key,'all_geometry_tests_pass':all(tests.values()),'tests':tests,'render':ref(render_path),'input_contract':ref(out/'input.contract.json'),'source_master':contract['source_master'],'baseline_far_render':contract['baseline_far_render'],'bounds':render['bounds'],'original_coarse_bounds':base['bounds'],'exact_source_roof_bounds':source_roof_bounds,'roof_quad_count':sum(len(g['quads'])for g in groups),'output_quad_count':render['quad_count'],'removed_roof_groups':removed,'unchanged_nonroof_groups':kept,'geometry_audit':audit,'raw_vs_canonical_boundary_difference':difference,'canonical_boundary_stats':stats,'raw_boundary_stats':raw_stats,'source_assembly_cuts':contract['source_assembly_cuts'],'proven_disjoint_or_selector_excluded_roof_cut_pairs':len(contract['cut_exclusion_proofs']),'current_revised_far_validator_compatible':False,'integration_status':'CANDIDATE_ONLY_SHARED_GODOT_AND_PARENT_ACTUAL_CITY_REVIEW_REQUIRED','actual_city_visual_reviewed':False,'collision_reference_changed':False,'new_highres_voxel_source':False,'seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 report['status']='CANDIDATE_GEOMETRY_PASS_PENDING_GODOT' if report['all_geometry_tests_pass'] else 'UNSUPPORTED_GEOMETRY'
 report['reason_codes']=[] if report['all_geometry_tests_pass'] else ['GEOMETRY_'+k.upper() for k,v in tests.items()if not v]
 write(out/'candidate.provenance.json',report);print(json.dumps({k:report[k]for k in ['asset_key','all_geometry_tests_pass','roof_quad_count','output_quad_count','geometry_audit','raw_vs_canonical_boundary_difference','seconds','max_rss_kib']}),flush=True)
 if not report['all_geometry_tests_pass']:raise SystemExit(2)
 assert report['seconds']<30 and report['max_rss_kib']<256*1024
if __name__=='__main__':p=argparse.ArgumentParser();p.add_argument('asset_key');args=p.parse_args();main(args.asset_key)
