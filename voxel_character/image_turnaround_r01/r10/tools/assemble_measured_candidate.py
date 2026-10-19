"""Assemble measured components without hand-authored substitute geometry."""
from build_full_measured import *

def assemble():
    paths=[FULL/'generated/volume_master_v03.json.gz',FULL/'generated/cloth_operations.json.gz',FULL/'generated/hair_adapter.json.gz',FULL/'generated/accessory_operations.json.gz'];body,cloth,hair,accessories=[gzread(p) for p in paths];master=copy.deepcopy(body);ops=master['components'][0]['operations'];materials=master['materials']
    contract=read(ROOT/'data/measurement_contract.json');bm=gzread(ROOT/'full_measurement/violet_branches/branch_measurements.json.gz')
    assert sha(REPO/contract['source'])==contract['source_sha256']==bm['source_sha256']
    assert sha(ROOT/'full_measurement/violet_branches/branch_masks.npz')==bm['branch_masks_sha256']
    for layer in (cloth,hair,accessories):ops.extend(layer['operations']);materials.update(layer['materials'])
    for op in ops:op.setdefault('transform',{})
    master['id']='violet_approved_r06_measured_whole_candidate_full01';master['components'][0]['parts']=[{'id':p,'pivot':[0,0,0]} for p in sorted({o['part'] for o in ops})];master['extensions'].update({'assembly_generator_sha256':sha(__file__),'source_components':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in paths],'whole_candidate_status':'Measured full major-part candidate with explicit incomplete correspondence and depth assumptions. Art/complete reconstruction NOT approved.','source_primitive_policy':'All supplied runs retained; no post-compile island deletion, automatic filling or thickness enlargement.','cloth_prior_sha256':sha(FULL/'data/cloth_depth_priors.json'),'hair_prior_sha256':sha(FULL/'data/hair_depth_priors.json'),'held_out_details':['individual flowers/stems','small hair ornaments','ribbon identity and three-dimensional attachment','GPU scene validation','rig and socket acceptance']})
    gzwrite(FULL/'generated/full_master.json.gz',master);c=read(ROOT/'data/measurement_contract.json');pre=preflight({},c,master);pre['source_component_counts']={p.name:len(layer['components'][0]['operations']) if 'components' in layer else len(layer['operations']) for p,layer in zip(paths,[body,cloth,hair,accessories])};pre['estimated_wall_seconds']=[10,45];pre['estimated_peak_rss_mib']=[130,300];pre['disk_bytes_before_compile']=disk_check();pre['full_master_bytes']=(FULL/'generated/full_master.json.gz').stat().st_size;write(FULL/'evidence/full_preflight.json',pre);print(json.dumps(pre));return master

def continuous_preview(master):
    groups={};count=0
    for op in master['components'][0]['operations']:
        part=op['part'];iscloth=('cloth_face' in part or 'skirt_visible' in part)
        if iscloth:
            p=[apply(transform(op.get('transform')),[*v,0]) for v in op['shape']['polygon']]
            q=[p[0],p[1],p[2],p[2]];quads=[q,list(reversed(q))]
            # Reversal of duplicate-ended triangle would degenerate normal.
            quads=[q,[p[2],p[1],p[0],p[0]]]
        else:quads=primitive_quads(op)
        groups.setdefault(op['material'],[]).extend(quads);count+=len(quads)
    r={'materials':master['materials'],'groups':[{'material':k,'quads':v} for k,v in groups.items()]};points=np.array([p for g in r['groups'] for q in g['quads'] for p in q]);center=(points.min(0)+points.max(0))/2;span=float(max(points.max(0)-points.min(0))*1.12);out=FULL/'generated';sheet=Image.new('RGB',(1536,480),'white');d=ImageDraw.Draw(sheet);d.text((12,10),'Approved pixels -> measured major parts -> inferred full continuous candidate (not art approved)',fill='black');images=[]
    for i,(name,yaw,tilt) in enumerate([('front',0,0),('three_quarter',45,12),('side',90,0),('back',180,0)]):
        im=raster(r,math.radians(yaw),math.radians(tilt),center,span,size=384);p=out/('full_continuous_'+name+'.png');im.save(p);sheet.paste(im,(i*384,40));d.text((i*384+8,430),name+' / actual source geometry CPU',fill='black');images.append({'view':name,'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
    d.text((12,454),'Cloth: actual fitted mid-surfaces before25mm thickness. Hair/body: closed common primitives. Unresolved branches/joins retained.',fill='black');path=out/'full_continuous_four_views.jpg';sheet.save(path,quality=90);write(FULL/'evidence/full_continuous_provenance.json',{'master_sha256':sha(out/'full_master.json.gz'),'render_payload_digest':digest(r),'renderer_source_sha256':sha(CPU_SOURCE),'primitive_exporter_sha256':sha(ROOT/'tools/build_full_measured.py'),'assembly_preview_sha256':sha(__file__),'quads':count,'camera_center':center.tolist(),'span_m':span,'images':images,'comparison_sha256':sha(path),'limits':'Cloth preview is the exact center surface of each normal-thickness prism, not the compiled exterior; other parts show primitive boundary caps including internal overlaps. No source image warp or texture plate. Actual common-voxel exterior is separately evaluated.'});print(json.dumps({'preview':str(path),'quads':count,'bytes':disk_check()}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['assemble','preview']);a=p.parse_args()
    if a.command=='assemble':assemble()
    else:continuous_preview(gzread(FULL/'generated/full_master.json.gz'))
