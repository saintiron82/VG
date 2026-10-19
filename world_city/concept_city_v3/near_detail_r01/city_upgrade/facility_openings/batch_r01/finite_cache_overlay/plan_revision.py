"""Plan finite authored-source changes over an immutable composed cache."""
import argparse,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE.parent.parent)]
import author as a
import estimate_run as estimate
from plan_regions import union_boxes

def run(catalog_path,retained_manifest_path,out):
    cat=a.load(catalog_path);contract=a.load(a.ROOT/cat['replacement_contract_path']);manifest=a.load(retained_manifest_path)
    assert a.sha(a.ROOT/contract['authored_master_path'])==contract['authored_master_sha256']==cat['canonical_master_sha256']
    assert manifest['source_master_sha256']==contract['source_master_sha256']
    render=a.ROOT/manifest['render_path'];assert a.sha(render)==manifest['render_sha256']
    regions,n=union_boxes([x['replacement_volume_master_m'] for x in contract['affected_regions']]);regions=[dict(r,id=f'revision_{i:03d}',kind='source_revision') for i,r in enumerate(regions)]
    bs=estimate.bounds_list(a.load(a.ROOT/contract['authored_master_path']),.05);plans=[]
    for r in regions:
        cb={k:[round(v*20) for v in r[k]] for k in ('min','max')};outer={'min':[v-1 for v in cb['min']],'max':[v+1 for v in cb['max']]}
        plans.append({'region':r,'fine_cell_bounds':cb,'chunks':estimate.split(bs,cb,outer,140000)})
    data={'schema':'riverstone.facility.finite_source_revision.plan.v1','asset_key':cat['asset_key'],'canonical_master_path':contract['authored_master_path'],'canonical_master_sha256':contract['authored_master_sha256'],'source_master_sha256':contract['source_master_sha256'],'source_revision':contract['source_revision'],'replacement_contract_path':cat['replacement_contract_path'],'replacement_contract_sha256':a.sha(a.ROOT/cat['replacement_contract_path']),'retained_manifest_path':str(retained_manifest_path.relative_to(a.ROOT)),'retained_manifest_sha256':a.sha(retained_manifest_path),'retained_render_path':manifest['render_path'],'retained_render_sha256':manifest['render_sha256'],'source_catalog_path':str(catalog_path.relative_to(a.ROOT)),'source_catalog_sha256':a.sha(catalog_path),'ordered_regions':regions,'affected_regions':contract['affected_regions'],'union_volume_m3':n/8,'chunk_count':sum(len(p['chunks']) for p in plans),'fine_candidates':sum(c['candidate_visits'] for p in plans for c in p['chunks']),'plans':plans,'pitch_m':.05,'grid_origin_m':[0,0,0],'candidate_cap':140000,'source_shapes_cropped':False,'collision_reference_changed':False,'plan_implementation_sha256':a.sha(__file__)}
    a.write(out,data);print({k:data[k] for k in ['asset_key','union_volume_m3','chunk_count','fine_candidates']},'packed_regions',len(regions))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('retained_manifest',type=Path);p.add_argument('output',type=Path);q=p.parse_args();run(q.catalog.resolve(),q.retained_manifest.resolve(),q.output.resolve())
