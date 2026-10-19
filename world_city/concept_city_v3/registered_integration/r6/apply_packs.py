"""Bounded common-cache placement changes over the sealed actual R5 scene.

This is orchestration, not a second voxel compiler or terrain engine. Source
packs remain unchanged. Applying placements alone cannot produce an accepted
scene: the caller must supply the finite ground/support patch separately.
"""
from __future__ import annotations
import copy, hashlib, json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CITY = HERE.parents[1]
ROOT = CITY.parents[1]
BASE_PATH = CITY / 'evidence/visual_registered_common_r5/bridge_scene.json'
BASE_SHA256 = 'a78e1b56bd59b06ec30d4bebec9f6da9d686dca87e6ef87f1d4da181f717a01a'
MERCHANT_PATH = CITY / 'assemblies/property/registered/merchant_fabric_r02/resolved_placements.json'
MERCHANT_SHA256 = 'fb365edf17a0f3f0c62ee1dc7d230a8bbbbda6403ed07d8b6bda118437ddd61d'


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
def load(path, expected=None):
    p = Path(path)
    if expected is not None and sha(p) != expected: raise ValueError('Changed sealed input: '+str(p))
    return json.loads(p.read_bytes())
def rel(path): return str(Path(path).resolve().relative_to(ROOT.resolve()))

def source_file(path):
    p = Path(path)
    if not p.is_absolute(): p = ROOT / p
    p = p.resolve()
    p.relative_to(ROOT.resolve())
    if not p.is_file(): raise ValueError('Missing project-local input: '+str(p))
    return p


def asset_record(asset):
    """Normalize and verify common master/cache references; never compile."""
    out = copy.deepcopy(asset)
    if 'source' in asset and 'cache' in asset:
        out.update(master_path=asset['source']['path'], master_sha256=asset['source']['sha256'],
                   render_path=asset['cache']['path'], render_sha256=asset['cache']['sha256'])
    for kind in ('master', 'render'):
        p = source_file(out[kind+'_path'])
        if sha(p) != out[kind+'_sha256']: raise ValueError('Changed common '+kind+': '+str(p))
        out[kind+'_path'] = rel(p)
    render = load(ROOT/out['render_path'])
    out.update(bounds=render['bounds'], quad_count=render['quad_count'], pitch_m=render['pitch'])
    return out


def validate_instances(scene):
    ids = set(); palettes = {}
    for p in scene['common_instances']:
        if p['id'] in ids: raise ValueError('Duplicate instance: '+p['id'])
        ids.add(p['id'])
        if p['asset_key'] not in scene['common_assets']: raise ValueError('Missing asset: '+p['asset_key'])
        if p.get('scale', [1,1,1]) != [1,1,1]: raise ValueError('Unexpected mesh scaling: '+p['id'])
        values = p['position_m']+[p.get('yaw_rad',0)]
        if len(p['position_m']) != 3 or any(not math.isfinite(v) for v in values): raise ValueError('Invalid transform: '+p['id'])
        key = (p['asset_key'], p['palette_id'])
        override = digest(p.get('palette_override',{}))
        if key in palettes and palettes[key] != override: raise ValueError('Palette cache alias changes colors between instances: '+str(key))
        palettes[key] = override
    return dict(instance_count=len(ids), palette_cache_keys=len(palettes))


