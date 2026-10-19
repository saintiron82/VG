"""JSON-driven, stable whole-tile material aliases; no shape or sampling changes."""
import collections,copy,hashlib,json,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B/'sampler_v2'),str(B.parent.parent/'house_rules')]
import author as a
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook

def reference(path):return {'path':str(Path(path).resolve().relative_to(a.ROOT)),'sha256':a.sha(path)}
def rgb_scale(rgb,m):
    out=[]
    for i in range(0,6,2):
        s=int(rgb[i:i+2],16)/255;l=s/12.92 if s<=.04045 else ((s+.055)/1.055)**2.4;l=min(1,max(0,l*m));s=l*12.92 if l<=.0031308 else 1.055*l**(1/2.4)-.055;out.append(round(s*255))
    return ''.join(f'{v:02x}' for v in out)
def material_selectors(obj):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if k in ['selector','a','b'] and isinstance(v,dict) and 'material' in v:yield v
            yield from material_selectors(v)
    elif isinstance(obj,list):
        for v in obj:yield from material_selectors(v)
def normalized(master,old,changes):
    result=copy.deepcopy(master);result['materials']=copy.deepcopy(old['materials']);ops={(c['id'],o['id']):o for c in result['components'] for o in c['operations']}
    for r in changes:ops[r['component'],r['operation']]['material']=r['before']
    return result

