from pathlib import Path
import json,sys,math,heapq,time
import numpy as np
from matplotlib.path import Path as MPath
from scipy.ndimage import distance_transform_edt
O=Path(__file__).resolve().parent;B=O.parent;ROOT=next(p for p in O.parents if (p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
C=ROOT/'world_city/concept_city_v3';L=lambda p:json.loads(p.read_text());cat=L(C/'traversal_r5/revisions/r06_r8_precinct/public_network_final_catalog_r01/route_catalog_481_r01.json');roads={r['id']:r for r in cat['routes']};pack=L(C/'assemblies/landmarks/registered/assembly_r01/resolved_placements.json')
entrances={e['id']:e for e in pack['entrances']}
selected={'castle':'castle_registered:front_gate_wing:main_entry','cathedral':'cathedral_registered:nave_aisles_transept:main_entry','monastery':'monastery_registered:monastic_church:main_entry'}
for group,eid in selected.items():
 e=entrances[eid];end=[e['threshold_world_xyz_m'][i]-.6*e['forward_into_asset_world'][i]for i in [0,2]];graph=L(B/f'entry_graph_{group}.json');rows=graph['rows'];parent=graph['parent'];seed=[i for i,r in enumerate(rows)if g.point_in_convex_polygon(end,r['polygon_xz_m'])];print(group,'end',end,'seed',seed,'connected',[(i,str(i)in parent)for i in seed],flush=True)
 chain=[]
 if seed:
  i=next((i for i in seed if str(i)in parent),None)
  while i is not None:chain.append(i);i=parent[str(i)]
 if chain:
  centers=[[sum(v[j]for v in rows[i]['polygon_xz_m'])/3 for j in [0,1]] for i in chain];print('chain',len(chain),'endcenter',centers[-1],'endlanding',rows[chain[-1]],flush=True)
  (O/f'{group}_graph_chain_diagnostic.json').write_text(json.dumps({'end':end,'entrance':e,'chain':chain,'centers_xz_m':centers,'rows':[rows[i]for i in chain]},indent=2)+'\n')
