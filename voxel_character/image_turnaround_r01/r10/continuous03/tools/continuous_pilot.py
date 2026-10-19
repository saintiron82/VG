"""Measured connected-domain pilot; source data, depth priors and shared adapters.
Only a selected image-domain cloth face and side-hair path are produced.
No global DCT, discarded voxel islands, or common grammar extensions.
"""
from pathlib import Path
import os,sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
sys.path.insert(0,str(ROOT/'tools'))
from build_full_measured import *
from measure_semantic_views import classify
from scipy.optimize import lsq_linear
from scipy.linalg import solve_banded
from PIL import ImageDraw


def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(p,v):p.write_bytes(gzip.compress(canonical(v),mtime=0))
def rounded(v):
    if isinstance(v,dict):return {k:rounded(x) for k,x in v.items()}
    if isinstance(v,list):return [rounded(x) for x in v]
    if isinstance(v,(float,np.floating)):return round(float(v),10)
    if isinstance(v,np.integer):return int(v)
    return v

def master(ops,mats,label):
    return {'schema':'riverstone.voxel.master.v1','id':label,'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':mats,'components':[{'id':'pilot','parts':[{'id':p,'pivot':[0,0,0]} for p in sorted({o['part'] for o in ops})],'operations':ops}],'instances':[{'id':'character','component':'pilot'}],'constraints':[{'id':'nonempty','kind':'nonempty','minimum_cells':1}],'extensions':{'source_sha256':C['source_sha256'],'source_contract_sha256':sha(ROOT/'data/measurement_contract.json'),'generator_sha256':sha(__file__),'assumptions_sha256':sha(BASE/'data/pilot_priors.json'),'art_approved':False}}

C=read(ROOT/'data/measurement_contract.json');height=C['alignment']['character_height_m_for_test'];F=C['views']['front'];S=C['views']['side'];scale=height/F['scale_px_per_unit'];ss=height/S['scale_px_per_unit'];angle=math.radians(S['yaw_degrees']);BM=np.load(ROOT/'full_measurement/violet_branches/branch_masks.npz');VOL=gzread(ROOT/'full01/generated/volume_master_v03.json.gz');FIT=gzread(ROOT/'full01/evidence/volume_fit_v03.json.gz');ANN=read(ROOT/'data/violet_full_semantic_annotations_v02.json');SOURCE=np.array(Image.open(REPO/C['source']).convert('RGB'));assert sha(REPO/C['source'])==C['source_sha256']


def footprint(part,view='front'):
    ops=[o for o in VOL['components'][0]['operations'] if o['part']==part]
    q=[q for o in ops for q in primitive_quads(o)]
    return project({'groups':[{'quads':q}]},C['views'][view],height)


def fresh_semantic(source,cl,view):
    spec=next(x for x in ANN['classes'] if x['id']==cl);v=C['views'][view];x0,y0,x1,y1=v['crop'];rgb=source[y0:y1,x0:x1];m=np.zeros(rgb.shape[:2],bool)
    for xa,ya,xb,yb in spec['boxes'].get(view,[]):m[max(0,ya-y0):yb-y0,max(0,xa-x0):xb-x0]=True
    for xa,ya,xb,yb in spec.get('exclude_boxes',{}).get(view,[]):m[max(0,ya-y0):yb-y0,max(0,xa-x0):xb-x0]=False
    m&=classify(rgb,spec['color'])
    # Pixel-local exterior rejection only. No image-wide flood or watershed;
    # semantic fences are explicit frozen annotation domains.
    a=rgb.astype(int);guide=(a[:,:,2]>=245)&(a[:,:,2]-a[:,:,0]>=25)&(a[:,:,2]-a[:,:,1]>=15)&(a[:,:,1]-a[:,:,0]>=6)
    return m&~guide&~BM[view+'__excluded__halo_semantic']


def rowdata(mask):return [{'y':int(y),'runs':[[a+F['crop'][0],b+F['crop'][0]] for a,b in runs(mask[y])]} for y in np.where(mask.any(1))[0]]


