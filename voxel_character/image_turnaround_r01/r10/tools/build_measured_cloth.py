"""Generic measured thin-face adapter with explicit, uncertain depth priors."""
from measured_panels import *
from scipy.fft import dctn,idctn
from scipy.optimize import lsq_linear

def regularize(a,weight):
    ny,nx=a.shape
    lap=(2-2*np.cos(np.pi*np.arange(ny)/ny))[:,None]+(2-2*np.cos(np.pi*np.arange(nx)/nx))[None,:]
    return idctn(dctn(a,norm='ortho')/(1+weight*lap**2),norm='ortho')

def build_cloth(contract,bm,masks,source,prior):
    height=contract['alignment']['character_height_m_for_test'];sv=contract['views']['side'];ss=height/sv['scale_px_per_unit'];theta=math.radians(sv['yaw_degrees']);ops=[];mats={};evidence=[];sidefaces=[b for b in bm['views']['side']['branches'] if b['role']=='cloth_face'];allside=masks['side__eligible__skirt_visible'];step=prior['row_step_px'];dx=prior['horizontal_step_px'];thick=prior['normal_thickness_m']
    def side_intervals(branch,world_y):
        py=int(math.floor(sv['sole_y']-world_y/ss));mask=masks['side__'+branch['id']];spans=runs(mask[py]) if 0<=py<mask.shape[0] else [];fallback=False
        if not spans and 0<=py<allside.shape[0]:spans=runs(allside[py]);fallback=True
        return [[sv['crop'][0]+a,sv['crop'][0]+b] for a,b in spans],py,fallback
    def quantile(spans,q):
        n=sum(b-a for a,b in spans);p=q*n
        for a,b in spans:
            if p<=b-a:return a+p
            p-=b-a
        return spans[-1][1]
    def prism(points,part,material,ident):
        # Nonplanar sampled quad is split into its two exact planar triangles.
        for ti,indices in enumerate(((0,1,2),(0,2,3))):
            p=np.array([points[k] for k in indices]);e1=p[1]-p[0];length=np.linalg.norm(e1)
            if length<1e-10:continue
            e1/=length;n=np.cross(p[1]-p[0],p[2]-p[0]);area=np.linalg.norm(n)
            if area<1e-12:continue
            n/=area;e2=np.cross(n,e1);poly=[[float((v-p[0])@e1),float((v-p[0])@e2)] for v in p]
            ops.append({'id':ident+'_'+str(ti),'part':part,'action':'paint','material':material,'shape':{'kind':'extrusion','polygon':poly,'z_min':-thick/2,'z_max':thick/2,'minimum_cells':0},'transform':{'translation':p[0].tolist(),'basis':np.stack([e1,e2,n],1).tolist()}})
    for view in ('front','back'):
        v=contract['views'][view];scale=height/v['scale_px_per_unit'];sign=1 if view=='front' else -1;branches=[b for b in bm['views'][view]['branches'] if b['role']=='cloth_face'];unknown=masks[view+'__unknown__skirt_visible'];ys,xs=np.where(unknown)
        if len(xs):branches.append({'id':'unknown__skirt_visible','role':'unknown_cloth','bbox_xyxy_px':[int(xs.min()+v['crop'][0]),int(ys.min()),int(xs.max()+v['crop'][0]+1),int(ys.max()+1)],'pixels':int(len(xs)),'apparent_rgb_median':np.median(source[v['crop'][1]:v['crop'][3],v['crop'][0]:v['crop'][2]][unknown],0).tolist()})
        for b in branches:
            part=view+'_'+b['id'];mask=masks[view+'__'+b['id']];x0,y0,x1,y1=b['bbox_xyxy_px'];lmask=mask[y0:y1,x0-v['crop'][0]:x1-v['crop'][0]];rgb=source[y0:y1,x0:x1].astype(float);luma=rgb.mean(2);values=luma[lmask];med=float(np.median(values));contrast=max(float(np.percentile(values,90)-np.percentile(values,10)),1.0);target=np.where(lmask,(luma-med)/contrast,0);field=regularize(target,prior['biharmonic_lambda']);field=np.clip(field,-.5,.5)
            scores=[]
            for sb in sidefaces:
                sy0,sy1=sb['bbox_xyxy_px'][1],sb['bbox_xyxy_px'][3];offset=sv['sole_y']-v['sole_y'];lo=max(y0,sy0-offset);hi=min(y1,sy1-offset);union=max(y1,sy1-offset)-min(y0,sy0-offset);scores.append({'id':sb['id'],'vertical_extent_IoU':max(0,hi-lo)/max(union,1)})
            scores.sort(key=lambda p:(-p['vertical_extent_IoU'],p['id']));chosen=next(s for s in sidefaces if s['id']==scores[0]['id']);material='cloth_'+part;srgb=np.clip(np.round(b['apparent_rgb_median']),0,255).astype(int);mats[material]={'color':'#'+''.join(f'{c:02x}' for c in srgb)};rows=[];missing=[]
            supports=[];observed=[]
            for py in range(y0,y1+1):
                spans,spy,fallback=side_intervals(chosen,(v['sole_y']-py)*scale);supports.append((spans,spy,fallback))
                if spans:
                    u=quantile(spans,prior['depth_quantile_by_primary_view'][view]);lo,hi=next((a,bb) for a,bb in spans if a<=u<=bb);observed.append([py-y0,u,lo,hi,sum(bb-a for a,bb in spans)])
            if not observed:
                evidence.append({'id':part,'operations':0,'failure':'No side support; measured face is preserved but no arbitrary depth generated'});continue
            observed=np.array(observed);ids=np.arange(y1-y0+1);profile=np.array([np.interp(ids,observed[:,0],observed[:,k]) for k in (1,2,3,4)]).T;n=len(ids);D=np.zeros((max(0,n-2),n))
            for k in range(n-2):D[k,k:k+3]=[1,-2,1]
            A=np.r_[np.eye(n),D*math.sqrt(prior['biharmonic_lambda'])];rhs=np.r_[profile[:,0],np.zeros(max(0,n-2))];solved=lsq_linear(A,rhs,bounds=(profile[:,1],profile[:,2]),tol=1e-10,max_iter=100)
            if not solved.success:raise ValueError('Bounded depth-profile solve failed: '+part)
            fitted=solved.x
            def point(x,y,spans):
                xx=sign*(x-v['axis_u'])*scale;wy=(v['sole_y']-y)*scale;findex=float(np.clip(y-y0,0,n-1));u=float(np.interp(findex,ids,fitted));width=float(np.interp(findex,ids,profile[:,3]))*ss;iy=int(np.clip(round(y-y0),0,y1-y0-1));ix=int(np.clip(round(x-x0),0,x1-x0-1));depth_residual=float(field[iy,ix])*width*prior['photometric_depth_fraction'];world_u=(u-sv['axis_u'])*ss+depth_residual
                # Project to the nearest allowed interval only when the proxy
                # exits support; every such bounded inference is counted below.
                # Bounds are a common function of the vertex's source Y, not
                # the calling strip. Adjacent strips therefore share depth.
                lo=float(np.interp(findex,ids,profile[:,1]));hi=float(np.interp(findex,ids,profile[:,2]));world_u=min(max(world_u,(lo-sv['axis_u'])*ss),(hi-sv['axis_u'])*ss);z=(math.cos(theta)*xx-world_u)/math.sin(theta)
                return [xx,wy,z]
            for ya in range(y0,y1,step):
                yb=min(ya+step,y1);ym=(ya+yb)//2;spans,spy,fallback=side_intervals(chosen,(v['sole_y']-(ya+yb)/2)*scale)
                if not spans:missing.append([ya,yb]);continue
                primary=runs(mask[ym]);rows.append({'source_y_range':[ya,yb],'source_row_used':ym,'side_row':spy,'side_intervals_px':spans,'selected_side_branch':chosen['id'],'fallback_all_cloth_support':fallback,'primary_intervals_px':[[a+v['crop'][0],bb+v['crop'][0]] for a,bb in primary]})
                for ri,(la,lb) in enumerate(primary):
                    left,right=la+v['crop'][0],lb+v['crop'][0]
                    for xa in range(left,right,dx):
                        xb=min(xa+dx,right);pts=[point(xa,ya,spans),point(xb,ya,spans),point(xb,yb,spans),point(xa,yb,spans)];prism(pts,part,material,f'{part}_y{ya}_r{ri}_x{xa}')
            evidence.append({'id':part,'primary_pixels':b['pixels'],'source_bbox':b['bbox_xyxy_px'],'side_candidate_scores':scores,'selected_side_branch_hypothesis':chosen['id'],'correspondence_status':'unknown; score is a conditional diagnostic placement heuristic, not an identified sewn panel','depth_rows':rows,'no_side_support_rows':missing,'normal_thickness_m':thick,'curvature_energy':float(np.sum(ndi.laplace(field)**2)),'center_profile_energy':float(np.sum((D@fitted)**2)),'shared_vertex_depth':True,'appearance_proxy_status':'Actual source luminance regularized with explicit unknown-lighting prior, not measured physical depth','operations':sum(o['part']==part for o in ops)})
    return ops,mats,evidence

if __name__=='__main__':
    root=ROOT/'full01';c=read(ROOT/'data/measurement_contract.json');mp=ROOT/'full_measurement/violet_branches/branch_measurements.json.gz';bm=gzread(mp);masks=np.load(mp.parent/'branch_masks.npz');source=np.array(Image.open(REPO/c['source']).convert('RGB'));pp=root/'data/cloth_depth_priors.json';p=read(pp);assert sha(REPO/c['source'])==bm['source_sha256'];ops,mats,e=build_cloth(c,bm,masks,source,p);gzwrite(root/'generated/cloth_operations.json.gz',{'operations':ops,'materials':mats,'source_sha256':bm['source_sha256'],'measurement_sha256':sha(mp),'prior_sha256':sha(pp),'generator_sha256':sha(__file__)});gzwrite(root/'evidence/cloth_fit.json.gz',e);print(json.dumps({'operations':len(ops),'parts':len(e),'missing_side_support_rows':sum(len(a['no_side_support_rows']) for a in e)}))
