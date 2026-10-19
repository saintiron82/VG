"""Same source geometry, explicit multilayer cloth and globally ordered paint.

No image editing or post-compile material changes. Existing shared compiler reads
only native extrusions; all non-cloth operations remain byte-semantically equal.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,sys
import numpy as np
from measure_cloth_faces import nearest_normals
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'r07';sys.path.insert(0,str(ROOT/'evidence/compiler_snapshot/common'))
from core import digest,compile_master
from render_data import make_render_data
CLOTH={'left_petal','right_petal','back_left_petal','back_right_petal','back_center_petal','front_short_panel'}
def read(p):return json.loads(gzip.decompress(p.read_bytes())) if p.suffix=='.gz' else json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')
def gz(p,obj):
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(obj,separators=(',',':')).encode())
def build(aid):
 basepath=ROOT/'generated'/(aid+'_curved06b')/'master.json.gz';base=read(basepath);master=copy.deepcopy(base);ops=base['components'][0]['operations'];noncloth=[o for o in ops if o['part'] not in CLOTH];outer=[o for o in ops if o['part'] in CLOTH and o['material']=='dress'];layers=[];thickness=.075
 for label,mat,lo,hi in [('inner','lining',-thickness/2,0),('outer','dress',0,thickness/2)]:
  for src in outer:
   o=copy.deepcopy(src);o['id']='cloth_r07_'+label+'_'+src['id'];o['material']=mat;o['shape'].update({'z_min':lo,'z_max':hi,'minimum_cells':0});layers.append(o)
 first=min(i for i,o in enumerate(ops) if o['part'] in CLOTH);before=[o for o in ops[:first] if o['part'] not in CLOTH];after=[o for o in ops[first:] if o['part'] not in CLOTH];master['components'][0]['operations']=before+layers+after;assert [o for o in master['components'][0]['operations'] if o['part'] not in CLOTH]==noncloth
 master['revision']=7;master['extensions']['cloth_r07']={'source_master_hash':digest(base),'source_master_file_sha256':sha(basepath),'all_noncloth_operations_digest':digest(noncloth),'noncloth_unchanged':True,'cloth_midsurface_and_normals_unchanged':True,'old_total_thickness_m':.035,'old_lining_band_m':.010,'new_total_thickness_m':thickness,'inner_band_m':[-thickness/2,0],'outer_band_m':[0,thickness/2],'paint_order':'all inner half-shell prisms, then all outer half-shell prisms; source signed normal + is outer','cell_classification':'unchanged common compiler cell center against signed normal half-prism','thickness_reason':'At 25mm pitch a one-layer cell cannot have different materials on opposite faces; 75mm shell supplies multiple actual voxel layers without raising resolution. This is an explicit coarse display thickness, not measured physical fabric.','adapter_sha256':sha(Path(__file__))};out=OUT/'generated'/(aid+'_r07c');out.mkdir(exist_ok=False);c=compile_master(master,{'pitch':.025},max_candidate_cells=2500000,max_output_cells=120000);assert c['valid'];candidate_hash=c['payload_hash'];corrected=[];changes=0;occupied={tuple(row[:3]) for row in c['cells']};mixed_total=0
 for part in sorted(CLOTH):
  triangles=[]
  for op in outer:
   if op['part']!=part:continue
   local=np.column_stack([np.array(op['shape']['polygon']),np.zeros(3)]);triangles.append(local@np.array(op['transform']['basis']).T+np.array(op['transform']['translation']))
  rows=[row for row in c['cells'] if row[4]==part];points=(np.array([row[:3] for row in rows])+.5)*.025;normal,distance,signed=nearest_normals(points,np.array(triangles),return_signed=True)
  face_points=[];face_dirs=[];owners=[]
  for ri,row in enumerate(rows):
   xyz=row[:3]
   for axis in range(3):
    for sign in [-1,1]:
     q=list(xyz);q[axis]+=sign
     if tuple(q) in occupied:continue
     pos=(np.array(xyz)+.5)*.025;pos[axis]+=sign*.025/2;n=np.zeros(3);n[axis]=sign;face_points.append(pos);face_dirs.append(n);owners.append(ri)
  normal_face,_=nearest_normals(np.array(face_points),np.array(triangles));agreement=(normal_face*np.array(face_dirs)).sum(1);votes=np.zeros((len(rows),2))
  for ri,dot in zip(owners,agreement):
   if dot>.35:votes[ri,0]+=1
   elif dot<-.35:votes[ri,1]+=1
  mixed_total+=int(((votes[:,0]>0)&(votes[:,1]>0)).sum())
  for ri,(row,side) in enumerate(zip(rows,signed)):
   if votes[ri].sum():mat='dress' if votes[ri,0]>=votes[ri,1] else 'lining'
   else:mat='dress' if side>=0 else 'lining'
   changes+=int(mat!=row[5]);corrected.append((row[1],row[2],part,mat,row[0]))
 groups={}
 for y,z,part,mat,x in corrected:groups.setdefault((y,z,part,mat),[]).append(x)
 paints=[]
 for (y,z,part,mat),xs in sorted(groups.items()):
  xs=sorted(xs);runs=[];start=last=xs[0]
  for x in xs[1:]:
   if x==last+1:last=x
   else:runs.append((start,last));start=last=x
  runs.append((start,last))
  for start,last in runs:paints.append({'id':'cloth_signed_material_'+str(len(paints)),'part':part,'action':'paint','material':mat,'shape':{'kind':'box','min':[start*.025,y*.025,z*.025],'max':[(last+1)*.025,(y+1)*.025,(z+1)*.025]}})
 master['components'][0]['operations']+=paints;master['extensions']['cloth_r07']['material_field']={'method':'Interior cell center uses closest signed midsurface; exposed cells use majority outer/inner source-normal face agreement, ties outer. Tangent faces do not vote. A cell has one material, so conflicting hem/corner votes remain measured.' ,'mixed_side_boundary_cells':mixed_total,'candidate_payload_hash':candidate_hash,'classification_pitch_m':.025,'material_changes':changes,'run_length_box_operations':len(paints),'classifier_sha256':sha(Path(__file__).with_name('measure_cloth_faces.py')),'geometry_not_changed':'box paint covers only already occupied cloth cells; original continuous shell remains the geometry source'};gz(out/'master.json.gz',master)
 final=compile_master(master,{'pitch':.025},max_candidate_cells=3000000,max_output_cells=120000);assert {tuple(row[:3]) for row in final['cells']}=={tuple(row[:3]) for row in c['cells']};c=final;gz(out/'compiled.cells.json.gz',c);r=make_render_data(c);r['frame']={'camera_center_m':[0,1.02,0]};gz(out/'character.render.json.gz',r);manifest={'master_hash':digest(master),'base_master_hash':digest(base),'noncloth_unchanged':True,'head_hair_body_operations_digest':digest(noncloth),'cells':len(c['cells']),'quads':r['quad_count'],'compiler_sha256':c['compiler_source_hash'],'master_file_sha256':sha(out/'master.json.gz'),'compiled_payload_hash':c['payload_hash'],'render_gzip_sha256':sha(out/'character.render.json.gz'),'all_appearance_approved':False,'cloth_policy':master['extensions']['cloth_r07']};dump(out/'manifest.json',manifest);print(json.dumps(manifest))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('asset',choices=['violet','cyan']);build(p.parse_args().asset)
