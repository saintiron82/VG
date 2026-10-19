"""Exact source aperture authoring with explicitly selected roof variants.

This is configuration of frozen author/composition functions; no voxel sampling.
"""
from pathlib import Path
import importlib.util,json,resource,sys
HERE=Path(__file__).resolve().parent;B=HERE.parent;ROOT=B.parents[5]
sys.path[:0]=[str(B.parent),str(B/'native_pitch_v1'),str(B/'sampler_v2'),str(B.parent.parent/'house_rules'),str(HERE)]
import author as a
import plan_selected_variant_r01 as planner
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
adapter=module('selected_aperture_author',B/'aperture_rules/adapter.py')
c=module('selected_roof_composer',B/'canonical_adapter/compose.py')
def ref(p):return {'path':str(Path(p).resolve().relative_to(ROOT)),'sha256':a.sha(p)}
def main(directory):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));d=directory.resolve();rules=a.load(d/'rules.v1.json');cfg=a.load(B.parent.parent/'house_rules/shared_output_budget.v2.json');identity={n:ref(p) for n,p in [('driver',__file__),('rules',d/'rules.v1.json'),('aperture_adapter',adapter.__file__),('canonical_adapter',c.__file__),('planner',planner.__file__),('roof_catalog',ROOT/rules['roof_catalog']),('selector',ROOT/rules['roof_selector'])]};book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);rk='facility_selected_aperture_sources:'+d.name;scopes=[{'directory':str(d.relative_to(ROOT)),'prefix':''},{'directory':str(HERE.relative_to(ROOT)),'prefix':'prepare_selected_aperture_sources.py'},{'directory':str(HERE.relative_to(ROOT)),'prefix':'plan_selected_variant_r01.py'}];book.reserve(rk,scopes,1500000,identity);book.acquire_writer(rk);w=rio.ReservedWriter(book,rk,B,scopes,ROOT)
 try:
  adapter.HERE=d;adapter.a.write=w.write;a.write=w.write;_,audits,windows=adapter.read_inputs();roofrows={r['asset_key']:r for r in a.load(ROOT/rules['roof_catalog'])['assets']};selector=a.load(ROOT/rules['roof_selector']);items=[];out=d/'canonical/generated'
  for key in rules['asset_keys']:
   variants={r['selected_variant_asset_key'] for r in selector['placements'] if r['native_asset_key']==key};assert len(variants)==1,'Whole-native replacement requires exactly one selected variant';variant=next(iter(variants));r=roofrows[variant];assert r['native_asset_key']==key;win=adapter.author_asset(audits[key],windows[key],rules)
   for path,sha in [(r['source_master_path'],r['source_sha256']),(r['emitted_master_path'],r['emitted_master_sha256']),(win['emitted_master_path'],win['emitted_master_sha256'])]:assert a.sha(ROOT/path)==sha
   assert r['source_sha256']==win['source_sha256'];source=a.load(ROOT/r['source_master_path']);window=a.load(ROOT/win['emitted_master_path']);roof=a.load(ROOT/r['emitted_master_path']);combined,proof=c.compose_master(source,window,roof,rules['roof_policy']);contract=a.load(ROOT/win['replacement_contract_path']);render=a.load(ROOT/contract['source_render_path']);assert a.sha(ROOT/contract['source_render_path'])==contract['source_render_sha256']==r['source_render_sha256'];scope=c.replacement_scope(source,render,proof,rules['roof_policy']);binding={'roof_variant_asset_key':variant,'roof_covering':r['covering'],'roof_selector_path':rules['roof_selector'],'roof_selector_sha256':a.sha(ROOT/rules['roof_selector']),'roof_master_path':r['emitted_master_path'],'roof_master_sha256':r['emitted_master_sha256']};combined['provenance']['canonical_roof_openings'].update(binding);mp=out/(key+'.canonical.master.json.gz');w.write(mp,combined);pp=out/(key+'.composition_proof.json.gz');proof.update(asset_key=key,source_master_sha256=r['source_sha256'],window_master_path=win['emitted_master_path'],window_master_sha256=win['emitted_master_sha256'],canonical_master_sha256=a.sha(mp),source_preparation_identity=identity,**binding);w.write(pp,proof)
   contract.update(authored_master_path=str(mp.relative_to(ROOT)),authored_master_sha256=a.sha(mp),roof_replacement_scope=scope,**binding);contract['roof_composition']={**binding,'canonical_master_path':str(mp.relative_to(ROOT)),'canonical_master_sha256':a.sha(mp),'composition_proof_path':str(pp.relative_to(ROOT)),'composition_proof_sha256':a.sha(pp),'native_instances_and_constraints_preserved':True,'full_compile':False};cp=out/(key+'.replacement.json.gz');w.write(cp,contract);items.append({**win,**binding,'emitted_master_path':str(mp.relative_to(ROOT)),'emitted_master_sha256':a.sha(mp),'replacement_contract_path':str(cp.relative_to(ROOT)),'replacement_contract_sha256':a.sha(cp),'composition_proof_path':str(pp.relative_to(ROOT)),'composition_proof_sha256':a.sha(pp),'canonical_common_master':True})
  catalog=out/'catalog.json';w.write(catalog,{'schema':'riverstone.canonical_roof_openings.catalog.v1','assets':items,'input_catalog_and_config_hashes':identity,'compile_calls':0,'runtime_ready':False});planner.HERE=d;plans=[]
  for item in items:
   p=planner.make(item['asset_key'],catalog);v=a.load(p);plans.append({k:v[k] for k in ['asset_key','selected_roof_binding','chunk_count','fine_candidates','roof_candidates']});plans[-1].update(window_count=item['window_count'],plan=ref(p))
  w.write(d/'source_preparation_report.json',{'all_pass':True,'compile_calls':0,'identity':identity,'plans':plans,'source_components_and_instances_preserved':True,'source_cuts_retained_before_additional_glass_trims':True,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss});book.release(rk,identity,'Exact selected roof variant, source aperture and finite plan prepared without sampling.');print(json.dumps({'plans':plans,'source_bytes':book.owned_bytes(scopes),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'compile_calls':0}),flush=True)
 finally:w.close()
if __name__=='__main__':main(Path(sys.argv[1]))