def measure(source,prior):
    head=footprint('head_cap_closed');eh=fresh_semantic(source,'hair_visible','front')&BM['front__eligible__hair_visible']
    residual=eh&~head;labels,n=ndi.label(residual);seed=prior['hair']['seed_xy_px'];label=int(labels[seed[1],seed[0]-F['crop'][0]])
    if not label:raise ValueError('Explicit hair seed no longer belongs to measured residual; reannotation required')
    domain=labels==label
    # A measured row-run path, selected by an explicit seed. Other runs remain
    # unselected pilot data, not deleted from a full asset.
    sy=seed[1];seedrun=next((r for r in runs(domain[sy]) if r[0]<=seed[0]-F['crop'][0]<r[1]),None)
    path={sy:seedrun}
    breaks=[]
    for direction in [-1,1]:
        old=seedrun
        for y in range(sy+direction,domain.shape[0] if direction>0 else -1,direction):
            candidates=runs(domain[y]);over=[r for r in candidates if min(r[1],old[1])>max(r[0],old[0])]
            if not over:breaks.append({'y':y,'reason':'no source-adjacent overlapping measured interval'});break
            ranked=sorted(over,key=lambda r:(-min(r[1],old[1])+max(r[0],old[0]),abs(sum(r)-sum(old)),r[0]));old=ranked[0];path[y]=old
    hairrows=[{'y':y,'x0':r[0]+F['crop'][0],'x1':r[1]+F['crop'][0]} for y,r in sorted(path.items())]
    # Frozen image-derived branch mask is an explicit semantic ownership fence.
    # Reclassify source pixels inside it; do not rerun global seed competition.
    fence=BM[prior['cloth']['frozen_domain_key']];cm=fence&fresh_semantic(source,'skirt_visible','front')
    out={'source_pixel_sha256':hashlib.sha256(np.ascontiguousarray(source).tobytes()).hexdigest(),'cloth_mask':cm,'hair_domain':domain,'hair_rows':hairrows,'hair_breaks':breaks,'head_footprint':head,'hair_eligible':eh,'hair_residual':residual,'cloth_rows':rowdata(cm),'side_hair':fresh_semantic(source,'hair_visible','side')&BM['side__eligible__hair_visible'],'side_cloth':fresh_semantic(source,'skirt_visible','side')&BM['side__eligible__skirt_visible'],'ownership':{'eligible_pixels':int(eh.sum()),'head_owned':int((eh&head).sum()),'strand_owned':int(residual.sum()),'missing':int((eh&~((eh&head)|residual)).sum()),'double_owned':int(((eh&head)&residual).sum()),'hair_pilot_pixels':sum(r['x1']-r['x0'] for r in hairrows),'unselected_residual_pixels':int(residual.sum())-sum(r['x1']-r['x0'] for r in hairrows)}}
    return out


def section_at(part,y):
    data=next(x for x in FIT if x['id']==part)
    return next((s for s in data['sections'] if s['world_y_range'][0]-1e-8<=y<=s['world_y_range'][1]+1e-8),None)

def z_line(poly,x):
    zs=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if min(a[0],b[0])-1e-9<=x<=max(a[0],b[0])+1e-9 and abs(a[0]-b[0])>1e-12:zs.append(a[1]+(x-a[0])/(b[0]-a[0])*(b[1]-a[1]))
    return [min(zs),max(zs)] if zs else None


