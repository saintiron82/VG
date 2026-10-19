"""Exact operation-scoped roof adapter for legacy/mixed native components.

Original classified whole-roof inputs use the frozen adapter unchanged.
New legacy inputs replace only hash-bound source paint IDs in original order.
Nonselected paint/cuts, local component frames, parts and constraints are intact.
"""
import copy,importlib.util,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sp=importlib.util.spec_from_file_location('frozen_operation_adapter_base',B/'canonical_adapter/compose.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
ROOT=base.ROOT;core=base.core;require=base.require;load=base.load;sha=base.sha;write=base.write;checked_load=base.checked_load
old_compose=base.compose_master;old_scope=base.replacement_scope

def dynamic(value):
    if isinstance(value,dict):
        if any(k in value and value[k] is True for k in ['dynamic','moving','animated']):return True
        if value.get('runtime_animation') not in (None,'not_integrated','static','none'):return True
        return any(dynamic(v) for v in value.values())
    if isinstance(value,list):return any(dynamic(v) for v in value)
    return False

def compose_master(source,window,roof,policy):
    selected_cids={c.get('metadata',{}).get('provenance',{}).get('source_component') for c in roof['components']}
    sc=core.indexed(source['components'],'component');si=core.indexed(source['instances'],'instance')
    require(all(cid in sc for cid in selected_cids),'Missing selected original component')
    require(not any(dynamic(sc[cid]) or any(dynamic(i) for i in source['instances'] if i['component']==cid) for cid in selected_cids),'Moving/dynamic selected component has no static roof duplication contract')
    legacy=any(any(o['action']!='paint' or o.get('material') not in policy['roof_materials'] for o in sc[cid]['operations']) or any(p.get('metadata',{}).get('source_category') not in policy['roof_part_categories'] for p in sc[cid]['parts']) for cid in selected_cids)
    if not legacy:return old_compose(source,window,roof,policy)
    pitch=policy['fine_pitch_m']
    for m in [source,window,roof]:core.validate_master(m,pitch)
    require(source==window,'Legacy operation extension currently requires unchanged whole source, no preexisting window revision')
    require(roof.get('metadata',{}).get('roof_only') is True and not roof.get('assembly_cuts') and not roof.get('constraints'),'Requires simple exact roof-only source')
    for field in ['axes','grid_origin','materials']:require(source.get(field)==roof.get(field),'Shared axes/grid/material mismatch')
    st=base.transforms(source);rt=base.transforms(roof);rc=core.indexed(roof['components'],'component');uses=base.Counter(i['component'] for i in source['instances']);ruses=base.Counter(i['component'] for i in roof['instances']);require(set(ruses)==set(rc) and all(n==1 for n in ruses.values()),'Finished components must each have one instance')
    replacements={};bindings=[];max_error=0.;order={};selected_labels=[]
    for ri in roof['instances']:
        c=rc[ri['component']];md=c.get('metadata',{});prov=md.get('provenance',{});identity=md.get('shared_row_source',{}).get('instance_metadata',{}).get('source_identity',{});cid=prov.get('source_component');iid=identity.get('instance');ids=prov.get('source_operations')
        require(cid in sc and iid in si and si[iid]['component']==cid and identity.get('component')==cid,'Inconsistent source component/instance binding');require(uses[cid]==1,'Shared original component needs a distinct-instance contract');require(isinstance(ids,list) and len(ids)==1,'Mixed-component detail must bind one original operation per finished component')
        originals=core.indexed(sc[cid]['operations'],'operation');oid=ids[0];require(oid in originals,'Unknown original source operation');op=originals[oid];require(op['action']=='paint' and not op.get('selector'),'Only an original paint operation is replaceable');require(op['material'] in policy['roof_materials'],'Nonroof material target rejected');require(op['part']==identity.get('part') and op['material']==identity.get('material'),'Source part/material binding mismatch');paint_ops=[o for o in c['operations'] if o['action']=='paint'];cut_ops=[o for o in c['operations'] if o['action']=='cut']
        require(paint_ops and all(not o.get('selector') and o['part']==op['part'] and o['material']==op['material'] for o in paint_ops),'Finished source part/material/action mismatch')
        if cut_ops:
            require(md.get('subtractive_subset_proof') is True and md.get('source_operation')==op,'Subtractive detail lacks exact original operation binding')
            require(len(paint_ops)==1 and c['operations'][0] is paint_ops[0] and all(not o.get('selector') and o['part']==op['part'] and o.get('metadata',{}).get('subtractive_only') is True for o in cut_ops),'Subtractive detail requires one initial paint and scoped trailing cuts')
            require(paint_ops[0]['shape']==op['shape'] and base.affine_error(core.compose(rt[ri['id']],core.transform(paint_ops[0].get('transform'))),core.compose(st[iid],core.transform(op.get('transform'))))<=policy['transform_tolerance_m'],'Initial subtractive solid differs from original world shape')
            # Destructive cuts cannot resurrect an earlier overwritten source
            # layer. Reject unless every prior same-component paint is strictly
            # disjoint from each added cut. Do not infer safety from selectors.
            def bounds(shape,tr):
                lo,hi=core.shape_bounds(core.prepare_shape(shape,pitch));points=[core.apply(tr,p) for p in itertools.product(*zip(lo,hi))];return [min(p[j] for p in points) for j in range(3)],[max(p[j] for p in points) for j in range(3)]
            preceding=sc[cid]['operations'][:next(i for i,x in enumerate(sc[cid]['operations']) if x['id']==oid)]
            for cut in cut_ops:
                clo,chi=bounds(cut['shape'],core.compose(rt[ri['id']],core.transform(cut.get('transform'))))
                for prior in preceding:
                    if prior['action']!='paint':continue
                    plo,phi=bounds(prior['shape'],core.compose(st[iid],core.transform(prior.get('transform'))))
                    require(any(clo[j]>=phi[j]+1e-9 or plo[j]>=chi[j]+1e-9 for j in range(3)),'Added roof cut could erase previously occupied source body; isolated-layer contract required')
        require(base.affine_error(core.transform(identity.get('transform')),st[iid])<=policy['transform_tolerance_m'],'Original instance transform mismatch')
        if oid not in order.setdefault(cid,[]):order[cid].append(oid)
        target=replacements.setdefault((cid,oid),[]);opbindings=[]
        for o in c['operations']:
            world=core.compose(rt[ri['id']],core.transform(o.get('transform')));local=core.compose(base.inverse_transform(st[iid]),world);back=core.compose(st[iid],local);err=max(base.affine_error(world,back),base.geometry_error(o['shape'],world,back,pitch));require(err<=policy['transform_tolerance_m'],'World geometry transform error');max_error=max(max_error,err);new=copy.deepcopy(o);new['id']=ri['id']+'__'+o['id'];new['transform']=local
            if o['action']=='cut':new['selector']={'feature':[ri['id']+'__'+x['id'] for x in paint_ops]}
            target.append(new);opbindings.append({'roof_operation':o['id'],'canonical_operation':new['id'],'shape_sha256':core.digest(o['shape']),'source_roof_operation_sha256':core.digest(o),'canonical_operation_sha256':core.digest(new),'world_transform':world,'finished_action':o['action'],'canonical_cut_selector':new.get('selector')})
        bindings.append({'source_component':cid,'source_instance':iid,'source_operations':ids,'roof_component':c['id'],'roof_instance':ri['id'],'operation_bindings':opbindings})
    require(replacements,'No mapped roof operations')
    for cid,finished_order in order.items():
        original_order=[o['id'] for o in sc[cid]['operations'] if (cid,o['id']) in replacements];labels={(o['part'],o['material']) for o in sc[cid]['operations'] if (cid,o['id']) in replacements}
        require(original_order==finished_order or len(labels)==1,'Finished order changes noncommuting original labels')
    for i in source['instances']:
        for o in sc[i['component']]['operations']:
            if (i['component'],o['id']) in replacements:selected_labels.append({'instance':i['id'],'component':i['component'],'part':o['part'],'material':o['material'],'feature':o['id']})
    selectors=[(o['id'],o.get('selector',{}),c['id']) for c in source['components'] for o in c['operations'] if o['action']=='cut']+[(o['id'],o.get('selector',{}),None) for o in source.get('assembly_cuts',[])]
    for con in source.get('constraints',[]):
        selectors += [(con['id'],con[f],None) for f in ['selector','a','b'] if f in con]
    for name,selector,cid in selectors:
        scope={k:v for k,v in selector.items() if k!='feature'}
        require(not ('feature' in selector and any((cid is None or l['component']==cid) and core.selector_matches(scope,l) for l in selected_labels)),'Feature-scoped selector touches replacement IDs: '+name)
    combined=copy.deepcopy(source);preserved=[];selected=[]
    for c in combined['components']:
        before=list(c['operations']);after=[]
        for index,o in enumerate(before):
            key=(c['id'],o['id'])
            if key in replacements:
                after.extend(replacements[key]);selected.append({'component':c['id'],'operation':o['id'],'original_index':index,'operation_sha256':core.digest(o),'replacement_operation_ids':[x['id'] for x in replacements[key]]})
            else:after.append(o);preserved.append({'component':c['id'],'operation':o['id'],'original_index':index,'operation_sha256':core.digest(o),'action':o['action']})
        c['operations']=after
        require([o for o in after if not any(o['id']==x['id'] for (cid,_),ops in replacements.items() if cid==c['id'] for x in ops)]==[o for o in before if (c['id'],o['id']) not in replacements],'Nonselected operation sequence changed')
    combined['id']=source['id']+'__canonical_roof_operations_r01';combined.setdefault('provenance',{})['canonical_roof_openings']={'adapter_schema':'riverstone.canonical_roof_operations.v1','source_semantic_sha256':core.digest(source),'contract':'Only mapped roof paint operations replaced in original slots; all other operations and cuts byte-preserved.','adapter_path':str(Path(__file__).relative_to(ROOT)),'adapter_sha256':sha(__file__),'frozen_transform_and_packaging_helper_sha256':sha(base.__file__),'source_instance_part_component_labels_preserved':True,'source_constraints_preserved':True,'feature_selector_remap':None,'full_compile':False,'runtime_activation':False};core.validate_master(combined,pitch)
    proof={'source_roof_components':sorted(selected_cids),'source_roof_instances':[i['id'] for i in source['instances'] if i['component'] in selected_cids],'selected_source_operations':selected,'preserved_original_operations':preserved,'source_roof_operation_count':len(replacements),'finished_roof_component_count':len(roof['components']),'finished_roof_operation_count':sum(len(v) for v in replacements.values()),'max_world_geometry_error_m':max_error,'bindings':bindings,'native_instances_sha256':core.digest(source['instances']),'constraints_sha256':core.digest(source.get('constraints',[])),'scoped_assembly_cuts_sha256':core.digest(source.get('assembly_cuts',[])),'nonroof_components_sha256':core.digest([c for c in source['components'] if c['id'] not in selected_cids]),'parts_metadata_and_component_order_preserved':True,'original_nonselected_operation_bytes_and_order_preserved':True,'replacement_original_operation_slots_preserved':True,'finished_detail_cuts_isolated_to_their_original_roof_paint_features':True,'finished_detail_cut_aabbs_strictly_disjoint_from_prior_same_component_paints':True,'source_and_finished_roof_paint_precedence_preserved':'Each source slot preserved; finished cross-slot ordering may commute only when component/part/material labels are identical and no feature-scoped selector is active.','constraint_semantics_preserved_global_constraints_not_evaluated':True,'operation_adapter_path':str(Path(__file__).relative_to(ROOT)),'operation_adapter_sha256':sha(__file__)}
    return combined,proof

def replacement_scope(source,render,proof,policy):
    if 'selected_source_operations' not in proof:return old_scope(source,render,proof,policy)
    selected={(x['component'],x['operation']) for x in proof['selected_source_operations']};sc={c['id']:c for c in source['components']};st=base.transforms(source);ops=[]
    for i in source['instances']:
        for o in sc[i['component']]['operations']:
            if (i['component'],o['id']) in selected:ops.append({'component':i['component'],'instance':i['id'],'operation':o['id'],'material':o['material'],'part':o['part'],'original_operation':copy.deepcopy(o),'operation_sha256':core.digest(o),'world_transform':core.compose(st[i['id']],core.transform(o.get('transform')))})
    materials={o['material'] for o in ops};nonroof={o['material'] for c in source['components'] for o in c['operations'] if o['action']=='paint' and (c['id'],o['id']) not in selected};require(not(materials&nonroof),'Selected roof material shared with nonselected source operation; exact labeled extraction required')
    groups=[];inventory=[]
    for index,g in enumerate(render['groups']):
        row={'group_index':index,'material':g['material'],'quad_count':len(g['quads']),'original_group_sha256':core.digest(g)};inventory.append(row)
        if g['material'] in materials:groups.append({**row,'original_group':copy.deepcopy(g)})
    require(groups,'No exact source roof group');return {'schema':'riverstone.canonical_roof_replacement_scope.v1','source_roof_operations':ops,'source_roof_materials':sorted(materials),'exclusive_source_material_ownership_verified':True,'exact_source_roof_groups':groups,'ordered_source_group_inventory':inventory,'source_material_bindings':copy.deepcopy(source['materials']),'operation_scope':'Only explicit selected original paint IDs; mixed component nonroof paints/cuts are retained.','removal_rule':'Only exact hash-bound source groups listed here when complete roof replacement is active.','window_overlap_rule':'Finite canonical ROIs own all surfaces inside their exact AABBs; detailed roof only outside.','runtime_ready':False}

def build(config):
    base.HERE=HERE;base.compose_master=compose_master;base.replacement_scope=replacement_scope
    def wrapped_write(path,value):
        if Path(path).name=='catalog.json':value={**value,'adapter_sha256':sha(__file__),'frozen_packaging_helper_sha256':sha(base.__file__)}
        write(path,value)
    base.write=wrapped_write
    return base.build(config)
