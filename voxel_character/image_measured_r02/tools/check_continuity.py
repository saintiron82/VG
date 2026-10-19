"""Exact mixed-pitch occupancy expanded to the smallest 6.25mm lattice.

Connectivity is a structural diagnostic, not proof of correct anatomy or depth.
"""
from pathlib import Path
import gzip,json
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]

def check(path):
 r=json.loads((path/'character.render.json').read_text());pitch=.00625;low=np.floor(np.array(r['bounds']['min'])/pitch+1e-6).astype(int);high=np.ceil(np.array(r['bounds']['max'])/pitch-1e-6).astype(int);shape=high-low
 assert np.prod(shape)<20_000_000,'Bounded diagnostic grid exceeded'
 volumes={};parts={};data=[]
 for layer in r['provenance']['layers']:
  c=json.loads(gzip.decompress((path/layer['file']).read_bytes()));data.append(c)
  for row in c['cells']:parts[row[4]]=parts.get(row[4],0)+c['pitch']**3
 subsets={'all':None,'body':{'head','neck','torso','left_arm','right_arm','left_leg','right_leg','body','bodice'},'cloth':{'skirt'},'hair':{'hair'}}
 for name,selection in subsets.items():
  volume=np.zeros(tuple(shape),bool)
  for c in data:
   factor=round(c['pitch']/pitch)
   for row in c['cells']:
    if selection is not None and row[4] not in selection:continue
    a=np.array(row[:3])*factor-low;b=a+factor;volume[a[0]:b[0],a[1]:b[1],a[2]:b[2]]=True
  labels,count=ndi.label(volume);sizes=np.bincount(labels.ravel())[1:];sizes=np.sort(sizes)[::-1];total=int(sizes.sum())
  volumes[name]={'connected_components_6_neighbor':int(count),'largest_component_fraction':float(sizes[0]/total) if total else None,'largest_10_component_volumes_m3':(sizes[:10]*pitch**3).tolist(),'total_volume_m3':total*pitch**3,'lattice_pitch_m':pitch,'lattice_shape':shape.tolist()}
 return {'subsets':volumes,'part_volume_m3':parts,'bounds_m':r['bounds'],'warning':'A connected solid can still have incorrect anatomy, depth or folds. Halo and airborne ribbons may intentionally remain detached. No unseen-view ground truth exists.'}

if __name__=='__main__':
 paths={'previous_depth_prior':ROOT.parent/'image_measured_r01/generated/violet','continuous_volume':ROOT/'generated/violet'}
 result={k:check(p) for k,p in paths.items()};(ROOT/'evidence/continuity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
