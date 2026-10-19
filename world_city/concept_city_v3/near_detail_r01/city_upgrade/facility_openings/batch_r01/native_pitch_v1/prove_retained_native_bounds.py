"""Prove preexisting coarse-cell excess is unchanged original render geometry."""
import collections,json,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path[:0]=[str(B.parent),str(B.parent/'composed_runtime'),str(B/'sampler_v2')]
import author as a
import stream_render as sr
import reserved_io_r04 as rio

def outside(point,bounds):return any(point[j]<bounds['min'][j]-1e-6 or point[j]>bounds['max'][j]+1e-6 for j in range(3))
def run(catalog):
    cat=a.load(catalog);key=cat['asset_key'];out=B/'composed'/key;pre=a.load(out/'preflight.json');master=a.load(a.ROOT/cat['canonical_master_path']);source=a.load(a.ROOT/cat['source_render_path']);assert a.sha(a.ROOT/cat['source_render_path'])==cat['source_render_sha256'];boxes=[bb for c,i,o,t,bb in a.source_inventory(master) if o['action']=='paint'];analytic={'min':[min(bb[0][j] for bb in boxes) for j in range(3)],'max':[max(bb[1][j] for bb in boxes) for j in range(3)]};w=rio.writer_for_catalog(cat,a.ROOT,B,a.HERE.parent/'house_rules');lookup=collections.defaultdict(list)
    for gi,g in enumerate(source['groups']):
        for qi,q in enumerate(g['quads']):lookup[a.core.digest([g['material'],q])].append({'group_index':gi,'quad_index':qi,'material':g['material'],'original_quad_sha256':a.core.digest(q)})
    count=outside_coarse=unmatched=0;rows=[];vertices=0
    for mat,q in sr.iter_quads(a.ROOT/pre['render_path']):
        vertices+=4;outside_coarse+=sum(outside(v,source['bounds']) for v in q);n=sum(outside(v,analytic) for v in q)
        if not n:continue
        count+=n;matches=lookup.get(a.core.digest([mat,q]),[]);unmatched+=not bool(matches);rows.append({'material':mat,'quad_sha256':a.core.digest(q),'outside_analytic_vertex_count':n,'exact_original_quad_matches':matches})
    assert count>0 and outside_coarse==unmatched==0;bounds=pre['summary']['bounds'];excess=max([max(0,analytic['min'][j]-bounds['min'][j],bounds['max'][j]-analytic['max'][j]) for j in range(3)]);assert excess<=source['pitch']/2+1e-6;report={'schema':'riverstone.retained_native_surface_bounds.v1','asset_key':key,'source_master_path':cat['source_master_path'],'source_master_sha256':cat['source_sha256'],'source_render_path':cat['source_render_path'],'source_render_sha256':cat['source_render_sha256'],'render_path':pre['render_path'],'render_sha256':pre['render_sha256'],'canonical_master_path':cat['canonical_master_path'],'canonical_master_sha256':cat['canonical_master_sha256'],'source_native_pitch_m':source['pitch'],'grid_origin_m':source['grid_origin'],'analytic_source_bounds':analytic,'coarse_render_bounds':source['bounds'],'composed_render_bounds':bounds,'vertices_checked':vertices,'outside_analytic_aabb_vertices':count,'outside_original_coarse_aabb_vertices':outside_coarse,'new_or_modified_outside_analytic_quads':unmatched,'all_outside_analytic_quads_exact_original':True,'max_excess_from_analytic_m':excess,'retained_original_quad_evidence':rows,'all_pass':True,'no_voxel_sampling_performed':True,'proof_scope':'Every outside-analytic output quad is exactly byte-value identical, including material and winding, to an authenticated original coarse-render quad. No new fine/seam vertex exceeds the analytic AABB. This is original baseline preservation, not a new fine-cell envelope or whole-solid containment proof.','driver_reference':{'path':str(Path(__file__).relative_to(a.ROOT)),'sha256':a.sha(__file__)}};p=out/'retained_native_bounds_proof.json';w.write(p,report);w.close();print(json.dumps({'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p),'outside_vertices':count,'exact_original_quads':len(rows),'new_outside':unmatched,'max_excess':excess}),flush=True)
if __name__=='__main__':run(Path(sys.argv[1]).resolve())
