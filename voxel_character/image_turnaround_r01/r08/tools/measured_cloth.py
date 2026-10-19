"""Pixel-driven bounded cloth-region experiment. No hand-authored shape curves.

Measurement is mandatory. Semantic view crops, metric calibration, sector and
elliptic section/thickness prior are separate, explicit annotation data.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,math,sys
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT.parents[1]/'common';sys.path.insert(0,str(COMMON))
from core import compile_master,digest
from render_data import make_render_data

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def gzwrite(p,v):
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':'),ensure_ascii=False).encode())
def gzread(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def budget():
 n=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
 if n>15*1024**2:raise RuntimeError('r08 additional 15 MiB budget exceeded')
 return n

def measure(contract_path, sheet_path, output_dir, variant=None):
 c=read(contract_path);sheet=Path(sheet_path);out=Path(output_dir);out.mkdir(parents=True,exist_ok=False)
 image_sha=sha(sheet);expected=c['sheet_sha256'] if variant is None else variant['mutant_sha256']
 if image_sha!=expected:raise ValueError('Input image SHA mismatch')
 if sha(ROOT/c['original'])!=c['original_sha256']:raise ValueError('Original image SHA mismatch')
 im=np.array(Image.open(sheet).convert('RGB')).astype(float);masks={};views={};scale=c['alignment']['metres_per_pixel'];cfg=c['mask'];overlay=Image.fromarray(im.astype(np.uint8));draw=ImageDraw.Draw(overlay)
 for name,v in c['views'].items():
  x0,y0,x1,y1=v['crop'];a=im[y0:y1,x0:x1];bg=np.median(np.concatenate([a[:,:8],a[:,-8:]],axis=1),axis=1)
  foreground=np.linalg.norm(a-bg[:,None,:],axis=2)>cfg['background_distance_min'];bright=a.mean(2);chroma=a.max(2)-a.min(2)
  mask=foreground&(bright>cfg['minimum_mean_rgb'])&(chroma<cfg['maximum_chroma'])&(a[:,:,2]-a[:,:,0]>=cfg['blue_minus_red_min'])
  ground=foreground&(np.indices(foreground.shape)[0]>780)&((chroma>5)|(bright>225));ys=np.where(ground)[0]
  if len(ys)<50:raise ValueError('Missing floor landmark in '+name)
  floor=float(np.percentile(ys,99.5));masks[name]=mask
  views[name]={'crop':v['crop'],'axis_u':v['axis_u'],'floor_y':floor,'floor_pixels':len(ys),'floor_landmark_status':'automatic foreground percentile, neutral floor line excluded','alignment_annotation_status':c['alignment']}
  draw.line((x0,floor,x1,floor),fill=(0,190,40),width=2)
  draw.text((x0+8,500),name+' | measured cloth mask / outer samples',fill=(10,30,60))
 sections=[];region=c['region'];n=round((region['world_y_max']-region['world_y_min'])/region['section_step_m'])+1
 for y in np.linspace(region['world_y_min'],region['world_y_max'],n):
  samples={}
  for name,v in views.items():
   py=round(v['floor_y']-y/scale);x0,_,x1,_=v['crop'];xs=np.where(masks[name][py])[0]+x0
   if len(xs)<15:raise ValueError('Missing garment measurement at '+name+' y='+str(py))
   lo,hi=int(xs.min()),int(xs.max());samples[name]={'row_y':py,'pixel_span':[lo,hi],'accepted_pixels':len(xs)}
   draw.ellipse((lo-2,py-2,lo+2,py+2),fill=(240,35,30));draw.ellipse((hi-2,py-2,hi+2,py+2),fill=(240,35,30))
  left_front=(samples['front']['pixel_span'][0]-views['front']['axis_u'])*scale
  left_back=(views['back']['axis_u']-samples['back']['pixel_span'][1])*scale
  front_z=(views['side']['axis_u']-samples['side']['pixel_span'][0])*scale
  back_z=(views['side']['axis_u']-samples['side']['pixel_span'][1])*scale
  if min(-left_front,-left_back,front_z-back_z)<=0:raise ValueError('Degenerate section measurement')
  sections.append({'y_m':float(y),'left_x_front_m':left_front,'left_x_back_m':left_back,'front_back_boundary_conflict_m':abs(left_front-left_back),'radius_x_m':-(left_front+left_back)/2,'center_z_m':(front_z+back_z)/2,'radius_z_m':(front_z-back_z)/2,'samples':samples})
 mask_path=out/'masks.npz';np.savez_compressed(mask_path,**masks);overlay.save(out/'measurement_landmarks.png')
 m={'schema':'riverstone.measured.cloth_region.v1','source':{'sheet_path':str(sheet.resolve()),'sheet_sha256':image_sha,'original_sha256':c['original_sha256'],'prompts_sha256':sha(ROOT/c['prompts']),'AI_status':'AI generated front/side/back design, not original observed hidden geometry','variant':variant},'contract_path':str(Path(contract_path).resolve()),'contract_sha256':sha(contract_path),'extractor_sha256':sha(__file__),'mask_path':str(mask_path.resolve()),'mask_sha256':sha(mask_path),'views':views,'sections':sections,'measurement_boundary':'Thresholded clothing foreground and outer extrema are measured; view semantic crops, axes, scale, sector selection and elliptic/thickness prior are annotated. Side range is full skirt envelope, not identifiable left-panel depth.'}
 write(out/'measurements.json',m);budget();return m

def geometry_from_measurement(m,c):
 sections=m['sections'];angle=math.radians(c['region']['angular_limit_degrees']);tt=np.linspace(-angle,angle,19);surfaces=[]
 for row in sections:
  surfaces.append([[-row['radius_x_m']*math.cos(t),row['y_m'],row['center_z_m']+row['radius_z_m']*math.sin(t)] for t in tt])
 surfaces=np.array(surfaces);ops=[];quads=[];thick=c['region']['thickness_m']
 for iy in range(len(surfaces)-1):
  for it in range(len(tt)-1):
   # Fixed orientation of exterior normal: toward negative X.
   a,b,c0,d=surfaces[iy,it],surfaces[iy,it+1],surfaces[iy+1,it+1],surfaces[iy+1,it]
   for ti,tri in enumerate([[a,b,c0],[a,c0,d]]):
    p,q,r=np.array(tri);u=q-p;u/=np.linalg.norm(u);normal=np.cross(q-p,r-p);normal/=np.linalg.norm(normal)
    if normal[0]>0:q,r=r,q;u=q-p;u/=np.linalg.norm(u);normal=np.cross(q-p,r-p);normal/=np.linalg.norm(normal)
    v=np.cross(normal,u);basis=np.stack([u,v,normal],1);poly=np.array([[0,0],[(q-p)@u,(q-p)@v],[(r-p)@u,(r-p)@v]])
    center=poly.mean(0);poly=center+(poly-center)*1.015
    ops.append({'id':f'row_{iy:03d}_arc_{it:02d}_tri_{ti}','part':'measured_cloth_sector','action':'paint','material':'dress','shape':{'kind':'extrusion','polygon':poly.tolist(),'z_min':-thick/2,'z_max':thick/2,'minimum_cells':0},'transform':{'translation':p.tolist(),'basis':basis.tolist()}})
    quads.append([p.tolist(),q.tolist(),r.tolist(),r.tolist()])
 return ops,quads,surfaces

def build(measurement_path, output_dir):
 path=Path(measurement_path)
 if not path.is_file():raise ValueError('A verified measurement file is mandatory; no geometry fallback')
 m=read(path)
 if m.get('schema')!='riverstone.measured.cloth_region.v1' or len(m.get('sections',[]))<3:raise ValueError('Missing measured cloth sections')
 if sha(m['source']['sheet_path'])!=m['source']['sheet_sha256']:raise ValueError('Stale source image')
 if sha(m['mask_path'])!=m['mask_sha256']:raise ValueError('Stale measured masks')
 if sha(m['contract_path'])!=m['contract_sha256']:raise ValueError('Stale annotation contract')
 c=read(m['contract_path']);ops,quads,surface=geometry_from_measurement(m,c);out=Path(output_dir);out.mkdir(parents=True,exist_ok=False)
 master={'schema':'riverstone.voxel.master.v1','id':'violet_measured_cloth_sector_r08','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':{'dress':{'color':'#f7f7fc'}},'components':[{'id':'cloth_region','parts':[{'id':'measured_cloth_sector','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'cloth_region','component':'cloth_region'}],'constraints':[{'id':'occupied','kind':'nonempty','minimum_cells':10}],'extensions':{'measurement_sha256':sha(path),'source_pixel_sha256':m['source']['sheet_sha256'],'original_sha256':m['source']['original_sha256'],'contract_sha256':m['contract_sha256'],'generator_sha256':sha(__file__),'prior':c['region'],'status':'bounded pixel-constrained sector; no complete garment/hidden wrinkle reconstruction'}}
 compiled=compile_master(master,{'pitch':c['compiler']['pitch_m']},max_candidate_cells=c['compiler']['max_candidates'],max_output_cells=c['compiler']['max_cells']);assert compiled['valid'];render=make_render_data(compiled);render['frame']={'camera_center_m':[-.45,.43,-.2]}
 gzwrite(out/'master.json.gz',master);gzwrite(out/'compiled.cells.json.gz',compiled);gzwrite(out/'region.render.json.gz',render)
 np.savez_compressed(out/'calculated_surface.npz',vertices=surface)
 manifest={'master_hash':digest(master),'operation_geometry_hash':digest(ops),'master_file_sha256':sha(out/'master.json.gz'),'payload_hash':compiled['payload_hash'],'cells':len(compiled['cells']),'quads':render['quad_count'],'candidate_cells':compiled['candidate_cells'],'compiler_sha256':sha(COMMON/'core.py'),'exporter_sha256':sha(COMMON/'render_data.py'),'mesher_sha256':render['provenance']['mesher_sha256'],'measurement_sha256':sha(path),'source_sha256':m['source']['sheet_sha256'],'output_sha256':sha(out/'region.render.json.gz'),'scope':'one left lower-skirt curved sector; body/head/other garment sources unchanged and not replaced','visual_approval':False}
 write(out/'manifest.json',manifest);budget();return manifest

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 a=sub.add_parser('measure');a.add_argument('--contract',type=Path,default=ROOT/'data/region_contract.json');a.add_argument('--sheet',type=Path,default=ROOT/'../../reference_turnarounds_r01/violet_turnaround.png');a.add_argument('--output',type=Path,required=True)
 b=sub.add_parser('build');b.add_argument('measurement',type=Path);b.add_argument('--output',type=Path,required=True)
 args=p.parse_args()
 if args.command=='measure':result=measure(args.contract,args.sheet,args.output)
 else:result=build(args.measurement,args.output)
 print(json.dumps(result if args.command=='build' else {'sections':len(result['sections']),'source':result['source']}))
