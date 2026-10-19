#!/usr/bin/env python3
"""Check actual published composition's unchanged-cache reuse provenance."""
from validate_cache_identity import *
def main():
 t=time.monotonic();cp=read(R/'cache_plan.json');c=read(R/'composition.json');fixed='45e9b206d2b126df7dd2ce878f70ada312a122a49c9a958098d08ae1406cb4d5';assert sha(R/'roof_repaired.render.json.gz')==fixed and c['render']['sha256']==fixed
 assert len(cp['chunks'])==len(c['chunks'])==88;reused=rebuilt=quads=0;records=[]
 for i,(p,r) in enumerate(zip(cp['chunks'],c['chunks'])):
  if p['reuse_exact_cache']:
   path=ROOT/p['original_cache']['path'];assert r['reused_exact_r03_cache'] is True and r['cache_reference']==p['original_cache'] and r['validated_halo_material_sha256']==p['r04_halo_material_sha256']==p['r03_halo_material_sha256'];cached=read(path);assert cached['record']==p['record'];reused+=1;union=cp['source_union']['sha256']
  else:
   path=R/f'mesh_cache/chunk_{i:03d}.json.gz';cached=read(path);assert cached['record']==r;rebuilt+=1;union=cp['new_union']['sha256']
  assert cached['upper_union_sha256']==union and cached['mesher_sha256']==cp['common_mesher']['sha256'] and cached['owned_z_cells']==p['owned_z_cells']==r['owned_z_cells'];count=sum(len(g['quads']) for g in cached['groups']);assert count==r['owned_quads'];quads+=count;records.append({'index':i,'reused':p['reuse_exact_cache'],'cache':ref(path),'quads':count});del cached;gc.collect()
 assert reused==63==c['r03_caches_reused_by_reference'] and rebuilt==25==c['common_mesher_calls'];assert quads+c['lower_original_quads_kept']==189901==c['quad_count'];assert c['lower_original_quads_clipped_at_join']==0
 final=stream_render(R/'roof_repaired.render.json.gz')
 for g in final['groups']:pass
 for key,path in [('cache_identity_proof',HERE/'cache_identity_proof.json'),('cache_plan',R/'cache_plan.json'),('upper_union',R/'upper_union_arrays.npz')]:assert final['provenance'][key]==ref(path)
 assert final['bounds']==read(OLD/'composition.json')['bounds'] and final['provenance']['previous_roof_render']==ref(OLD/'roof_repaired.render.json.gz')
 report={'schema':'riverstone.roof_repair_r04.actual_cache_usage.v1','status':'PASS','candidate_render':ref(R/'roof_repaired.render.json.gz'),'reused_exact_pinned_r03_caches':reused,'recomputed_changed_material_caches':rebuilt,'upper_cached_quads':quads,'lower_quads':c['lower_original_quads_kept'],'total_quads':c['quad_count'],'all_actual_cache_provenance_matches_plan':True,'published_render_pins_cache_gate_and_union':True,'render_bounds_identical_to_r03':True,'records':records,'sampling_calls':0,'mesher_calls':0,'address_space_limit_mib':256,'cpu_limit_seconds':60,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'validator':ref(Path(__file__))}
 save(HERE/'cache_usage_validation.json',report);print(json.dumps({k:v for k,v in report.items() if k!='records'}))
if __name__=='__main__':main()
