"""Whole unique roof with exact original paint/cut prefix plus subtractive detail.

The original native operation order is retained byte-for-byte. Only trailing,
explicitly subtractive detailed cuts are appended inside that same component.
No primitive is cropped or sampled here; all transforms are proved equivalent.
"""
import copy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parents[1]
sys.path.insert(0,str(B/'native_pitch_v1'))
import operation_roof_adapter_v2 as previous
base=previous.operation_adapter.base
core=base.core;require=base.require

def compose_master(source,window,roof,policy):
    for m in (source,window,roof):core.validate_master(m,policy['fine_pitch_m'])
    for k in ('axes','grid_origin','materials'):require(source.get(k)==window.get(k)==roof.get(k),'Source/window/roof identity mismatch: '+k)
    require(roof.get('metadata',{}).get('roof_only') is True and not roof.get('constraints') and not roof.get('assembly_cuts'),'Roof-only global semantics unsupported')
    require(window['components'][:len(source['components'])]==source['components'],'Original component prefix differs')
    require(window['instances'][:len(source['instances'])]==source['instances'],'Original instance prefix differs')
    require(window.get('constraints')==source.get('constraints'),'Original constraints differ')
    extras=window['components'][len(source['components']):];exinst=window['instances'][len(source['instances']):]
    require((not extras and not exinst) or ([x['id'] for x in extras]==['opening_details'] and exinst==[{'id':'opening_details','component':'opening_details'}] and all(o['action']=='paint' for o in extras[0]['operations'])),'Unknown appended window components/instances')
    for k,v in source.items():
        if k not in ('id','components','instances','assembly_cuts','provenance'):require(window.get(k)==v,'Unapproved source field differs: '+k)
    original_cuts=source.get('assembly_cuts',[])
    require(window.get('assembly_cuts',[])[:len(original_cuts)]==original_cuts,'Original assembly-cut prefix differs')
    sc=core.indexed(source['components'],'component');si=core.indexed(source['instances'],'instance');rc=core.indexed(roof['components'],'roof component')
    st=base.transforms(source);rt=base.transforms(roof);uses=base.Counter(i['component'] for i in source['instances']);ruses=base.Counter(i['component'] for i in roof['instances'])
    require(set(ruses)==set(rc) and all(v==1 for v in ruses.values()),'Finished roof components require one instance')
    grouped={};bindings=[];selected=[];original_prefixes=[];max_error=0.;source_order=[]
    for ri in roof['instances']:
        c=rc[ri['component']];md=c.get('metadata',{});prov=md.get('provenance',{});identity=md.get('shared_row_source',{}).get('instance_metadata',{}).get('source_identity',{})
        cid=prov.get('source_component');iid=identity.get('instance')
        require(cid in sc and iid in si and si[iid]['component']==cid and identity.get('component')==cid,'Unknown source component/instance')
        require(uses[cid]==1 and cid not in grouped,'Requires one finished whole roof per unique original component')
        require(not previous.operation_adapter.dynamic(sc[cid]) and not previous.operation_adapter.dynamic(si[iid]),'Dynamic roof forbidden')
        require(all(p.get('metadata',{}).get('source_category') in policy['roof_part_categories'] for p in sc[cid]['parts']),'Whole-roof component contains nonroof/unclassified part')
        ops=sc[cid]['operations'];require(len(ops)>=2 and ops[0]['action']=='paint' and all(o['action']=='cut' for o in ops[1:]),'Original roof must have one paint then original terminal cuts')
        require(all(not o.get('selector') and o['part']==identity.get('part') for o in ops),'Original local selector/part mismatch')
        require(ops[0]['material']==identity.get('material') and ops[0]['material'] in policy['roof_materials'],'Original material mismatch')
        require(prov.get('source_operations')==[ops[0]['id']] and md.get('source_operation')==ops[0] and md.get('source_cuts')==ops[1:] and md.get('subtractive_subset_proof') is True,'Missing exact original paint/cut metadata binding')
        require(base.affine_error(core.transform(identity.get('transform')),st[iid])<=policy['transform_tolerance_m'],'Source transform differs')
        require(len(c['operations'])>len(ops),'No new subtractive detail')
        target=[];opbindings=[]
        for n,o in enumerate(c['operations']):
            world=core.compose(rt[ri['id']],core.transform(o.get('transform')))
            local=core.compose(base.inverse_transform(st[iid]),world)
            if n<len(ops):
                old=ops[n];require(o['id']==old['id'] and o['action']==old['action'] and o['part']==old['part'] and o.get('material')==old.get('material') and o['shape']==old['shape'] and not o.get('selector'),'Finished prefix changes original operation')
                expected=core.compose(st[iid],core.transform(old.get('transform')));err=max(base.affine_error(world,expected),base.geometry_error(o['shape'],world,expected,policy['fine_pitch_m']));require(err<=policy['transform_tolerance_m'],'Finished original prefix changes world geometry');new=copy.deepcopy(old)
            else:
                require(o['action']=='cut' and not o.get('selector') and o['part']==identity['part'] and o.get('metadata',{}).get('subtractive_only') is True,'New detail must be same-part local subtractive-only cut')
                require(o['id'] not in {x['id'] for x in ops},'Detail ID collides with original operation');new=copy.deepcopy(o);new['id']=ri['id']+'__'+o['id'];new['transform']=local;expected=core.compose(st[iid],local);err=max(base.affine_error(world,expected),base.geometry_error(o['shape'],world,expected,policy['fine_pitch_m']));require(err<=policy['transform_tolerance_m'],'Inverse transform changes added cut')
            max_error=max(max_error,err);target.append(new);opbindings.append({'roof_operation':o['id'],'canonical_operation':new['id'],'shape_sha256':core.digest(o['shape']),'source_roof_operation_sha256':core.digest(o),'canonical_operation_sha256':core.digest(new),'world_transform':world})
        require(target[:len(ops)]==ops,'Original operation bytes/order changed');grouped[cid]=target;source_order.append(iid);selected.append({'component':cid,'operation':ops[0]['id']});original_prefixes.append({'component':cid,'instance':iid,'operations':copy.deepcopy(ops),'original_prefix_sha256':core.digest(ops),'canonical_prefix_sha256':core.digest(target[:len(ops)])});bindings.append({'source_component':cid,'source_instance':iid,'source_operations':[ops[0]['id']],'roof_component':c['id'],'roof_instance':ri['id'],'operation_bindings':opbindings})
    require(grouped,'No complete roof bindings');require(source_order==[i['id'] for i in source['instances'] if i['component'] in grouped],'Finished roof component order differs')
    labels=[x for i in source['instances'] if i['component'] in grouped for x in base.labels_for(sc[i['component']],i['id'])]
    # Even original feature selectors are conservatively rejected until the
    # same instance/component/part semantic scope has been separately proven.
    for item in window.get('assembly_cuts',[])+window.get('constraints',[]):
        for k in ('selector','a','b'):
            selector=item.get(k,{})
            require(not('feature' in selector and any(core.selector_matches({n:v for n,v in selector.items() if n!='feature'},lab) for lab in labels)),'Feature-scoped roof selector unsupported')
    combined=copy.deepcopy(window)
    for c in combined['components']:
        if c['id'] in grouped:c['operations']=grouped[c['id']]
    combined['id']=source['id']+'__canonical_cut_roof_openings_r01';combined.setdefault('provenance',{})['canonical_roof_openings']={'adapter_schema':'riverstone.canonical_cut_roof_openings.v1','source_semantic_sha256':core.digest(source),'contract':'Exact original whole-roof paint/cut prefix; only same-part subtractive detail appended; source instances and constraints preserved.','full_compile':False,'runtime_activation':False};core.validate_master(combined,policy['fine_pitch_m'])
    proof={'source_roof_components':list(grouped),'source_roof_instances':source_order,'source_roof_operation_count':sum(len(sc[k]['operations']) for k in grouped),'finished_roof_component_count':len(roof['components']),'finished_roof_operation_count':sum(map(len,grouped.values())),'max_world_geometry_error_m':max_error,'bindings':bindings,'selected_source_operations':selected,'original_paint_cut_prefixes':original_prefixes,'original_roof_operations_byte_preserved':True,'additional_detail_subtractive_only':True,'native_instances_sha256':core.digest(window['instances']),'constraints_sha256':core.digest(window.get('constraints',[])),'scoped_assembly_cuts_sha256':core.digest(window.get('assembly_cuts',[])),'nonroof_components_sha256':core.digest([c for c in window['components'] if c['id'] not in grouped]),'parts_metadata_and_component_order_preserved':True,'source_and_finished_roof_paint_precedence_preserved':True,'constraint_semantics_preserved_global_constraints_not_evaluated':True,'adapter_path':str(Path(__file__).relative_to(base.ROOT)),'adapter_sha256':base.sha(__file__)}
    return combined,proof

def replacement_scope(source,render,proof,policy):
    return previous.replacement_scope(source,render,proof,policy)
