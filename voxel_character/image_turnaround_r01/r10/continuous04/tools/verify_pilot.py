from continuous_pilot import *


def compile_ops(ops,mats,label):
    m=master(ops,mats,label);co=compile_master(m,{'pitch':.025},max_candidate_cells=400000,max_output_cells=80000);return co,make_render_data(co)
def cells(c):return {tuple(r[:3]) for r in c['cells']}
def contacts(a,b):
    aa,bb=cells(a),cells(b);touch=[]
    for p in aa:
        if p in bb or any(tuple(p[k]+(d if k==j else 0) for k in range(3)) in bb for j in range(3) for d in [-1,1]):touch.append(p)
    return {'overlap_cells':len(aa&bb),'face_touching_or_overlap_cells':len(touch),'contact_center_bounds_m':[[min(p[k] for p in touch)*.025+.0125 for k in range(3)],[max(p[k] for p in touch)*.025+.0125 for k in range(3)]] if touch else None}
def geometry_index(a):return {o['id']:{k:v for k,v in o.items() if k!='material'} for o in a['components'][0]['operations']}
def delta(a,b):
    aa=geometry_index(a);bb=geometry_index(b);ids=[i for i in sorted(set(aa)|set(bb)) if aa.get(i)!=bb.get(i)];return {'geometry_operations_changed':len(ids),'parts_changed':sorted({(aa.get(i) or bb[i])['part'] for i in ids}),'operation_ids_sha256':digest(ids),'master_shape_digest':digest(bb)}

