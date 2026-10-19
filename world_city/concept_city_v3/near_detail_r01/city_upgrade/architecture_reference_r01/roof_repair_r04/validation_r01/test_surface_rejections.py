#!/usr/bin/env python3
"""Deterministic adversarial tests; only local in-memory fixtures are mutated."""
from validate_exterior import *
import copy,gc

class TwoCellOracle(BaselineOracle):
    def __init__(self):self.low=(0,0,0);self.high=(1,2,1)
    def values(self,x,y,z):
        x,y,z=np.broadcast_arrays(x,y,z)
        return np.where((x==0)&(y>=0)&(y<2)&(z==0),0,-1).astype(np.int16)

def surface_tests():
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
    return tests
