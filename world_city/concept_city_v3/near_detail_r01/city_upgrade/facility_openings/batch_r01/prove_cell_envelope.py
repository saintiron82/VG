"""Separate analytic operands from exact cell-centre voxel boundary corners.

Only cells incident to actually emitted faces beyond the analytic AABB are
replayed, directly from both the original and canonical unpruned sources.
"""
import argparse,math,resource,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE.parent/'composed_runtime')]
import author as a
import stream_render as sr
P=.05

def outside(v,b):return any(v[j]<b['min'][j]-1e-6 or v[j]>b['max'][j]+1e-6 for j in range(3))
def run(key):
    out=HERE/'composed'/key;pre=a.load(out/'preflight.json');render=a.ROOT/pre['render_path'];assert a.sha(render)==pre['render_sha256'];cat=a.load(HERE/'compiled'/key/'catalog.json');canonical=a.load(a.ROOT/cat['canonical_master_path']);original=a.load(a.ROOT/cat['source_master_path']);coarse=a.load(a.ROOT/cat['source_render_path']);origin=canonical['grid_origin'];assert origin==[0,0,0]
    boxes=[bb for c,i,o,t,bb in a.source_inventory(canonical) if o['action']=='paint'];analytic={'min':[min(b[0][j] for b in boxes) for j in range(3)],'max':[max(b[1][j] for b in boxes) for j in range(3)]}
    # Tight AABB enclosure of grid cells whose centres may lie inside analytic
    # bounds, with inclusive analytic endpoints conservatively admitted.
    envelope={'min':[(math.ceil(analytic['min'][j]/P-.5-1e-8))*P for j in range(3)],'max':[(math.floor(analytic['max'][j]/P-.5+1e-8)+1)*P for j in range(3)]}
    excess=[max(0,analytic['min'][j]-envelope['min'][j],envelope['max'][j]-analytic['max'][j]) for j in range(3)];assert max(excess)<=P/2+1e-6
    raw_out=grid_out=coarse_out=vertices=0;cells=set();faces=0;max_actual=[0.,0.,0.]
    for material,q in sr.iter_quads(render):
        vertices+=4;raw_out+=sum(outside(v,analytic) for v in q);grid_out+=sum(outside(v,envelope) for v in q);coarse_out+=sum(outside(v,coarse['bounds']) for v in q)
        for v in q:
            for j in range(3):max_actual[j]=max(max_actual[j],analytic['min'][j]-v[j],v[j]-analytic['max'][j])
        if not any(outside(v,analytic) for v in q):continue
        axis,t,plane,sign,rect=a.quad_info(q);ip=round(plane/P);ir=[round(v/P) for v in rect]
        for u in range(ir[0],ir[2]):
            for v in range(ir[1],ir[3]):
                face=a.rect_quad([u*P,v*P,(u+1)*P,(v+1)*P],axis,t,plane,sign)
                if not any(outside(p,analytic) for p in face):continue
                cell=[0,0,0];cell[axis]=ip-1 if sign>0 else ip;cell[t[0]]=u;cell[t[1]]=v;cells.add(tuple(cell));faces+=1
    assert grid_out==coarse_out==0
    assert all(v<=P/2+1e-6 for v in max_actual)
    chunks=[];source_sets=[];canonical_sets=[]
    buckets={}
    for cell in cells:buckets.setdefault(tuple(n//20 for n in cell),[]).append(cell)
    for k,points in sorted(buckets.items()):
        cb={'min':[min(p[j] for p in points) for j in range(3)],'max':[max(p[j] for p in points)+1 for j in range(3)]}
        s=a.core.compile_master(original,{'pitch':P},max_candidate_cells=20000,max_output_cells=20000,cell_bounds=cb);f=a.core.compile_master(canonical,{'pitch':P},max_candidate_cells=20000,max_output_cells=20000,cell_bounds=cb);ss={tuple(r[:3]):r[5] for r in s['cells']};ff={tuple(r[:3]):r[5] for r in f['cells']};assert all(p in ss and p in ff for p in points)
        chunks.append({'cell_bounds':cb,'witness_cell_count':len(points),'source_payload_sha256':s['payload_hash'],'canonical_payload_sha256':f['payload_hash'],'source_candidate_cells':s['candidate_cells'],'canonical_candidate_cells':f['candidate_cells'],'every_witness_source_and_canonical_occupied':True,'witness_cells':[list(p) for p in sorted(points)]})
    result={'schema':'riverstone.common.cell_center_envelope_proof.v1','asset_key':key,'render_path':pre['render_path'],'render_sha256':pre['render_sha256'],'source_master_path':cat['source_master_path'],'source_master_sha256':cat['source_sha256'],'canonical_master_path':cat['canonical_master_path'],'canonical_master_sha256':cat['canonical_master_sha256'],'analytic_source_bounds':analytic,'outside_analytic_aabb_vertices':raw_out,'all_emitted_vertices':vertices,'voxel_cell_envelope':{**envelope,'pitch_m':P,'grid_origin_m':origin,'sampling':'cell_center','outside_envelope_vertices':0,'max_excess_from_analytic_m':max(max_actual),'max_excess_by_axis_m':max_actual},'outside_original_coarse_aabb_vertices':coarse_out,'outside_analytic_incident_face_pixels':faces,'source_occupied_boundary_cell_count':len(cells),'source_canonical_replay':chunks,'common_engine_path':str(Path(a.core.__file__).relative_to(a.ROOT)),'common_engine_sha256':a.sha(a.core.__file__),'verifier_path':str(Path(__file__).relative_to(a.ROOT)),'verifier_sha256':a.sha(__file__),'source_shapes_cropped':False,'full_building_cells_created':False,'proof_scope':'Every emitted vertex tested. Every unit face extending outside analytic AABB has its inward adjacent fine cell independently replayed occupied in original and canonical common sources. This is a bounded cell-centre rasterization proof, not arbitrary AABB expansion or whole-solid containment.','max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};a.write(out/'cell_envelope_proof.json',result);print({k:result[k] for k in ['asset_key','outside_analytic_aabb_vertices','outside_original_coarse_aabb_vertices','source_occupied_boundary_cell_count','voxel_cell_envelope']})
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('asset');run(p.parse_args().asset)