def run():
    start=time.monotonic();p=read(BASE/'data/pilot_priors.json');a=gzread(BASE/'generated/pilot_master.json.gz');fresh,mm,ef,cq=build(SOURCE,p);re,_,_,_=build_from_measurement(load_measurement(),SOURCE,p);assert fresh==a==re
    ops=a['components'][0]['operations'];mats=a['materials'];co,rr=compile_ops(ops,mats,'pilot_common');again,rr2=compile_ops(ops,mats,'pilot_common');assert co==again and rr==rr2
    save(BASE/'generated/pilot_compiled.cells.json.gz',co);save(BASE/'generated/pilot.render.json.gz',rr)
    ctxops=VOL['components'][0]['operations'];ctxmats=VOL['materials'];ctx,ctxr=compile_ops(ctxops,ctxmats,'context_unchanged')
    combined,cr=compile_ops(ctxops+ops,ctxmats|mats,'pilot_context');save(BASE/'generated/context.render.json.gz',cr)
    groups={};renders={};struct={};contact={}
    for part,parent in [('hair_pilot','head_cap_closed'),('cloth_pilot','torso_closed')]:
        cc,r=compile_ops([o for o in ops if o['part']==part],mats,part);parentcc,_=compile_ops([o for o in ctxops if o['part']==parent],ctxmats,parent);groups[part]=cc;renders[part]=r;struct[part]=components(cc['cells']);contact[part]=contacts(cc,parentcc)
    oldhair=gzread(ROOT/'full01/generated/hair_adapter.json.gz');oldcloth=gzread(ROOT/'full01/generated/cloth_operations.json.gz');oo=[o for o in oldhair['operations'] if o['part']=='long_hair_front_hair_region_02']+[o for o in oldcloth['operations'] if o['part']=='front_cloth_face_05'];om=oldhair['materials']|oldcloth['materials'];old,oldr=compile_ops(oo,om,'previous_partial');oldcontext,oldctx=compile_ops(ctxops+oo,ctxmats|om,'previous_partial_context')
    oldstats={}
    for part in ['long_hair_front_hair_region_02','front_cloth_face_05']:
        c0,r0=compile_ops([o for o in oo if o['part']==part],om,part);oldstats[part]=components(c0['cells'])
    fronttarget={'cloth_pilot':mm['cloth_mask'],'hair_pilot':np.zeros_like(mm['cloth_mask'])}
    for r in mm['hair_rows']:fronttarget['hair_pilot'][r['y'],r['x0']-F['crop'][0]:r['x1']-F['crop'][0]]=True
    metrics={};overlays=[]
    for name,v in C['views'].items():
        metrics[name]={};rgb=SOURCE[v['crop'][1]:v['crop'][3],v['crop'][0]:v['crop'][2]].astype(float);predall=np.zeros(rgb.shape[:2],bool);targetall=np.zeros_like(predall)
        for part in groups:
            pr=project(renders[part],v,height);tar=fronttarget[part] if name=='front' else BM[name+'__eligible__'+('hair_visible' if part=='hair_pilot' else 'skirt_visible')];inter=int((pr&tar).sum());metrics[name][part]={'source_support':inter/int(pr.sum()) if pr.any() else 0,'outside_mask_pixels':int((pr&~tar).sum()),'IoU':inter/int((pr|tar).sum()) if name=='front' else None,'correspondence':'selected front-domain target' if name=='front' else 'unknown: all visible class is permissive support, not a matching-part target'};predall|=pr;targetall|=tar
        rgb[predall&targetall]=rgb[predall&targetall]*.5+[15,110,20];rgb[predall&~targetall]=rgb[predall&~targetall]*.4+[140,15,10]
        if name=='front':rgb[targetall&~predall]=rgb[targetall&~predall]*.5+[10,40,120]
        im=Image.fromarray(np.clip(rgb,0,255).astype('uint8'));im.save(BASE/'generated'/f'{name}_overlay.png');overlays.append(im)
    # Pixel-local input changes; the declared dependency is the selected part,
    # not a false promise that a constrained connected solve only changes1row.
    regression={}
    for label,box,expected in [('cloth',[540,475,551,482],'cloth_pilot'),('hair',[259,300,279,320],'hair_pilot')]:
        mutant=SOURCE.copy();xa,ya,xb,yb=box;mutant[ya:yb,xa:xb]=[255,0,0];new,me,fe,_=build(mutant,p);d=delta(a,new);beforemask=fronttarget[expected];after=me['cloth_mask'] if expected=='cloth_pilot' else np.zeros_like(beforemask)
        if expected=='hair_pilot':
            for r in me['hair_rows']:after[r['y'],r['x0']-F['crop'][0]:r['x1']-F['crop'][0]]=True
        mutco,mutr=compile_ops(new['components'][0]['operations'],new['materials'],'mutant');occupancy=cells(co)^cells(mutco);pr={}
        for name,v in C['views'].items():
            pd=project(rr,v,height)^project(mutr,v,height);ys,xs=np.where(pd);pr[name]={'changed_pixels':int(pd.sum()),'bbox_xyxy':([int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None)}
        regression[label]={'recipe_box_xyxy':box,'recipe_rgb':[255,0,0],'test_only_source_pixel_digest':hashlib.sha256(mutant.tobytes()).hexdigest(),'actual_changed_source_pixels':int(np.any(mutant!=SOURCE,2).sum()),'annotations_unchanged':True,'mutant_master_source_status':new['extensions']['source_status'],'mutant_is_not_approved_original':new['extensions']['source_sha256'] is None,'measured_selected_domain_pixel_delta':int((beforemask^after).sum()),**d,'declared_scope_only':d['parts_changed']==[expected],'voxel_occupancy_delta':len(occupancy),'projection_delta':pr,'other_part_measurement_exact': (me['hair_rows']==mm['hair_rows'] if label=='cloth' else np.array_equal(me['cloth_mask'],mm['cloth_mask']))}
    try:build_from_measurement({},SOURCE,p);missing=False
    except ValueError:missing=True
    contradiction=copy.deepcopy(mm);contradiction['side_cloth']=np.zeros_like(mm['side_cloth'])
    try:build_from_measurement(contradiction,SOURCE,p);contradiction_rejected=False
    except ValueError:contradiction_rejected=True
    report={'source_sha256':C['source_sha256'],'master_sha256':sha(BASE/'generated/pilot_master.json.gz'),'compiler_sha256':co['compiler_source_hash'],'mesher_sha256':rr['provenance']['mesher_sha256'],'exporter_sha256':rr['provenance']['exporter_sha256'],'pitch_m':.025,'grid_origin':[0,0,0],'cells':len(co['cells']),'quads':rr['quad_count'],'actual_candidates':co['candidate_cells'],'same_source_master_exact':a==fresh,'saved_measurement_master_exact':a==re,'same_common_compile_exact':co==again,'same_common_mesh_exact':rr==rr2,'source_numeric_rounding_m':1e-10,'solver_environment':{'OPENBLAS_NUM_THREADS':os.environ['OPENBLAS_NUM_THREADS'],'OMP_NUM_THREADS':os.environ['OMP_NUM_THREADS']},'structures':struct,'previous_structures':oldstats,'parent_attachment':contact,'global_context_structure':components(combined['cells']),'projection':metrics,'pixel_regression':regression,'missing_measurement_rejected':missing,'contradictory_side_support_rejected':contradiction_rejected,'ownership':mm['ownership'],'root_surface_constraint':{key:ef['cloth'].get(key) for key in ['actual_generated_root_vertex_xyz_m','root_vertex_solver_depth_error_m','root_constraint_in_surface_triangulation']},'roots':{k:{key:ef[k][key] for key in ['actual_parent_contact','anchor_depth_compatible_with_side']} for k in ['hair','cloth']},'runtime_seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'art_approved':False,'whole_character_complete':False,'GPU_validated':False,'rig_socket_validated':False,'repair_performed':False,'limits':['This is only one selected image-domain cloth face and one measured adjacent hair-run path. Other pixels remain unselected, not erased from full01.','A circular swept hidden hair section is an explicit prior; not recovered hair anatomy. Native source width may flare rather than taper because source part correspondence is imperfect.','Side75deg hypothesis and support-only masks do not resolve matching-panel identity or rear topology.','Full01 branch fences are frozen explicit semantics. In-domain image mutation changes this part only; new pixels beyond fence require new explicit annotation.','25mm cloth representation thickness unchanged. No occupancy islands removed.']}
    write(BASE/'evidence/verification.json',report)
    center=(np.array(cr['bounds']['min'])+cr['bounds']['max'])/2;span=float(max(np.array(cr['bounds']['max'])-cr['bounds']['min'])*1.12);sheet=Image.new('RGB',(1536,1150),'white');d=ImageDraw.Draw(sheet);d.text((10,10),'CONTINUOUS04 PILOT | unchanged common25mm | actual CPU mesh | art/full asset not approved',fill='black');reference=Image.fromarray(SOURCE[:624]);reference.thumbnail((1536,375));sheet.paste(reference,(0,35));d.text((10,415),'Full01 selected face + hair branch, unchanged body context: front / 3-4 / side90 / back',fill='black')
    viewmeta=[]
    for i,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side',90,0),('back',180,0)]):
        bef=raster(oldctx,math.radians(yaw),math.radians(tilt),center,span,size=340);aft=raster(cr,math.radians(yaw),math.radians(tilt),center,span,size=340);sheet.paste(bef,(i*384+22,440));sheet.paste(aft,(i*384+22,795));aft.save(BASE/'generated'/f'cpu_{name}.png');viewmeta.append({'name':name,'sha256':sha(BASE/'generated'/f'cpu_{name}.png')})
    d.text((10,780),'New continuous domain + explicit parent contact constraints. Body/head source unchanged.',fill='black');sheet.save(BASE/'generated/continuous_pilot_before_after.jpg',quality=89)
    write(BASE/'evidence/CPU_provenance.json',{'renderer_sha256':sha(CPU_SOURCE),'input_render_sha256':sha(BASE/'generated/context.render.json.gz'),'comparison_sha256':sha(BASE/'generated/continuous_pilot_before_after.jpg'),'camera_center':center.tolist(),'span_m':span,'views':viewmeta,'GPU':False})
    print(json.dumps({k:report[k] for k in ['cells','actual_candidates','structures','previous_structures','parent_attachment','roots','projection','pixel_regression','runtime_seconds','peak_rss_mib']}));used=sum(q.stat().st_size for q in ROOT.rglob('*') if q.is_file());assert used<40*1048576;print('r10 bytes',used)
if __name__=='__main__':run()
