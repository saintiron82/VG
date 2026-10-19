"""Source-bound accounting separates stored district plans from scene activation."""
import json,sys
from pathlib import Path
from .build_scene import a,HERE

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main(scene_name):
 p=Path(scene_name).resolve();s=a.load(p);m_path=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/effective_city_manifest_r01.json';m=a.load(m_path)
 active={r['source']['sha256']:r for r in s['r8_provenance']['pack_ledgers']};ids={i['id']for i in s['common_instances']};rows=[]
 for r in m['districts']:
  ledger=active.get(r['pack']['sha256']);pack=a.load(a.source_file(r['pack']['path']),r['pack']['sha256'])
  row=dict(block_id=r['block_id'],pack=r['pack'],source_revision=r['source_revision'],source_summary=r['summary'],stage='NATIVE_SOURCE_PENDING_TERRAIN_ACTIVATION')
  if ledger:
   assert set(ledger['inserted_runtime_ids'])<=ids
   assert not (set(ledger['retired_native_ids'])&ids)
   row.update(stage='SCENE_INTEGRATED_PENDING_RUNTIME_AND_VISUAL_ACCEPTANCE',scene_placements=len(ledger['inserted_runtime_ids']),scene_retirements=len(ledger['retired_native_ids']))
  rows.append(row)
 rows+= [dict(block_id=r.get('block_id'),stage='EXPLICIT_SOURCE_HOLD',detail=r)for r in m['held_districts']]
 out=dict(schema='riverstone.r8.scene_activation_ledger.v1',scene=ref(p),effective_city_sources=ref(m_path),whole_city_complete=False,ordinary_blocks=rows,integrated_packs=[dict(name=r['name'],source=r['source'],placed=len(r['inserted_runtime_ids']),retired=len(r['retired_native_ids']))for r in s['r8_provenance']['pack_ledgers']],live_scene_counts=dict(native_placements=len(s['common_instances']),shared_native_assets=len(s['common_assets']),foundation_proxies=len(s['boxes']),terrain_triangles=sum(len(v)//3 for v in s['surfaces'].values())),inherited_count_notice='Legacy building_masses and early terrain domain counts in scene.counts are source-history snapshots, not live coverage or completion measures.',pending=['Remaining ordinary district terrain/road activation and B07 contour refit','Named backland functions with actual access and native enclosure activation','Remaining protected precinct connections and land-use ownership','Canonical public corridor field and whole-network unchanged-controller replay','Same-camera concept silhouette/density review and complete recovery archive'],scope='Exterior spatial composition with selective functional entrances. Interiors, NPC economy and microscopic texture polish are outside this stage.')
 target=p.parent/'activation_ledger.json';assert not target.exists();target.write_text(json.dumps(out,indent=2)+'\n');print(ref(target))
if __name__=='__main__':main(sys.argv[1])