def solve_depth(rows,side,part,prior):
    ys=np.array([r['y'] for r in rows]);xs=np.array([(r['x0']+r['x1'])/2 for r in rows]);cx=(xs-F['axis_u'])*scale;worldy=(F['sole_y']-ys-.5)*scale
    supports=[];chosen=[];previous=None;missing=[]
    anchor_sec=section_at(part,worldy[0]);anchor_poly=anchor_sec['polygon_xz_m'] if anchor_sec else None;root_r=(rows[0]['x1']-rows[0]['x0'])*scale/2
    if anchor_poly:
        # Choose an actual volume surface point nearest to observed root X.
        target=np.array(min(anchor_poly,key=lambda p:abs(p[0]-cx[0])))
        rootz=float(target[1]);rootx_gap=abs(float(target[0])-cx[0])
    else:rootz=0.;rootx_gap=None
    for i,(y,x) in enumerate(zip(worldy,cx)):
        sy=int(math.floor(S['sole_y']-y/ss));spans=runs(side[sy]) if 0<=sy<side.shape[0] else []
        zints=[]
        for a,b in spans:
            ul=(a+S['crop'][0]-S['axis_u'])*ss;uh=(b+S['crop'][0]-S['axis_u'])*ss
            zints.append([(math.cos(angle)*x-uh)/math.sin(angle),(math.cos(angle)*x-ul)/math.sin(angle)])
        if not zints:missing.append(int(ys[i]));supports.append([]);chosen.append(None);continue
        if i==0:
            contact_radius=root_r if part=='head_cap_closed' else prior['cloth']['normal_thickness_m']/2
            contacts=[]
            for sec in next(v for v in FIT if v['id']==part)['sections']:
                yl,yh=sec['world_y_range'];cy=min(max(float(y),yl),yh);dy=abs(cy-y)
                if dy>contact_radius:continue
                span=z_line(sec['polygon_xz_m'],float(x))
                if not span:continue
                for zi,(lo,hi) in enumerate(zints):
                    a,b=max(lo,span[0]),min(hi,span[1])
                    if b<a:continue
                    if dy>1e-10:
                        # A horizontal cap is a true boundary of this closed
                        # extrusion. Keep enough overlap inside measured radius.
                        zz=(a+b)/2;distance=dy
                    else:
                        faces=[q for q in span if lo<=q<=hi]
                        if not faces:continue
                        zz=min(faces,key=abs);distance=0.
                    contacts.append((distance,abs(zz),zz,float(cy),zi,sec['source_y_range']))
            if contacts:
                best_contact=min(contacts);rootz=best_contact[2];rootx_gap=0.;anchor_contact={'parent_point_xyz_m':[float(x),best_contact[3],rootz],'center_to_parent_surface_m':best_contact[0],'contact_radius_m':contact_radius,'parent_source_y_range':best_contact[5],'method':'Exact measured-parent extrusion side or cap boundary intersected with actual side support. Root X/Y unchanged.'}
            else:anchor_contact={'failure':'No actual parent surface contact lies in measured root radius and side support. No connector added.'}
        target=rootz if previous is None else previous
        best=min(zints,key=lambda ab:(max(ab[0]-target,0,target-ab[1]),abs(sum(ab)/2-target)))
        previous=min(max(target,best[0]),best[1]);chosen.append(best);supports.append(zints)
    if missing:raise ValueError('Measured side support absent at rows '+str(missing))
    bounds=np.array(chosen);n=len(rows);D1=np.diff(np.eye(n),axis=0);D2=np.diff(np.eye(n),n=2,axis=0);target=np.array([sum(b)/2 for b in chosen]);weights=prior['depth_solver']
    A=np.r_[np.eye(n)*math.sqrt(weights['data_weight']),D1*math.sqrt(weights['tangent_weight']),D2*math.sqrt(weights['curvature_weight'])];b=np.r_[target*math.sqrt(weights['data_weight']),np.zeros(len(D1)+len(D2))]
    # Anchor at a measured-body surface depth only where side allows it.
    root_feasible='failure' not in anchor_contact and bounds[0,0]-1e-9<=rootz<=bounds[0,1]+1e-9
    if root_feasible:
        rest=lsq_linear(A[:,1:],b-A[:,0]*rootz,bounds=(bounds[1:,0],bounds[1:,1]),tol=1e-12,max_iter=200);z=np.r_[rootz,rest.x]
    else:
        rest=lsq_linear(A,b,bounds=(bounds[:,0],bounds[:,1]),tol=1e-12,max_iter=200);z=rest.x
    if not rest.success:raise ValueError('Continuous bounded depth solve failed')
    record={'rows':rows,'side_z_allowed_intervals_m':supports,'chosen_intervals_m':chosen,'solved_center_z_m':z.tolist(),'data_residual_l2':float(np.linalg.norm(z-target)),'tangent_energy':float(np.sum((D1@z)**2)),'curvature_energy':float(np.sum((D2@z)**2)),'anchor_part':part,'actual_parent_contact':anchor_contact,'anchor_y_m':float(worldy[0]),'root_x_gap_m':rootx_gap,'measured_root_halfwidth_m':root_r,'anchor_depth_compatible_with_side':bool(root_feasible),'hidden_attachment_status':'Surface depth constrained to an actual parent volume boundary when compatible. X/Y are measured and unchanged; no new connector is fabricated. Contact still requires voxel verification.','correspondence':'side silhouette is permissive support only; selected interval branch is a continuity hypothesis','dependency_scope':'this explicitly selected connected panel/strand; outside scope cannot change'}
    return cx,worldy,z,record


def material(source,mask,name):
    v=F;rgb=np.median(source[v['crop'][1]:v['crop'][3],v['crop'][0]:v['crop'][2]][mask],0);return {name:{'color':'#'+''.join(f'{int(v):02x}' for v in np.round(rgb))}}


