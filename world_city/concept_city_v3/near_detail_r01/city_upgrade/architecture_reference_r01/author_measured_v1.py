"""Data-driven measured Assembly dispatch, without a new voxel engine.

Every metric argument is a measurement reference. A perspective plan or blank
grid cannot emit a production master. The parent owns six-view image review.
"""
import copy,gzip,hashlib,json,sys
from pathlib import Path
from parts_v1 import AssemblyKit,ROOT,need
from measurements_v1 import validate_measurements,resolve_dimensions,verify_ref
from validate_assembly_v1 import validate
ALLOWED={'solid_box','plank','perforated_board','brace','wall','window','open_doorway','roof_gable','gallery_deck','extruded_unit'}
PIXEL_REQUIRED={'wall':{'width','height'},'window':{'width','height','center_x','bottom_y'},'open_doorway':{'width','height','center_x','bottom_y'},'roof_gable':{'width','eave_y','ridge_y'}}


def build_source(recipe,measurement,repo_root=ROOT):
    proof=validate_measurements(measurement,repo_root,require_review=True)
    need(measurement.get('purpose')=='production_measurements','Synthetic test measurements cannot author production source')
    need(recipe.get('schema')=='riverstone.architecture.measured_recipe.v1','Explicit measured recipe required')
    need(recipe.get('measurement_data_sha256')==hashlib.sha256(json.dumps(measurement,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),'Recipe measurement identity differs')
    palette=measurement.get('material_palette');need(isinstance(palette,dict) and palette,'Measured material palette required')
    for name,value in palette.items():need(isinstance(name,str) and isinstance(value,str) and len(value)==6 and all(c in '0123456789abcdefABCDEF' for c in value),'Palette must use explicit finite RGB hex values')
    families=measurement.get('material_families');need(isinstance(families,dict) and families,'Measured limited material families required')
    for family,row in families.items():
        need(isinstance(row,dict) and 1<=len(row.get('slots',[]))<=3 and set(row['slots'])<=palette.keys(),'Family tone contract invalid')
        need(row.get('pixel_samples_reference'),'Color family requires actual image sample evidence');verify_ref(Path(repo_root),row['pixel_samples_reference'])
    kit=AssemblyKit(recipe['asset_id'],palette,recipe['unit_seed']);walls={};bindings=[]
    for part in recipe.get('parts',[]):
        method=part.get('method');need(method in ALLOWED,'Unknown part method')
        need(part.get('feature_id'),'Part must identify a reviewed physical image/semantic feature')
        args=copy.deepcopy(part.get('static',{}));geometry=part.get('geometry',{})
        need('ident' in args and isinstance(args['ident'],str),'Stable part ID required')
        # Static fields are identifiers/enums/material slots only. Numeric static
        # values would silently bypass the measured boundary contract.
        allowed_static={'ident','material','role','style','state','side','family','slots'}
        need(set(args)<=allowed_static,'Only identifiers and enums may bypass dimension references')
        need(all(isinstance(v,str) or (k=='slots' and isinstance(v,list) and all(isinstance(x,str) for x in v)) for k,v in args.items()),'Unmeasured static geometry rejected')
        for name,value in geometry.items():args[name]=resolve_dimensions(value,proof,'pixel_measurement' if name in PIXEL_REQUIRED.get(method,set()) else None)
        need(PIXEL_REQUIRED.get(method,set())<=geometry.keys(),'Required measured boundaries absent')
        if method in ('window','open_doorway'):
            owner=part.get('wall_id');need(owner in walls,'Opening must reference an earlier measured wall');args['wall']=walls[owner]
        result=getattr(kit,method)(**args)
        if method=='wall':walls[args['ident']]=result
        bindings.append({'part_id':args['ident'],'feature_id':part['feature_id'],'method':method,'geometry_references':copy.deepcopy(geometry)})
    need(kit.components,'No source parts')
    contract=copy.deepcopy(recipe['validation_contract'])
    def metric_tree(obj):
        if isinstance(obj,dict):
            if set(obj)=={'measurement'}:return resolve_dimensions(obj,proof)
            return {k:metric_tree(v) for k,v in obj.items()}
        if isinstance(obj,list):return [metric_tree(x) for x in obj]
        need(not isinstance(obj,(int,float)),'Validation metrics also require explicit references');return obj
    contract=metric_tree(contract);master=kit.master();validation=validate(master,contract);need(validation['all_pass'],'Source envelope/route/support validation failed')
    master['provenance'].update({'measurement_review_pending':False,'measurement_data_sha256':recipe['measurement_data_sha256'],'measurement_sources':proof['source_references'],'measured_part_bindings':bindings,'unit_seed':recipe['unit_seed'],'not_visual_approval':True})
    master['metadata'].update({'measurement_status':'REVIEWED_INPUT_SOURCE_RECONSTRUCTION_CANDIDATE','envelope':contract['envelope'],'sampling_not_run':True,'global_voxel_connectivity_pending':True})
    bom={'schema':'riverstone.architecture.parts_and_connections.v1','asset_key':master['id'],'units':kit.units,'openings':kit.openings,'part_bindings':bindings,'reservations':contract.get('reservations',[]),'support_connections':contract.get('support_connections',[]),'source_only':True}
    return master,bom,validation,{'schema':'riverstone.window_grain_axes.v1','operations':kit.grain_axes}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path,required=True);p.add_argument('--measurements',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);q=p.parse_args()
    # No automatic fallbacks, implicit overrides or blanket mass resizing.
    result=build_source(json.loads(q.recipe.read_text()),json.loads(q.measurements.read_text()));out=q.output_dir.resolve();need(out.is_relative_to(Path(__file__).resolve().parent),'Authoring output outside owned folder')
    need(not out.exists(),'Immutable new output directory required');out.mkdir(parents=True)
    master,bom,validation,axes=result;data=json.dumps(master,separators=(',',':'),allow_nan=False).encode();need(len(data)<=2_000_000,'Compact source cap exceeded; review before increasing')
    target=out/(master['id']+'.master.json.gz');target.write_bytes(gzip.compress(data,mtime=0));axes['authored_master_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    for name,value in [('parts.json',bom),('source_validation.json',validation),('grain_axes.json',axes)]: (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'master':str(target.relative_to(ROOT)),'sha256':axes['authored_master_sha256'],'all_pass':True,'sampled':False}))
