"""Measured multi-contour panel candidates and 3-view feasible-depth CSG.
All geometry is sourced from measured masks; no ellipse/hand 3D section,
physical thickness, smoothing, fragment deletion or hole filling is used.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,math,sys
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1];COMMON=ROOT.parents[1]/'common';sys.path.insert(0,str(COMMON))
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
 if n>12*1048576:raise RuntimeError('r09 12MiB budget exceeded')
 return n

def runs(row):
 a=np.r_[False,row,False].astype(np.int8);return np.column_stack([np.where(np.diff(a)==1)[0],np.where(np.diff(a)==-1)[0]]).tolist()

def contours(mask):
 """Exact unit-pixel boundaries, directed with occupied area on right.
 No area threshold; collinear vertices only are removed exactly.
 """
 a=np.pad(mask,1);h,w=mask.shape;edges={}
 def add(u,v):edges.setdefault(u,[]).append(v)
 for y,x in np.argwhere(mask):
  if not a[y,x+1]:add((int(x),int(y)),(int(x+1),int(y)))
  if not a[y+1,x+2]:add((int(x+1),int(y)),(int(x+1),int(y+1)))
  if not a[y+2,x+1]:add((int(x+1),int(y+1)),(int(x),int(y+1)))
  if not a[y+1,x]:add((int(x),int(y+1)),(int(x),int(y)))
 direction={(1,0):0,(0,1):1,(-1,0):2,(0,-1):3};polygons=[]
 while edges:
  start=min(edges);p=start;prev=None;loop=[]
  while True:
   loop.append(p);choices=edges[p]
   if prev is None:q=choices[0]
   else:
    old=direction[(p[0]-prev[0],p[1]-prev[1])]
    q=min(choices,key=lambda q:{1:0,0:1,3:2,2:3}[(direction[(q[0]-p[0],q[1]-p[1])]-old)%4])
   choices.remove(q)
   if not choices:del edges[p]
   prev,p=p,q
   if p==start:break
  keep=[]
  for i,b in enumerate(loop):
   aa=loop[i-1];cc=loop[(i+1)%len(loop)]
   if (b[0]-aa[0])*(cc[1]-b[1])!=(b[1]-aa[1])*(cc[0]-b[0]):keep.append(b)
  area=sum(keep[i][0]*keep[(i+1)%len(keep)][1]-keep[(i+1)%len(keep)][0]*keep[i][1] for i in range(len(keep)))/2
  polygons.append({'polygon_px':keep,'signed_area_px':area,'kind':'outer' if area>0 else 'hole'})
 return sorted(polygons,key=lambda v:-abs(v['signed_area_px']))

def measure(contract_path,source_path,out,variant=None,save_images=True):
 contract_path=Path(contract_path);c=read(contract_path);source_path=Path(source_path);out=Path(out);out.mkdir(parents=True,exist_ok=False)
 expected=c['source_sha256'] if variant is None else variant['sha256'];assert sha(source_path)==expected;assert sha(ROOT/c['original'])==c['original_sha256']
 image=np.array(Image.open(source_path).convert('RGB'));im=image.astype(float);scale=c['alignment']['metres_per_pixel'];arrays={};views={}
 for name,v in c['views'].items():
  x0,y0,x1,y1=v['crop'];a=im[y0:y1,x0:x1];bg=np.median(np.concatenate([a[:,:8],a[:,-8:]],1),axis=1);fg=np.linalg.norm(a-bg[:,None],axis=2)>c['mask']['background_distance_min'];bright=a.mean(2);chroma=a.max(2)-a.min(2);ground=fg&(np.indices(fg.shape)[0]>780)&((chroma>5)|(bright>225));ys=np.where(ground)[0]
  if len(ys)<50:raise ValueError('Missing measured ground landmark')
  floor=float(np.percentile(ys,99.5));cloth=fg&(bright>c['mask']['cloth_min_mean'])&(chroma<c['mask']['cloth_max_chroma'])&(a[:,:,2]-a[:,:,0]>=c['mask']['cloth_blue_minus_red_min']);arrays[name+'_fg']=fg;arrays[name+'_cloth']=cloth;views[name]={**v,'floor_y':floor,'floor_status':'automatic foreground percentile'}
 front=arrays['front_cloth'];h,w=front.shape;selected=np.zeros_like(front);ymin,ymax=c['region']['world_y_min'],c['region']['world_y_max']
 for y in range(h):
  wy=(views['front']['floor_y']-y)*scale
  if ymin<=wy<=ymax:
   xx=np.where(front[y])[0]
   if len(xx):selected[y]=front[y]&(np.arange(w)<=(xx.min()+c['views']['front']['axis_u'])/2)
 # Two actual pixel edges, with missing edges marked unknown rather than
 # filled with a hand-authored curve. Every selected pixel is retained.
 gray=im[:837,:660].mean(2);seams=[]
 for ann in c['front_visible_boundary_annotations']:
  values=[]
  for x in range(*ann['x_search']):
   a,b=ann['y_search'];scores=gray[a-2:b-2,x]-gray[a+2:b+2,x];i=int(np.argmax(scores));confidence=float(scores[i]);values.append({'x':x,'y':a+i if confidence>=8 else None,'edge_strength':confidence})
  seams.append({'id':ann['id'],'annotation':ann,'samples':values})
 maps=[{p['x']:p['y'] for p in s['samples']} for s in seams];labels=np.zeros(selected.shape,np.uint8)
 for y,x in np.argwhere(selected):
  a=maps[0].get(int(x));b=maps[1].get(int(x));labels[y,x]=4 if a is None or b is None else (1 if y<a else 2 if y<b else 3)
 arrays['front_selected']=selected;arrays['front_panel_labels']=labels;panels=[]
 for i,name in [(1,'upper_visible_patch'),(2,'middle_visible_patch'),(3,'lower_visible_patch'),(4,'boundary_unknown_patch')]:
  mask=labels==i;cc,n=ndi.label(mask);colors=image[:837,:660][mask];color=np.median(colors,axis=0).astype(int).tolist() if len(colors) else [240,240,250]
  panels.append({'id':name,'label':i,'pixels':int(mask.sum()),'measured_4_connected_components':int(n),'component_sizes_pixels':sorted(np.bincount(cc.ravel())[1:].tolist(),reverse=True),'color_rgb_median':color,'contours':contours(mask),'semantic_status':'visible fold patch candidate; sewn-panel identity unknown'})
 # Exact intervals preserve gaps, not one min/max envelope.
 interval_rows=[]
 for py in np.where(selected.any(1))[0]:
  wy=(views['front']['floor_y']-py)*scale;sv={}
  for name in ['front','side','back']:
   row=int(round(views[name]['floor_y']-wy/scale));sv[name]={'row_y':row,'foreground_intervals_px':runs(arrays[name+'_fg'][row]),'cloth_intervals_px':runs(arrays[name+'_cloth'][row])}
  interval_rows.append({'front_y':int(py),'world_y_m':float(wy),'views':sv,'panel_intervals':{p['id']:runs(labels[py]==p['label']) for p in panels}})
 np.savez_compressed(out/'measured_masks.npz',**arrays);m={'schema':'riverstone.measured.multicontour_panels.v1','source':{'path':str(source_path.resolve()),'sha256':sha(source_path),'original_sha256':c['original_sha256'],'prompts_sha256':sha(ROOT/c['prompts']),'AI_views':True,'variant':variant},'contract_path':str(contract_path.resolve()),'contract_sha256':sha(contract_path),'extractor_sha256':sha(__file__),'views':views,'panels':panels,'measured_edges':seams,'interval_rows':interval_rows,'masks_path':str((out/'measured_masks.npz').resolve()),'masks_sha256':sha(out/'measured_masks.npz'),'view_correspondence':c['view_correspondence'],'manual_automatic_boundary':'Search bands/semantic patch names/crops/axes/scale are explicit annotations. Masks, edge locations, contour vertices, intervals and colors come from actual pixels.'};write(out/'measurements.json',m)
 if save_images:
  crop=Image.fromarray(image[:837,:660]).crop((0,540,250,770)).resize((750,690));dr=ImageDraw.Draw(crop)
  for j,s in enumerate(seams):
   points=[(q['x']*3,(q['y']-540)*3) for q in s['samples'] if q['y'] is not None]
   for q in points:dr.ellipse((q[0]-2,q[1]-2,q[0]+2,q[1]+2),fill=['red','lime'][j])
  crop.save(out/'actual_measured_fold_edges.png');rgb=np.full((h,w,3),245,np.uint8)
  for i,col in [(1,[230,170,100]),(2,[140,190,225]),(3,[190,140,210]),(4,[180,180,180])]:rgb[labels==i]=col
  Image.fromarray(rgb).crop((0,540,250,770)).resize((750,690),Image.Resampling.NEAREST).save(out/'panel_candidate_masks.png')
 budget();return m

def world_polygon(poly,view,name,scale):
 x0,_,_,_=view['crop'];out=[]
 for u,v in poly:
  horiz=((u+x0)-view['axis_u'])*scale
  if name in ['side','back']:horiz=-horiz
  out.append([horiz,(view['floor_y']-v)*scale])
 return out

def build(measurement_path,out,strict=False):
 mp=Path(measurement_path)
 if not mp.is_file():raise ValueError('Verified independent measurement input required')
 m=read(mp)
 if m.get('schema')!='riverstone.measured.multicontour_panels.v1':raise ValueError('Missing panel/contour measurements')
 for path,expected in [(m['source']['path'],m['source']['sha256']),(m['contract_path'],m['contract_sha256']),(m['masks_path'],m['masks_sha256'])]:
  if sha(path)!=expected:raise ValueError('Stale measured input')
 c=read(m['contract_path']);a=np.load(m['masks_path']);scale=c['alignment']['metres_per_pixel'];selected=a['front_selected'];frontv=m['views']['front'];backv=m['views']['back'];sidev=m['views']['side'];rows=[];unsupported=0;total=int(selected.sum())
 for py in np.where(selected.any(1))[0]:
  wy=(frontv['floor_y']-py)*scale;sy=round(sidev['floor_y']-wy/scale);by=round(backv['floor_y']-wy/scale);xx=np.where(selected[py])[0];backu=np.rint(backv['axis_u']-(xx-frontv['axis_u'])).astype(int)-backv['crop'][0];support=np.zeros(len(xx),bool);valid=(backu>=0)&(backu<a['back_fg'].shape[1]);support[valid]=a['back_fg'][by,backu[valid]];depths=runs(a['side_fg'][sy]);n=int((~support).sum()) if depths else len(xx);unsupported+=n;rows.append({'front_y':int(py),'source_pixels':len(xx),'unsupported_by_silhouette_intersection_pixels':n,'side_depth_interval_count':len(depths),'whole_row_infeasible':n==len(xx)})
 conflicts=[r for r in rows if r['whole_row_infeasible']]
 if strict and conflicts:raise ValueError('Contradictory view constraints: measured front panel has no feasible depth in '+str(len(conflicts))+' rows')
 # Global Z bounds are derived from all measured side foreground intervals
 # in this exact band, not an artist-authored depth or cloth thickness.
 zs=[]
 for row in m['interval_rows']:
  for lo,hi in row['views']['side']['foreground_intervals_px']:zs.extend([(sidev['axis_u']-(lo+sidev['crop'][0]))*scale,(sidev['axis_u']-(hi+sidev['crop'][0]))*scale])
 if not zs:raise ValueError('No measured side depth support')
 zlo,zhi=min(zs),max(zs);ops=[];mats={};partids=[]
 for panel in m['panels']:
  if not panel['pixels']:continue
  pid=panel['id'];partids.append(pid);mats[pid]={'color':'#'+''.join(f'{x:02x}' for x in panel['color_rgb_median'])}
  for i,contour in enumerate(panel['contours']):
   kind=contour['kind'];ops.append({'id':pid+'_contour_'+str(i),'part':pid,'action':'paint' if kind=='outer' else 'cut','material':pid,'selector':{'part':pid},'shape':{'kind':'extrusion','polygon':world_polygon(contour['polygon_px'],frontv,'front',scale),'z_min':zlo,'z_max':zhi,'minimum_cells':0}})
 # Background is known free space, while other foreground is potentially
 # occluding. It cannot identify a particular panel or be used as its target.
 for name in ['side','back']:
  view=m['views'][name];fg=a[name+'_fg'];yy=np.indices(fg.shape)[0];wy=(view['floor_y']-yy)*scale;within=(wy>=c['region']['world_y_min'])&(wy<=c['region']['world_y_max']);bg=(~fg)&within
  polygons=contours(bg)
  # Background holes are foreground islands: represent each connected
  # background component with pixel-exact row runs if holes exist? Instead
  # use nested CSG components so cuts respect complete binary foreground.
  # We construct a filled allowed silhouette and cut its complementary runs
  # as concave row-strip polygons, merging identical spans vertically.
  spans={};rectangles=[]
  for y in range(fg.shape[0]+1):
   current=set(tuple(v) for v in runs(bg[y])) if y<fg.shape[0] else set()
   for run,start in list(spans.items()):
    if run not in current:rectangles.append((run[0],start,run[1],y));del spans[run]
   for run in current:
    if run not in spans:spans[run]=y
  # Rectangles are exact measured free-space intervals, not sculpted blocks.
  # Painted body stays arbitrary multi-contour polygons; these cuts perform
  # the orthographic silhouette intersection without filling image holes.
  for i,(u0,v0,u1,v1) in enumerate(rectangles):
   poly=world_polygon([[u0,v0],[u1,v0],[u1,v1],[u0,v1]],view,name,scale);shape={'kind':'extrusion','polygon':poly,'z_min':-2 if name=='side' else zlo,'z_max':2 if name=='side' else zhi,'minimum_cells':0};op={'id':name+'_free_space_'+str(i),'part':partids[0],'action':'cut','shape':shape}
   if name=='side':op['transform']={'basis':[[0,0,-1],[0,1,0],[1,0,0]]}
   ops.append(op)
 master={'schema':'riverstone.voxel.master.v1','id':'violet_multicontour_feasible_panels_r09','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':mats,'components':[{'id':'feasibility','parts':[{'id':p,'pivot':[0,0,0]} for p in partids],'operations':ops}],'instances':[{'id':'feasibility','component':'feasibility'}],'constraints':[{'id':'occupied','kind':'nonempty','minimum_cells':1}],'extensions':{'source_pixel_sha256':m['source']['sha256'],'measurement_sha256':sha(mp),'contract_sha256':m['contract_sha256'],'generator_sha256':sha(__file__),'representation':c['representation'],'view_correspondence':c['view_correspondence'],'reconstruction_valid':False,'reason':'unknown side/back panel correspondence and nonzero source silhouette residual; feasible-depth volume only'}}
 out=Path(out);out.mkdir(parents=True,exist_ok=False);compiled=compile_master(master,{'pitch':c['compile']['pitch_m']},max_candidate_cells=c['compile']['max_candidates'],max_output_cells=c['compile']['max_output_cells']);render=make_render_data(compiled);render['frame']={'camera_center_m':[-.5,.43,-.2]};gzwrite(out/'master.json.gz',master);gzwrite(out/'compiled.cells.json.gz',compiled);gzwrite(out/'region.render.json.gz',render)
 report={'master_hash':digest(master),'payload_hash':compiled['payload_hash'],'cells':len(compiled['cells']),'quads':render['quad_count'],'candidate_cells':compiled['candidate_cells'],'measured_front_pixels':total,'source_pixels_excluded_by_other_view_silhouettes':unsupported,'excluded_ratio':unsupported/total,'whole_row_infeasible_count':len(conflicts),'rows':rows,'compiler_sha256':sha(COMMON/'core.py'),'mesher_sha256':render['provenance']['mesher_sha256'],'source_sha256':m['source']['sha256'],'measurement_sha256':sha(mp),'master_file_sha256':sha(out/'master.json.gz'),'output_sha256':sha(out/'region.render.json.gz'),'reconstruction_approved':False,'depth_is_surface':False,'depth_status':'all silhouette-feasible intervals retained as uncertainty volume; no guessed shell or thickness'};write(out/'manifest.json',report);budget();return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['measure','build']);p.add_argument('--input',type=Path);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 if args.command=='measure':r=measure(ROOT/'data/measurement_contract.json',args.input or ROOT/'../../reference_turnarounds_r01/violet_turnaround.png',args.output);print(json.dumps({'panels':[(p['id'],p['pixels'],len(p['contours'])) for p in r['panels']]}))
 else:print(json.dumps(build(args.input,args.output)))
