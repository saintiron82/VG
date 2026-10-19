"""Pinned shared compiler + actual mesh, with independent body solid checks."""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,shutil,sys
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,separators=(',',':'))+'\n')
def run(tag):
 snapshot=ROOT/'evidence/compiler_snapshot';(snapshot/'common').mkdir(parents=True,exist_ok=True);(snapshot/'tools').mkdir(exist_ok=True)
 for rel in ['common/core.py','common/render_data.py','tools/mesh.py']:
  target=snapshot/rel
  if not target.exists():shutil.copy2(ROOT.parent/rel,target)
 sys.path.insert(0,str(snapshot/'common'));from core import compile_master,digest;from render_data import make_render_data
 d=ROOT/'generated'/tag;master=json.loads(gzip.decompress((d/'master.json.gz').read_bytes()));pitch=.025
 c=compile_master(master,{'pitch':pitch},max_candidate_cells=1800000,max_output_cells=120000);assert c['valid'];render=make_render_data(c);render['frame']={'camera_center_m':[0,1.02,0]};render_path=d/('character.render.json.gz' if tag.endswith('b') else 'character.render.json')
 if render_path.suffix=='.gz':
  with gzip.GzipFile(filename=str(render_path),mode='wb',mtime=0) as f:f.write(json.dumps(render,separators=(',',':')).encode())
 else:dump(render_path,render)
 with gzip.GzipFile(filename=str(d/'compiled.cells.json.gz'),mode='wb',mtime=0) as f:f.write(json.dumps(c,separators=(',',':')).encode())
 # Recompile only anatomy volumes before hair/cloth overwrite; do not infer
 # connectivity from a skirt connecting otherwise separated body regions.
 anatomy=copy.deepcopy(master);anatomy['components'][0]['operations']=[o for o in anatomy['components'][0]['operations'] if o['part'] in ['head','neck','torso','arm_left','arm_right','hand_left','hand_right','leg_left','leg_right','shoe_left','shoe_right']]
 body=compile_master(anatomy,{'pitch':pitch},max_candidate_cells=400000,max_output_cells=80000);rows=body['cells'];positions=np.array([r[:3] for r in rows]);low=positions.min(0)-1;shape=positions.max(0)-low+2;volume=np.zeros(tuple(shape),bool);positions-=low;volume[tuple(positions.T)]=True;labels,count=ndi.label(volume);sizes=np.sort(np.bincount(labels.ravel())[1:])[::-1]
 body_report={'six_connected_components':int(count),'largest_fraction':float(sizes[0]/sizes.sum()),'sizes_cells':sizes[:20].tolist(),'enclosed_empty_cells':int((ndi.binary_fill_holes(volume)&~volume).sum()),'scope':'anatomy alone, without hair, clothing panels, bouquet or halo'}
 head=copy.deepcopy(master);head['components'][0]['operations']=[o for o in head['components'][0]['operations'] if o['part']=='head'];hc=compile_master(head,{'pitch':pitch},max_candidate_cells=100000,max_output_cells=30000);ps=np.array([r[:3] for r in hc['cells']]);lo=ps.min(0)-1;sh=ps.max(0)-lo+2;hv=np.zeros(tuple(sh),bool);hv[tuple((ps-lo).T)]=True;hl,hn=ndi.label(hv);head_report={'six_connected_components':int(hn),'cells':len(hc['cells']),'enclosed_empty_cells':int((ndi.binary_fill_holes(hv)&~hv).sum()),'skin_geometry':'closed complete head volume; source skin ROI not used as an isolated patch'}
 cellmap={tuple(r[:3]):r[4] for r in rows};contacts={}
 for xyz,part in cellmap.items():
  for axis in range(3):
   q=list(xyz);q[axis]+=1;other=cellmap.get(tuple(q))
   if other and part!=other:
    key=' / '.join(sorted([part,other]));contacts[key]=contacts.get(key,0)+1
 report={'master_hash':digest(master),'compiler_sha256':sha(snapshot/'common/core.py'),'renderer':render['provenance'],'cells':len(c['cells']),'quads':render['quad_count'],'head_solid':head_report,'anatomy_solid':body_report,'part_face_contacts':contacts,'compile_valid':True,'visual_approval':False,'validation_boundary':'Connected/cavity-free solids are structural checks only; do not establish likeness or inferred rear correctness.'}
 dump(d/'solid_validation.json',report);dump(d/'compile_manifest.json',{'master_file_sha256':sha(d/'master.json.gz'),'master_hash':digest(master),'compiled_payload_hash':c['payload_hash'],'compiled_file_sha256':sha(d/'compiled.cells.json.gz'),'render_file_sha256':sha(render_path),'compiler_sha256':report['compiler_sha256'],'generator_sha256':master['extensions']['generator_sha256'],'status':'coarse common voxel compile, appearance not approved'});print(json.dumps(report))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('tag');run(p.parse_args().tag)
