"""Coordinate/ownership regressions without common compilation."""
import itertools,json,math,random,sys
from pathlib import Path
import native_grid as n
B=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime')]
from compile_source_contacts import ExactOutside as OldOutside

def run():
    tests={};rnd=random.Random(81123);g=n.Grids();points=[[rnd.uniform(-100,100) for _ in range(3)] for _ in range(1000)]+[[i/20,j/20,k/20] for i,j,k in itertools.product(range(-2,3),repeat=3)]
    tests['default_point_index_exact']=all(g.world_cell(p)==tuple(math.floor(v*2+1e-8) for v in p) and g.world_cell(p,True)==tuple(math.floor(v*20+1e-8) for v in p) for p in points)
    bounds=[{'min':[i,i-17,-i-31],'max':[i+17,i+23,-i+1]} for i in range(-100,101)]
    tests['default_bounds_exact']=all(g.native_bounds(b)=={'min':[math.floor(v/10)-1 for v in b['min']],'max':[math.ceil(v/10)+1 for v in b['max']]} for b in bounds)
    tests['default_contact_domain_exact']=all(g.contact_domain(p,[v+.17 for v in p])=={'min':[math.floor((v-.5)*2+1e-8)/2 for v in p],'max':[math.ceil((v+.17+.5)*2-1e-8)/2 for v in p]} for p in points)
    for pitch in [.5,.25,.2,.1,.05]:
        grid=n.Grids(pitch,.05,(-.1,.2,.3),(.05,-.05,.1));ok=True
        for bound in bounds:
            nb=grid.native_bounds(bound,0)
            for j in range(3):
                flo=grid.detail_origin[j]+bound['min'][j]*.05;fhi=grid.detail_origin[j]+bound['max'][j]*.05
                lo=grid.native_origin[j]+nb['min'][j]*pitch;hi=grid.native_origin[j]+nb['max'][j]*pitch
                ok &= lo<=flo+1e-8 and hi>=fhi-1e-8 and 0<=flo-lo+1e-8<pitch+1e-8 and 0<=hi-fhi+1e-8<pitch+1e-8
        tests[f'ratio_{grid.ratio}_negative_nonzero_origin_bounds']=ok
        c={'pitch':pitch,'grid_origin':[0,0,0],'cells':[[0,0,0,0,0,'stone']]};f={'pitch':.05,'grid_origin':[0,0,0],'cells':[[0,0,0,0,0,'timber']]};out=n.ExactOutside(f,c,{(5,0,0):'slate'},[{'min':[0,0,0],'max':[.05,.05,.05]}],['slate']);tests[f'ratio_{grid.ratio}_ownership_precedence']=out.sample([.025]*3)==(True,'timber',None) and out.sample([.275,.025,.025])==(True,'slate',None) and out.sample([-.025]*3)==(False,None,None)
    c={'pitch':.5,'grid_origin':[0,0,0],'cells':[[i,j,k,0,0,'stone'] for i,j,k in itertools.product(range(-2,3),repeat=3)]};f={'pitch':.05,'grid_origin':[0,0,0],'cells':[[i,j,k,0,0,'timber'] for i,j,k in itertools.product(range(-2,3),repeat=3)]};regions=[{'min':[-.1]*3,'max':[.15]*3}];a=OldOutside(f,c,{},regions,['slate']);b=n.ExactOutside(f,c,{},regions,['slate']);tests['default_outside_tuple_byte_equivalence']=all(json.dumps(a.sample(p),separators=(',',':'))==json.dumps(b.sample(p),separators=(',',':')) for p in points)
    for name,args in [('fractional_ratio',(.22,)),('too_fine_native',(.025,)),('invalid_origin',(.5,.05,(.01,0,0))),('zero_pitch',(0,)),('nan_pitch',(float('nan'),))]:
        try:n.Grids(*args);passed=False
        except AssertionError:passed=True
        tests['refuse_'+name]=passed
    assert all(tests.values()),tests
    return tests
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
