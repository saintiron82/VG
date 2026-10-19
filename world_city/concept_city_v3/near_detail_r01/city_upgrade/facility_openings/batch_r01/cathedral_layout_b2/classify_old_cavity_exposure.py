"""Classify old-cavity witnesses as external surfaces or hidden solid joins.

Use unchanged common source predicates and exact canonical layering. No voxel
compile, shape cropping, or render modification occurs.
"""
import math
from pathlib import Path
import test_revision as t
HERE=Path(__file__).resolve().parent

def run():
    canonical=HERE/'canonical.b2.authored.master.json.gz';contract=t.a.load(HERE/'replacement.b2.json.gz');point,stats=t.evaluator(t.a.load(canonical),{'min':[-18,4,-27],'max':[18,13.5,18]});rows=[]
    for w in contract['relocated_windows']:
        tr=w['old_transform'];side=tr['basis'][0][2];assert abs(side)==1
        for x in (-.6,.6):
            q=t.core.apply(tr,[x,8,0]);q[1]=(math.floor(q[1]/.05)+.5)*.05;q[2]=(math.floor(q[2]/.05)+.5)*.05;plane=round(q[0]/.05)*.05;inside=list(q);outside=list(q);inside[0]=plane-side*.025;outside[0]=plane+side*.025;li=point(inside);lo=point(outside)
            rows.append({'patch_id':w['patch_id'],'local_x_m':x,'sample_yz_m':q[1:],'expected_wall_plane_x_m':plane,'inside_point':inside,'outside_point':outside,'inside_label':li,'outside_label':lo,'surface_exposed':bool(li and not lo),'hidden_solid_continuation':bool(li and lo)})
    assert all(x['inside_label'] for x in rows)
    data={'schema':'riverstone.revision.old_cavity_exposure.v1','canonical_master_sha256':t.a.sha(canonical),'predicate_implementation_path':str((HERE/'test_revision.py').relative_to(t.a.ROOT)),'predicate_implementation_sha256':t.a.sha(HERE/'test_revision.py'),'classification_implementation_path':str(Path(__file__).resolve().relative_to(t.a.ROOT)),'classification_implementation_sha256':t.a.sha(__file__),'witnesses':rows,'exposed_count':sum(x['surface_exposed'] for x in rows),'hidden_count':sum(x['hidden_solid_continuation'] for x in rows),'prepared_operations':stats,'source_compile_calls':0,'meaning':'If both neighboring source cells are occupied, there is no exterior face at the restored former window plane. An emitted solid ray interval, not a fake internal quad, must represent that restoration.'};t.a.write(HERE/'old_cavity_exposure.json',data);print({k:data[k] for k in ['exposed_count','hidden_count','source_compile_calls']})
if __name__=='__main__':run()
