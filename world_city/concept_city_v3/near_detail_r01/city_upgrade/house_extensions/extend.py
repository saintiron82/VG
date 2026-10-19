"""Data-driven source-equivalent extensions; only existing common-master grammar.

Uses house_rules' physical authoring functions, adding explicit selector and
shape contracts. No asset-key geometry dispatch and no whole-house compilation.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import gzip
import io
import json
import math
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'house_rules'
sys.path.insert(0,str(BASE))
import adapter as a
from layered_compile import signed_permutation
VERSION='house-source-equivalent-extensions-1'


def load(path):
    path=Path(path)
    if path.suffix=='.gz':
        with gzip.open(path,'rt') as f:return json.load(f)
    return a.load(path)


def configuration():
    config=load(HERE/'extensions.v1.json')
    rules=load(HERE/config['base_rules']);selectors=load(HERE/config['base_selectors'])
    for role,categories in config['component_extensions'].items():
        selectors['components'][role]['source_categories']+=categories
    selectors['surfaces'].update(copy.deepcopy(config['surface_overrides']))
    selectors['id']='source_equivalent_extension_selectors_v1'
    return config,rules,selectors


def write_gzip(path,value):
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write(raw)
    return len(raw)


def verify_native_sources(source,config):
    meta=source.get('metadata',{})
    modules=meta.get('native_modules')
    if not modules:return []
    refs=source.get('provenance',{}).get('native_sources',[])
    a.fail(len(modules)==len(refs)==meta.get('source_unit_count'),'native_module_count_contract')
    expected_components=[];expected_instances=[];verified=[]
    for ordinal,(module,ref) in enumerate(zip(modules,refs)):
        path=a.ROOT/ref['path']
        a.fail(a.sha(path)==ref['sha256'],'native_source_hash_mismatch',ref)
        native=load(path)
        a.fail(native['id']==module['asset_key'],'native_source_identity_mismatch')
        a.fail(native['materials']==source['materials'],'native_material_equivalence_failed')
        prefix=config['native_module_contract']['component_prefix_format'].format(ordinal=ordinal)
        for c in native['components']:
            c=copy.deepcopy(c);c['id']=prefix+c['id'];expected_components.append(c)
        for inst in native['instances']:
            inst=copy.deepcopy(inst);inst['id']=prefix+inst['id'];inst['component']=prefix+inst['component']
            a.fail(not inst.get('parent'),'native_parent_transform_pending')
            t=a.core.transform(inst.get('transform'))
            t['translation']=[v+delta for v,delta in zip(t['translation'],module['translation'])]
            inst['transform']=t;expected_instances.append(inst)
        verified.append({'asset_key':native['id'],'path':ref['path'],'sha256':ref['sha256'],
                         'component_prefix':prefix,'metadata':native['metadata']})
    a.fail(expected_components==source['components'],'native_component_equivalence_failed')
    a.fail(expected_instances==source['instances'],'native_instance_equivalence_failed')
    return verified


def assert_source_contract(source,config,selectors,natives):
    a.core.validate_master(source,.05)
    metas=[r['metadata'] for r in natives] or [source.get('metadata',{})]
    for meta in metas:
        a.fail(meta.get('style') in config['source_styles'],'unsupported_source_style',{'style':meta.get('style')})
        a.fail(meta.get('roof_form') in config['roof_forms'],'unsupported_roof_form',{'roof_form':meta.get('roof_form')})
        # Legacy r1 omits assembly_class and explicit dimensions: source envelopes
        # and actual component geometry establish its bounds; no metadata is forged.
        a.fail(meta.get('assembly_class','regular_house') in config['source_classes'],'unsupported_source_class')
        a.fail(type(meta.get('floors')) is int and meta['floors']>0,'source_floor_count_missing')
        a.fail(bool(meta.get('body_bounds')) and bool(meta.get('entrance')),'source_bounds_or_entrance_missing')
    a.fail(len(source['components'])==len(source['instances']),'shared_components_pending')
    a.fail(Counter(i['component'] for i in source['instances'])==Counter(c['id'] for c in source['components']),'component_instance_contract')
    a.fail(all(c['kind'] in config['supported_constraints'] for c in source.get('constraints',[])),'constraint_kind_pending')
    for inst in source['instances']:
        a.fail(signed_permutation(a.core.transform(inst.get('transform'))['basis']),'instance_transform_pending')
    for c in source['components']:
        if a.component_role(c,selectors) in ('wall','foundation','door_insert'):
            a.fail(not any(o.get('transform') for o in c['operations']),'nonroof_operation_transform_pending',{'component':c['id']})
    return metas


def ridge_caps(op,config,selectors,counts):
    r=config['ridge'];lo=op['shape']['min'];hi=op['shape']['max']
    a.fail(hi[2]-lo[2]>hi[0]-lo[0] and hi[1]-lo[1]>r['underlay_recess_m'],'ridge_box_axis_contract')
    base=copy.deepcopy(op);base['shape']['max'][1]-=r['underlay_recess_m'];base['material']=selectors['materials']['roof_underlay']
    out=[base];mid=(lo[0]+hi[0])/2;peak=hi[1]
    n=max(1,math.ceil((hi[2]-lo[2])/r['cap_length_m']));step=(hi[2]-lo[2])/n
    for i in range(n):
        za=lo[2]+i*step+r['joint_m']/2;zb=lo[2]+(i+1)*step-r['joint_m']/2
        if zb<=za:continue
        poly=[[lo[0],peak-r['cap_thickness_m']],[mid,peak+r['cap_rise_m']-r['cap_thickness_m']],[hi[0],peak-r['cap_thickness_m']],
              [hi[0],peak],[mid,peak+r['cap_rise_m']],[lo[0],peak]]
        cap=a.prism(op['id']+f'__near_ridge_cap_{i}',poly,za,zb,selectors['materials']['roof_tiles'][i%len(selectors['materials']['roof_tiles'])],op['part'])
        if 'transform' in op:cap['transform']=copy.deepcopy(op['transform'])
        out.append(cap);counts['ridge_caps']+=1
    return out


def improve_planes(c,rules,selectors,config,counts):
    planes=a.selected(c,'roof_plane',selectors)
    cuts=[o for o in c['operations'] if o['action']=='cut']
    categories={p.get('metadata',{}).get('source_category') for p in c['parts']}
    hip=config['hip_contract']['source_category'] in categories
    a.fail(bool(planes),'no_roof_planes')
    for op in c['operations']:
        transform=a.core.transform(op.get('transform'))
        a.fail(signed_permutation(transform['basis']) and transform['basis'][1]==[0,1,0], 'roof_operation_transform_contract', {'component':c['id'],'operation':op['id']})
        if hip:a.fail(transform['translation']==config['hip_contract']['operation_translation_m'],'hip_operation_translation_pending',{'component':c['id'],'operation':op['id']})
    if hip:
        h=config['hip_contract']
        a.fail(len(planes)==h['plane_count_per_component'] and len(cuts)==h['cut_count_per_component'],'hip_plane_cut_count_contract')
        a.fail(c['operations'][-len(cuts):]==cuts,'hip_trim_order_contract')
        a.fail(all(re.fullmatch(h['trim_id_regex'],o['id']) and o['shape']['kind']=='extrusion' for o in cuts),'hip_trim_shape_contract')
        highest=max(p[1] for o in planes for p in o['shape']['polygon'])
        a.fail(all(max(p[1] for p in o['shape']['polygon'])>=highest+h['trim_top_clearance_min_m'] for o in cuts),'hip_trim_lip_clearance_contract')
    else:a.fail(not cuts,'nonhip_trim_pending')
    output=[]
    for op in c['operations']:
        if op not in planes:
            if a.matches(op,config['ridge']['selector']):output.extend(ridge_caps(op,config,selectors,counts))
            else:output.append(copy.deepcopy(op))
            continue
        t=a.core.transform(op.get('transform'))
        a.fail(signed_permutation(t['basis']) and t['basis'][1]==[0,1,0], 'roof_operation_transform_contract')
        a.roof_geometry(op)
        local=copy.deepcopy(op);local.pop('transform',None)
        temporary={'id':c['id'],'parts':copy.deepcopy(c['parts']),'operations':[local]}
        a.improve_roof(temporary,rules,selectors,counts,rules['seed'])
        for generated in temporary['operations']:
            if 'transform' in op:generated['transform']=copy.deepcopy(op['transform'])
            output.append(generated)
    if hip and all(not op.get('transform') for op in planes):
        # Long hip planes have the ridge in local Z. The two transformed trims
        # supply the exact ends of that interval at source peak height.
        peak=max(p[1] for op in planes for p in op['shape']['polygon'])
        ends=[]
        for cut in cuts:
            t=a.core.transform(cut.get('transform'))
            points=[a.core.apply(t,[x,y,0]) for x,y in cut['shape']['polygon'] if abs(y-peak)<1e-8]
            a.fail(len(points)==1,'hip_ridge_trim_endpoint_contract')
            ends.append(points[0][2])
        z0,z1=sorted(ends);width=config['ridge']['hip_half_width_m']
        a.fail(z1>z0,'hip_ridge_interval_contract')
        op=a.box('hip_ridge__near_support',[-width,peak-.20,z0],[width,peak,z1],selectors['materials']['roof_underlay'],planes[0]['part'])
        output[-len(cuts):-len(cuts)]=ridge_caps(op,config,selectors,counts)
    c['operations']=output
    counts['hip_roof_components']+=int(hip)
    counts['hip_trim_cuts_preserved']+=len(cuts)


def improve_timber(c,config,counts):
    r=config['timber'];output=[]
    for op in c['operations']:
        output.append(op)
        if not a.matches(op,r['selector']) or op.get('material') not in r['material_slots']:continue
        lo,hi=op['shape']['min'],op['shape']['max']
        axis=0 if hi[0]-lo[0]>=hi[1]-lo[1] else 1;cross=1-axis
        if hi[axis]-lo[axis]<r['minimum_length_m'] or hi[cross]-lo[cross]<r['minimum_cross_width_m']:continue
        low=lo.copy();high=hi.copy();low[axis]+=r['end_inset_m'];high[axis]-=r['end_inset_m']
        mid=(lo[cross]+hi[cross])/2
        low[cross]=mid-r['groove_width_m']/2;high[cross]=mid+r['groove_width_m']/2
        low[2]=max(lo[2],hi[2]-r['groove_depth_m'])
        output.append(a.box(op['id']+'__near_timber_recess',low,high,part=op['part'],action='cut'))
        counts['timber_recesses']+=1
    c['operations']=output


def improve_wall(c,rules,selectors,config,counts,pending,windows):
    panel=a.selected(c,'wall_panel',selectors)
    a.fail(len(panel)==1,'wall_panel_count_contract')
    local_selectors=copy.deepcopy(selectors)
    if panel[0]['material'] in config['institutional_masonry']['wall_material_slots']:
        # Keep full depth backing: existing improve_wall expects an earlier panel
        # behind a skin, so explicitly insert that skin instead of replacing body.
        p=panel[0];skin=copy.deepcopy(p);skin['id']=config['institutional_masonry']['skin_operation_id']
        p['material']=selectors['materials']['mortar']
        c['operations'].insert(c['operations'].index(p)+1,skin)
        local_selectors['surfaces']['masonry']['id_regex']='('+local_selectors['surfaces']['masonry']['id_regex']+')|^'+re.escape(skin['id'])+'$'
        counts['full_masonry_wall_panels']+=1
    a.improve_wall(c,rules,local_selectors,counts,pending,windows,rules['seed'])
    improve_timber(c,config,counts)


def preservation(source,out,selectors):
    checks={key:source.get(key)==out.get(key) for key in ('instances','materials','grid_origin','assembly_cuts','constraints','metadata')}
    checks.update(component_ids=True,source_cut_order=True,thresholds=True,roof_plane_footprints=True,roof_operation_transforms=True)
    for old,new in zip(source['components'],out['components']):
        checks['component_ids'] &= old['id']==new['id']
        source_cuts=[o for o in old['operations'] if o['action']=='cut']
        checks['source_cut_order'] &= source_cuts==[o for o in new['operations'] if o['action']=='cut' and '__near' not in o['id']]
        newops={o['id']:o for o in new['operations']}
        for op in a.selected(old,'threshold',selectors):checks['thresholds'] &= op==newops.get(op['id'])
        if a.component_role(old,selectors)=='roof':
            for plane in a.selected(old,'roof_plane',selectors):
                x0,x1,*_=a.roof_geometry(plane)
                tiles=[o for o in new['operations'] if o['id'].startswith(plane['id']+'__near_tile_')]
                a.fail(bool(tiles),'roof_plane_without_tiles')
                for tile in tiles:
                    s=tile['shape'];old_s=plane['shape']
                    checks['roof_plane_footprints'] &= min(p[0] for p in s['polygon'])>=x0-1e-8 and max(p[0] for p in s['polygon'])<=x1+1e-8 and s['z_min']>=old_s['z_min']-1e-8 and s['z_max']<=old_s['z_max']+1e-8
                    checks['roof_operation_transforms'] &= tile.get('transform')==plane.get('transform')
    a.fail(all(checks.values()),'preservation_failed',checks)
    return checks


def author(source,config=None,rules=None,selectors=None,source_info=None):
    if config is None:config,rules,selectors=configuration()
    a.fail(config.get('schema')=='riverstone.house_detail.extensions.v1','extension_schema_pending')
    a.fail(rules.get('schema')=='riverstone.surface_detail.rules.v2' and rules.get('near_pitch_m')==.05,'base_rules_contract')
    natives=verify_native_sources(source,config)
    metas=assert_source_contract(source,config,selectors,natives)
    candidate=copy.deepcopy(source)
    counts={k:0 for k in ('roof_tiles','roof_planes','windows','door_leaves','masonry_strips','thresholds_preserved','hip_roof_components','hip_trim_cuts_preserved','full_masonry_wall_panels','timber_recesses','ridge_caps')}
    pending=[];windows=[];roles=Counter()
    for c in candidate['components']:
        role=a.component_role(c,selectors);roles[role or 'retained']+=1
        if role=='roof':improve_planes(c,rules,selectors,config,counts)
        elif role=='wall':improve_wall(c,rules,selectors,config,counts,pending,windows)
        elif role=='foundation':a.improve_foundation(c,rules,selectors,counts,rules['seed'])
        elif role=='door_insert':
            leaves=a.selected(c,'door_leaf',selectors);a.fail(bool(leaves),'door_insert_without_leaf')
            ops=[]
            for op in c['operations']:
                if op in leaves:ops.extend(a.improve_door(op,selectors['contracts']['door_insert_surface_m'],rules,selectors['materials']));counts['door_leaves']+=1
                else:ops.append(op)
            c['operations']=ops
    a.fail(roles['foundation']==len(metas),'foundation_module_count_contract',dict(roles))
    a.fail(roles['wall']==sum(m['floors']*4 for m in metas),'wall_floor_count_contract',dict(roles))
    a.fail(counts['door_leaves']==sum(m.get('row_units',1) for m in metas),'door_module_count_contract',counts)
    expected_hip=sum(m['roof_form']=='hip' for m in metas)*config['hip_contract']['component_count']
    a.fail(counts['hip_roof_components']==expected_hip,'hip_component_count_contract')
    checks=preservation(source,candidate,selectors)
    identity=a.core.digest({'source':source,'config':config,'rules':rules,'selectors':selectors,'engine':a.sha(__file__),'base':a.sha(a.__file__)})[:16]
    candidate['id']=source['id']+'__near_ext_'+identity;candidate['revision']=source['revision']+1
    counts['source_operations']=sum(len(c['operations']) for c in source['components'])
    counts['output_operations']=sum(len(c['operations']) for c in candidate['components'])
    prov={'engine':VERSION,'engine_sha256':a.sha(__file__),'base_engine_sha256':a.sha(a.__file__),'extension_contract_sha256':a.core.digest(config),
          'rules_sha256':a.core.digest(rules),'selectors_sha256':a.core.digest(selectors),'source_canonical_sha256':a.core.digest(source),
          'source_id':source['id'],'inputs':source_info or {},'seed':rules['seed'],'native_sources_verified':natives,
          'counts':counts,'geometry_scaling':False,'new_steps':0,'new_corbels':0,'source_metadata_preserved':True,
          'roof_material_geometry':'Overlapping physical planar slate/tile courses; per-placement palette does not establish wood-shingle variant approval.',
          'status':'authored_not_visual_approved'}
    candidate.setdefault('provenance',{})['city_near_material_extension']=prov
    a.core.validate_master(candidate,.05)
    report={'status':'structural_pass_feature_pending' if pending else 'structural_pass_not_compiled','source_id':source['id'],'output_id':candidate['id'],
            'counts':counts,'roles':dict(roles),'preservation':checks,'pending_features':pending,'windows':windows,
            'full_compile':False,'visual_approval':False,'city_support_validation':False, 'preserved_constraint_kinds':sorted({c['kind'] for c in source.get('constraints',[])}), 'layered_compile_requires_connected_validation':any(c['kind']=='connected' for c in source.get('constraints',[]))}
    return candidate,prov,report


def build():
    config,rules,selectors=configuration()
    index_path=a.ROOT/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
    index=load(index_path);house_catalog=load(BASE/'generated/active_catalog.json')
    pending_keys={r['asset_key'] for r in house_catalog['assets'] if r['status']=='coverage_pending'}
    usages=defaultdict(dict);tile_hashes=[]
    for tile_id,tile in index['tiles'].items():
        path=a.ROOT/tile['instances_path'];a.fail(a.sha(path)==tile['instances_sha256'],'tile_hash_changed')
        tile_hashes.append({'id':tile_id,'path':tile['instances_path'],'sha256':tile['instances_sha256']})
        for inst in load(path)['common_instances']:
            key=inst['asset_key']
            if key in pending_keys or key.startswith('attached_native_row_'):usages[key][inst['id']]=inst
    records=[];used_bytes=0
    for key,instances in sorted(usages.items()):
        asset=index['common_assets'][key];source_path=a.ROOT/asset['master_path']
        a.fail(a.sha(source_path)==asset['master_sha256'],'source_hash_changed')
        record={'asset_key':key,'instance_count':len(instances),'instance_ids':sorted(instances),
                'source_master_path':asset['master_path'],'source_sha256':asset['master_sha256'],'emitted_master_path':None}
        try:
            master,provenance,report=author(load(source_path),config,rules,selectors,record)
            path=HERE/'generated/masters'/(key+'.master.json.gz')
            raw_bytes=write_gzip(path,master);used_bytes+=path.stat().st_size
            a.fail(used_bytes<config['budget']['disk_bytes'],'disk_budget_exceeded')
            a.write(path.parent/(key+'.provenance.json'),provenance)
            a.write(path.parent/(key+'.validation.json'),report)
            record.update({'status':report['status'],'counts':report['counts'],'preservation':report['preservation'],
                           'pending_features':report['pending_features'],'layered_compile_requires_connected_validation':report['layered_compile_requires_connected_validation'],'emitted_master_path':str(path.relative_to(a.ROOT)),
                           'emitted_master_sha256':a.sha(path),'compression':'gzip','uncompressed_json_bytes':raw_bytes,
                           'compressed_json_bytes':path.stat().st_size})
            print(key,record['status'],report['counts']['roof_tiles'],'tiles',path.stat().st_size,'bytes',flush=True)
        except a.UnsupportedSurface as error:
            record.update(error.report);print(key,record['reason'],record.get('details'),flush=True)
        records.append(record)
    summary={'assets':len(records),'placements':sum(r['instance_count'] for r in records),'supported_assets':sum(r['status']!='coverage_pending' for r in records),
             'pending_assets':sum(r['status']=='coverage_pending' for r in records),'master_compressed_bytes':used_bytes,
             'counts':dict(sum((Counter(r.get('counts',{})) for r in records),Counter())), 'full_compiles':0}
    result={'schema':'riverstone.house_detail.extension_catalog.v1','engine':VERSION,'engine_sha256':a.sha(__file__),
            'base_engine_sha256':a.sha(a.__file__),'index_path':str(index_path.relative_to(a.ROOT)),'index_sha256':a.sha(index_path),
            'extension_config_path':str((HERE/'extensions.v1.json').relative_to(a.ROOT)),'extension_config_sha256':a.sha(HERE/'extensions.v1.json'),
            'material_semantics_path':'world_city/concept_city_v3/near_detail_r01/city_upgrade/surface_mapping/material_surface_map.v1.json',
            'tile_sources':tile_hashes,'summary':summary,'assets':records}
    a.write(HERE/'generated/active_catalog.json',result);a.write(HERE/'generated/summary.json',summary)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--build',action='store_true');args=parser.parse_args()
    if args.build:print(json.dumps(build()['summary'],indent=2))
