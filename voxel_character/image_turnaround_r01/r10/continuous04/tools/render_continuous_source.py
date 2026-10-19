"""Render the actual continuous loft/mid-surface definition, not image retouch."""
from continuous_pilot import *

def run():
    fits=gzread(BASE/'evidence/continuous_fit.json.gz');h=fits['hair'];centers=np.array(h['centers_xyz_m']);rs=np.array(h['radii_m']);nodes=[(centers[0]+[0,scale/2,0],rs[0])]+list(zip(centers,rs))+[(centers[-1]-[0,scale/2,0],rs[-1])];rings=[]
    nv=32
    for p,r in nodes:rings.append([[float(p[0]+r*math.cos(2*math.pi*j/nv)),float(p[1]),float(p[2]+r*math.sin(2*math.pi*j/nv))] for j in range(nv)])
    hq=[]
    for a,b in zip(rings,rings[1:]):
        for j in range(nv):k=(j+1)%nv;hq.append([a[j],a[k],b[k],b[j]])
    for ring in [rings[0],rings[-1]]:
        for j in range(1,nv-1):hq.append([ring[0],ring[j],ring[j+1],ring[j+1]])
    p=read(BASE/'data/pilot_priors.json');m=load_measurement();ops,mats,fit,cq=cloth_build(m,SOURCE,p);cq=[]
    for op in ops:
        tr=transform(op['transform']);q=[apply(tr,[*pt,0]) for pt in op['shape']['polygon']];cq.append(q+[q[-1]])
    hairmat=gzread(BASE/'generated/pilot_master.json.gz')['materials']['hair'];r={'materials':mats|{'hair':hairmat},'groups':[{'material':'hair','quads':hq},{'material':'cloth','quads':cq+[[q[0],q[2],q[1],q[1]] for q in cq]}]}
    points=np.array([v for g in r['groups'] for q in g['quads'] for v in q]);center=(points.min(0)+points.max(0))/2;span=float(max(points.max(0)-points.min(0))*1.15);sheet=Image.new('RGB',(1536,500),'white');d=ImageDraw.Draw(sheet);d.text((10,10),'Actual continuous source: horizontal-section loft + measured cloth mid-surface. Common25mm result is separate.',fill='black');meta=[]
    for i,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side',90,0),('back',180,0)]):
        im=raster(r,math.radians(yaw),math.radians(tilt),center,span,size=384);sheet.paste(im,(384*i,45));d.text((384*i+10,440),name,fill='black');meta.append({'view':name,'yaw_deg':yaw,'pitch_deg':tilt})
    d.text((10,473),'No occupancy repair. Hidden depth / circular sections / panel pairing are hypotheses. Not an approved full character.',fill='black');out=BASE/'generated/continuous_source_four_views.jpg';sheet.save(out,quality=89)
    write(BASE/'evidence/continuous_source_render_provenance.json',{'source_fit_sha256':sha(BASE/'evidence/continuous_fit.json.gz'),'source_master_sha256':sha(BASE/'generated/pilot_master.json.gz'),'script_sha256':sha(__file__),'CPU_renderer_sha256':sha(CPU_SOURCE),'render_payload_digest':digest(r),'render_payload_retained':False,'regenerate':'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python '+str(Path(__file__).relative_to(REPO)),'hair_closed_loft_side_quads':len(hq),'cloth_mid_surface_quads':len(cq),'cloth_display_double_sided':True,'loft_adapter':h['common_adapter'],'camera_center':center.tolist(),'span_m':span,'views':meta,'comparison_sha256':sha(out),'GPU':False,'limits':['Loft ring tessellation follows the same measured centers/radii as common adapter.','Cloth displayed is measured mid-surface before25mm normal thickness; it is not an alternative voxel render.','Continuous connected source does not imply25mm six-connected occupancy.']});print(sha(out))
if __name__=='__main__':run()
