"""Deterministic B13 material overlay; native geometry and sealed r3 stay unchanged."""
import hashlib,json,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[1];ROOT=CITY.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=HERE.parent/'r3/candidate.json';d=json.loads(src.read_bytes())
 palettes={
 'wood_brown':dict(slate='80664a',slate_dark='624f3d',slate_light='8c7355',slate_worn='9c8568'),
 'clay_red':dict(slate='a16b51',slate_dark='80523f',slate_light='ac775c',slate_worn='b18a6c'),
 'weathered_slate_gray':dict(slate='646b69',slate_dark='4b5352',slate_light='7d8580',slate_worn='92968a')}
 pattern=['wood_brown','wood_brown','clay_red','wood_brown','weathered_slate_gray','wood_brown','wood_brown','clay_red','wood_brown','wood_brown','weathered_slate_gray','clay_red','wood_brown','wood_brown','clay_red','wood_brown']
 rows=sorted((x for x in d['common_instances'] if x['source_pack']=='ordinary_density'),key=lambda x:x['id']);assert len(rows)==len(pattern)
 entries=[]
 for p,family in zip(rows,pattern):
  a=d['common_assets'][p['asset_key']]
  entries.append(dict(id=p['id'],asset_key=p['asset_key'],position_m=p['position_m'],yaw_rad=p['yaw_rad'],scale=p['scale'],master_sha256=a['master_sha256'],render_sha256=a['render_sha256'],palette_id='b13_'+family,palette_family=family,palette_override=palettes[family]))
 out=dict(schema='riverstone.material_overlay.r4',status='color_only_candidate_needs_actual_visual_review',reconstruction='Reauthored from retained design after 2026-10-18 workspace loss; not a restoration of unarchived bytes.',source=dict(path=str(src.relative_to(ROOT)),sha256=sha(src)),palette_counts=dict(collections.Counter(pattern)),placements=entries,geometry_changed=False,original_master_changed=False)
 dest=HERE/'b13_palette_overlay.json';dest.write_text(json.dumps(out,indent=2)+'\n');print(sha(dest),out['palette_counts'])
if __name__=='__main__':main()
