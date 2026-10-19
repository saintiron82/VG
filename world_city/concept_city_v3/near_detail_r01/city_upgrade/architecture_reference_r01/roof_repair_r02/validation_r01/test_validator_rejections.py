#!/usr/bin/env python3
"""Deterministic adversarial tests; only local in-memory fixtures are mutated."""
from validate_exterior import *
from validate_cells import CandidateOracle,prove_cells
import copy,gc

class TwoCellOracle(BaselineOracle):
    def __init__(self):self.low=(0,0,0);self.high=(1,2,1)
    def values(self,x,y,z):
        x,y,z=np.broadcast_arrays(x,y,z)
        return np.where((x==0)&(y>=0)&(y<2)&(z==0),0,-1).astype(np.int16)

def run():
    started=time.monotonic()
    # Explicit rectangular boundary of two neighboring cells. No mesher used.
    grid=[[[1,0,0],[1,2,0],[1,2,1],[1,0,1]],
          [[0,0,1],[0,2,1],[0,2,0],[0,0,0]],
          [[0,2,0],[0,2,1],[1,2,1],[1,2,0]],
          [[1,0,0],[1,0,1],[0,0,1],[0,0,0]],
          [[0,0,1],[1,0,1],[1,2,1],[0,2,1]],
          [[0,2,0],[1,2,0],[1,0,0],[0,0,0]]]
    quads=[[[n*PITCH for n in p] for p in q] for q in grid]
    source={'schema':'riverstone.voxel.render.v1','unit':'m','groups':[{'material':'a','quads':quads}],'quad_count':6}
    oracle=TwoCellOracle();_,order=adapter_order();ids={'a':0,'b':1}
    baseline=audit_render(source,oracle,ids,order,interface_y=1)
    assert baseline['outward_CCW_matches_actual_solid_exterior'] and baseline['expected_unit_faces']==10
    tests={}
    def rejected(name,mutate,want=None):
        bad=copy.deepcopy(source);mutate(bad)
        try:
            result=audit_render(bad,oracle,ids,order,interface_y=1)
            assert not result['outward_CCW_matches_actual_solid_exterior'],'Mutation was accepted'
            if want:assert result[want]>0,'Required diagnostic counter absent'
            tests[name]={'rejected':True,**{k:result[k] for k in ['same_direction_duplicate_unit_faces','missing_unit_faces','extraneous_unit_faces','wrong_material_unit_faces','artificial_interface_unit_faces']}}
        except AssertionError as e:
            if str(e) in ('Mutation was accepted','Required diagnostic counter absent'):raise
            tests[name]={'rejected':True,'reason':str(e)}
    def duplicate(d):d['groups'][0]['quads'].append(copy.deepcopy(d['groups'][0]['quads'][0]));d['quad_count']+=1
    def missing(d):d['groups'][0]['quads'].pop(0);d['quad_count']-=1
    def cap(d):d['groups'][0]['quads'].append([[0,PITCH,0],[0,PITCH,PITCH],[PITCH,PITCH,PITCH],[PITCH,PITCH,0]]);d['quad_count']+=1
    rejected('same_direction_duplicate_face',duplicate,'same_direction_duplicate_unit_faces')
    rejected('missing_surface',missing,'missing_unit_faces')
    rejected('outward_winding_reversed',lambda d:d['groups'][0]['quads'][0].reverse(),'extraneous_unit_faces')
    rejected('wrong_surface_material',lambda d:d['groups'][0].__setitem__('material','b'),'wrong_material_unit_faces')
    rejected('internal_interface_cap',cap,'artificial_interface_unit_faces')
    rejected('quad_off_lattice',lambda d:d['groups'][0]['quads'][0][0].__setitem__(0,PITCH/2))
    rejected('bowtie_quad',lambda d:d['groups'][0]['quads'][0].__setitem__(slice(1,3),[d['groups'][0]['quads'][0][2],d['groups'][0]['quads'][0][1]]))
    rejected('nonfinite_quad',lambda d:d['groups'][0]['quads'][0][0].__setitem__(0,float('nan')))
    rejected('unknown_material',lambda d:d['groups'][0].__setitem__('material','unknown'))
    try:audit_render(source,oracle,ids,[0,1,2,0,2,3],interface_y=1)
    except AssertionError as e:tests['godot_winding_not_reversed']={'rejected':True,'reason':str(e)}
    else:raise AssertionError('Incorrect Godot triangle order accepted')
    # Mutate the actual loaded candidate only in RAM, never its file.
    candidate=CandidateOracle(ARCH/'foundation_repair_r01/foundation_arrays.npz',R/'upper_union_arrays.npz')
    arr=np.load(R/'upper_union_arrays.npz');retained=arr['retained_baseline'];point=tuple(np.argwhere(retained[4:])[0]+np.array([4,0,0]))
    value=int(candidate.upper[point]);candidate.upper[point]=(value+1)%15
    try:prove_cells(candidate)
    except AssertionError as e:tests['actual_preserved_upper_material_mutation']={'rejected':True,'reason':str(e)}
    else:raise AssertionError('Preserved material mutation accepted')
    candidate.upper[point]=value
    # Outside the original X extent and outside the compiled roof (far padding).
    point=(4,0,0);assert candidate.upper[point]<0;candidate.upper[point]=15
    try:prove_cells(candidate)
    except AssertionError as e:tests['actual_unowned_upper_addition']={'rejected':True,'reason':str(e)}
    else:raise AssertionError('Unowned upper addition accepted')
    report={'schema':'riverstone.roof_repair.independent_adversarial_validation.v1','status':'PASS','positive_two_cell_fixture':baseline,'negative_tests':tests,'negative_tests_count':len(tests),'source_files_mutated':False,'sampling_calls':0,'mesher_calls':0,'address_space_limit_mib':256,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-started,'validator':ref(Path(__file__))}
    save(HERE/'adversarial_validation.json',report)
    print(json.dumps({'status':report['status'],'negative_tests_count':len(tests),'peak_rss_kib':report['peak_rss_kib'],'elapsed_seconds':report['elapsed_seconds']}))
if __name__=='__main__':run()
