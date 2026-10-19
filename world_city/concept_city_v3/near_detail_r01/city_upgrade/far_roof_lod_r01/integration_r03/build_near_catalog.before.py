"""Register only actually compiled and verified near-house files, preserving source poses."""
from pathlib import Path
import gzip,hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CITY=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from voxel_character.common import core
def load(p):return json.loads(gzip.decompress(p.read_bytes()).decode() if p.suffix=='.gz' else p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def native_binding_equal(a,b):
    # Godot JSON decimal transport loses the last binary-float digits. Only
    # this cache selector permits <=1e-14 relative / 1e-15 absolute drift.
    # Geometry/proof file SHA and Godot runtime contract SHA remain exact.
    if isinstance(a,dict) and isinstance(b,dict):
        return a.keys()==b.keys() and all(native_binding_equal(a[k],b[k])for k in a)
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(native_binding_equal(x,y)for x,y in zip(a,b))
    if isinstance(a,(float,int)) and not isinstance(a,bool) and isinstance(b,(float,int)) and not isinstance(b,bool):
        return abs(a-b)<=max(1e-15,1e-14*max(abs(a),abs(b)))
    return a==b
def native_binding_inputs(entry):
    mapping={'source_render':'replacement_source_render_sha256','source_master':'source_master_sha256','fine_render':'sha256','replace_groups':'replace_source_groups','added_source_materials':'added_source_materials','composed_manifest':'composed_manifest_sha256','window_regions':'window_regions','surface_exclusion_regions':'surface_exclusion_regions','window_contract':'window_contract_sha256','shadow_proxy':'shadow_proxy_sha256'}
    lists={'replace_groups','added_source_materials','window_regions','surface_exclusion_regions'}
    result={name:entry.get(field,[] if name in lists else '')for name,field in mapping.items()}
    if 'visual_bounds' in entry:result.update(visual_bounds=entry['visual_bounds'],bounds_contract=entry.get('bounds_contract',{}))
    if entry.get('source_revision'):result.update(source_revision=entry['source_revision'],source_revision_sha256=entry['source_revision_sha256'])
    if entry.get('surface_source_render_path'):result.update(surface_source_render_sha256=entry['surface_source_render_sha256'])
    return result
def source_parts(source):
    components={c['id']:c for c in source['components']};instances={i['id']:i for i in source['instances']};transforms={}
    def tr(key):
        if key not in transforms:
            i=instances[key];value=core.transform(i.get('transform'))
            transforms[key]=core.compose(tr(i['parent']),value) if i.get('parent') else value
        return transforms[key]
    for i in source['instances']:
        for op in components[i['component']]['operations']:
            yield i,op,core.compose(tr(i['id']),core.transform(op.get('transform')))
def main():
    index_path=CITY/'playable_r01/generated/tile_r01/index.json';index=load(index_path)
    output=CITY/'playable_detail_r01/near_catalog.json';catalog=load(output)
    assert catalog['source_city_index_sha256']==sha(index_path)
    reports=[]
    # Ordinary full references remain preserved; exact exterior-equivalent layered
    # outputs supersede them only after their per-chunk checks actually pass.
    holds_path=HERE/'house_rules/compiled/provenance_holds.json'
    holds=load(holds_path).get('assets',{}) if holds_path.exists() else {}
    for held in holds:
        if holds[held].get('status')=='PENDING_NATIVE_REISSUE':catalog['assets'].pop(held,None)
    selected={}
    for candidate in sorted((HERE/'house_rules/compiled').glob('*.stats.json')):
        item=load(candidate)
        if item.get('status') not in (None,'pass','PASS','passed','PASS_STRUCTURAL_PENDING_VISUAL'):continue
        key=item['asset_key']
        if holds.get(key,{}).get('status')=='PENDING_NATIVE_REISSUE':continue
        if key not in selected or '.layered.' in candidate.name:selected[key]=candidate
    overrides_path=HERE/'house_rules/compiled/selection_overrides.json'
    if overrides_path.exists():
        for key,row in load(overrides_path).get('assets',{}).items():
            p=ROOT/row['stats_path'];q=ROOT/row['qa_path']
            assert sha(p)==row['stats_sha256'] and sha(q)==row['qa_sha256']
            selected[key]=p
    for key,stats_path in sorted(selected.items()):
        stats=load(stats_path);key=stats['asset_key']
        if key=='ordinary_r2_5ab0065a8cd6bf':
            # Approved r04 sample remains the visual reference; generic variant is separate QA.
            continue
        assert all(c['pass'] for c in stats['constraints'])
        if '.layered.' in stats_path.name:
            assert stats['all_chunks_exact_exterior_face_match'] and stats['all_chunks_overlap_free']
            assert stats['core_visible_faces']==0 and not stats['geometry_fallback']
        render=ROOT/stats['files']['.render.json']['path'];data=load(render)
        assert sha(render)==stats['files']['.render.json']['sha256']
        source_path=ROOT/index['common_assets'][key]['master_path'];source=load(source_path)
        assert sha(source_path)==index['common_assets'][key]['master_sha256']
        roofs=[];doors=[]
        for instance,op,tr in source_parts(source):
            if op['action']!='paint':continue
            shape=op['shape'];local={'basis':tr['basis'],'translation':tr['translation']}
            if op.get('part')=='door' and 'closed_door_leaf' in op['id']:
                assert shape['kind']=='box'
                doors.append({'id':instance['id']+'/'+op['id'],'type':'box','min':shape['min'],'max':shape['max'],'transform':local,'reason':'Exact already-closed authored leaf; no new interior or automatic stair'})
            semantic_roof=(instance.get('component')=='roof' and op['id'].startswith('slope_'))
            if (op['id'].startswith('roof_plane') or semantic_roof) and shape['kind']=='extrusion':
                if semantic_roof:
                    from facility_roofs.author_facility_roofs import instance_transforms
                    from build_source_roof_shadow_proxy import prove_unaffected_roof_operation
                    component=next(c for c in source['components']if c['id']==instance['component'])
                    prove_unaffected_roof_operation(source,component,op,instance_transforms(source))
                assert len(shape['polygon'])==4
                roofs.append({'polygon':shape['polygon'],'z_min':shape['z_min'],'z_max':shape['z_max'],'transform':local})
        assert roofs and doors
        proxy_path=HERE/'shadow_proxies'/(key+'.json');write(proxy_path,{'schema':'riverstone.source_roof_shadow_proxy.v1','asset':key,'source_master_sha256':sha(source_path),'extrusions':roofs,'visible_geometry':False,'purpose':'Smooth source underlay casts only; fine visible tiles receive shadow without self-shadow striping'})
        previous_entry=catalog['assets'].get(key,{})
        catalog['assets'][key]={'render_path':str(render.relative_to(ROOT)),'sha256':sha(render),'source_master_sha256':sha(source_path),'geometry_estimated_bytes':data['quad_count']*144,'status':'common_compiled_candidate_pending_actual_city_visual_and_entry_tests','shadow_proxy_path':str(proxy_path.relative_to(ROOT)),'shadow_proxy_sha256':sha(proxy_path),'collision_repairs':doors,'stats_path':str(stats_path.relative_to(ROOT)),'stats_sha256':sha(stats_path),'visible_pitch_m':.05,'hidden_core_pitch_m':.1 if '.layered.' in stats_path.name else .05}
        if previous_entry.get('sha256')==catalog['assets'][key]['sha256'] and previous_entry.get('source_master_sha256')==catalog['assets'][key]['source_master_sha256']:
            for field,value in previous_entry.items():
                if field.startswith('far_visual_') or field.startswith('far_union_'):catalog['assets'][key][field]=value
        reports.append({'asset':key,'quads':data['quad_count'],'source_roof_planes':len(roofs),'exact_closed_doors':len(doors)})
    for native_path in sorted((CITY/'playable_detail_r01/generated').glob('native_near_r*/manifest.json')):
        native=load(native_path)
        if not native.get('all_pass') or native['source_city_index_sha256']!=catalog['source_city_index_sha256']:continue
        for key,row in native['assets'].items():
            if key not in catalog['assets'] or catalog['assets'][key]['sha256']!=row['source_render_sha256']:continue
            # Fine-render identity alone misses a changed shadow/composition source.
            # Legacy transport is retained on disk, but not promoted by this selector.
            if not native_binding_equal(row.get('binding_inputs'),native_binding_inputs(catalog['assets'][key])):continue
            path=CITY/'playable_detail_r01'/row['native_scene_path'].removeprefix('res://')
            assert row['exact_reload_pass'] and sha(path)==row['native_scene_sha256']
            catalog['assets'][key].update(native_scene_path=str(path.relative_to(ROOT)),native_scene_sha256=sha(path))
    write(output,catalog);write(HERE/'catalog_build_report.json',{'new_compiled_assets':reports,'catalog_assets':len(catalog['assets']),'whole_city_upgrade_complete':False})
    print(json.dumps(reports))
if __name__=='__main__':main()