def run(config_path):
    config=a.load(config_path);key=config['asset_key'];oldcat=a.load(a.ROOT/config['canonical_catalog_path']);row=next(r for r in oldcat['assets'] if r['asset_key']==key);oldproof=a.load(a.ROOT/row['composition_proof_path']);roof=a.load(a.ROOT/row['roof_master_path']);canonical=a.load(a.ROOT/row['emitted_master_path']);source=a.load(a.ROOT/row['source_master_path']);assert not list(material_selectors(source)) and not list(material_selectors(canonical)) and not list(material_selectors(roof))
    for field,sha in [('roof_master_path','roof_master_sha256'),('emitted_master_path','emitted_master_sha256'),('source_master_path','source_sha256'),('composition_proof_path','composition_proof_sha256')]:assert a.sha(a.ROOT/row[field])==row[sha]
    refs=[reference(config_path),reference(__file__),reference(a.ROOT/config['canonical_catalog_path'])]+[reference(a.ROOT/row[f]) for f in ['roof_master_path','emitted_master_path','source_master_path','composition_proof_path','replacement_contract_path']];identity={'asset_key':key,'source_references':refs};cfg=a.load(B.parent.parent/'house_rules/shared_output_budget.v2.json');book=ReservationBook(a.ROOT/cfg['book_path'],a.ROOT,[a.ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);rk='facility_material_authoring:r02:'+key;scopes=[{'directory':str((HERE/'generated').relative_to(a.ROOT)),'prefix':''}];book.reserve(rk,scopes,1000000,identity);book.acquire_writer(rk);w=rio.ReservedWriter(book,rk,B,scopes,a.ROOT)
    nr=copy.deepcopy(roof);nc=copy.deepcopy(canonical);changes=[];canonical_changes=[];counts=collections.Counter();canonical_ops={(c['id'],o['id']):o for c in nc['components'] for o in c['operations']};binding={(b['roof_component'],o['roof_operation']):(b['source_component'],o['canonical_operation']) for b in oldproof['bindings'] for o in b['operation_bindings']};aliases=config['material_role_aliases']
    for master in [nr,nc]:
        for alias in aliases:assert alias['material_id'] not in master['materials'];master['materials'][alias['material_id']]=rgb_scale(master['materials'][alias['base_material_id']],alias['luminance_multiplier'])
    for component in nr['components']:
        for op in component['operations']:
            oid=op['id'];role='tile' if '_tile_' in oid else 'underlay' if 'underlay' in oid else None
            if role is None:continue
            assert op['action']=='paint' and op['material']==config['base_tile_material']
            if role=='tile':
                seed=hashlib.sha256((row['source_sha256']+'|'+component['id']+'|'+oid).encode()).hexdigest();bucket=int(seed[:16],16)%100;new=next(r['material_id'] for r in config['tile_tones'] if bucket<r['upper_percentile'])
            else:seed=None;new=config['underlay_material']
            before=op['material'];op['material']=new;cid,coid=binding[component['id'],oid];cop=canonical_ops[cid,coid];assert cop['material']==before;cop['material']=new;changes.append({'component':component['id'],'operation':oid,'before':before,'after':new,'role':role,'stable_sha256':seed});canonical_changes.append({'component':cid,'operation':coid,'before':before,'after':new,'role':role});counts[role,new]+=1
    assert len({r['stable_sha256'] for r in changes if r['role']=='tile'})==sum(r['role']=='tile' for r in changes)
    assert normalized(nr,roof,changes)==roof and normalized(nc,canonical,canonical_changes)==canonical
    for master in [nr,nc]:a.core.validate_master(master,.05)
    out=HERE/'generated';rp=out/(key+'.roof.material.master.json.gz');cp=out/(key+'.canonical.material.master.json.gz');w.write(rp,nr);w.write(cp,nc)
    revision={'schema':'riverstone.roof.material_revision.v1','asset_key':key,'change_kind':'stable_tile_material_aliases','original_master_path':row['source_master_path'],'original_master_sha256':row['source_sha256'],'base_roof':reference(a.ROOT/row['roof_master_path']),'revised_roof':reference(rp),'base_canonical':reference(a.ROOT/row['emitted_master_path']),'revised_canonical':reference(cp),'source_references':refs,'material_role_aliases':aliases,'underlay_base_material_id':config['underlay_material'],'roof_operation_changes':changes,'canonical_operation_changes':canonical_changes,'changed_operations':len(changes),'counts':[{'role':role,'material':mat,'count':n} for (role,mat),n in counts.items()],'tests':{'exact_roof_unchanged_after_material_restore':True,'exact_canonical_unchanged_after_material_restore':True,'all_shapes_transforms_operation_order_cuts_instances_constraints_unchanged':True,'source_material_selectors_absent':True,'original_palette_entries_byte_identical':True,'whole_tile_seed_no_cell_randomness':True},'all_pass':True,'original_index_unchanged':True,'collision_reference_changed':False,'occupancy_and_exterior_face_equality':'Analytic operation equivalence proven here; original/new actual full-roof and bounded-ROI equality still required after compile.','runtime_alias_resolution':'Resolve base_material_id using original source palette then current placement palette override. Convert sRGB to linear, multiply RGB by luminance_multiplier, convert back to sRGB. Underlay uses existing slate_dark directly.','visual_acceptance':'PENDING identical-camera real-city A/B. No propagation until parent review.'};revp=out/'material_revision.json';w.write(revp,revision)
    proof=copy.deepcopy(oldproof);proof.update(canonical_master_sha256=a.sha(cp),roof_master_path=str(rp.relative_to(a.ROOT)),roof_master_sha256=a.sha(rp),material_revision_path=str(revp.relative_to(a.ROOT)),material_revision_sha256=a.sha(revp),base_composition_proof=reference(a.ROOT/row['composition_proof_path']))
    rops={(c['id'],o['id']):o for c in nr['components'] for o in c['operations']}
    for binding in proof['bindings']:
        for op in binding['operation_bindings']:op['source_roof_operation_sha256']=a.core.digest(rops[binding['roof_component'],op['roof_operation']]);op['canonical_operation_sha256']=a.core.digest(canonical_ops[binding['source_component'],op['canonical_operation']])
    pp=out/(key+'.composition_proof.json.gz');w.write(pp,proof);contract=a.load(a.ROOT/row['replacement_contract_path']);contract.update(authored_master_path=str(cp.relative_to(a.ROOT)),authored_master_sha256=a.sha(cp),material_revision_path=str(revp.relative_to(a.ROOT)),material_revision_sha256=a.sha(revp));contract['roof_composition'].update(canonical_master_path=str(cp.relative_to(a.ROOT)),canonical_master_sha256=a.sha(cp),composition_proof_path=str(pp.relative_to(a.ROOT)),composition_proof_sha256=a.sha(pp),roof_master_path=str(rp.relative_to(a.ROOT)),roof_master_sha256=a.sha(rp));wp=out/(key+'.replacement.json.gz');w.write(wp,contract)
    newrow=copy.deepcopy(row);newrow.update(emitted_master_path=str(cp.relative_to(a.ROOT)),emitted_master_sha256=a.sha(cp),roof_master_path=str(rp.relative_to(a.ROOT)),roof_master_sha256=a.sha(rp),composition_proof_path=str(pp.relative_to(a.ROOT)),composition_proof_sha256=a.sha(pp),replacement_contract_path=str(wp.relative_to(a.ROOT)),replacement_contract_sha256=a.sha(wp));cc=out/'canonical_catalog.json';w.write(cc,{'schema':oldcat['schema'],'assets':[newrow],'material_revision':reference(revp)})
    plan=a.load(a.ROOT/config['base_contact_plan_path']);plan.update(canonical_catalog_path=str(cc.relative_to(a.ROOT)),canonical_catalog_sha256=a.sha(cc),canonical_master_path=str(cp.relative_to(a.ROOT)),canonical_master_sha256=a.sha(cp),roof_master_path=str(rp.relative_to(a.ROOT)),roof_master_sha256=a.sha(rp),window_contract_path=str(wp.relative_to(a.ROOT)),window_contract_sha256=a.sha(wp),source_native_pitch_m=.5,grid_origin_m=[0,0,0],material_revision=reference(revp));w.write(out/(key+'.plan.json'),plan)
    roofrow={'asset_key':key,'native_asset_key':key,'source_master_path':row['source_master_path'],'source_sha256':row['source_sha256'],'emitted_master_path':str(rp.relative_to(a.ROOT)),'emitted_master_sha256':a.sha(rp),'source_render_path':contract['source_render_path'],'source_render_sha256':contract['source_render_sha256'],'source_only':True,'canonical_common_master':True,'material_revision':reference(revp)};w.write(out/'roof_compile_catalog.json',{'schema':'riverstone.facility_roof.layered_compile_catalog.v1','assets':[roofrow]});book.release(rk,identity,'One original header material-only source and canonical revision prepared; all geometry remains exactly equal.');w.close();print(json.dumps({'asset_key':key,'roof_catalog':str((out/'roof_compile_catalog.json').relative_to(a.ROOT)),'roof_master_sha256':a.sha(rp),'canonical_sha256':a.sha(cp),'revision_path':str(revp.relative_to(a.ROOT)),'revision_sha256':a.sha(revp),'counts':revision['counts']}),flush=True)
if __name__=='__main__':run(Path(sys.argv[1]).resolve())
