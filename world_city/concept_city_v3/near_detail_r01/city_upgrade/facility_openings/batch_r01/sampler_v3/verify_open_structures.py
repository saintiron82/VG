"""Independent actual-mesh probes through original open component cuts.

No new aperture is inferred: each ray lies inside an original cut primitive,
passes the original retained render, and must pass the emitted composition.
"""
import argparse,hashlib,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime'),str(B/'sampler_v2')]
import author as a
import stream_render as sr
import reserved_io_r03 as rio

def hits(q,probe):
    axis,t,p,sign,r=a.quad_info(q)
    return axis==probe['axis'] and probe['interval_m'][0]-1e-8<=p<=probe['interval_m'][1]+1e-8 and r[0]-1e-8<=probe['point_m'][t[0]]<r[2]-1e-8 and r[1]-1e-8<=probe['point_m'][t[1]]<r[3]-1e-8

def main(catalog,render_path):
    start=time.monotonic();cat=a.load(catalog);w=rio.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');contract=a.load(a.ROOT/cat['window_contract_path']);assert not contract['patches'];source=a.load(a.ROOT/cat['source_master_path']);original=a.load(a.ROOT/cat['source_render_path']);assert a.sha(a.ROOT/cat['source_master_path'])==cat['source_sha256'];assert a.sha(a.ROOT/cat['source_render_path'])==cat['source_render_sha256'];probes=[]
    for cid,iid,op,t,bb in a.source_inventory(source):
        if op['action']!='cut':continue
        sh=a.core.prepare_shape(op['shape'],.05);lo,hi=a.core.shape_bounds(sh);axis=max(range(3),key=lambda j:abs(t['basis'][j][2]));assert abs(abs(t['basis'][axis][2])-1)<1e-10
        for fu in [.25,.5,.75]:
            for fv in [.25,.5,.75]:
                local=[lo[0]+(hi[0]-lo[0])*fu,lo[1]+(hi[1]-lo[1])*fv,(lo[2]+hi[2])/2];assert a.core.contains(sh,local)
                point=a.core.apply(t,local);interval=sorted([a.core.apply(t,[local[0],local[1],z])[axis] for z in [lo[2],hi[2]]]);probe={'id':iid+':'+op['id']+':'+str(fu)+':'+str(fv),'component':cid,'instance':iid,'operation':op['id'],'operation_sha256':a.core.digest(op),'axis':axis,'point_m':point,'interval_m':interval,'original_cut_contains_probe':True};count=sum(hits(q,probe) for g in original['groups'] for q in g['quads']);probe['original_render_crossing_faces']=count;assert count==0,probe;probes.append(probe)
    assert probes,'Open structure QA needs actual original component-cut passage witnesses'
    ref={'source_master':{'path':cat['source_master_path'],'sha256':cat['source_sha256']},'source_render':{'path':cat['source_render_path'],'sha256':cat['source_render_sha256']},'canonical_master':{'path':cat['canonical_master_path'],'sha256':cat['canonical_master_sha256']},'replacement_contract':{'path':cat['window_contract_path'],'sha256':cat['window_contract_sha256']},'driver':{'path':str(Path(__file__).relative_to(a.ROOT)),'sha256':a.sha(__file__)}}
    witness={'schema':'riverstone.facility.open_structure_passage_witnesses.v1','asset_key':cat['asset_key'],'source_references':ref,'window_count':0,'probes':probes,'scope':'Finite orthographic rays inside original component-cut passages; no whole-area or global-room claim.'};wp=B/'polygon_sources/emitted_qa'/(cat['asset_key']+'.open_source_witnesses.json');w.write(wp,witness)
    crossings=[0]*len(probes);digest=hashlib.sha256();count=0
    for material,q in sr.iter_quads(render_path):
        count+=1;digest.update(json.dumps([material,q],separators=(',',':')).encode())
        for i,probe in enumerate(probes):crossings[i]+=hits(q,probe)
    failures=[{'id':p['id'],'crossing_faces':n} for p,n in zip(probes,crossings) if n];report={'schema':'riverstone.facility.open_structure_emitted_geometry_qa.v1','asset_key':cat['asset_key'],'render_path':str(render_path.relative_to(a.ROOT)),'render_sha256':a.sha(render_path),'quad_count':count,'ordered_material_quad_digest':digest.hexdigest(),'source_witness_reference':{'path':str(wp.relative_to(a.ROOT)),'sha256':a.sha(wp)},'reserved_driver_reference':ref['driver'],'window_count':0,'entry_passage_ray_count':len(probes),'failure_count':len(failures),'failures':failures,'all_pass':not failures,'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};w.write(B/'polygon_sources/emitted_qa'/(cat['asset_key']+'.emitted_geometry_qa.json'),report);w.close();print(json.dumps(report),flush=True);assert report['all_pass']
if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024));p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('render',type=Path);q=p.parse_args();main(q.catalog.resolve(),q.render.resolve())
