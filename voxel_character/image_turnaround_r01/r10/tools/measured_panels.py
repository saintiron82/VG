"""Approved pixels -> independent measurements -> measured section feasibility.
This is not an albedo solver or complete cloth reconstruction. No asset-specific
curves, guessed ellipse or post-compile repair is used.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,itertools,json,math,sys,time,resource
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[2];COMMON=ROOT.parents[1]/'common'
sys.path.insert(0,str(COMMON))
from core import compile_master,digest,prepare_shape,shape_bounds,apply,transform
from render_data import make_render_data

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def gzwrite(p,v):Path(p).write_bytes(gzip.compress(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode(),mtime=0))
def gzread(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def runs(row):
 a=np.r_[False,row,False].astype(np.int8);return np.column_stack((np.where(np.diff(a)==1)[0],np.where(np.diff(a)==-1)[0])).tolist()
def budget():
 n=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
 if n>read(ROOT/'data/measurement_contract.json')['compile']['max_output_bytes']:raise ValueError('r10 disk budget exceeded')
 return n

def extract(contract_path,source_path=None,variant=None):
 cp=Path(contract_path);c=read(cp);sp=Path(source_path) if source_path else REPO/c['source']
 expected=c['source_sha256'] if variant is None else variant['mutant_sha256']
 if sha(sp)!=expected or sha(REPO/c['original'])!=c['original_sha256']:raise ValueError('Source pixel hash mismatch')
 im=np.array(Image.open(sp).convert('RGB'));arrays={};views={}
 for name,v in c['views'].items():
  x0,y0,x1,y1=v['crop'];a=im[y0:y1,x0:x1].astype(float);bright=a.mean(2);chroma=a.max(2)-a.min(2)
  white=(a.min(2)>=c['mask']['exterior_white_min_channel'])&(chroma<=c['mask']['exterior_white_max_chroma'])
  seeds=np.zeros_like(white);seeds[0]=white[0];seeds[-1]=white[-1];seeds[:,0]=white[:,0];seeds[:,-1]=white[:,-1]
  exterior=ndi.binary_propagation(seeds,mask=white);fg=~exterior
  # Flooding classifies 2D exterior. It is not 3D gap filling or component cleanup.
  cloth=fg&(bright>=c['mask']['cloth_min_mean'])&(chroma<=c['mask']['cloth_max_chroma'])&((a[:,:,2]-a[:,:,0])>=c['mask']['cloth_blue_minus_red_min'])
  arrays[name+'_foreground']=fg;arrays[name+'_cloth']=cloth;views[name]=copy.deepcopy(v)
 fv=views['front'];x0,y0,x1,y1=fv['crop'];gray=im[y0:y1,x0:x1].mean(2);edges=[];maps=[]
 for band in c['fold_search_bands']:
  pts=[];lookup={};r=band['difference_radius_px'];ya,yb=band['y_range']
  for x in range(*band['x_range']):
   local=x-x0;scores=gray[ya-r:yb-r,local]-gray[ya+r:yb+r,local];index=int(np.argmax(scores));strength=float(scores[index]);edge=ya+index if strength>=band['minimum_gradient'] else None
   pts.append({'x_px':x,'y_px':edge,'gradient':round(strength,6)});lookup[x]=edge
  edges.append({'id':band['id'],'annotation':band,'measured_points':pts});maps.append(lookup)
 labels=np.zeros_like(arrays['front_cloth'],dtype=np.uint8);rx0,ry0,rx1,ry1=c['region']['front_pixel_roi']
 for y in range(ry0,ry1):
  for x in range(rx0,rx1):
   if not arrays['front_cloth'][y-y0,x-x0]:continue
   e0,e1=(lookup.get(x) for lookup in maps)
   labels[y-y0,x-x0]=4 if e0 is None or e1 is None or e1<=e0 else 1 if y<e0 else 2 if y<e1 else 3
 arrays['front_patch_labels']=labels
 scale=c['alignment']['character_height_m_for_test']/fv['scale_px_per_unit'];rows=[]
 for y in range(ry0,ry1):
  world_y=(fv['sole_y']-y-.5)*scale;view_samples={}
  for name,v in views.items():
   s=c['alignment']['character_height_m_for_test']/v['scale_px_per_unit'];py=int(math.floor(v['sole_y']-world_y/s));py_local=py-v['crop'][1]
   if py_local<0 or py_local>=arrays[name+'_foreground'].shape[0]:raise ValueError('Aligned section lies outside image view')
   view_samples[name]={'pixel_y':py,'foreground_intervals_px':[[a+v['crop'][0],b+v['crop'][0]] for a,b in runs(arrays[name+'_foreground'][py_local])],'cloth_intervals_px':[[a+v['crop'][0],b+v['crop'][0]] for a,b in runs(arrays[name+'_cloth'][py_local])]}
  patches={str(i):[[a+x0,b+x0] for a,b in runs(labels[y-y0]==i)] for i in range(1,5)}
  # Native-row provenance survives into every shape operation.
  rows.append({'source_front_row':y,'y_min_m':(fv['sole_y']-y-1)*scale,'y_max_m':(fv['sole_y']-y)*scale,'patch_intervals_px':patches,'views':view_samples})
 patches=[]
 for i in range(1,5):
  m=labels==i;cc,n=ndi.label(m);pixels=im[y0:y1,x0:x1][m];colors=np.median(pixels,0).tolist() if len(pixels) else None
  patches.append({'id':str(i),'name':['upper_visible_patch','middle_visible_patch','lower_visible_patch','unknown_fold_patch'][i-1],'pixel_count':int(m.sum()),'four_connected_components':int(n),'component_sizes':sorted(np.bincount(cc.ravel())[1:].tolist(),reverse=True),'apparent_rgb_median':colors,'identity_status':'visible face patch candidate; sewn panel identity not established'})
 m={'schema':'riverstone.r10.independent_measurements.v1','source_path':str(sp.resolve()),'source_sha256':sha(sp),'source_parent_sha256':c['source_sha256'],'variant':variant,'original_sha256':c['original_sha256'],'contract_path':str(cp.resolve()),'contract_sha256':sha(cp),'extractor_sha256':sha(__file__),'views':views,'metres_per_front_pixel':scale,'patches':patches,'measured_fold_edges':edges,'sections':rows,'correspondence':c['correspondence'],'interpretation':c['representation']}
 return m,arrays

def save_measurement(cpath,out,source=None,variant=None):
 m,a=extract(cpath,source,variant);out=Path(out);out.mkdir(parents=True,exist_ok=False);np.savez_compressed(out/'masks.npz',**a);m['masks_path']=str((out/'masks.npz').resolve());m['masks_sha256']=sha(out/'masks.npz');gzwrite(out/'measurements.json.gz',m)
 c=read(cpath);roi=c['region']['front_pixel_roi'];img=Image.open(m['source_path']).convert('RGB').crop(roi).resize(((roi[2]-roi[0])*3,(roi[3]-roi[1])*3));d=ImageDraw.Draw(img)
 for i,edge in enumerate(m['measured_fold_edges']):
  for p in edge['measured_points']:
   if p['y_px'] is not None:d.ellipse(((p['x_px']-roi[0])*3-1,(p['y_px']-roi[1])*3-1,(p['x_px']-roi[0])*3+1,(p['y_px']-roi[1])*3+1),fill=['red','lime'][i])
 img.save(out/'measured_fold_overlay.png');budget();return m

def verify_measurement(path):
 p=Path(path)
 if not p.is_file():raise ValueError('Independent measured input is mandatory')
 m=gzread(p)
 if m.get('schema')!='riverstone.r10.independent_measurements.v1' or not m.get('sections'):raise ValueError('Measured sections are mandatory')
 for q,h in [(m['source_path'],m['source_sha256']),(m['contract_path'],m['contract_sha256']),(m['masks_path'],m['masks_sha256'])]:
  if sha(q)!=h:raise ValueError('Stale measured input')
 return m,read(m['contract_path'])

def geometry(m,c,yaw=None):
 angle=c['views']['side']['yaw_degrees'] if yaw is None else yaw;theta=math.radians(angle)
 if not 0<angle<180:raise ValueError('Side projection must constrain depth')
 sv=m['views']['side'];bv=m['views']['back'];fv=m['views']['front'];ss=c['alignment']['character_height_m_for_test']/sv['scale_px_per_unit'];bs=c['alignment']['character_height_m_for_test']/bv['scale_px_per_unit'];fs=m['metres_per_front_pixel'];ops=[];residual=[]
 for row in m['sections']:
  side=[((a-sv['axis_u'])*ss,(b-sv['axis_u'])*ss) for a,b in row['views']['side']['foreground_intervals_px']]
  back=[((bv['axis_u']-b)*bs,(bv['axis_u']-a)*bs) for a,b in row['views']['back']['foreground_intervals_px']]
  total=supported=0
  for label,spans in row['patch_intervals_px'].items():
   for j,(pa,pb) in enumerate(spans):
    xl,xh=(pa-fv['axis_u'])*fs,(pb-fv['axis_u'])*fs;total+=xh-xl
    for bi,(bl,bh) in enumerate(back):
     lo,hi=max(xl,bl),min(xh,bh)
     if hi<=lo:continue
     if side:supported+=hi-lo
     for si,(ul,uh) in enumerate(side):
      # Exact half-plane intersection: front/back X interval and side U strip.
      # U = cos(theta)*X - sin(theta)*Z. No guessed center or thickness.
      poly=[[x,-((math.cos(theta)*x-u)/math.sin(theta))] for x,u in [(lo,ul),(hi,ul),(hi,uh),(lo,uh)]]
      ops.append({'id':f'row{row["source_front_row"]}_p{label}_r{j}_b{bi}_s{si}','part':'patch_'+label,'action':'paint','material':'patch_'+label,'shape':{'kind':'extrusion','polygon':poly,'z_min':row['y_min_m'],'z_max':row['y_max_m'],'minimum_cells':0},'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
  residual.append({'source_row':row['source_front_row'],'front_width_m':total,'feasible_width_m':supported,'unsupported_width_m':max(0,total-supported)})
 mats={'patch_'+p['id']:{'color':'#'+''.join(f'{int(round(v)):02x}' for v in p['apparent_rgb_median'])} for p in m['patches'] if p['pixel_count']}
 master={'schema':'riverstone.voxel.master.v1','id':'violet_r10_measured_panel_feasibility','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':mats,'components':[{'id':'measured_sections','parts':[{'id':p,'pivot':[0,0,0]} for p in mats],'operations':ops}],'instances':[{'id':'measured_sections','component':'measured_sections'}],'constraints':[{'id':'has_measured_support','kind':'nonempty','minimum_cells':1}],'extensions':{'source_pixel_sha256':m['source_sha256'],'contract_sha256':m['contract_sha256'],'measurement_content_sha256':digest(m),'generator_sha256':sha(__file__),'side_yaw_hypothesis_degrees':angle,'side_yaw_uncertainty_degrees':c['alignment']['side_yaw_uncertainty_degrees'],'representation':c['representation'],'correspondence':m['correspondence'],'approved_reference':c['approval'],'complete_garment_reconstruction':False}}
 return master,residual

def preflight(m,c,master):
 pitch=c['compile']['pitch_m'];candidates=0;allpoints=[]
 for op in master['components'][0]['operations']:
  lo,hi=shape_bounds(prepare_shape(op['shape'],pitch));pts=[apply(transform(op['transform']),p) for p in itertools.product(*zip(lo,hi))];low=np.min(pts,0);high=np.max(pts,0);candidates+=math.prod(max(0,math.ceil(b/pitch-1e-9)-math.floor(a/pitch+1e-9)) for a,b in zip(low,high));allpoints.extend(pts)
 if allpoints:
  low=np.min(allpoints,0);high=np.max(allpoints,0);bound=math.prod(max(0,math.ceil(b/pitch)-math.floor(a/pitch)) for a,b in zip(low,high))
 else:low=high=np.zeros(3);bound=0
 return {'operations':len(master['components'][0]['operations']),'exact_candidate_cell_iterations_estimate':candidates,'output_bounding_grid_cells_upper_bound':bound,'world_bounds_m':[low.tolist(),high.tolist()],'compiler_sha256':sha(COMMON/'core.py'),'pitch_m':pitch,'estimated_wall_seconds':[2,20],'estimated_peak_rss_mib':[70,160],'estimate_status':'Conservative unbenchmarked timing/RSS; candidate iteration count derived by common shape bounds, no compile yet.'}

def build(mp,out,strict=False,yaw=None):
 m,c=verify_measurement(mp);master,residual=geometry(m,c,yaw)
 conflicts=[r for r in residual if r['front_width_m']>0 and r['feasible_width_m']==0]
 if strict and conflicts:raise ValueError('Contradictory view support: '+str(len(conflicts))+' nonempty front rows have no feasible depth')
 out=Path(out);out.mkdir(parents=True,exist_ok=False);t=time.monotonic();compiled=compile_master(master,{'pitch':c['compile']['pitch_m']},max_candidate_cells=c['compile']['max_candidates'],max_output_cells=c['compile']['max_cells']);render=make_render_data(compiled)
 gzwrite(out/'master.json.gz',master);gzwrite(out/'compiled.cells.json.gz',compiled);gzwrite(out/'region.render.json.gz',render)
 report={'source_sha256':m['source_sha256'],'measurement_file_sha256':sha(mp),'master_content_sha256':digest(master),'compiled_payload_sha256':compiled['payload_hash'],'cells':len(compiled['cells']),'quads':render['quad_count'],'candidate_cells':compiled['candidate_cells'],'wall_seconds':time.monotonic()-t,'maxrss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'compiler_sha256':compiled['compiler_source_hash'],'renderer_exporter_sha256':render['provenance']['exporter_sha256'],'mesher_sha256':render['provenance']['mesher_sha256'],'per_row_constraint_residual':residual,'zero_feasible_rows':len(conflicts),'reconstruction_approved':False}
 write(out/'manifest.json',report);budget();return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['measure','preflight','build']);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();cp=ROOT/'data/measurement_contract.json'
 if a.command=='measure':
  m=save_measurement(cp,a.output);print(json.dumps({'sections':len(m['sections']),'patches':m['patches']}))
 elif a.command=='preflight':
  m,c=verify_measurement(a.input);master,r=geometry(m,c);report=preflight(m,c,master);write(a.output,report);print(json.dumps(report))
 else:print(json.dumps(build(a.input,a.output)))
