#!/usr/bin/env python3
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(60,)*2)
import datetime,gzip,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent;R=next(p for p in D.parents if (p/'voxel_character/common/core.py').exists())
def read(p):
 with gzip.open(p,'rt') if p.suffix=='.gz' else p.open() as f:return json.load(f)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
a=read(D/'report.json');v=read(D/'validation_r01/validation.json');sp=read(D/'sourcepins.json');assert v['status']=='PASS_EXHAUSTIVE_FULL_ROOF_SIDECAR_TECHNICAL_GATE';assert a['payload']['gzip_sha256']==v['sidecar_sha256']==sha(D/'normal_split_sidecar.json.gz')
pins=sp['inputs']|v['source_pins'];assert all(sha(R/p)==h for p,h in pins.items())
oldseal=read(A/'roof_normal_full_r01/seal_manifest.json');oldseal_ok=all(sha(R/f['path'])==f['sha256'] for f in oldseal['files']);assert oldseal_ok
changes=read(A/'roof_repair_r05/delta_cells.json.gz')['cells'];same=sum(x[3]==x[4] for x in changes);empty=sum(x[6]=='empty' for x in changes);support=sum(x[6]=='original_support' for x in changes);assert (len(changes),same,empty,support)==(18965,149,18775,190)
budget={'schema':'riverstone.roof_normal_full.budget_snapshot.v1','status':'OBSERVED_WITHIN_APPROVED_BUDGET_CONFIGURED_CPU_ENFORCEMENT_UNPROVEN','caps':{'address_space_mib':256,'CPU_seconds_per_process':60,'gzip_bytes':8*1024**2,'raw_bytes':32*1024**2,'partition_total_cells':200000},'author':{k:a[k] for k in ('CPU_seconds','elapsed_seconds','peak_rss_kib')},'independent_validation':{k:v[k] for k in ('CPU_seconds','elapsed_seconds','peak_rss_kib')},'actual':{'gzip_bytes':v['sidecar_gzip_bytes'],'raw_bytes':v['sidecar_decompressed_bytes'],'partition_total_cells':v['totals']['partition_total_cells'],'max_partition_cells':v['totals']['max_original_split_unit_faces'],'final_mesh_quads':v['totals']['final_mesh_quads']},'observed_CPU_seconds_below_60_each':a['CPU_seconds']<60 and v['CPU_seconds']<60,'no_limit_escalation':True,'configured_CPU_seconds_recorded_in_reports':45,'configured_45_second_limit_guaranteed':False,'configured_vs_observed_CPU_mismatch':True,'limit_introspection':read(D/'limit_introspection.json'),'caveat':'The 45-second report field records configured setrlimit values, not proven runtime enforcement. Actual measured CPU exceeded 45 seconds but stayed below the approved 60-second budget. Fresh getrlimit and /proc limits confirm configuration only; original launcher enforcement is not retrospectively established.'}
assert budget['observed_CPU_seconds_below_60_each'];save(D/'budget_snapshot.json',budget)
save(D/'revision_ledger.json',{'status':'NEW_R05_BOUND_PAYLOAD_TECHNICALLY_VALIDATED','frozen_old_r01_seal_all_files_unchanged':oldseal_ok,'frozen_old_r01_payload_sha256':oldseal['payload']['gzip_sha256'],'new_payload':a['payload'],'render_sha256':a['render_sha256'],'original_source_profiles_and_crop_operations_unchanged':True,'only_recorded_delta_applied':True,'applied_delta_cells':len(changes),'same_material_owner_transfers':same,'empty_cells_added':empty,'support_cells_replaced':support,'protected_deferrals':v['R5_applied_ownership_validation']['deferred_by_reason'],'attempts':[{'name':'author_attempt01','result':'Public NPY header API mismatch before payload creation; fixed without classification or limit changes.','log':'author_attempt01.log'},{'name':'validation_attempt01','result':'Full cache JSON read reached address-space cap; replaced only that extra cache read with streaming.','log':'validation_r01/validation_attempt01.log'},{'name':'author_final','result':a['status'],'log':'author.log'},{'name':'validation_final','result':v['status'],'log':'validation_r01/validation.log'}],'production_gate_open':False,'visual_acceptance':False,'sampler_calls':0,'compiler_calls':0,'mesher_calls':0,'GUI_calls':0})
(D/'README.md').write_text('''# Fresh r05-bound full source roof normal sidecar

This separate r02 sidecar binds only to r05 render SHA-256 `22baa95f2afc2bf9f1753eaf256bd172aed9fa9c161a21a0b96626b7c2ab9925`. The frozen r02/r03/r04 geometry, original classifier, and old `roof_normal_full_r01` payload remain unchanged. The entire prior r01 technical seal was rechecked.

## Ownership and source identity

All 354 source profiles (339 measured appearance regions and 15 recovered intervals) reuse the exact original operations and crop cuts. The source profile, height, overlap and thickness are still explicit model priors, not measured photo-derived 3D curvature.

Ownership is reconstructed from frozen r02/r03/r04 caches, then updated using exactly the 18,965 applied r05 delta rows. These comprise 18,775 previously empty cells and 190 support replacements, including 149 same-material owner transfers. The isolated 189,026-row compile is independently checked as evidence, never adopted wholesale as applied ownership. There are 169,726 preserved original tile rows and 335 deferred protected conflicts: 172 r03 original/foreground, 72 r04 material-owner, and 91 other preserved-source conflicts. The 2,609 r04 recolor cells remain non-source owners.

## Exact payload and runtime counts

- Schema: `riverstone.roof.normal_split_sidecar.v1`; grid pitch 0.03125.
- 188,539 original render quads; 47,414 complete normal patches.
- 17,097 split originals replaced by 39,204 subquads, including 21,613 analytic and 17,591 preserved-cardinal pieces.
- `partition_total_cells = 54,944`; maximum 12 per split parent; runtime cap remains 200,000.
- 106,746 analytic treated unit faces; 18,954 preserved unit faces inside splits.
- 26,926 exterior unit faces owned by restored cells, of which 8,686 receive analytic normals.
- Net 22,107 extra quads; final mesh 210,646 quads.
- Raw JSON 27,012,630 bytes; gzip 848,144 bytes.
- Raw SHA-256 `c19eef05844ec156f789a0ff98261fc53d54d8432aabce9cbf9605cdff1b3b61`.
- Gzip SHA-256 `d24193d021f8a03aa435e6a617dd2cc9cf0c19e0493c17a385f51db0308269d1`.

Each split is a complete, disjoint, same-plane lattice partition of its own r05 render quad. Material, outward winding, and cardinal normals for uncertain or unsupported faces are preserved. There is no vertex displacement, but vertex/index representation changes. This claim concerns sidecar application to r05; it does not assert that r05 has the same exterior geometry as r04.

## Independent validation

`validation_r01/validate_full.py` does not import the author. It independently reconstructs source ownership, verifies every isolated source row's accepted/deferred outcome, checks source operation identity, replays every render target and unit-face classification, and validates the actual emitted payload. Every patch/split target, material, cardinal plane, winding, normal and exact partition is checked. All 23 malformed/unsafe fixtures are rejected. Source and payload pins are rechecked at the end.

The old 12-source diagnostic baseline has 3,960 analytic face/source-ID/normal triples. All 3,960 remain exterior and equal in r05; 258 additional analytic triples are reported separately, making 4,218 current triples. This is a retained-surface comparison, not an assertion of full old-geometry equivalence.

## Budgets and gates

Author CPU 54.767 seconds, peak RSS 158,248 KiB; independent validation CPU 48.422 seconds, peak RSS 152,664 KiB. Both observed CPU times remain below the approved 60-second budget; address space is configured at 256 MiB. The author and validation reports record a configured CPU limit of 45 seconds, yet their measured CPU times exceed 45 seconds. These are not 45-second passes, and 45-second enforcement is not claimed. Fresh introspection found both getrlimit and kernel `/proc/self/limits` set to 45 seconds, while the parent bash limits were unlimited. That confirms the new probe's configuration, not enforcement during the already-completed runs. Original launcher enforcement remains unverified; see `limit_introspection.json` and the explicit configured-versus-measured caveat in `budget_snapshot.json`. This operational limit discrepancy does not invalidate the exhaustive face/ownership/classification results. Raw/gzip caps remain 32/8 MiB. No sampler, compiler, mesher, GUI, render rewrite or limit widening was used for this sidecar. Initial API/memory-read failures and their corrective attempts are retained in the revision ledger.

Technical validation passed. The parent owns actual adapter loading, render screenshots, visual review and production acceptance; none is implied here. Production gate remains closed.
''')
(D/'validation_r01/README.md').write_text('''# Independent r05 full-roof sidecar validation

Run `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python validate_full.py` from this directory. The validator reads the fixed sibling payload and pinned r05 render, using the unchanged original SourceTile classifier. It never imports the author or runs sampling/meshing/GUI tools.

`validation.json` contains exhaustive counts, source pins, all 23 rejected negative cases, the exact ownership acceptance/deferral partition, the retained 12-source comparison, actual byte hashes, and measured resources. `validation_attempt01.log` records the initial bounded full-cache-read failure. The final version streams that cache crosscheck and passes without widening memory limits.
''')
vs={'schema':'riverstone.roof_normal_full.independent_validation_seal.v1','status':v['status'],'payload_sha256':v['sidecar_sha256'],'render_sha256':v['render_sha256'],'files':[{ 'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((D/'validation_r01').iterdir()) if p.is_file() and p.name!='seal_manifest.json']}
save(D/'validation_r01/seal_manifest.json',vs)
seal={'schema':'riverstone.roof_normal_full.technical_seal.v1','status':'TECHNICAL_PASS_VISUAL_SEPARATELY_GATED','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'payload':a['payload'],'render_sha256':a['render_sha256'],'source_inputs_unchanged':True,'configured_CPU_limit_enforcement_unproven':True,'observed_CPU_within_approved_60_seconds':True,'frozen_old_r01_seal_all_files_unchanged':True,'partition_total_cells':v['totals']['partition_total_cells'],'final_mesh_quads':v['totals']['final_mesh_quads'],'files':[{'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size}for p in sorted(D.rglob('*'))if p.is_file() and p!=D/'seal_manifest.json'],'production_gate_open':False,'visual_acceptance':False}
save(D/'seal_manifest.json',seal)
assert all(sha(R/f['path'])==f['sha256'] for f in seal['files'])
print(json.dumps({'status':seal['status'],'seal_sha256':sha(D/'seal_manifest.json'),'files_sealed':len(seal['files']),'old_r01_seal_verified_files':len(oldseal['files']),'payload':a['payload'],'partition_total_cells':v['totals']['partition_total_cells'],'final_mesh_quads':v['totals']['final_mesh_quads']}))
