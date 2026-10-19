"""Measure actual common-cell exposed faces against original curved panel normals."""
from pathlib import Path
import argparse,gzip,json,sys,hashlib
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'r07'
CLOTH={'left_petal','right_petal','back_left_petal','back_right_petal','back_center_petal','front_short_panel'}
def read(p):return json.loads(gzip.decompress(p.read_bytes())) if p.suffix=='.gz' else json.loads(p.read_text())
def nearest_normals(points,triangles,return_signed=False):
 centers=triangles.mean(1);tree=cKDTree(centers);_,idx=tree.query(points,k=min(16,len(triangles)));tri=triangles[idx];a,b,c=tri[:,:,0],tri[:,:,1],tri[:,:,2];ab=b-a;ac=c-a;norm=np.cross(ab,ac);norm/=np.linalg.norm(norm,axis=2)[:,:,None];q=points[:,None,:]-a;plane=(q*norm).sum(2);projection=q-plane[:,:,None]*norm;d00=(ab*ab).sum(2);d01=(ab*ac).sum(2);d11=(ac*ac).sum(2);d20=(projection*ab).sum(2);d21=(projection*ac).sum(2);den=d00*d11-d01*d01;u=(d11*d20-d01*d21)/den;v=(d00*d21-d01*d20)/den;inside=(u>=0)&(v>=0)&(u+v<=1);dist=np.where(inside,plane**2,np.inf)
 for aa,bb in [(a,b),(b,c),(c,a)]:
  seg=bb-aa;t=np.clip(((points[:,None,:]-aa)*seg).sum(2)/(seg*seg).sum(2),0,1);sq=((points[:,None,:]-(aa+t[:,:,None]*seg))**2).sum(2);dist=np.minimum(dist,sq)
 k=np.argmin(dist,axis=1);
 if return_signed:return norm[np.arange(len(points)),k],np.sqrt(dist[np.arange(len(points)),k]),plane[np.arange(len(points)),k]
 return norm[np.arange(len(points)),k],np.sqrt(dist[np.arange(len(points)),k])
def measure(aid,tag,folder):
 old=read(ROOT/'generated'/(aid+'_curved06b')/'master.json.gz');c=read(folder/'compiled.cells.json.gz');mapping={tuple(row[:3]):row for row in c['cells']};pitch=c['pitch'];report={};total={'outer':{},'inner':{},'tangent':{}}
 for part in sorted(CLOTH):
  triangles=[]
  for o in old['components'][0]['operations']:
   if o['part']==part and o['material']=='dress':
    t=o['transform'];xy=np.array(o['shape']['polygon']);local=np.column_stack([xy,np.zeros(len(xy))]);triangles.append(local@np.array(t['basis']).T+np.array(t['translation']))
  triangles=np.array(triangles);centers=[];directions=[];materials=[]
  for xyz,row in mapping.items():
   if row[4]!=part:continue
   for axis in range(3):
    for sign in [-1,1]:
     q=list(xyz);q[axis]+=sign
     if tuple(q) in mapping:continue
     pos=(np.array(xyz)+.5)*pitch;pos[axis]+=sign*pitch/2;n=np.zeros(3);n[axis]=sign;centers.append(pos);directions.append(n);materials.append(row[5])
  if not centers:continue
  normal,dist=nearest_normals(np.array(centers),triangles);alignment=(normal*np.array(directions)).sum(1);groups={}
  for label,selected in [('outer',alignment>.35),('inner',alignment<-.35),('tangent',np.abs(alignment)<=.35)]:
   counts={mat:int(sum(bool(sel) and m==mat for sel,m in zip(selected,materials))) for mat in sorted(set(materials))};counts={k:v for k,v in counts.items() if v};groups[label]={'faces':int(selected.sum()),'material_faces':counts,'mean_abs_normal_alignment':float(np.abs(alignment[selected]).mean()) if selected.any() else 0}
   for k,v in counts.items():total[label][k]=total[label].get(k,0)+v
  report[part]=groups
 ratios={}
 for label,expected in [('outer','dress'),('inner','lining')]:
  n=sum(total[label].values());ratios[label]={'faces':n,'expected_material':expected,'expected_material_fraction':total[label].get(expected,0)/n if n else None,'material_faces':total[label]}
 return {'asset':aid,'tag':tag,'pitch_m':pitch,'compiled_payload_hash':c['payload_hash'],'measurement':'Every exposed unit voxel face; source triangle normal found by closest point among 16 nearest triangle centroids of the owning cloth panel. Dot > .35 outer; < -.35 inner; tangent excluded from agreement.','ratios':ratios,'parts':report,'scope':'Actual common-cell materials and 3D geometry, not rendered image colors. Overlapping panels and hem/tangent faces reported separately; not whole-asset art approval.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('asset',choices=['violet','cyan']);p.add_argument('--tag',default='r07c');args=p.parse_args();a=args.asset;tag=args.tag;result={'before':measure(a,'curved06b',ROOT/'generated'/(a+'_curved06b')),'after':measure(a,tag,OUT/'generated'/(a+'_'+tag)),'measurement_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(OUT/'generated'/(a+'_'+tag)/'cloth_face_metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v['ratios'] for k,v in result.items() if isinstance(v,dict)}))
