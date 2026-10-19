"""Configure frozen polygon windows + exact native-cut roof prefix composition."""
from pathlib import Path
import copy,json,resource,sys
HERE=Path(__file__).resolve().parent;B=HERE.parent;D=HERE/'hip_sources';ROOT=B.parents[5]
sys.path[:0]=[str(B.parent),str(B/'native_pitch_v1'),str(B/'sampler_v2'),str(HERE/'hip_contract_r01'),str(B.parent.parent/'house_rules')]
import author as a
import compose_cut_roof as adapter
import plan_regions_native_r02 as planner
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook

def ref(p):return {'path':str(Path(p).resolve().relative_to(ROOT)),'sha256':a.sha(p)}
def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));rules=a.load(D/'rules.v1.json');cfg=a.load(B.parent.parent/'house_rules/shared_output_budget.v2.json');identity={'driver':ref(__file__),'rules':ref(D/'rules.v1.json'),'polygon_author':ref(a.__file__),'roof_adapter':ref(adapter.__file__),'planner':ref(planner.__file__),'roof_catalog':ref(ROOT/rules['roof_catalog'])};book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);rk='facility_small_polygon_cut_sources:r01';scopes=[{'directory':str(D.relative_to(ROOT)),'prefix':''}];book.reserve(rk,scopes,1500000,identity);book.acquire_writer(rk);w=rio.ReservedWriter(book,rk,B,scopes,ROOT)
 try:
  a.HERE=D;a.write=w.write;(D/'generated').mkdir(parents=True,exist_ok=True);a.author();windows=a.load(D/'generated/catalog.json');roofrows={r['asset_key']:r for r in a.load(ROOT/rules['roof_catalog'])['assets']};items=[];proofrefs=[];out=D/'canonical/generated'
  for win in windows['assets']:
   key=win['asset_key'];r=roofrows[key]
   for path,sha in [(r['source_master_path'],r['source_sha256']),(r['emitted_master_path'],r['emitted_master_sha256']),(win['emitted_master_path'],win['emitted_master_sha256'])]:assert a.sha(ROOT/path)==sha
   assert r['source_sha256']==win['source_sha256'];source=a.load(ROOT/r['source_master_path']);window=a.load(ROOT/win['emitted_master_path']);roof=a.load(ROOT/r['emitted_master_path']);combined,proof=adapter.compose_master(source,window,roof,rules['roof_policy']);contract=a.load(ROOT/win['replacement_contract_path']);render=a.load(ROOT/contract['source_render_path']);assert a.sha(ROOT/contract['source_render_path'])==contract['source_render_sha256']==r['source_render_sha256'];scope=adapter.replacement_scope(source,render,proof,rules['roof_policy']);mp=out/(key+'.canonical.master.json.gz');w.write(mp,combined);pp=out/(key+'.composition_proof.json.gz');proof.update(asset_key=key,source_master_sha256=r['source_sha256'],window_master_path=win['emitted_master_path'],window_master_sha256=win['emitted_master_sha256'],roof_master_path=r['emitted_master_path'],roof_master_sha256=r['emitted_master_sha256'],canonical_master_sha256=a.sha(mp),source_preparation_identity=identity);w.write(pp,proof)
   contract.update(authored_master_path=str(mp.relative_to(ROOT)),authored_master_sha256=a.sha(mp),roof_replacement_scope=scope,roof_composition={'canonical_master_path':str(mp.relative_to(ROOT)),'canonical_master_sha256':a.sha(mp),'composition_proof_path':str(pp.relative_to(ROOT)),'composition_proof_sha256':a.sha(pp),'roof_master_path':r['emitted_master_path'],'roof_master_sha256':r['emitted_master_sha256'],'native_instances_and_constraints_preserved':True,'original_roof_paint_cut_prefix_preserved':True,'full_compile':False});cp=out/(key+'.replacement.json.gz');w.write(cp,contract);items.append({**win,'emitted_master_path':str(mp.relative_to(ROOT)),'emitted_master_sha256':a.sha(mp),'replacement_contract_path':str(cp.relative_to(ROOT)),'replacement_contract_sha256':a.sha(cp),'composition_proof_path':str(pp.relative_to(ROOT)),'composition_proof_sha256':a.sha(pp),'roof_master_path':r['emitted_master_path'],'roof_master_sha256':r['emitted_master_sha256'],'canonical_common_master':True});proofrefs.append(ref(pp))
  catalog=out/'catalog.json';w.write(catalog,{'schema':'riverstone.canonical_roof_openings.catalog.v1','assets':items,'input_catalog_and_config_hashes':identity,'compile_calls':0,'runtime_ready':False});planner.HERE=D;plans=[]
  for item in items:
   p=planner.make(item['asset_key'],catalog);d=a.load(p);plans.append({'asset_key':item['asset_key'],'window_count':item['window_count'],'chunk_count':d['chunk_count'],'fine_candidates':d['fine_candidates'],'roof_candidates':d['roof_candidates'],'contact_region_count':len(d['contact_regions']),'plan':ref(p)})
  w.write(D/'source_preparation_report.json',{'all_pass':True,'compile_calls':0,'identity':identity,'proofs':proofrefs,'plans':plans,'source_reference_preserved':True,'new_solid_body_or_collider_authored':False,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss});book.release(rk,identity,'Original roof cut-prefix and generic polygon window sources/finite plans ready; no voxel sampling.');print(json.dumps({'plans':plans,'source_bytes':book.owned_bytes(scopes),'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'compile_calls':0}),flush=True)
 finally:w.close()
if __name__=='__main__':main()
