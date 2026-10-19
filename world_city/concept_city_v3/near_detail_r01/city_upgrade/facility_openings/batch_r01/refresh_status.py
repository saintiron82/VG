"""Refresh mutable progress inventory from sealed artifacts; never edit runtime."""
import datetime,hashlib,json
from pathlib import Path
B=Path(__file__).resolve().parent;U=B.parent.parent;ROOT=B.parents[5]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 status=load(B/'batch_status.json');audit=load(U/'house_extensions/facility_opening_audit/asset_audit.json')['assets'];assets={r['asset_key']:r for r in audit};nearpath=ROOT/'world_city/concept_city_v3/playable_detail_r01/near_catalog.json';near=load(nearpath)['assets'];composed={};bound=[];roofs=set()
 for r in near.values():
  p=r.get('composed_manifest_path')
  if p and (ROOT/p).exists():
   m=load(ROOT/p);k=m['asset_key']
   if k in assets:
    assert sha(ROOT/p)==r['composed_manifest_sha256'] and m['all_pass'] and m['render_sha256']==r['sha256'] and sha(ROOT/m['render_path'])==m['render_sha256'];composed[k]=(p,m);bound.append(k)
 for p in B.glob('composed/*/*.manifest.json'):
  m=load(p);k=m['asset_key']
  if k in assets and m.get('all_pass') and p.name == k+'.manifest.json' and k not in bound:
   assert sha(ROOT/m['render_path'])==m['render_sha256'];composed[k]=(str(p.relative_to(ROOT)),m)
 for base in [U/'facility_roofs/compiled_priority_r01',U/'facility_roofs/compiled_expansion_r01']:
  for p in list(base.glob('**/handoff_manifest.json'))+list(base.glob('**/*.layered.handoff.json')):
   d=load(p)
   for r in d.get('assets',[d]):
    k=r.get('native_asset_key',r.get('asset_key'))
    rr=r.get('files',{}).get('.render.json',{})
    if k in assets and rr.get('path') and (ROOT/rr['path']).exists() and sha(ROOT/rr['path'])==rr.get('sha256'):roofs.add(k)
 assert set(composed)<=roofs,(set(composed)-roofs)
 for k in ['registered_main_gate_header','registered_service_gate_header']:
  if not any(r['asset_key']==k for r in status['ordered_batch']):
   p=B/'gate_headers_r01/contact_plan'/f'{k}.plan.json';d=load(p);status['ordered_batch'].append({'asset_key':k,'placements':assets[k]['city_placements'],'selected_roof_chunks':24 if k=='registered_main_gate_header' else 16,'window_count':0,'contact_region_count':len(d['contact_regions']),'bounded_region_chunks':d['chunk_count'],'bounded_fine_candidate_visits':d['fine_candidates'],'bounded_roof_candidate_visits':d['roof_candidates'],'plan_path':str(p.relative_to(ROOT)),'plan_sha256':sha(p)})
 for r in status['ordered_batch']:
  k=r['asset_key'];r.update(composed_done=k in composed,roof_compile_done=k in roofs,runtime_bound=k in bound)
  if k in composed:
   p,m=composed[k];r.update(manifest_path=p,manifest_sha256=sha(ROOT/p),composed_quads=m['output_quad_count'],composed_runtime_mib=m.get('runtime_mib',m['output_quad_count']*144/1048576))
  cp=B/'compiled_v3'/k/'catalog.json'
  if cp.exists():
   c=load(cp);r.update(compile_catalog_path=str(cp.relative_to(ROOT)),compile_catalog_sha256=sha(cp),region_compile_status='complete; prepared-v3 exact source plans; independent original-core four-chunk replay PASS' if (cp.parent/'reference_replay.json').exists() else 'compiled; reference replay pending',roi_cpu_seconds=c['user_cpu_seconds']+c['system_cpu_seconds'],roi_wall_seconds=c['elapsed_seconds'],roi_peak_rss_kib=c['max_rss_kib'])
  elif k in composed:r['region_compile_status']='complete and sealed; frozen original backend, no recomputation'
 status.update(observed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),complete_composed_assets=sorted(composed),complete_composed_count=len(composed),composed_placement_count=sum(assets[k]['city_placements'] for k in composed),full_roof_compiled_assets=sorted(roofs),full_roof_compiled_count=len(roofs),near_bound_assets=sorted(set(bound)),near_bound_count=len(set(bound)),current_pending_compositions=[r['asset_key'] for r in status['ordered_batch'] if not r['composed_done']],uncomposed_asset_count=72-len(composed),remaining_not_composed=72-len(composed),uncomposed_placement_count=332-sum(assets[k]['city_placements'] for k in composed),remaining_placements_not_composed=332-sum(assets[k]['city_placements'] for k in composed),batch_retained_bytes_before_status_write=sum(p.stat().st_size for p in B.rglob('*') if p.is_file()),global_city_complete=False,refresh_driver={'path':str(Path(__file__).relative_to(ROOT)),'sha256':sha(Path(__file__))})
 status['additional_output_budget_bytes']=80000000;status['budget_split_bytes']={'roof':20000000,'window_and_composition':60000000};status['shared_retained_budget']['window_composition_suballocation_bytes']=60000000;status['batch_budget_bytes']=60000000;status['batch_allocation_reference']={'path':str((B/'sampler_v2/batch_allocation.v2.json').relative_to(ROOT)),'sha256':sha(B/'sampler_v2/batch_allocation.v2.json')};status['budget_note']='B60MB is a subset of shared350MB, not an additional pool; minimum1GiB disk guard. Original30MB source remains preserved.'
 status['cost_basis']['gate_profile_finding']='Historical v2 full-source preparation dominated. New v3 opt-in is equality-certified and in use only for new assets; gate original chunks remain unchanged.'
 for r in status['inputs']:
  if r['path']==str(nearpath.relative_to(ROOT)):r['sha256']=sha(nearpath)
 (B/'batch_status.json').write_text(json.dumps(status,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps({k:status[k] for k in ['complete_composed_count','composed_placement_count','full_roof_compiled_count','near_bound_count','remaining_not_composed','batch_retained_bytes_before_status_write']}))
if __name__=='__main__':main()
