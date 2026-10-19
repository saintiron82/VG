import itertools,json,sys,resource
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from sparse_ray_cache import SparseRayCache,a
import seam_adapter as seam
sys.path.insert(0,str(a.ROOT/'voxel_character/tools'))
import mesh

def run():
    fixtures=[[(x,y,z,'stone') for x,y,z in itertools.product(range(-3,3),range(-2,3),range(-3,3))],[(x,y,z,'stone' if x<0 else 'timber') for x,y,z in itertools.product(range(-3,3),range(-2,3),range(-3,3)) if not(x==0 and y==0 and z==0)],[(x,y,z,'stone') for x,y,z in itertools.product(range(-3,3),range(-2,3),range(-3,3)) if y!=0 or z!=0]]
    regions=[{'min':[-.3,-.3,-.3],'max':[.3,.3,.3]}];tests=[]
    for n,cells in enumerate(fixtures):
        groups={}
        for q,m in mesh.greedy_faces(cells):groups.setdefault(m,[]).append([[v*.05 for v in p] for p in q])
        render={'pitch':.05,'grid_origin':[0,0,0],'groups':[{'material':m,'quads':qs} for m,qs in groups.items()]};base=seam.CacheOccupancy(render);factory=lambda:((gi,qi,g['material'],q) for gi,g in enumerate(render['groups']) for qi,q in enumerate(g['quads']));count=0
        for axis in range(3):
            sparse=SparseRayCache(None,regions,axis=axis,factory=factory)
            for point in itertools.product(*([[-.225,-.175,-.125,-.075,-.025,.025,.075,.125,.175,.225]]*3)):
                assert sparse.sample(point)[0]==base.sample(point)[0];count+=1
        tests.append({'fixture':n,'occupancy_comparisons':count,'pass':True})
    # Open or inward-wound source surfaces are never silently treated as empty.
    q=a.rect_quad([-.1,-.1,.1,.1],0,[1,2],.1,1)
    bad=SparseRayCache(None,regions,factory=lambda:iter([(0,0,'stone',q)]));rejected=False
    try:bad.sample([0,.025,.025])
    except AssertionError:rejected=True
    assert rejected
    result={'schema':'riverstone.sparse_retained_cache.tests.v1','fixtures':tests,'open_surface_rejected':True,'negative_coordinates_tested':True,'all_three_ray_axes':True,'source_voxel_compile_calls':0,'reader_sha256':a.sha(HERE/'sparse_ray_cache.py'),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};a.write(HERE/'unit_tests.json',result);print(result)
if __name__=='__main__':run()
