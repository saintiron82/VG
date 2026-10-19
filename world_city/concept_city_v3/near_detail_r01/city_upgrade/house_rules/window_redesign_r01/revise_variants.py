"""Photo-informed window presets over the immutable first proportion revision.
Only common source grammar is emitted. No sampler, renderer or runtime mutation.
"""
import argparse,copy,json
from pathlib import Path
import revise_windows as base
from revise_windows import a,load,need,rect,set_box,is_window,save_gz
HERE=Path(__file__).resolve().parent

def revise_variant(source,near,r,variants,style,state,provenance):
    need(style in variants['styles'],'Unsupported window architecture style')
    preset=variants['styles'][style];canonical,candidate,windows,axes=base.revise(source,near,r,state,provenance)
    if preset['separate_recessed_casement']:
        for master in (canonical,candidate):
            need(all(slot in master['materials'] for slot in [preset['trim_material_slot'],preset['casement_material_slot']]),'Required material slot missing')
            components={c['id']:c for c in master['components']}
            for record in windows:
                c=components[record['component_id']];ops={o['id']:o for o in c['operations']};name=record['window_base'];lo,hi=rect(ops[record['aperture_operation_id']]);x0,y0=lo[:2];x1,y1=hi[:2];surface=rect(ops[r['selectors']['panel_id']])[1][2];w=preset['trim_width_m'];z0=surface+preset['trim_back_m'];z1=surface+preset['trim_front_m']
                trim={'_left':([x0-w,y0-w,z0],[x0,y1+w,z1]),'_right':([x1,y0-w,z0],[x1+w,y1+w,z1]),'_sill':([x0-w,y0-w,z0],[x1+w,y0,z1]),'_lintel':([x0-w,y1,z0],[x1+w,y1+w,z1])}
                for suffix,bounds in trim.items():set_box(ops[name+suffix],*bounds);ops[name+suffix]['material']=preset['trim_material_slot']
                w=preset['casement_width_m'];z0=surface+preset['casement_back_m'];z1=surface+preset['casement_front_m']
                case={'left':([x0,y0,z0],[x0+w,y1,z1]),'right':([x1-w,y0,z0],[x1,y1,z1]),'bottom':([x0,y0,z0],[x1,y0+w,z1]),'head':([x0,y1-w,z0],[x1,y1,z1])}
                for suffix,bounds in case.items():
                    ident=name+'__casement_'+suffix;need(ident not in ops,'Casement ID collision');op={'id':ident,'part':'windows','action':'paint','material':preset['casement_material_slot'],'shape':{'kind':'box'}};set_box(op,*bounds);c['operations'].append(op)
                set_box(ops[name+'_glass'],[x0,y0,surface-preset['glass_recess_m']-r['glass_thickness_m']],[x1,y1,surface-preset['glass_recess_m']])
                for suffix in ('__near_mullion','__near_transom'):
                    op=ops[name+suffix];blo,bhi=rect(op);blo=list(blo);bhi=list(bhi);blo[2]=surface+preset['casement_back_m'];bhi[2]=surface+preset['casement_front_m'];set_box(op,blo,bhi);op['material']=preset['casement_material_slot']
            master['revision']+=1
        # Plaster surround has no wood grain. Keep IDs while assigning the new
        # inner sash its own stable semantic ID and component-local grain axis.
        axes=[row for row in axes if not any(row['operation_id'].endswith(s) for s in ('_left','_right','_sill','_lintel'))]
        for record in windows:
            for suffix,axis in [('left',[0,1,0]),('right',[0,1,0]),('bottom',[1,0,0]),('head',[1,0,0])]:axes.append({'component_id':record['component_id'],'operation_id':record['window_base']+'__casement_'+suffix,'part_id':'windows','material':preset['casement_material_slot'],'role':'recessed_wood_casement','grain_axis_component_local':axis})
            record['new_outer_span_m']=[v+2*preset['trim_width_m'] for v in record['aperture_m']];record['new_visible_glass_ratio_with_near_cross']=max(0,record['new_clear_span_m'][0]-.05)*max(0,record['new_clear_span_m'][1]-.05)/(record['new_outer_span_m'][0]*record['new_outer_span_m'][1]) if state=='glazed_closed_shutters_open' else 0;record['glass_recess_m']=preset['glass_recess_m'];record['trim_width_m']=preset['trim_width_m']
    for master in (canonical,candidate):
        master['provenance']['window_architecture_variant']={'style':style,'state':state,'variants_sha256':a.core.digest(variants),'engine_sha256':a.sha(__file__),'proportion_adapter_sha256':a.sha(base.__file__),'visual_reference_inference':'Style direction only; no measurement scale is inferred from photographs.','runtime_activation':False}
        a.core.validate_master(master,.05)
    for cc,nc in zip(canonical['components'],candidate['components']):need({o['id']:o for o in cc['operations'] if is_window(o,r)}=={o['id']:o for o in nc['operations'] if is_window(o,r)},'Near/far variant identity differs')
    for record in windows:record['style_id']=style
    return canonical,candidate,windows,axes

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--asset',required=True);p.add_argument('--style',required=True);p.add_argument('--state',default='glazed_closed_shutters_open');p.add_argument('--output',type=Path,required=True);x=p.parse_args();r=load(HERE/'window_rules.v1.json');variants=load(HERE/'window_variants.v2.json');record=next(v for v in load(x.catalog)['assets'] if v['asset_key']==x.asset)
    for field,sha in [('source_master_path','source_sha256'),('emitted_master_path','emitted_master_sha256')]:need(a.sha(a.ROOT/record[field])==record[sha],'Input hash changed')
    provenance={'asset_key':x.asset,'original_source_path':record['source_master_path'],'original_source_sha256':record['source_sha256'],'previous_near_path':record['emitted_master_path'],'previous_near_sha256':record['emitted_master_sha256']}
    canonical,candidate,windows,axes=revise_variant(load(a.ROOT/record['source_master_path']),load(a.ROOT/record['emitted_master_path']),r,variants,x.style,x.state,provenance);out=x.output.resolve();out.mkdir(parents=True,exist_ok=True)
    files={'canonical':save_gz(out/(x.asset+'.canonical.master.json.gz'),canonical),'near':save_gz(out/(x.asset+'.near.master.json.gz'),candidate)}
    report={'schema':'riverstone.window_architecture_variant.candidate.v2','asset_key':x.asset,'style_id':x.style,'state':x.state,'status':'SOURCE_STRUCTURAL_PASS_RENDER_PENDING','inputs':provenance,'files':files,'window_count':len(windows),'windows':windows,'all_nonwindow_geometry_and_cuts_unchanged':True,'near_far_window_operation_identity':True,'compile_run':False,'runtime_activation':False}
    a.write(out/(x.asset+'.candidate.json'),report);a.write(out/(x.asset+'.grain_axes.json'),{'schema':'riverstone.window_grain_axes.v1','source_master_sha256':files['canonical']['sha256'],'authored_master_sha256':files['near']['sha256'],'operations':axes});print(json.dumps({'asset':x.asset,'style':x.style,'windows':len(windows),'files':files}))