def triangle_prism(pts,part,mat,ident,thick):
    p=np.array(pts);u=p[1]-p[0];u/=np.linalg.norm(u);n=np.cross(p[1]-p[0],p[2]-p[0]);n/=np.linalg.norm(n);v=np.cross(n,u)
    return {'id':ident,'part':part,'action':'paint','material':mat,'shape':{'kind':'extrusion','polygon':[[float((q-p[0])@u),float((q-p[0])@v)] for q in p],'z_min':-thick/2,'z_max':thick/2,'minimum_cells':0},'transform':{'translation':p[0].tolist(),'basis':np.stack([u,v,n],axis=1).tolist()}}


def cloth_build(m,source,prior):
    mask=m['cloth_mask'];rows=[]
    for r in m['cloth_rows']:
        xs=[x for a,b in r['runs'] for x in range(a,b)];rows.append({'y':r['y'],'x0':min(xs),'x1':max(xs)+1})
    cx,wy,z,fit=solve_depth(rows,m['side_cloth'],'torso_closed',prior);ys=np.array([r['y']+.5 for r in rows]);umin=math.cos(angle)*cx-math.sin(angle)*z
    def vertex(x,y):
        wx=(x-F['axis_u'])*scale;worldy=(F['sole_y']-y)*scale;u=np.interp(y,ys,umin);zz=(math.cos(angle)*wx-u)/math.sin(angle);return [wx,worldy,float(zz)]
    ops=[];quads=[]
    # Exact native binary domain: shared pixel-corner vertices, not independent
    # row-width rectangles. Adjacent faces share the same continuous depth.
    for y,x in zip(*np.where(mask)):
        x+=F['crop'][0];p=[vertex(x,y),vertex(x+1,y),vertex(x+1,y+1),vertex(x,y+1)];quads.append(p)
        for k,t in enumerate(((0,1,2),(0,2,3))):ops.append(triangle_prism([p[j] for j in t],'cloth_pilot','cloth',f'cloth_y{y}_x{x}_t{k}',prior['cloth']['normal_thickness_m']))
    return ops,material(source,mask,'cloth'),fit,quads


def lathe_between(a,b,r0,r1,ident):
    v=np.array(b)-a;L=np.linalg.norm(v);axis=v/L;ref=np.array([1.,0,0]) if abs(axis[0])<.8 else np.array([0.,0,1]);u=np.cross(axis,ref);u/=np.linalg.norm(u);w=np.cross(u,axis);basis=np.stack([u,axis,w],1)
    return {'id':ident,'part':'hair_pilot','action':'paint','material':'hair','shape':{'kind':'lathe','profile':[[0,0],[r0,0],[r1,float(L)],[0,float(L)]]},'transform':{'translation':list(a),'basis':basis.tolist()}}

def ball(p,r,ident):
    profile=[[0,-r]]+[[r*math.sin(a),-r*math.cos(a)] for a in np.linspace(0,math.pi,17)[1:-1]]+[[0,r]]
    return {'id':ident,'part':'hair_pilot','action':'paint','material':'hair','shape':{'kind':'lathe','profile':profile},'transform':{'translation':list(p)}}

