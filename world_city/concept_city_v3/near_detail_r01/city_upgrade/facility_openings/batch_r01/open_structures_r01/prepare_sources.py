"""Data-driven zero-window facility adapter using frozen roof composition.

No window geometry is invented for open structures. Native ordered nonroof
operations, passages, cuts and original constraints are passed through exactly.
"""
import importlib.util,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent;ROOT=HERE.parents[6]
sys.path[:0]=[str(B),str(B.parent),str(B/'sampler_v2'),str(B.parents[1]/'house_rules')]
import author as a
import plan_regions as planner
import reserved_io_r03 as rio
from output_reservations_v3 import ReservationBook
spec=importlib.util.spec_from_file_location('frozen_canonical_adapter',B/'canonical_adapter/compose.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def main():
    rules=a.load(HERE/'rules.json');cfgpath=B.parents[1]/'house_rules/shared_output_budget.v2.json';cfg=a.load(cfgpath);assert a.sha(cfgpath)==rio.CONFIG_SHA
    identity={'rules_sha256':a.sha(HERE/'rules.json'),'driver_sha256':a.sha(__file__),'roof_catalog_sha256':a.sha(ROOT/rules['roof_catalog']),'source_audit_sha256':a.sha(ROOT/rules['source_audit']),'adapter_sha256':a.sha(c.__file__),'planner_sha256':a.sha(planner.__file__),'budget_helper_sha256':rio.HELPER_SHA}
    book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);key='facility_sources:'+HERE.name;scopes=[{'directory':str(HERE.relative_to(ROOT)),'prefix':''}];book.reserve(key,scopes,rules['source_preparation_cap_bytes'],identity);book.acquire_writer(key);w=rio.ReservedWriter(book,key,B,scopes,ROOT)
    try:
        roofs={r['asset_key']:r for r in a.load(ROOT/rules['roof_catalog'])['assets']};audits={r['asset_key']:r for r in a.load(ROOT/rules['source_audit'])['assets']};items=[]
        for asset in rules['assets']:
            r=roofs[asset];audit=audits[asset];assert audit['source_sha256']==r['source_sha256'] and audit['render_sha256']==r['source_render_sha256'];assert audit['source_roles'].get('glass',0)==rules['require_source_glass_count']==0 and rules['new_window_operations_allowed'] is False
            src=c.checked_load(ROOT/r['source_master_path'],r['source_sha256']);render=c.checked_load(ROOT/r['source_render_path'],r['source_render_sha256']);cp=HERE/'source_contracts'/(asset+'.replacement.json.gz')
            contract={'schema':'riverstone.facility_openings.replacement.v1','asset_key':asset,'source_master_path':r['source_master_path'],'source_sha256':r['source_sha256'],'source_render_path':r['source_render_path'],'source_render_sha256':r['source_render_sha256'],'authored_master_path':r['source_master_path'],'authored_master_sha256':r['source_sha256'],'source_pitch_m':render['pitch'],'fine_pitch_m':.05,'grid_origin':src.get('grid_origin',[0,0,0]),'patches':[],'cache_quad_edits':[],'original_assembly_cuts':src.get('assembly_cuts',[]),'protected_component_entry_cuts':[],'entrances':audit['entrance_metadata'],'city_placement_ids':audit['placement_ids'],'open_structure_policy':{'source_glass_count':0,'window_count':0,'no_new_windows':True,'original_nonroof_operations_unchanged':True,'original_open_passages_preserved':True},'activation':{'runtime_ready':False,'atomic':True,'collision_reference_changed':False}}
            w.write(cp,contract);items.append({'asset_key':asset,'source_master_path':r['source_master_path'],'source_sha256':r['source_sha256'],'emitted_master_path':r['source_master_path'],'emitted_master_sha256':r['source_sha256'],'replacement_contract_path':str(cp.relative_to(ROOT)),'replacement_contract_sha256':a.sha(cp),'window_count':0,'city_placements':audit['city_placements'],'runtime_ready':False})
        wc=HERE/'unchanged_source_catalog.json';w.write(wc,{'schema':'riverstone.facility_openings.catalog.v1','assets':items,'policy':'No glazing authored in original open structure; no opening layer fabricated.'});config={'roof_catalog':rules['roof_catalog'],'window_catalog':str(wc.relative_to(ROOT)),'assets':rules['assets'],'policy':rules['policy'],'max_output_bytes':rules['source_preparation_cap_bytes']};cp=HERE/'canonical_rules.json';w.write(cp,config);c.HERE=HERE/'canonical';c.write=w.write;c.build(cp)
        planner.HERE=HERE;a.write=w.write;plans=[]
        for asset in rules['assets']:
            path=planner.make(asset,HERE/'canonical/generated/catalog.json');p=a.load(path);plans.append({k:p[k] for k in ['asset_key','chunk_count','fine_candidates','roof_candidates','contact_regions']})
        w.write(HERE/'source_preparation_report.json',{'schema':'riverstone.facility.open_structure_preparation.v1','all_pass':True,'identity':identity,'compile_calls':0,'new_window_count':0,'plans':plans,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'original_body_cut_constraint_contract':'Exact original native components and instances retained by frozen canonical adapter; later bounded occupancy and actual passage probes required.'});print(json.dumps({'source_assets':len(items),'plans':plans,'stored_bytes':book.owned_bytes(scopes),'compile_calls':0,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True);book.release(key,identity,'Source-only composition and finite-region plans complete; no sampling or runtime activation.')
    finally:w.close()
if __name__=='__main__':main()