def apply_pack(scene, pack, name, source_ref=None, extra_retire_ids=()):
    """Return a copy-on-write scene and explicit retirement/addition ledger.

    Terrain and bridge mechanism are shared read-only with the parent. Both are
    hash-checked by the sealing caller after applying the separate local patch.
    """
    old = {p['id']:p for p in scene['common_instances']}
    if len(old) != len(scene['common_instances']): raise ValueError('Duplicate parent IDs')
    retired = set(pack.get('replaced_placement_ids',[])) | set(extra_retire_ids)
    if not retired <= old.keys(): raise ValueError('Unknown retired IDs: '+str(sorted(retired-old.keys())))
    additions = pack['placements']; new_ids = [p['id'] for p in additions]
    if len(new_ids) != len(set(new_ids)): raise ValueError('Duplicate pack IDs')
    collision = (set(new_ids) & set(old))-retired
    if collision: raise ValueError('Unretired IDs reused: '+str(sorted(collision)))
    result = dict(scene)
    result['common_assets'] = dict(scene['common_assets'])
    entries = pack['assets'].items() if isinstance(pack['assets'],dict) else ((a['id'],a) for a in pack['assets'])
    assets = []
    for key, a in entries:
        a = asset_record(a)
        prior = result['common_assets'].get(key)
        if prior and (prior['master_sha256'],prior['render_sha256']) != (a['master_sha256'],a['render_sha256']): raise ValueError('Asset key collision: '+key)
        result['common_assets'][key] = a
        assets.append(dict(key=key, master_path=a['master_path'],master_sha256=a['master_sha256'],render_path=a['render_path'],render_sha256=a['render_sha256']))
    result['common_instances'] = [p for p in scene['common_instances'] if p['id'] not in retired]
    for p in additions:
        q = {k:copy.deepcopy(p[k]) for k in ('id','asset_key','position_m','yaw_rad','palette_id','palette_override','scale','collision_policy') if k in p}
        q.setdefault('yaw_rad',0);q.setdefault('scale',[1,1,1]);q.setdefault('palette_id','native_'+name);q.setdefault('palette_override',{})
        q['source_pack'] = name
        result['common_instances'].append(q)
    removed_boxes = [b for b in scene.get('boxes',[]) if b.get('source_mass_id') in retired or b['id'] in {x+s for x in retired for s in (':support',':owned_foundation')}]
    removed_box_ids = {b['id'] for b in removed_boxes}
    result['boxes'] = [b for b in scene.get('boxes',[]) if b['id'] not in removed_box_ids]
    checks = validate_instances(result)
    ledger = dict(name=name, source=source_ref, retired_native_ids=sorted(retired),
        retired_foundation_proxy_ids=sorted(removed_box_ids), inserted_runtime_ids=new_ids,
        component_provenance_rendered=False, assets=assets,
        unchanged_surfaces=True, ground_activation=False,
        retired_private_route_ids=sorted(set(pack.get('superseded_source_path_ids',[])+pack.get('superseded_native_access_ids',[]))),
        source_door_count=len(pack.get('actual_doors',[])), validation=checks)
    if result['surfaces'] is not scene['surfaces']: raise AssertionError('Placement orchestration changed ground')
    return result, ledger


def merchant_candidate():
    scene=load(BASE_PATH,BASE_SHA256);pack=load(MERCHANT_PATH,MERCHANT_SHA256)
    result,ledger=apply_pack(scene,pack,'merchant_fabric_r02',dict(path=rel(MERCHANT_PATH),sha256=MERCHANT_SHA256))
    assert len(ledger['retired_native_ids'])==58 and len(ledger['inserted_runtime_ids'])==38
    assert len(ledger['retired_foundation_proxy_ids'])==58
    assert ledger['source_door_count']==126
    return result,ledger

if __name__=='__main__':
    result,ledger=merchant_candidate()
    report=dict(schema='riverstone.r6_source_placement_plan.v1',status='assembly_verified_not_scene_activated',
        base_scene=dict(path=rel(BASE_PATH),sha256=BASE_SHA256),placement_ledger=ledger,
        terrain_requirement='R15 finite triangle/road-collar/support acceptance is required before scene activation.',
        current_instances=len(result['common_instances']),current_foundation_proxies=len(result['boxes']),
        no_scene_written=True)
    dest=HERE/'merchant_placement_review.json'
    if dest.exists(): raise ValueError('Preserve prior source review.')
    dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='placement_ledger'},indent=2))
