"""Bounded first application of the shared lathe stave rule; source preserved."""
from pathlib import Path
import copy, gzip, hashlib, json, resource, sys, time
H=Path(__file__).resolve().parent; U=H.parent; R=U.parents[3]
sys.path.insert(0,str(R))
from voxel_character.common import core, render_data
from voxel_character.common import prepared_sampling_v3 as prepared
from lathe_stave_rule import apply

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p, d):
    b=(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
    if p.suffix=='.gz': b=gzip.compress(b,mtime=0)
    if p.exists(): assert p.read_bytes()==b, 'Preserve prior output; use new revision'
    else: p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)

def main():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    start=time.perf_counter()
    ip=R/'world_city/concept_city_v3/playable_r01/generated/tile_r01/index.json'
    index=json.loads(ip.read_text()); identity=index['common_assets']['r9_port_barrel']
    src=R/identity['master_path']; assert sha(src)==identity['master_sha256']
    master=json.loads(src.read_text())
    spec={'schema':'riverstone.profile_stave_detail.v1','component':'body','operation':'barrel_staves',
          'stave_count':16,'phase':.5,'groove_depth_m':.025,'groove_width_m':.025,
          'cap_board_spacing_m':.15,'pitch_m':.025,
          'source_master_sha256':sha(src),'source_operation_sha256':core.digest(master['components'][0]['operations'][0]),
          'source_city_index_sha256':sha(ip),'collision_policy':'unchanged original coarse source',
          'scope':'Near-only radial profile seams and cap board seams; original iron hoops unchanged'}
    candidate, added=apply(master,spec)
    assert core.digest(candidate)==core.digest(apply(master,spec)[0])
    before_by_id={c['id']:c for c in master['components']}
    for c in candidate['components']:
        old=before_by_id[c['id']]
        if c['id']=='body': assert c['operations'][:len(old['operations'])]==old['operations']
        else: assert c==old
    assert candidate['instances']==master['instances'] and candidate['materials']==master['materials']
    # Full original and detailed source at the same pitch, not merely mesh hashes.
    old=prepared.compile_prepared(prepared.prepare_master(master,{'pitch':.025}),max_candidate_cells=750000,max_output_cells=120000)
    new=prepared.compile_prepared(prepared.prepare_master(candidate,{'pitch':.025}),max_candidate_cells=750000,max_output_cells=120000)
    oldcells={tuple(c[:3]):c[3:] for c in old['cells']}; newcells={tuple(c[:3]):c[3:] for c in new['cells']}
    assert newcells.keys() <= oldcells.keys(), 'Decorative cuts cannot expand source footprint'
    assert all(v==oldcells[k] for k,v in newcells.items()), 'All retained material/part/operation identities unchanged'
    removed=[k for k in oldcells if k not in newcells]
    assert removed and all(oldcells[k][2].startswith('timber') for k in removed)
    assert all(t['pass'] for t in new['constraints'])
    render=render_data.make_render_data(new)
    out=H/'barrel_r01';write(out/'rule.json',spec);write(out/'master.json',candidate);write(out/'render.json.gz',render)
    # Full original-core replay includes every source constraint and exterior face.
    ref=core.compile_master(candidate,{'pitch':.025},max_candidate_cells=750000,max_output_cells=120000)
    assert ref['cells']==new['cells'] and ref['valid']
    assert render_data.make_render_data(ref)['groups']==render['groups']
    report={'schema':'riverstone.prop_stave_candidate.v1','all_pass':True,'asset_key':'r9_port_barrel',
            'source_master':identity,'source_master_unchanged':sha(src)==identity['master_sha256'],
            'added_cut_operations':len(added),'old_cells':len(oldcells),'candidate_cells':len(newcells),
            'removed_wood_cells':len(removed),'retained_cell_metadata_identical':True,
            'new_occupied_cells_outside_source':0,'common_core_replay_exact':True,
            'quads':render['quad_count'],'render_path':str((out/'render.json.gz').relative_to(R)),
            'render_sha256':sha(out/'render.json.gz'),'master_sha256':sha(out/'master.json'),
            'seconds':time.perf_counter()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'runtime_activation':False,'actual_multiview_review':'PENDING','whole_city_complete':False}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
