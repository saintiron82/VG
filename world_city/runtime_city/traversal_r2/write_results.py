#!/usr/bin/env python3
"""Write comparison/report from preserved, separately audited physics evidence."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent;E=H/'evidence'
def read(p):return json.loads(p.read_text())
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
variants={n:read(E/(n+'_results.json')) for n in ['fine','fine_candidate','proxy','integrated_actual','integrated_proxy']}
p=read(H/'prepared.integrated_proxy.json');actual={v['id']:v for v in variants['integrated_actual']['routes']};prox={v['id']:v for v in variants['integrated_proxy']['routes']}
exceptions=p['secondary_entrance_exceptions'];doors=[]
for b in exceptions:
 for index,entry in enumerate(b['all_entrance_contracts']):
  if abs(entry.get('floor_minus_ground_m',0))>.1:
   doors.append({'building_id':b['id'],'entrance_index':index,**entry})
exception_report={'status':'unresolved_source_exceptions_not_traversal_verified','building_count':len(exceptions),'door_count_above_0p1m':len(doors),'maximum_absolute_door_ground_delta_m':max(abs(x['floor_minus_ground_m']) for x in doors),'source':p['sources']['topography'],'doors':doors,'building_contracts':exceptions}
write(E/'secondary_door_exceptions.json',exception_report)
comparison={'schema':'riverstone.city.r2.traversal_comparison.v1','design_status':'technical height/collision candidate; not final terrain design approval',
 'source_hashes':p['sources'],'controller':p['assumptions'],'proxy_summary':p['proxy_validation'],
 'variants':{name:{'status':r['status'],'summary':r['summary'],'report':str((E/(name+'_results.json')).relative_to(H))} for name,r in variants.items()},
 'paired_routes':[{'id':id,'actual_voxel_status':a['status'],'actual_voxel_pass':a['pass'],'actual_floor_miss_frames':a['not_on_floor_frames'],'actual_ray_miss_frames':a['ground_ray_miss_frames'],
 'proxy_status':prox[id]['status'],'proxy_pass':prox[id]['pass'],'proxy_floor_miss_frames':prox[id]['not_on_floor_frames'],'proxy_ray_miss_frames':prox[id]['ground_ray_miss_frames']} for id,a in actual.items()],
 'secondary_door_exception_buildings':len(exceptions),'secondary_door_exception_count':len(doors),
 'A01_note':'Baseline label means preserved street XZ. The new hill reaches1.09547924m within A01 even though segment endpoints areY0; A04/L13/bridge are flat baselines.',
 'limitations':['Only24fixed integrated routes; no whole-city arbitrary-path guarantee.','Not productioncontroller,navmesh,NPCs,carts,interiors,door thresholds or wallwalk certification.',
 'Building collision uses conservative envelopes, with only existing explicit openings removed.','Entry routes end0.8m outside conservative shell; recessed cathedral doorway is not entered.',
 '45secondary-door building exceptions remain unresolved and untested.','Full finite proxy is an optional separate collision layer; common voxel visual geometry and actual authored stairs unchanged.']}
write(E/'comparison.json',comparison)
rows=['| Route | Actual voxel result | Source-grade proxy |','| --- | --- | --- |']
for id,a in actual.items():
 state=('PASS' if a['pass'] else 'FAIL')+': '+a['status']
 if a['not_on_floor_frames'] or a['ground_ray_miss_frames']:state+=f" (floor {a['not_on_floor_frames']}, ray {a['ground_ray_miss_frames']})"
 rows.append(f"| {id} | {state} | PASS: {prox[id]['status']} |")
text=f'''# r2 actual capsule evidence and finite source-grade collision candidate

## Result

The integrated optional source-grade proxy passed **24/24 fixed cases**: 21 positive routes and three expected-failure controls. The original generic no-step capsule walked **1,481.53 m over 22,253 physics ticks**, with **zero is_on_floor misses, zero ground-ray misses, and zero obstacle contacts** on the positive routes. Maximum centerline error was 0.03982 m.

The same integrated routes against actual stepped common-voxel terrain passed **12/24 strict cases**. Uphill voxel risers blocked the capsule; medium downhill routes reached their endpoints with real floor/ray loss. The failures are preserved, not rerouted or replaced. Mathematical grade alone did not establish capsule traversal.

All five evidence sets passed their provenance/completeness audits. This is a technical height/collision candidate, **not final terrain design approval** and not a production-controller or whole-city guarantee.

## Controlled comparison

- Fine actual-voxel, original no-step capsule: 1/7 strict passes, 4/7 endpoint completions. No ray misses, but three uphill blockers and 32 floor-state misses.
- Fine separate step candidate: 7/7 endpoints with nearby support plus 2/2 safety controls. Maximum step 0.15 m; 67 successful swept steps. 35 is_on_floor misses remain explicitly recorded as nearby-support misses, not continuous physical contact. A real 0.25 m riser and low ceiling both blocked with zero successful steps.
- Fine exact source-grade proxy, original no-step capsule: 7/7 strict route passes plus 4/4 controls. Zero floor/ray loss and no contacts. The finite 1024 m² cap uses two triangles; independently measured against all 102,400 actual fine visual cell centers, maximum difference 0.04999854 m. Outside bounds and river have no floor; actual solid wall and 0.25 m step stay solid.
- Integrated actual-voxel baseline: 12/24 strict cases.
- Integrated finite source-grade proxy: 24/24 strict cases.

## Finite owned-ground proxy contract

The optional full layer has 611 source-owned finite tiles and 7,112 triangles. It covers 578,802 m² after subtracting all 326 realized building body footprints, removing 46,862 m² of body voids. Exact polygon checks found zero triangle/body-void intersection. Maximum triangle-center deviation from authored H is 2.84e-14 m. None of the graded source tiles intersects the original river mask, so river support was not added.

This collision adapter changes no voxel cells, visual triangles, source XZ layout or common visual mesher. Actual foundations, retaining strips with authored door apertures, wall foundations, structures, bridges and explicit stair/obstacle controls stay separate actual collision. The proxy is not installed as a production controller or navmesh. Wider use still requires source-ground ownership and void contracts to remain true.

## Integrated routes

“Floor” counts is_on_floor misses; “ray” counts missing support within the ordinary capsule ray range. Negative cases pass only when the expected failure is observed, and wall/step cases must report the intended collider.

{chr(10).join(rows)}

A01 retains its original street XZ but is not flat after this height candidate: exact source H reaches 1.09547924 m inside its first segment although its endpoints are Y=0. Its failure in the actual-voxel run is a new 0.5 m riser followed by deflection into a conservative building shell. The proxy follows the same unchanged path without contact. A04, L13 and the bridge remain flat baselines.

## Unresolved entry exceptions and scope

- {len(exceptions)} buildings have {len(doors)} authored secondary doors differing from source terrain by more than 0.1 m; maximum absolute difference is {exception_report['maximum_absolute_door_ground_delta_m']:.6f} m. These are retained in evidence/secondary_door_exceptions.json and are **not** certified by the two sampled landmark approaches.
- Castle and cathedral entry cases stop 0.8 m outside their conservative collision envelope. Recessed doors, thresholds, interiors and all other entry approaches remain untested.
- Generic capsule: radius 0.30 m, total height 1.80 m, speed 4 m/s, 60 Hz GodotPhysics3D, 45° floor angle, 0.2 m floor snap, 0.001 m safe margin. Building collisions are conservative envelopes minus only existing authored openings.
- There is no infinite floor, within-route teleport, route change after a failure, invisible support ramp, navigation or NPC guarantee.

## Exact evidence and reproduction

- Integrated scene SHA256: {p['sources']['scene']['sha256']}
- Optional full proxy manifest SHA256: {p['sources']['city_proxy']['sha256']}
- prepared.integrated_actual.json / evidence/integrated_actual_results.json / evidence/integrated_actual_audit.json
- prepared.integrated_proxy.json / evidence/integrated_proxy_results.json / evidence/integrated_proxy_audit.json
- proxy_city/layer_manifest.json and its 611 individually hash-bound finite tile resources
- evidence/comparison.json and evidence/secondary_door_exceptions.json
- Original fine failures, step candidate and fine proxy remain separately named under evidence/.

Run prepare_integrated.py with --scene world_city/runtime_city/generated/r2/scene.graded_property.json. Use --proxy for the separate proxy prepared file, then run.sh or run_city_proxy.sh with explicit absolute --prepared and --report paths. Preserve prior report filenames. Audit actual results with audit_report.py and proxy results with audit_city_proxy.py. Nine lightweight harness unit tests pass.

The early preflight logs retain a rejected stale source-plan reference and a corrected relative-path/prepared-file setup error. Those were harness preflight failures, not physics successes; no engine result was inferred from them.
'''
(H/'RESULTS.md').write_text(text)
print(json.dumps({'comparison':'evidence/comparison.json','report':'RESULTS.md','secondary_exception_buildings':len(exceptions),'secondary_exception_doors':len(doors),'maximum_door_ground_delta_m':exception_report['maximum_absolute_door_ground_delta_m']},indent=2))
