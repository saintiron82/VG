"""Non-visual, directional and solid-contact checks for curved06."""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,sys
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'evidence/compiler_snapshot/common'))
from core import compile_master,digest

def topology(rows):
 ps=np.array([r[:3] for r in rows]);lo=ps.min(0)-1;grid=np.zeros(tuple(ps.max(0)-lo+2),bool);grid[tuple((ps-lo).T)]=True;label,n=ndi.label(grid);sizes=sorted(np.bincount(label.ravel())[1:].tolist(),reverse=True);return {'six_connected_components':n,'component_cells':sizes[:12],'cells':len(rows)},grid,lo

def run(tag):
 d=ROOT/'generated'/tag;m=json.loads(gzip.decompress((d/'master.json.gz').read_bytes()));ops=m['components'][0]['operations'];cache={}
 def compile_parts(key,predicate):
  mm=copy.deepcopy(m);mm['components'][0]['operations']=[o for o in ops if predicate(o['part'])];c=compile_master(mm,{'pitch':.025},max_candidate_cells=1800000,max_output_cells=120000);cache[key]=c;return c
 def positions(c):return {tuple(r[:3]) for r in c['cells']}
 head=compile_parts('head',lambda p:p=='head');hair=compile_parts('hair',lambda p:p.startswith(('scalp','hair_lock','bang')));cloth=compile_parts('cloth',lambda p:'petal' in p or p=='front_short_panel');hs=positions(head);hairs=positions(hair)
 htop,hg,hlo=topology(head['cells']);inner=ndi.binary_erosion(hg);interior={tuple(x+hlo) for x in np.argwhere(inner)}
 panels=[]
 for p in ['left_petal','right_petal','back_left_petal','back_right_petal','back_center_petal','front_short_panel']:
  c=compile_parts(p,lambda part:part==p);top,_,_=topology(c['cells']);panels.append({'part':p,**top,'nominal_surface_thickness_m':.035})
 ribbon=compile_parts('ribbon',lambda p:p.startswith('ribbon_'));legs=compile_parts('legs',lambda p:p.startswith('leg_'));contact=len(positions(ribbon)&positions(legs));anchors=json.loads((d/'ribbon_attachment.json').read_text());support=[]
 for a in anchors:
  cells=cache[a['support_panel']]['cells'];tree=cKDTree((np.array([r[:3] for r in cells])+.5)*.025);dist,_=tree.query(np.array(a['centerline'])[2:]);support.append({'part':a['part'],'support_panel':a['support_panel'],'maximum_centerline_to_compiled_panel_cell_center_m':float(dist.max()),'median_distance_m':float(np.median(dist)),'root':'bouquet/waist manual attachment, not hidden-view observation','open_path':True})
 axes=[np.array(o['transform']['basis']) for o in ops if 'transform' in o];maxerror=max(float(np.max(np.abs(b.T@b-np.eye(3)))) for b in axes);mindet=min(float(np.linalg.det(b)) for b in axes)
 result={'master_hash':digest(m),'compiler_sha256':hashlib.sha256((ROOT/'evidence/compiler_snapshot/common/core.py').read_bytes()).hexdigest(),'head':htop,'hair':topology(hair['cells'])[0],'head_hair_overlap_cells':len(hs&hairs),'hair_inside_one_cell_eroded_head_cells':len(interior&hairs),'overlap_boundary':'Surface mounting overlap is expected. Deep-overlap count is diagnostic and may include scalp/bangs; it is not an automatic art acceptance.','cloth_union':topology(cloth['cells'])[0],'panels':panels,'ribbon_legs_overlap_cells':contact,'ribbon_support':support,'adapter_frames':{'max_orthogonality_error':maxerror,'min_determinant':mindet,'handedness':'right handed; panel inner material on negative normal'},'appearance_approved':False,'gpu_visual_review':False}
 (d/'surface_integrity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('tags',nargs='+');args=a.parse_args()
 for tag in args.tags:run(tag)
