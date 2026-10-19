"""Exact native-coordinate composition of a roof-only finish and opening source."""
from collections import defaultdict
import copy,json
from pathlib import Path
import author as a
import estimate_run as budget
HERE=a.HERE;OUT=HERE/'composed'
ROOF=a.ROOT/'world_city/concept_city_v3/near_detail_r01/city_upgrade/facility_roofs/finished/registered_cathedral_nave_aisles_transept.finished.master.json.gz'
ROOF_SHA='806392e7bc2feac7a6389a60eae2fa5840f46ef4acc9b292b090e6b9dce96c32'
KEY='registered_cathedral_nave_aisles_transept'

def retained_groups(render,contract):
    lookup={(e['group_index'],e['quad_index']):e for e in contract['cache_quad_edits']};groups=[]
    for gi,g in enumerate(render['groups']):
        quads=[]
        for qi,q in enumerate(g['quads']):
            e=lookup.get((gi,qi));quads+=e['retained_quads'] if e else [q]
        if quads:groups.append({'material':g['material'],'quads':quads})
    return groups

def main():
    OUT.mkdir(exist_ok=True);catalog=a.load(HERE/'generated/catalog.json');base=next(x for x in catalog['assets'] if x['asset_key']==KEY);window=a.load(a.ROOT/base['emitted_master_path']);source=a.load(a.ROOT/base['source_master_path']);roof=a.load(ROOF);assert a.sha(ROOF)==ROOF_SHA;assert roof['metadata']['source_master_sha256']==base['source_sha256'];assert roof['metadata']['roof_only'];assert roof.get('assembly_cuts',[])==[];assert roof['materials']==window['materials'];assert a.core.transform(next(i for i in source['instances'] if i['id']=='roof').get('transform'))==a.core.transform(None)
    allops=[];bindings=[];source_ops=set();byid={c['id']:c for c in roof['components']}
    for inst in roof['instances']:
        assert a.core.transform(inst.get('transform'))==a.core.transform(None) and not inst.get('parent');c=byid[inst['component']];assert all(o['action']=='paint' for o in c['operations']);source_ops.update(c['metadata']['provenance']['source_operations'])
        for op in c['operations']:
            o=copy.deepcopy(op);o['id']=c['id']+'__'+o['id'];allops.append(o)
        bindings.append({'roof_component':c['id'],'roof_instance':inst['id'],'operation_count':len(c['operations']),'source_operations':c['metadata']['provenance']['source_operations']})
    original_roof=next(c for c in source['components'] if c['id']=='roof');assert source_ops=={o['id'] for o in original_roof['operations']},('Unmapped source roof operations',source_ops)
    combined=copy.deepcopy(window);target=next(c for c in combined['components'] if c['id']=='roof');target['operations']=allops;target['metadata']={'exact_finished_roof_composition':{'finished_path':str(ROOF.relative_to(a.ROOT)),'finished_sha256':ROOF_SHA,'source_component':'roof','paint_only_flattening_preserves_last_write_order':True}};combined['id']=KEY+'__roof_opening_composition_r01'
    combined['provenance']['roof_opening_composition']={'window_master_path':base['emitted_master_path'],'window_master_sha256':base['emitted_master_sha256'],'roof_master_path':str(ROOF.relative_to(a.ROOT)),'roof_master_sha256':ROOF_SHA,'source_master_sha256':base['source_sha256'],'native_coordinates_unchanged':True,'roof_geometry_fields_unchanged':True,'source_outside_window_ROIs_not_compiled':True}
    a.core.validate_master(combined,.05);mp=OUT/(KEY+'.roof_openings.master.json.gz');a.write(mp,combined)
    contract=a.load(a.ROOT/base['replacement_contract_path']);affected={r['patch_id'] for e in contract['cache_quad_edits'] if 'slate' in e['material'] for r in e['removed_rectangles']}
    contract['authored_master_path']=str(mp.relative_to(a.ROOT));contract['authored_master_sha256']=a.sha(mp)
    contract['roof_composition']={'roof_master_path':str(ROOF.relative_to(a.ROOT)),'roof_master_sha256':ROOF_SHA,'standalone_window_master_path':base['emitted_master_path'],'standalone_window_master_sha256':base['emitted_master_sha256'],'affected_patch_ids':sorted(affected),'ownership':'Window ROI owns every combined surface inside its exact AABB; external detailed roof quads must be clipped against the same AABBs. Original coarse roof groups are never reintroduced in those regions.','outside_detailed_roof_exclusion_aabbs':[{'patch_id':p['id'],**p['replacement_volume_master_m']} for p in contract['patches']],'atomic_source_bindings':[base['source_sha256'],base['emitted_master_sha256'],ROOF_SHA],'source_ops_replaced':len(source_ops),'finished_paint_ops':len(allops),'extra_roof_frame_transform':False}
    contract['activation']['coarse_grid_transition_seams']='Exact cache/fine XOR interface adapter; combined source must pass bounded ROI and whole-window edge closure checks.'
    cp=OUT/(KEY+'.replacement.json.gz');a.write(cp,contract)
    composed={**base,'emitted_master_path':str(mp.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(mp),'replacement_contract_path':str(cp.relative_to(a.ROOT)),'replacement_contract_sha256':a.sha(cp),'roof_composition_sha256':ROOF_SHA}
    newcat={**catalog,'assets':[composed if x['asset_key']==KEY else x for x in catalog['assets']]};a.write(OUT/'catalog.json',newcat)
    budgetplan=a.load(HERE/'generated/cost_plan.json');bs=budget.bounds_list(combined,.05);plans=[]
    for p in contract['patches']:
        plans.append({'patch_id':p['id'],'source_glass_operation':p['source_glass']['operation'],'whole_patch_candidate_visits':budget.cost(bs,p['fine_cell_bounds']),'chunks':budget.split(bs,p['fine_cell_bounds'],p['fine_cell_bounds'],200000)})
    aggregate={'asset_key':KEY,'windows':len(plans),'chunk_count':sum(len(p['chunks']) for p in plans),'max_whole_patch_candidates':max(p['whole_patch_candidate_visits'] for p in plans),'max_chunk_candidates':max(c['candidate_visits'] for p in plans for c in p['chunks']),'total_candidates_with_halos':sum(c['candidate_visits'] for p in plans for c in p['chunks']),'plans':plans}
    budgetplan['assets']=[aggregate if x['asset_key']==KEY else x for x in budgetplan['assets']];budgetplan['total_candidates_with_halos']=sum(x['total_candidates_with_halos'] for x in budgetplan['assets']);budgetplan['basis']='New composed source exact AABB estimates; timing extrapolation from standalone common probes, to be checked by roof-overlap subset QA.';a.write(OUT/'cost_plan.json',budgetplan)
    outputs=[]
    for item in newcat['assets']:
        c=a.load(a.ROOT/item['replacement_contract_path']);r=a.load(a.ROOT/c['source_render_path']);out=OUT/(item['asset_key']+'.outside_retained_sourcequads.json.gz');a.write(out,{'schema':'riverstone.facility_openings.outside_source_quads.v1','asset_key':item['asset_key'],'source_render_path':c['source_render_path'],'source_render_sha256':c['source_render_sha256'],'replacement_contract_sha256':item['replacement_contract_sha256'],'groups':retained_groups(r,c),'world_local_aabbs':[{'patch_id':p['id'],**p['replacement_volume_master_m']} for p in c['patches']],'surface_module_rule':'For an active fine-window instance, create wall surface modules only on these outside-retained original faces. Never reapply original solid-wall patches inside the window AABBs.','collision_input_unchanged':True});outputs.append({'asset_key':item['asset_key'],'path':str(out.relative_to(a.ROOT)),'sha256':a.sha(out)})
    a.write(OUT/'composition_report.json',{'source_master_sha256':base['source_sha256'],'roof_master_sha256':ROOF_SHA,'standalone_window_master_sha256':base['emitted_master_sha256'],'composed_master_sha256':a.sha(mp),'roof_paint_operations_preserved':len(allops),'original_source_roof_operations_replaced':len(source_ops),'native_transform_unchanged':True,'other_source_components_and_window_cuts_unchanged':all(c==next(x for x in combined['components'] if x['id']==c['id']) for c in window['components'] if c['id']!='roof') and combined['assembly_cuts']==window['assembly_cuts'],'roof_overlap_patch_ids':sorted(affected),'source_identity_bindings':bindings,'outside_retained_sourcequads':outputs,'composed_cost':{k:v for k,v in aggregate.items() if k!='plans'},'subset_qa_status':'pending','runtime_activated':False})
    print(json.dumps({'roof_ops':len(allops),'roof_overlap_patches':sorted(affected),'composed_cost':{k:v for k,v in aggregate.items() if k!='plans'},'master_sha256':a.sha(mp)},indent=2))
if __name__=='__main__':main()
