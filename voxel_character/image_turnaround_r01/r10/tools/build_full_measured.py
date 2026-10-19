"""Whole candidate adapter: measured pixels plus explicit depth/topology priors.

No asset-specific geometry code. The observed intervals and semantic annotations
are independent inputs; hidden cross sections are hypotheses, not measurements.
"""
from measured_panels import *
from scipy.linalg import solve
from verify_and_render import raster, CPU_SOURCE, project, components

FULL=ROOT/'full01'

def disk_check():
    used=sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    assert used<=read(ROOT/'data/resource_budget.json')['approved_total_mib']*1048576
    return used

def clip_halfplane(poly,n,h):
    out=[]
    for p,q in zip(poly,poly[1:]+poly[:1]):
        a=float(np.dot(n,p)-h);b=float(np.dot(n,q)-h)
        if a<=1e-10:out.append(p)
        if (a<=0)!=(b<=0):out.append((np.array(p)+(np.array(q)-p)*a/(a-b)).tolist())
    return out

def support_solver(n,yaw):
    angles=np.arange(n)*2*math.pi/n;normals=np.stack((np.cos(angles),np.sin(angles)),1)
    idx=[0,n//2,int(round(-yaw/360*n))%n,int(round((180-yaw)/360*n))%n]
    assert all(abs(math.atan2(normals[i,1],normals[i,0])-math.atan2(math.sin(a),math.cos(a)))<1e-8 for i,a in zip(idx,[0,math.pi,-math.radians(yaw),math.pi-math.radians(yaw)]))
    D=np.roll(np.eye(n),1,0)-2*np.eye(n)+np.roll(np.eye(n),-1,0)
    Q=D.T@D+np.eye(n)*1e-7;A=np.eye(n)[idx]
    K=np.block([[Q,A.T],[A,np.zeros((4,4))]])
    response=solve(K,np.r_[np.zeros((n,4)),np.eye(4)])[:n]
    def section(xlo,xhi,ulo,uhi):
        theta=math.radians(yaw);cx=(xlo+xhi)/2;um=(ulo+uhi)/2;cz=(math.cos(theta)*cx-um)/math.sin(theta)
        h=response@np.array([(xhi-xlo)/2]*2+[(uhi-ulo)/2]*2)
        poly=[[-4,-4],[4,-4],[4,4],[-4,4]]
        for normal,hi in zip(normals,h):poly=clip_halfplane(poly,normal,float(hi))
        if len(poly)<3:raise ValueError('Measured support and convex closure prior produced empty section')
        poly=(np.array(poly)+[cx,cz]).tolist()
        return poly,[cx,cz],float(np.min(h))
    return section

def palette(rgb,mats):
    rgb=np.clip(np.round(np.array(rgb)/16)*16,0,255).astype(int)
    key='rgb_'+'_'.join(map(str,rgb));mats[key]={'color':'#'+''.join(f'{v:02x}' for v in rgb)};return key

def primitive_quads(op):
    s=op['shape'];tr=transform(op.get('transform'));p=s['polygon'];lo=s['z_min'];hi=s['z_max'];bottom=[apply(tr,[*v,lo]) for v in p];top=[apply(tr,[*v,hi]) for v in p]
    # Local polygon orientation may differ. Make all local boundary normals out.
    area=sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
    if area<0:bottom.reverse();top.reverse()
    q=[]
    for i in range(len(top)):
        j=(i+1)%len(top);q.append([bottom[i],bottom[j],top[j],top[i]])
    for i in range(1,len(top)-1):
        q.extend([[top[0],top[i],top[i+1],top[i+1]],[bottom[0],bottom[i+1],bottom[i],bottom[i]]])
    return q

def volume_parts(contract,measure,annotations,masks,source,branches=None):
    fv=contract['views']['front'];sv=contract['views']['side'];height=contract['alignment']['character_height_m_for_test'];fs=height/fv['scale_px_per_unit'];ss=height/sv['scale_px_per_unit'];fit=support_solver(annotations['support_directions'],sv['yaw_degrees']);ops=[];mats={k:{'color':'#'+''.join(f'{v:02x}' for v in rgb)} for k,rgb in annotations['material_base_srgb'].items()};evidence=[];sockets=[]
    def masked_span(spec,view,y):
        v=contract['views'][view];x0,y0,x1,y1=spec[view];py=int(y);m=np.zeros((v['crop'][3]-v['crop'][1],v['crop'][2]-v['crop'][0]),bool)
        cls=spec['classes']
        eyes=[v['centroid_xy_px'][1] for v in measure['landmarks'] if v['view']==view and v['centroid_xy_px']]
        if spec.get('lower_head_face_after_eye_row') and eyes and y>=np.mean(eyes):cls=['face_skin']
        for cl in cls:
            if cl=='hair_visible' and branches is not None:m|=branches[view+'__eligible__hair_visible']
            else:m|=masks[view+'_'+cl]
        if not y0<=py<y1:return None
        # A specific color rule identifies blue illustration guides; it does not
        # remove arbitrary small components or perform connectivity repair.
        rgb=source[py,x0:x1].astype(int);good=~((rgb[:,2]>=245)&((rgb[:,2]-rgb[:,0])>=55)&((rgb[:,2]-rgb[:,1])>=25))
        xs=np.where(m[py-v['crop'][1],x0-v['crop'][0]:x1-v['crop'][0]]&good)[0]
        return [int(xs.min()+x0),int(xs.max()+x0+1)] if len(xs) else None
    for spec in annotations['parts']:
        observations=[]
        for y in range(spec['front'][1],spec['front'][3]):
            sy=int(math.floor(sv['sole_y']-((fv['sole_y']-y-.5)*fs)/ss));f=masked_span(spec,'front',y);s=masked_span(spec,'side',sy)
            observations.append({'front_y_px':y,'side_y_px':sy,'front_span':f,'side_span':s})
        valid=[i for i,o in enumerate(observations) if o['front_span'] and o['side_span']]
        for o in observations:
            o['occluded_profile_observation']={}
            for view,key in [('front','front_span'),('side','side_span')]:
                py=o[view+'_y_px']
                if any(lo<=py<hi for lo,hi in spec.get('unobserved_profile_rows',{}).get(view,[])):
                    o['occluded_profile_observation'][key]=o[key];o[key]=None
        valid=[i for i,o in enumerate(observations) if o['front_span'] and o['side_span']]
        if len(valid)<2:raise ValueError('Part lacks measured front and side support: '+spec['id'])
        samples=[];missing=[]
        for i in range(valid[0],valid[-1]+1):
            vals=[]
            for key in ('front_span','side_span'):
                ids=[j for j,o in enumerate(observations) if o[key]]
                vals.append([float(np.interp(i,ids,[observations[j][key][k] for j in ids])) for k in (0,1)])
            if not (observations[i]['front_span'] and observations[i]['side_span']):missing.append(observations[i]['front_y_px'])
            samples.append((i,vals))
        sigma=annotations.get('profile_smoothing_sigma_pixels',0)
        if sigma:
            smooth=ndi.gaussian_filter1d(np.array([b for i,b in samples]),sigma=sigma,axis=0,mode='nearest',truncate=3)
            samples=[(item[0],value.tolist()) for item,value in zip(samples,smooth)]
        step=annotations['row_step_source_pixels'];sections=[]
        for start in range(0,len(samples),step):
            band=samples[start:start+step];i=band[len(band)//2][0];f,s=band[len(band)//2][1];y=observations[i]['front_y_px'];ya=observations[band[0][0]]['front_y_px'];yb=observations[band[-1][0]]['front_y_px']+1
            xl,xh=[(p-fv['axis_u'])*fs for p in f];ul,uh=[(p-sv['axis_u'])*ss for p in s]
            if spec.get('side_depth_half')=='low':uh=(ul+uh)/2
            if spec.get('side_depth_half')=='high':ul=(ul+uh)/2
            poly,center,hmin=fit(xl,xh,ul,uh);ylo,yhi=(fv['sole_y']-yb)*fs,(fv['sole_y']-ya)*fs
            sections.append({'source_y_range':[ya,yb],'front_span_px':f,'side_span_px':s,'polygon_xz_m':poly,'center_xz_m':center,'world_y_range':[ylo,yhi],'support_prior_min_m':hmin})
            base=spec['material']
            # Visible skin clothing transitions are source-derived per row.
            if not spec.get('appearance'):
                px=int(np.clip(sum(f)/2,0,source.shape[1]-1));rgb=source[y,px]
                localx=px-fv['crop'][0]
                if masks['front_body_exposed_skin'][y,localx] and y<spec['front'][1]+(spec['front'][3]-spec['front'][1])*.33:base='skin'
                polys=[(poly,base)]
            else:
                polys=[]
                for k in range(len(poly)):
                    p,q=poly[k],poly[(k+1)%len(poly)];mid=(np.array(p)+q)/2;normal=mid-np.array(center);normal/=max(np.linalg.norm(normal),1e-10)
                    vn=max(spec.get('appearance_views',list(contract['views'])),key=lambda name:np.dot(normal,[math.sin(math.radians(contract['views'][name]['yaw_degrees'])),math.cos(math.radians(contract['views'][name]['yaw_degrees']))]))
                    v=contract['views'][vn];scale=height/v['scale_px_per_unit'];a=math.radians(v['yaw_degrees']);u=v['axis_u']+(math.cos(a)*mid[0]-math.sin(a)*mid[1])/scale;py=v['sole_y']-(ylo+yhi)/2/scale
                    u=int(np.clip(round(u),v['crop'][0],v['crop'][2]-1));py=int(np.clip(round(py),0,v['crop'][3]-1));rgb=source[py,u]
                    # If source projection falls in white background, use actual
                    # measured hair median, rather than painting white skin holes.
                    if rgb.min()>225 and rgb.max()-rgb.min()<25:rgb=annotations['material_base_srgb']['hair']
                    polys.append(([center,p,q],palette(rgb,mats)))
            for k,(p,material) in enumerate(polys):
                ops.append({'id':f'{spec["id"]}_row{ya}_{k}','part':spec['id'],'action':'paint','material':material,'shape':{'kind':'extrusion','polygon':[[x,-z] for x,z in p],'z_min':ylo,'z_max':yhi,'minimum_cells':0},'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
        evidence.append({'id':spec['id'],'observations':observations,'interior_interpolated_rows':missing,'sections':sections,'hidden_closure_status':'explicit inferred convex minimum-bending support interpolation','back_constraint':'held out; not forced'})
        for name,sec in [('top',sections[0]),('bottom',sections[-1])]:sockets.append({'id':spec['id']+'_'+name,'xyz_m':[sec['center_xz_m'][0],sum(sec['world_y_range'])/2,sec['center_xz_m'][1]],'status':'inferred rest anchor from measured section center; rig/socket not validated'})
    return ops,mats,evidence,sockets

def build_volumes(revision=''):
    cp=ROOT/'data/measurement_contract.json';mp=ROOT/'full_measurement/violet_v02/full_measurements.json.gz';ap=FULL/'data'/('volume_annotations'+revision+'.json');contract=read(cp);m=gzread(mp);a=read(ap);assert sha(REPO/contract['source'])==m['source_sha256']==a['source_sha256'];masks=np.load(ROOT/'full_measurement/violet_v02/semantic_masks.npz');assert sha(ROOT/'full_measurement/violet_v02/semantic_masks.npz')==m['masks_sha256'];source=np.array(Image.open(REPO/contract['source']).convert('RGB'));bp=ROOT/'full_measurement/violet_branches/branch_masks.npz';branches=np.load(bp) if revision else None;ops,mats,evidence,sockets=volume_parts(contract,m,a,masks,source,branches)
    master={'schema':'riverstone.voxel.master.v1','id':'approved_measured_whole_candidate01','revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':mats,'components':[{'id':'measured_character','parts':[{'id':s['id'],'pivot':[0,0,0]} for s in a['parts']],'operations':ops}],'instances':[{'id':'character','component':'measured_character'}],'constraints':[{'id':'nonempty','kind':'nonempty','minimum_cells':1}],'extensions':{'source_sha256':m['source_sha256'],'source_approval':contract['approval'],'measurement_sha256':sha(mp),'volume_annotations_sha256':sha(ap),'generator_sha256':sha(__file__),'interpretation':a['interpretation'],'sockets':sockets,'complete_reconstruction':False}}
    if branches is not None:master['extensions']['branch_masks_sha256']=sha(bp)
    gzwrite(FULL/'generated'/('volume_master'+revision+'.json.gz'),master);gzwrite(FULL/'evidence'/('volume_fit'+revision+'.json.gz'),evidence);write(FULL/'evidence'/('volume_preflight'+revision+'.json'),preflight(m,contract,master));print(json.dumps({'operations':len(ops),'materials':len(mats),'parts':len(a['parts']),'bytes':disk_check()}));return master

def preview(master,out,prefix='continuous'):
    groups={}
    for comp in master['components']:
        for op in comp['operations']:groups.setdefault(op['material'],[]).extend(primitive_quads(op))
    r={'materials':master['materials'],'groups':[{'material':k,'quads':v} for k,v in groups.items()]};gzwrite(out/(prefix+'.render.json.gz'),r);points=np.array([p for g in r['groups'] for q in g['quads'] for p in q]);center=(points.min(0)+points.max(0))/2;span=float(max(points.max(0)-points.min(0))*1.16);sheet=Image.new('RGB',(1536,450),'white');d=ImageDraw.Draw(sheet);d.text((12,10),'Measured whole candidate | explicit hidden-depth/topology priors | actual common primitive surfaces before voxel compile',fill='black')
    for i,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side',90,0),('back',180,0)]):
        im=raster(r,math.radians(yaw),math.radians(tilt),center,span,size=384);im.save(out/(prefix+'_'+name+'.png'));sheet.paste(im,(i*384,40));d.text((i*384+8,425),name,fill='black')
    sheet.save(out/(prefix+'_four_views.jpg'),quality=89);write(out/(prefix+'_provenance.json'),{'master_content_sha256':digest(master),'render_input_sha256':sha(out/(prefix+'.render.json.gz')),'primitive_adapter_sha256':sha(__file__),'CPU_renderer_sha256':sha(CPU_SOURCE),'camera_center':center.tolist(),'span_m':span,'notes':'Every primitive boundary is rendered, including internal overlapping faces. This is the actual source primitives, not a smoothed stand-in or a Godot screenshot. Common compiled union is a separate validation.'});disk_check();return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['volumes','preview']);p.add_argument('--revision',default='');a=p.parse_args()
    if a.command=='volumes':build_volumes(a.revision)
    else:preview(gzread(FULL/'generated'/('volume_master'+a.revision+'.json.gz')),FULL/'generated','volume_continuous'+a.revision)
