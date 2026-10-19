"""Read-only final protected native activation and exact cap-field inclusion check."""
from pathlib import Path
import sys,json,hashlib,argparse,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
OUT=Path(__file__).resolve().parent

def canonical(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scene',required=True);ap.add_argument('--scene-sha256',required=True);ap.add_argument('--binding',required=True);args=ap.parse_args()
    sp=Path(args.scene).resolve();bp=Path(args.binding).resolve();assert ref(sp)['sha256']==args.scene_sha256
    scene=load(sp);binding=load(bp);actual={p['id']:p for p in scene['common_instances']};assets=scene['common_assets'];rows=[];retired=[];fail=[];seenfiles={}
    def checkfile(r):
        if r['path']not in seenfiles:seenfiles[r['path']]=ref(ROOT/r['path'])['sha256']
        assert seenfiles[r['path']]==r['sha256'],r['path']
    for pr in binding['packs']:
        if 'precinct_r06_whole/'not in pr['path']and 'precinct_r05_ground/phase02/'not in pr['path']:continue
        checkfile(pr);pack=load(ROOT/pr['path']);packrows=[]
        for p in pack['placements']:
            q=actual.get(p['id']);errors=[]
            if q is None:errors.append('not_activated')
            else:
                for k in('asset_key','position_m','yaw_rad','scale'):
                    if q.get(k)!=p.get(k):errors.append('pose_or_asset:'+k)
                a=assets[q['asset_key']]
                for k,target in(('source','master_sha256'),('cache','render_sha256')):
                    if k in p:
                        checkfile(p[k])
                        if p[k]['sha256']!=a[target]:errors.append('actual_'+target)
            row=dict(native_id=p['id'],source_pack=pr,errors=errors);packrows.append(row)
            if errors:fail.append(row)
        for nativeid in pack.get('replacement_ledger',{}).get('existing_native_placements_removed',[]):
            r=dict(native_id=nativeid,source_pack=pr,absent=nativeid not in actual);retired.append(r)
            if not r['absent']:fail.append(r)
        rows.append(dict(source_pack=pr,expected_placements=len(packrows),placements=packrows))
    cap_path=BASE/'residual_completion_r01/noble_cap_route_repair_r01/finite_surface_patch_bound.json';cap=load(cap_path);floorrows=[]
    for mat,vs in cap['appended_surfaces'].items():
        current=scene['surfaces'][mat]
        # Scene stores flat triangle vertex arrays, like the frozen producer.
        expected=collections.Counter(canonical(vs[i:i+3])for i in range(0,len(vs),3));got=collections.Counter(canonical(current[i:i+3])for i in range(0,len(current),3))
        missing=expected-got;row=dict(material=mat,expected_triangles=sum(expected.values()),missing_triangle_hashes=dict(missing));floorrows.append(row)
        if missing:fail.append(row)
    result=dict(status='PASS_ACTUAL_PROTECTED_ACTIVATION'if not fail else'FAIL',scene=ref(sp),binding=ref(bp),protected_source_ledger=ref(BASE/'final_acceptance_r01/protected_exterior_acceptance.json'),native_pack_rows=rows,retired_native_rows=retired,exact_cap_field_rows=floorrows,cap_field_source=ref(cap_path),summary=dict(packs=len(rows),native_placements=sum(r['expected_placements']for r in rows),retired_native_ids=len(retired),bound_source_cache_files=len(seenfiles),failures=len(fail)),failures=fail,runtime_ready=False,limit='Exact source/cache/pose and finite cap-field activation only. Actual unchanged-controller replay is separate.')
    (OUT/'activation_review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary']|{'status':result['status']},indent=2));assert not fail


if __name__=='__main__':main()
