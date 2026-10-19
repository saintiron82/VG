"""Source-defined open-structure verification for cut-free zero-window assets.

This deliberately rejects functional cuts; the native cut-witness path is used
for those assets. Rays prove sampled passages, not complete empty volumes.
"""
import argparse,hashlib,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B/'native_pitch_v1'),str(B/'sampler_v2')]
import verify_native_semantics as v
a=v.a

def source_proof(source,canonical,contract,proof):
 assert not contract['patches'],'Window assets need actual pane-depth witnesses'
 assert not source.get('assembly_cuts'),'Functional assembly cuts need independent cut-state witnesses'
 assert all(o['action']=='paint' for c in source['components'] for o in c['operations']),'Functional component cuts need independent cut-state witnesses'
 assert source['instances']==canonical['instances'] and source.get('constraints',[])==canonical.get('constraints',[])
 selected=set(proof['source_roof_components']);old={c['id']:c for c in source['components']};new={c['id']:c for c in canonical['components']};assert list(old)==list(new)
 assert selected<=old.keys() and all(new[k]==old[k] for k in old if k not in selected)
 assert source.get('assembly_cuts',[])==canonical.get('assembly_cuts',[])
 assert any(c.get('kind')=='empty_region' and not c.get('selector',{}) and c.get('shape',{}).get('kind')=='box' and not c.get('transform') for c in source.get('constraints',[])),'No supported original empty box'
 return {'original_instances_constraints_and_nonroof_components_exact':True,'original_functional_cut_count':0,'selected_roof_components':sorted(selected),'window_count':0}

def main(catalog,render):
 start=time.monotonic();cat=a.load(catalog);w=v.rio.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules')
 try:
  for path,sha in [(cat['source_master_path'],cat['source_sha256']),(cat['source_render_path'],cat['source_render_sha256']),(cat['canonical_master_path'],cat['canonical_master_sha256']),(cat['window_contract_path'],cat['window_contract_sha256'])]:assert a.sha(a.ROOT/path)==sha
  source=a.load(a.ROOT/cat['source_master_path']);canonical=a.load(a.ROOT/cat['canonical_master_path']);contract=a.load(a.ROOT/cat['window_contract_path']);pr=contract['roof_composition'];assert a.sha(a.ROOT/pr['composition_proof_path'])==pr['composition_proof_sha256'];proof=a.load(a.ROOT/pr['composition_proof_path']);structural=source_proof(source,canonical,contract,proof)
  original=a.load(a.ROOT/cat['source_render_path']);oldrows=[(g['material'],q) for g in original['groups'] for q in g['quads']];newrows=list(v.sr.iter_quads(render));probes=v.empty_constraint_probes(source,oldrows);assert probes
  references={'driver':v.ref(__file__),'finite_ray_and_functional_domain_helper':v.ref(v.__file__),'source_master':v.ref(a.ROOT/cat['source_master_path']),'source_render':v.ref(a.ROOT/cat['source_render_path']),'canonical_master':v.ref(a.ROOT/cat['canonical_master_path']),'replacement_contract':v.ref(a.ROOT/cat['window_contract_path']),'composition_proof':v.ref(a.ROOT/pr['composition_proof_path']),'source_preparation_identity':proof.get('source_preparation_identity',{})}
  semantic=contract.get('semantic_protection_path')
  if semantic:assert a.sha(a.ROOT/semantic)==contract['semantic_protection_sha256'];references['source_semantic_inventory']=v.ref(a.ROOT/semantic)
  witness={'schema':'riverstone.facility.native_functional_witnesses.v1','asset_key':cat['asset_key'],'source_references':references,'window_count':0,'probes':probes,'functional_features':[],'structural_checks':structural,'scope':'Finite rays inside unchanged original all-part empty box constraints; original nonroof components and instances are exact. No functional cuts exist. No full-volume emptiness or architectural manifold claim.'};wp=B/'polygon_sources/emitted_qa'/(cat['asset_key']+'.native_source_witnesses.json');w.write(wp,witness)
  failures=[{'id':p['id'],'crossing_faces':sum(v.hits(q,p) for _,q in newrows)} for p in probes];failures=[p for p in failures if p['crossing_faces']];digest=hashlib.sha256()
  for m,q in newrows:digest.update(json.dumps([m,q],separators=(',',':')).encode())
  report={'schema':'riverstone.facility.native_emitted_geometry_qa.v1','asset_key':cat['asset_key'],'render_path':str(render.relative_to(a.ROOT)),'render_sha256':a.sha(render),'quad_count':len(newrows),'ordered_material_quad_digest':digest.hexdigest(),'source_witness_reference':v.ref(wp),'reserved_driver_reference':v.ref(__file__),'window_count':0,'entry_passage_ray_count':len(probes),'functional_feature_count':0,'semantic_protection_all_pass':not failures,'failure_count':len(failures),'failures':failures,'all_pass':not failures,'elapsed_seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};w.write(B/'polygon_sources/emitted_qa'/(cat['asset_key']+'.emitted_geometry_qa.json'),report);print(json.dumps(report),flush=True);assert report['all_pass']
 finally:w.close()
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('render',type=Path);q=p.parse_args();main(q.catalog.resolve(),q.render.resolve())