def hair_build(m,source,prior):
    rows=m['hair_rows'];cx,wy,z,fit=solve_depth(rows,m['side_hair'],'head_cap_closed',prior);centers=np.stack([cx,wy,z],1);rs=np.array([(r['x1']-r['x0'])*scale/2 for r in rows]);ops=[];tol=prior['hair']['adapter_tolerance_m'];nv=prior['hair']['section_vertices'];samples=[];errors=[]
    # The actual source is a continuous horizontal-circle loft with piecewise
    # linear center and radius between measured row centers. The common grammar
    # has no loft primitive: bounded-error midpoint extrusion discretization is
    # explicit, at fixed voxel25mm. This is geometry approximation, not repair.
    nodes=[(centers[0]+[0,scale/2,0],rs[0])]+list(zip(centers,rs))+[(centers[-1]-[0,scale/2,0],rs[-1])]
    for ni,((a,r0),(b,r1)) in enumerate(zip(nodes,nodes[1:])):
        bound=np.linalg.norm((b-a)[[0,2]])+abs(r1-r0);steps=max(1,int(math.ceil(bound/(2*tol))))
        for k in range(steps):
            t0=k/steps;t1=(k+1)/steps;t=(t0+t1)/2;p=a+(b-a)*t;r=r0+(r1-r0)*t;ya=float((a+(b-a)*t0)[1]);yb=float((a+(b-a)*t1)[1]);poly=[[float(p[0]+r*math.cos(2*math.pi*j/nv)),float(-(p[2]+r*math.sin(2*math.pi*j/nv)))] for j in range(nv)]
            ops.append({'id':f'hair_loft_segment{ni}_sub{k}','part':'hair_pilot','action':'paint','material':'hair','shape':{'kind':'extrusion','polygon':poly,'z_min':min(ya,yb),'z_max':max(ya,yb),'minimum_cells':0},'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
            errors.append(float(bound/(2*steps)+r*(1-math.cos(math.pi/nv))));samples.append((p[[0,2]],r))
    overlap_fail=sum(np.linalg.norm(a[0]-b[0])>=a[1]+b[1] for a,b in zip(samples,samples[1:]))
    mask=np.zeros_like(m['hair_domain'])
    for r in rows:mask[r['y'],r['x0']-F['crop'][0]:r['x1']-F['crop'][0]]=True
    fit['section_prior']='Horizontal circular XZ sections with measured exact X diameter; hidden Z diameter remains isotropic prior. Neighbor centers/radii linearly interpolate as continuous loft.'
    fit['radii_m']=rs.tolist();fit['centers_xyz_m']=centers.tolist();fit['source_path_breaks']=m['hair_breaks'];fit['common_adapter']={'kind':'bounded midpoint horizontal extrusion approximation','source_loft_continuous':True,'voxel_pitch_unchanged_m':.025,'longitudinal_tolerance_m':tol,'total_Hausdorff_bound_including_section_polygon_m':max(errors),'operations':len(ops),'adjacent_section_nonoverlap_count':int(overlap_fail),'section_vertices':nv,'no_thickness_floor_or_island_deletion':True}
    return ops,material(source,mask,'hair'),fit


def build_from_measurement(m,source,prior):
    if not m or not m.get('cloth_rows') or not m.get('hair_rows'):raise ValueError('Independent measured domains/rows are mandatory')
    co,cm,cf,cq=cloth_build(m,source,prior);ho,hm,hf=hair_build(m,source,prior);ops=rounded(co+ho);mats=cm|hm
    return master(ops,mats,'measured_continuous_pilot03'),m,{'cloth':rounded(cf),'hair':rounded(hf),'ownership':m['ownership']},cq

def build(source,prior):return build_from_measurement(measure(source,prior),source,prior)

def save_measurement(m):
    arrays={k:v for k,v in m.items() if isinstance(v,np.ndarray)};meta={k:v for k,v in m.items() if not isinstance(v,np.ndarray)}
    np.savez_compressed(BASE/'evidence/independent_masks.npz',**arrays)
    meta.update(schema='riverstone.continuous_pilot.measured_input.v1',arrays_sha256=sha(BASE/'evidence/independent_masks.npz'),source_file_sha256=C['source_sha256'],semantic_annotation_sha256=sha(ROOT/'data/violet_full_semantic_annotations_v02.json'),frozen_branch_domains_sha256=sha(ROOT/'full_measurement/violet_branches/branch_masks.npz'),head_volume_sha256=sha(ROOT/'full01/generated/volume_master_v03.json.gz'),extractor_sha256=sha(__file__))
    save(BASE/'evidence/independent_measurements.json.gz',meta)

def load_measurement():
    p=BASE/'evidence/independent_measurements.json.gz'
    if not p.is_file():raise ValueError('Independent measurement file absent')
    m=gzread(p);assert m['schema']=='riverstone.continuous_pilot.measured_input.v1';assert m['arrays_sha256']==sha(BASE/'evidence/independent_masks.npz');assert m['source_file_sha256']==sha(REPO/C['source'])
    m.update({k:v for k,v in np.load(BASE/'evidence/independent_masks.npz').items()});return m

if __name__=='__main__':
    p=read(BASE/'data/pilot_priors.json');t=time.monotonic();m=measure(SOURCE,p);save_measurement(m);a,m,e,cq=build_from_measurement(load_measurement(),SOURCE,p);save(BASE/'generated/pilot_master.json.gz',a);save(BASE/'evidence/continuous_fit.json.gz',e);np.savez_compressed(BASE/'evidence/measured_domains.npz',cloth=m['cloth_mask'],hair_residual=m['hair_residual'],head=m['head_footprint'],selected_hair=m['hair_domain']);print(json.dumps({'ops':len(a['components'][0]['operations']),'measurements':e['ownership'],'seconds':time.monotonic()-t,'bytes':sum(q.stat().st_size for q in ROOT.rglob('*') if q.is_file())}))
