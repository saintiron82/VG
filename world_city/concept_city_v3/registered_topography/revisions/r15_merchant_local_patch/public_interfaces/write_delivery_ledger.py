import json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
C=json.loads((H.parent/'source_contract.json').read_text());M=json.loads((H/'accepted_subset_manifest.json').read_text());E=json.loads((H/'all19_frozen_endpoint_proof.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
for n,g in enumerate(C['gate_profiles']):
 if n in M['accepted_profile_indices']:continue
 candidates=[]
 for prefix in('retaining_bound','retaining_grid','buffer_grid'):
  p=H/f'{prefix}_interface_{n:02d}.json'
  if p.exists():
   r=json.loads(p.read_text());candidates.append(dict(path=p.name,sha256=sha(p),status=r['status'],fixed_conflict_count=len(r.get('fixed_conflicts',[])),fixed_grade_infeasibility_count=len(r.get('fixed_edge_grade_infeasibilities',[])),unbound_boundary_count=len(r.get('unbound_boundary_segments',[])),conflict_examples=r.get('fixed_conflicts',[])[:2],fixed_grade_examples=r.get('fixed_edge_grade_infeasibilities',[])[:2],solver_message=r.get('solver_message'),actual_max_gradient=r.get('proof',{}).get('maximum_actual_clipped_triangle_grade')))
 if n in(4,14):reason='Gate independently passed, but parent whole-property restoration proof increases retained backland steps. Entire property remains inactive.'
 elif any(v['status']=='FINITE_PROFILE_SOLVED_PENDING_PARENT_MASK_ACCEPTANCE' for v in candidates):reason='A wider alternate finite field solved mathematically, but its changed masks, complete independent audit, and parent restoration acceptance are not sealed. It is not part of the seven-property subset.'
 else:reason='The tested envelopes retain a genuine protected/public fixed-height conflict, a fixed-segment grade lower bound above12%, or an infeasible joint LP. No seam averaging, public vertical step, or grade waiver is permitted.'
 rows.append(dict(index=n,property_id=g['property_id'],gate_id=g['id'],accepted=False,active=False,reason=reason,original_native_and_door_owner_policy='Retain every original owner and instance for this inactive property.',source_endpoint_proof_index=n,maximum_nine_anchor_vs_actual_frozen_terminal_error_m=E['reports'][n]['maximum_nine_anchor_vs_actual_triangle_error_m'],candidate_evidence=candidates))
out=dict(schema='riverstone.r15_inactive_public_interface_ledger.v1',accepted_subset_manifest_sha256=sha(H/'accepted_subset_manifest.json'),inactive_count=len(rows),records=rows,policy='This ledger never promotes a wider candidate. Only the seven indices in accepted_subset_manifest.json may be consumed.')
(H/'inactive_interface_ledger.json').write_text(json.dumps(out,indent=2)+'\n')
readme='''# R15 finite public interfaces: seven-property accepted subset

The integration authority is `accepted_subset_manifest.json` (SHA256 %s).
It contains exactly indices 03, 11, 12, 13, 15, 16, 18. All other twelve properties remain inactive and retain their original native/door owners. Profiles04 and14 pass the gate-only audit but are held by the parent restoration proof.

## Consume these files
- `accepted_public_profiles.json`: seven complete triangle fields, per-field convex masks, full boundary records, exact source-triangle references, and independent audits.
- `accepted_masks.json`: the446 convex replacement masks, tagged by exact property and gate IDs.
- `accepted_boundary_knots.json`: all266 boundary segments plus109 explicit two-sided, nonwalkable retaining edges. Restoration-side XYZ must be shared exactly with the parent restoration mesh.
- `accepted_interface_03.json`, `_11`, `_12`, `_13`, `_15`, `_16`, `_18`: standalone equivalents.

## Checked results
The seven fields contain1,604 actual final triangles. Their measured Euclidean gradient is at most0.1200000000000004 (12%% plus floating-point roundoff), fixed public/door seam error at most4.44e-16 m, full-width gate coverage error at most1.85e-13 m², positive triangle overlap0, and protected-owner overlap0. Every inner gate edge remains at its exact property datum and full3.5 m width. None of the declared retaining edges lies inside a gate or reserved public/door walking ribbon. Exact cut/fill against the removed frozen faces is0.0501484107954423 m³ cut and0.7094493136704162 m³ fill.

`solved_profiles_audit.json` retains the nine gate-only passes, including the two later held properties. The seven-property manifest is the final inclusion authority, not that nine-row audit.

`all19_frozen_endpoint_proof.json` binds all19 source terminal edges to actual R5 triangle IDs, original XYZ, and exact affine heights. No terminal length is uncovered. Actual frozen discrepancies can exceed the earlier analytic screen; the largest nine-anchor terminal difference is0.3616403352451667 m.

`inactive_interface_ledger.json` records all twelve inactive properties, exact failures, and any unaccepted alternate candidates. `superseded_nine_*` files are historical evidence only. Wider `grid_*`, `retaining_grid_*`, and `buffer_grid_*` candidates are not promoted.

## Preserved guards
The old48.3%% skinny-triangle failure remains a regression concern: acceptance uses every actual clipped triangle, not an analytic grade estimate. Shared knots are distance-welded; incompatible retained traffic/door heights are never averaged to obtain acceptance. Retired owners do not constrain the new field. Outside walking ribbons, explicitly approved inherited backland differences retain both exact sides through finite vertical retaining records.

The original R5 scene and R14 files remain unchanged. No house origin was lifted, no native voxel compile was invoked, no whole-city export was made, and no scene was activated. Parent integration, restoration, support, and subsequent traversal review remain separate.
'''%sha(H/'accepted_subset_manifest.json')
(H/'README.md').write_text(readme)
print('inactive',len(rows),'manifest',sha(H/'accepted_subset_manifest.json'))
