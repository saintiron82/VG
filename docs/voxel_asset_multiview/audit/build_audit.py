"""Read-only, bounded evidence snapshot; does not regenerate existing assets."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHAR = 'voxel_character/'
LILY = CHAR+'lily_city/revisions/original_lily_r01/'


def file_record(path, role):
    p=REPO/path
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return {'path':path,'role':role,'sha256':h.hexdigest(),'bytes':p.stat().st_size}


def master_evidence(path):
    p=REPO/path
    opener=gzip.open if p.suffix=='.gz' else open
    with opener(p,'rt') as stream:data=json.load(stream)
    operations=data.get('operations',[])+[op for c in data.get('components',[]) for op in c.get('operations',[])]
    counts=Counter(op.get('shape',{}).get('kind','unknown') for op in operations)
    depths=[]
    for op in operations:
        shape=op.get('shape',{})
        if shape.get('kind')=='box':depths.append(shape['max'][2]-shape['min'][2])
        elif shape.get('kind')=='extrusion':depths.append(shape['z_max']-shape['z_min'])
    return {'schema':data.get('schema'),'operations':len(operations),'shape_kinds':dict(sorted(counts.items())),
            'instances':len(data.get('instances',[])), 'explicit_positive_z_box_or_extrusion_count':sum(d>0 for d in depths),
            'local_shape_depth_range_m':[min(depths),max(depths)] if depths else None,
            'limits':'Local primitive ranges are existence evidence only, not assembled bounds, thickness quality or visual approval.'}


def row(identifier, classification, geometry, origins, technical, visual, missing, evidence, master=None):
    value={'id':identifier,'classification':classification,'geometry_finding':geometry,
      'reference_origins':origins,'recorded_technical_status':technical,'visual_status':visual,
      'new_process_gaps_or_next_review':missing,'evidence':[file_record(p,r) for p,r in evidence],
      'multiview_contract_pass':'NOT_EVALUATED_NO_NATIVE_V1_CONTRACT',
      'coverage_pass':False,'asset_complete':False}
    if master:value['inspected_source_geometry']=master_evidence(master)
    return value


def build():
    rows=[]
    rows.append(row('ordinary_buildings_and_landmark_representative','parametric_3d',
      'Dimensioned walls, real sloped roofs, openings and component transforms form 3D common masters. Existing buildings are not universally image planes.',
      ['dimension_and_construction_rules'],
      'R2 README records bounded common compilation at 0.5/0.25 m and 499-master grammar/envelope preflight; no new compile performed by this audit.',
      'Existing bounded structural checks do not certify whole-city visual acceptance.',
      ['Retain dimension-driven construction for regular building parts. Complex sculpture/organic ornaments need their own classification.',
       'Current audit samples sources and cathedral master; not an exhaustive per-building coverage review.'],
      [('world_city/runtime_city/archetypes/ordinary_r2.py','dimensioned 3D authoring'),
       ('world_city/runtime_city/archetypes/README_R2.md','documented scope and bounded tests'),
       ('world_city/concept_city_v3/assemblies/landmarks/author.py','landmark assembly author'),
       ('world_city/concept_city_v3/assemblies/landmarks/masters/cathedral.json','actual continuous 3D master')],
      'world_city/concept_city_v3/assemblies/landmarks/masters/cathedral.json'))
    rows.append(row('shared_standard_surface_parts','dimension_generated_standard_component',
      'Small shared stone/plank/paving masters contain real occupied cells, shallow joints and bevels. Their intended surface depth is not a character-depth failure.',
      ['explicit_dimensions','muted_semantic_material_rules'],
      'Small JSON rules lower to common compile/render; safe visual offset contract and edge trim occupancy evidence are separate.',
      'Dimension checks and material evidence do not approve an entire city scene.',
      ['Keep dimension-first generation; do not invent AI turnaround references for bricks.'],
      [('world_city/concept_city_v3/near_detail_r01/city_upgrade/surface_modules/author_surfaces.py','shared author adapter'),
       ('world_city/concept_city_v3/near_detail_r01/city_upgrade/surface_modules/inputs/safe_offset_rules.v1.json','safe dimensional rules'),
       ('world_city/concept_city_v3/near_detail_r01/city_upgrade/surface_modules/generated_safe/manifest.json','compiled/render provenance')]))
    rows.append(row('first_image_characters_r05','manual_3d_approximation',
      'Actual authored 3D cloth sweeps, hair geometry and common occupancy exist; this is a manual interpretation of a single illustration, not faithful original multi-view reconstruction.',
      ['observed_user_front_illustration','manual_unobserved_side_back_and_depth'],
      'STATUS records common recompile, common renderer, GLB roundtrip and eight GUI comparison views.',
      'visual_review_r05 explicitly art_acceptance=false; pose, face, hair and lining differences remain.',
      ['Obtain/declare three-view design references; preserve observed versus inferred distinction.',
       'Inspect section/curve body, hair and clothing volumes in matched front/side/back frames before next delivery compile.'],
      [(CHAR+'image_characters_r01/STATUS.json','revision scope'),
       (CHAR+'image_characters_r01/evidence/visual_review_r05.json','actual prior visual review, acceptance false'),
       (CHAR+'image_characters_r01/evidence/shape_audit_violet_r05.json','structural audit not art score'),
       (CHAR+'image_characters_r01/generated/violet_bride_r05/master.json','actual 3D common master'),
       (CHAR+'image_characters_r01/reference/1000041593.webp','observed original violet illustration'),
       (CHAR+'image_characters_r01/reference/1000041592.webp','observed original cyan illustration')],
      CHAR+'image_characters_r01/generated/violet_bride_r05/master.json'))
    rows.append(row('image_measured_r01','shallow_2_5d_actual_xyz_volume',
      'Front mask/RGB/eye measurements drive actual XYZ occupancy; side/back thickness and colours are manual priors. A front-conditioned shallow volume is not literally a textured billboard.',
      ['observed_user_front_pixels','manual_ROI_and_semantics','manual_depth_back_colour_priors'],
      'README records common layered recompilation and actual CPU common-quad views; headless Godot mesh check is not a GUI art review.',
      'Side/three-quarter volumes, steps and gaps remain; not a finished rotatable character.',
      ['Replace independent front slabs with coherent section/curve volumes informed by three explicitly labelled reference views.',
       'Front projection similarity cannot certify unseen depth or back.'],
      [(CHAR+'image_measured_r01/README_KO.md','process and limits'),
       (CHAR+'image_measured_r01/data/volume_rules.json','manual depth priors'),
       (CHAR+'image_measured_r01/generated/violet/master.json','actual common master'),
       (CHAR+'image_measured_r01/generated/violet/side.png','actual model side evidence'),
       (CHAR+'image_measured_r01/generated/violet/rear.png','actual model back evidence'),
       (CHAR+'image_measured_r01/evidence/verification.json','technical checks')],
      CHAR+'image_measured_r01/generated/violet/master.json'))
    rows.append(row('image_measured_r02','front_constrained_continuous_2_5d_attempt',
      'Actual continuous-section attempt and common occupancy exist, but manual inferred depth still creates a shallow skirt/background-like mass and an overextended head cap.',
      ['same_observed_front_as_r01','manual_centrelines','measured_widths_and_occlusion_priors','inferred_depth_back'],
      'Preserved halted attempt; README records 69,507 cells/14,741 quads and 3/3 common recompile. Global 98.80% largest component is not visual success.',
      'Side skirt and head/neck cap defects explicitly remain; back is unverified inference; no r02 GUI review claim.',
      ['Keep failed evidence sealed rather than relabel a continuity ratio as quality PASS.',
       'Assess body, hair and garment parts separately; a skirt can connect unrelated masses and inflate a global continuity ratio.'],
      [(CHAR+'image_measured_r02/README_KO.md','stopped revision and visible known defects'),
       (CHAR+'image_measured_r02/data/continuous_rules.json','manual centre/depth/section rules'),
       (CHAR+'image_measured_r02/generated/violet/master.json','actual continuous/common master'),
       (CHAR+'image_measured_r02/generated/violet/side.png','actual model side evidence'),
       (CHAR+'image_measured_r02/evidence/continuity.json','global and per-part diagnostics'),
       (CHAR+'image_measured_r02/sealed_manifest.json','preserved failed attempt hashes')],
      CHAR+'image_measured_r02/generated/violet/master.json'))
    rows.append(row('new_reference_turnaround_r01','ai_generated_three_view_design_inference',
      'AI front/right-side/back reference sheets are design input, not 3D assets and not newly observed original side/back views.',
      ['observed_user_original_front_illustration','AI_generated_front_side_back_interpretation'],
      'Prompt/provenance hashes and per-view measurement files exist. Cyan profile turns toward camera; sheet pose and clothing consistency conflicts are recorded.',
      'Generated reference sheet quality does not prove any model view; alignment/landmark conflicts need explicit resolution.',
      ['Keep source and generated image hashes linked and label all unobserved surfaces.',
       'Calibrate shared ground baseline, physical scale, right-profile orientation and view conflicts before accepting aligned reference input.'],
      [(CHAR+'reference_turnarounds_r01/provenance.json','AI provenance and limitations'),
       (CHAR+'reference_turnarounds_r01/prompts.json','generation request with unseen-view disclosure'),
       (CHAR+'reference_turnarounds_r01/violet_turnaround.png','AI generated violet reference sheet'),
       (CHAR+'reference_turnarounds_r01/cyan_turnaround.png','AI generated cyan reference sheet'),
       (CHAR+'image_turnaround_r01/measurements/violet/measurements.json','measured AI sheet and alignment conflicts'),
       (CHAR+'image_turnaround_r01/measurements/cyan/measurements.json','measured AI sheet and alignment conflicts')]))
    rows.append(row('image_turnaround_r01_curved03_snapshot','section_curve_3d_design_in_progress_from_inferred_views',
      'The active new workflow already has a curved common-compatible source master and genuine continuous-volume CPU front/side/back/three-quarter renders. This snapshot is curved03 only.',
      ['AI_inferred_three_view_reference','measured_sheet_landmarks','authored_curve_and_section_interpretation'],
      'Pinned design_manifest says curved design master, voxel compilation pending; 7,793 operations/28,440 preview quads. Later work is outside this immutable snapshot.',
      'No final compiled-character/visual acceptance is inferred from continuous preview existence.',
      ['Inspect matched multiview source-volume renders, record source review, then common compile and inspect actual compiled model views.',
       'Re-audit newer revision separately; never treat this snapshot as the live latest state.'],
      [(CHAR+'image_turnaround_r01/generated/violet_curved03/master.json.gz','fixed curved03 source master'),
       (CHAR+'image_turnaround_r01/generated/violet_curved03/design_manifest.json','fixed source stage status'),
       (CHAR+'image_turnaround_r01/generated/violet_curved03/section_measurements.json','section measurements'),
       (CHAR+'image_turnaround_r01/generated/violet_curved03/continuous_render_provenance.json','actual continuous render source/cameras/hashes'),
       (CHAR+'image_turnaround_r01/generated/violet_curved03/continuous_front.png','actual source-volume front'),
       (CHAR+'image_turnaround_r01/generated/violet_curved03/continuous_side.png','actual source-volume side'),
       (CHAR+'image_turnaround_r01/generated/violet_curved03/continuous_rear.png','actual source-volume back')],
      CHAR+'image_turnaround_r01/generated/violet_curved03/master.json.gz'))
    c04=CHAR+'image_turnaround_r01/generated/violet_curved04/'
    rows.append(row('image_turnaround_r01_curved04_snapshot','section_curve_3d_common_compile_present_visual_pending',
      'Later fixed curved04 contains actual common compiled cells and front/side/back voxel render images, in addition to continuous source-volume previews.',
      ['AI_inferred_three_view_reference','measured_sheet_constraints','authored_section_curve_interpretation'],
      'solid_validation records 17,716 cells, 15,566 quads, head/anatomy each one connected component and no enclosed cavities; compile_manifest binds common core SHA 2a64ed2c.',
      'solid_validation explicitly visual_approval=false. Three-view projection IoU constrains AI-sheet alignment, not original likeness or unseen-rear correctness.',
      ['Keep numerical structural/projection diagnostics separate from visual approval.',
       'The new contract is not retroactively asserted PASS: its calibrated-reference, explicit precompile review and evidence adapters remain to be authored.',
       'Later curved05 work is outside this pinned snapshot.'],
      [(c04+'master.json.gz','fixed curved04 authored master'),(c04+'compiled.cells.json.gz','actual native common occupancy'),
       (c04+'character.render.json','actual common occupancy surface'),(c04+'compile_manifest.json','master/compiler/payload/render binding'),
       (c04+'solid_validation.json','structural diagnostics, visual approval false'),
       (c04+'three_view_projection_metrics.json','AI-sheet constraint metrics, not likeness approval'),
       (c04+'voxel_render_provenance.json','actual compiled model view cameras and source hashes'),
       (c04+'voxel_front.png','actual compiled front'),(c04+'voxel_side.png','actual compiled side'),
       (c04+'voxel_rear.png','actual compiled back')],c04+'master.json.gz'))
    rows.append(row('original_lily_r03','existing_authored_3d_needs_new_multiview_process_review',
      'Lily has real common-master geometry, rigged render data and prior GUI views; side/back and full lower legs are explicitly new interpretations of a cropped front portrait.',
      ['observed_cropped_front_portrait','manual_side_back_legs','preserved_medieval_r5_costume'],
      'STATUS records 74 Lily and 210 resident runtime checks, 33 sampled gait phases, prior image review; not continuous collision certification.',
      'Existing visual_review_final records findings, but STATUS art_acceptance remains pending user review.',
      ['Do not erase existing real-3D/GUI evidence, and do not treat it as satisfaction of the newly requested three-reference/section-curve process.',
       'Review body depth, hairstyle volume, identity and costume clearance from aligned front/side/back views.'],
      [(LILY+'STATUS.json','existing technical and user-art status'),(LILY+'data/reference.json','front source and inferred unseen geometry'),
       (LILY+'generated/lily_r03/derived.master.json','actual common master'),
       (LILY+'evidence/visual_review_final.json','prior actual image findings and limits')],LILY+'generated/lily_r03/derived.master.json'))
    rows.append(row('resident_body_modules','authored_extrusion_and_box_3d_needs_volume_review',
      'adult_base explicitly authors pelvis, torso, limbs, fingers and feet as finite-depth extrusions/boxes. This is genuine 3D source but does not by itself establish rounded anatomical quality.',
      ['manual_parametric_body_proportions','shared_style_family','not_observed_multiangle_anatomy'],
      'Combination review index references ten resident appearance caches; previous source/runtime tests are documented in parent STATUS.',
      'New multiview anatomical/body-section review remains required; no numeric ratio can approve likeness or silhouette.',
      ['Review shoulder/hip/chest and limb cross-sections, head-neck joining, front/side/back proportions and child-specific nonuniform proportions.',
       'Separate body structural review from costume shell clearance.'],
      [(LILY+'data/modules/adult_base.json','finite-depth anatomical source primitives'),
       (LILY+'data/resident_review_index.json','resident appearance combinations and review scope'),
       (LILY+'data/combination_rules.json','body/face/hair/costume assembly rules'),
       (LILY+'STATUS.json','recorded bounded runtime evidence')],LILY+'data/modules/adult_base.json'))
    rows.append(row('clothing_library','authored_thin_3d_shells_needs_curved_multiview_and_motion_review',
      'Clothing is separate source geometry: front/rear leaves, side returns, thin pelvic shells and open split skirts, not body replacement or a solid leg-filling block.',
      ['manual_garment_pattern_geometry','new_unobserved_rear_seams_panels_ties'],
      'SOURCE_QA records 36 modules, 10 outfits, 843 operations, 17 source tests. Its own not_run list excludes shared-cache compile/final fitting/animated sweep.',
      'Parent revision has later selected contact/gait/image evidence. These scopes differ and neither grants automatic latest-process approval.',
      ['Retain garment volume/thickness and leg interior negative-space checks; add section/curve drape review and matched three-view evidence.',
       'Static intersection thresholds and sampled gait checks are not continuous collision-free certification.'],
      [(LILY+'clothing_library/README.md','source geometry contract and explicit scope'),
       (LILY+'clothing_library/SOURCE_QA.json','source-only QA and not-run list'),
       (LILY+'clothing_library/generate_clothing.py','dimensioned garment author'),
       (LILY+'clothing_library/validation_rules.json','source constraints'),
       (LILY+'evidence/visual_review_final.json','later parent fitting/image findings')]))
    return {'schema':'riverstone.asset.multiview_evidence_audit.v1','created_utc':datetime.now(timezone.utc).isoformat(),
      'scope':'Representative source families and pinned revision evidence only; no exhaustive city/character coverage claim.',
      'new_rendering_or_regeneration':False,'direct_new_visual_inspection':False,
      'visual_findings_source':'Existing authored review records; this read-only audit did not independently rejudge image quality.',
      'all_assets_are_billboards':False,'coverage_pass':False,'asset_complete':False,'entries':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check',type=Path)
    args=parser.parse_args()
    if args.check:
        data=json.loads(args.check.read_text());errors=[];count=0
        for entry in data['entries']:
            for artifact in entry['evidence']:
                count+=1
                actual=file_record(artifact['path'],artifact['role'])
                if actual['sha256']!=artifact['sha256']:errors.append(artifact['path'])
        print(json.dumps({'evidence_hashes_checked':count,'changed_sources':errors,'snapshot_integrity_pass':not errors,
                          'coverage_pass':False},ensure_ascii=False))
        return int(bool(errors))
    data=build()
    text=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x') as stream:stream.write(text)
    else:print(text,end='')
    return 0

if __name__=='__main__':raise SystemExit(main())
