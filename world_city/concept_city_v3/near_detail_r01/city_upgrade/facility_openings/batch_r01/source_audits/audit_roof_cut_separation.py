"""Conservative analytic proof of assembly-cut disjointness from selected roofs.

AABB separation is sufficient to prove solid separation. Intersecting bounds
are inconclusive and fail closed; there is no voxel sampling or source edit.
"""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path.insert(0,str(B.parent))
import author as a

def audit(path,materials):
    m=a.load(path);roof=[]
    for c,i,o,t,bb in a.source_inventory(m):
        if o['action']=='paint' and o.get('material') in materials:
            roof.append({'component':c,'instance':i,'operation':o['id'],'operation_sha256':a.core.digest(o),'shape_kind':o['shape']['kind'],'world_transform':t,'world_bounds':{'min':bb[0],'max':bb[1]},'material':o['material']})
    cuts=[];pairs=[]
    for op in m.get('assembly_cuts',[]):
        bb=a.bounds(op['shape'],a.core.transform(op.get('transform')));cuts.append({'id':op['id'],'operation_sha256':a.core.digest(op),'shape':op['shape'],'world_transform':a.core.transform(op.get('transform')),'selector':op.get('selector',{}),'world_bounds':{'min':bb[0],'max':bb[1]}})
        for r in roof:
            rb=r['world_bounds'];gaps=[max(rb['min'][i]-bb[1][i],bb[0][i]-rb['max'][i]) for i in range(3)];axes=[i for i,g in enumerate(gaps) if g>1e-7];pairs.append({'cut':op['id'],'roof_operation':r['operation'],'strictly_separated_axes':axes,'signed_axis_gaps_m':gaps,'solid_intersection_impossible':bool(axes)})
    component_cuts=[{'component':c['id'],'operation':o['id'],'operation_sha256':a.core.digest(o)} for c in m['components'] for o in c['operations'] if o['action']=='cut'];allpass=bool(roof) and all(p['solid_intersection_impossible'] for p in pairs) and not component_cuts
    return {'schema':'riverstone.source_roof_cut_separation.v1','asset_key':m['id'],'source_master_path':str(path.relative_to(a.ROOT)),'source_master_sha256':a.sha(path),'selected_materials':materials,'roof_operations':roof,'assembly_cuts':cuts,'component_cuts':component_cuts,'pair_proofs':pairs,'all_pass':allpass,'source_shapes_modified':False,'compile_calls':0,'proof_method':'Conservative bounds from every original primitive and exact instance/operation transform. Strict separation on any world axis proves no possible solid overlap. AABB intersection or component cuts would fail closed rather than be waived.','scope':'Only the listed source master hash, selected original roof operations and current global cuts. This does not approve dropping arbitrary cuts from another source revision.','audit_implementation_sha256':a.sha(__file__),'reference_core_sha256':a.sha(a.core.__file__),'source_inventory_helper_sha256':a.sha(a.__file__)}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('master',type=Path);p.add_argument('--material',action='append',required=True);p.add_argument('--output',type=Path,required=True);q=p.parse_args();r=audit(q.master.resolve(),q.material);assert not q.output.exists();a.write(q.output,r);print(json.dumps({'all_pass':r['all_pass'],'roof_operations':len(r['roof_operations']),'assembly_cuts':len(r['assembly_cuts']),'pair_proofs':len(r['pair_proofs']),'output':str(q.output),'sha256':a.sha(q.output)}))
