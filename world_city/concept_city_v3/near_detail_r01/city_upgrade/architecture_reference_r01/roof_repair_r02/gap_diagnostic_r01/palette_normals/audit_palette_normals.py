#!/usr/bin/env python3
"""Read frozen source, compiled cells and bounded upper union; no new sampling/mesh/GUI."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(45,)*2)
import json,gzip,hashlib,time,collections,math,gc
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; R=HERE.parent.parent; A=R.parent
ROOT=next(p for p in HERE.parents if (p/'voxel_character/common/core.py').exists())
def read(p):
    with (gzip.open(p,'rt') if p.suffix=='.gz' else p.open()) as f:return json.load(f)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def stats(c):
    c={str(k):int(v) for k,v in sorted(c.items())};t=sum(c.values())
    return {'count':c,'total':t,'percentage':{k:round(100*v/t,5) if t else 0 for k,v in c.items()}}
def nested(d):return {k:stats(v) for k,v in sorted(d.items())}
def faces(c,pitch):
    n={k:int(v) for k,v in zip(dirs,c)};total=sum(n.values());five=total-n['-Y']
    return {'counts':n,'area_m2':{k:round(v*pitch*pitch,9) for k,v in n.items()},'all_six_face_count':total,'top_and_vertical_face_count':five,'top_and_vertical_split_pct':{'+Y':round(100*n['+Y']/five,5) if five else 0,'+-X':round(100*(n['+X']+n['-X'])/five,5) if five else 0,'+-Z':round(100*(n['+Z']+n['-Z'])/five,5) if five else 0}}
t0=time.monotonic();Tpath=A/'roof_repair_r01/tile_measurement_r01/tile_regions.json'
paths=[Tpath,R/'roof_patch.master.json.gz',R/'compile.json',R/'upper_union_arrays.npz',R/'validation_r01/cell_validation.json',R/'roof_repaired.render.json.gz']
before={str(p.relative_to(ROOT)):sha(p) for p in paths}
assert before[str((R/'roof_repaired.render.json.gz').relative_to(ROOT))]=='d71a5987debe5e3e22a3663f8ee4b604bd7d880a0fa7d8188e4d9247c26edb17'
T=read(Tpath);M=read(R/'roof_patch.master.json.gz');C=read(R/'compile.json');V=read(R/'validation_r01/cell_validation.json')['proof']['top_first_hit_tile_cells_by_region']
ops={o['id']:o for c in M['components'] for o in c['operations']}
a=np.load(R/'upper_union_arrays.npz');u=a['materials'];names=a['material_names'].tolist();ids={n:i for i,n in enumerate(names)};pitch=float(a['pitch_m']);assert u.shape==(148,400,328);origin=a['origin_cell_xyz'].tolist();assert origin==[-200,300,-164]
part_names=['retained_baseline','measured_tile_regions','thin_roof_support','finite_chimney_prior'];part_ids={n:i for i,n in enumerate(part_names)}
# Bounded 19.4 MB upper-only provenance array; no full-house allocation or mesh.
q=np.zeros(u.shape,np.uint8);compiled=collections.Counter();inserted=collections.Counter();blocked=collections.Counter();by_part=collections.defaultdict(collections.Counter);inserted_part=collections.defaultdict(collections.Counter);source=collections.Counter();visible=collections.Counter();region_rows=[]
for r in T['regions']:
    pid=r['color']['palette_id'];material=f'top_tile_{pid:02d}';assert ops[r['id']]['material']==material
    source[material]+=1;visible[material]+=V[r['id']]
    region_rows.append({'region':r['id'],'side':r['side'],'palette_id':pid,'material_id':material,'source_rgb':r['color']['source_sample_rgb'],'source_median_rgb':r['color']['median_rgb'],'top_first_hit_cells':V[r['id']]})
assert len(region_rows)==339 and sum(visible.values())==71549
for record in C['chunks']:
    p=ROOT/record['compiled']['path'];assert sha(p)==record['compiled']['sha256'];before[str(p.relative_to(ROOT))]=record['compiled']['sha256'];c=read(p)
    for x,y,z,instance,part,material,feature in c['cells']:
        compiled[material]+=1;by_part[part][material]+=1;iy=y-300;ix=x+200;iz=z+164
        if u[iy,ix,iz]==ids[material]:
            q[iy,ix,iz]=part_ids[part];inserted[material]+=1;inserted_part[part][material]+=1
        else:blocked[material]+=1
    del c;gc.collect()
assert sum(compiled.values())==644352 and sum(inserted.values())==635554
actual=collections.Counter();topmat=np.full((400,328),-1,np.int16);toppart=np.full((400,328),-1,np.int8)
for iy in range(4,148):
    p=u[iy];positive=p>=0; b=np.bincount(p[positive],minlength=len(names))
    actual.update({names[i]:int(v) for i,v in enumerate(b) if v});topmat[positive]=p[positive];toppart[positive]=q[iy][positive]
actual_top=collections.Counter({names[i]:int(v) for i,v in enumerate(np.bincount(topmat[topmat>=0],minlength=len(names))) if v})
part_top={name:collections.Counter({names[i]:int(v) for i,v in enumerate(np.bincount(topmat[toppart==j],minlength=len(names))) if v}) for j,name in enumerate(part_names)}
assert dict(part_top['measured_tile_regions'])==dict(visible)
dirs=['+Y','-Y','+X','-X','+Z','-Z'];normal_mat=np.zeros((len(names),6),np.int64);normal_part=np.zeros((4,6),np.int64)
for iy in range(4,148):
    p=u[iy];pp=q[iy];solid=p>=0
    # Only one plane of neighbor masks at a time. y=300..303 is an actual join halo.
    for di,d in enumerate(dirs):
        if d=='+Y': air=(u[iy+1]<0) if iy+1<148 else np.ones(p.shape,np.bool_)
        elif d=='-Y': air=u[iy-1]<0
        elif d=='+X': air=np.ones(p.shape,np.bool_);air[:-1,:]=p[1:,:]<0
        elif d=='-X': air=np.ones(p.shape,np.bool_);air[1:,:]=p[:-1,:]<0
        elif d=='+Z': air=np.ones(p.shape,np.bool_);air[:,:-1]=p[:,1:]<0
        else: air=np.ones(p.shape,np.bool_);air[:,1:]=p[:,:-1]<0
        exposed=solid&air;normal_mat[:,di]+=np.bincount(p[exposed],minlength=len(names));normal_part[:,di]+=np.bincount(pp[exposed],minlength=4)
    del air,exposed
palette=[]
for pal in T['palette']:
    rgb=pal['rgb'];lin=[v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4 for v in rgb]
    palette.append({**pal,'material_id':f"top_tile_{pal['id']:02d}",'relative_luminance_srgb':round(sum(a*b for a,b in zip(lin,[.2126,.7152,.0722])),8)})
neighbor=[{'palette_ids':[i,i+1],'rgb_euclidean_distance_0_255':round(math.dist(palette[i]['rgb'],palette[i+1]['rgb']),5)} for i in range(5)]
report={'schema':'riverstone.roof_repair_r02.palette_normals_diagnostic.v1','status':'DIAGNOSTIC_ONLY_GLOBAL_ART_FAIL_UNCHANGED','frozen_render_sha256':before[str((R/'roof_repaired.render.json.gz').relative_to(ROOT))],'palette':palette,'rgb_separation':{'adjacent_palette_distances':neighbor,'endpoints_euclidean_distance_0_255':round(math.dist(palette[0]['rgb'],palette[-1]['rgb']),5),'note':'RGB distances are numeric encoding-space distances, not perceptual Delta E. No lighting/shadow measurement is inferred.'},'source_assigned_regions':stats(source),'tile_actual_top_first_hit_by_material':stats(visible),'compiled_patch_cells_by_material':stats(compiled),'compiled_patch_cells_by_part':nested(by_part),'inserted_union_patch_cells_by_material':stats(inserted),'inserted_union_patch_cells_by_part':nested(inserted_part),'baseline_blocked_patch_cells_by_material':stats(blocked),'actual_upper_union_cells_by_material':stats(actual),'actual_upper_union_top_first_hit_by_material':stats(actual_top),'actual_upper_union_top_first_hit_by_part':nested(part_top),'exposed_axis_faces_by_material':{n:faces(normal_mat[i],pitch) for i,n in enumerate(names)},'exposed_axis_faces_by_part':{n:faces(normal_part[i],pitch) for i,n in enumerate(part_names)},'exposed_axis_faces_all_upper':faces(normal_mat.sum(0),pitch),'scope':{'pitch_m':pitch,'upper_union_shape_yxz':list(u.shape),'included_cell_y_range_exclusive':[304,448],'halo_cell_y_range_exclusive':[300,304],'full_house_fine_volume_allocated':False,'mesh_allocated':False,'geometry_sampling_calls':0,'new_image_samples':0,'gui_calls':0,'part_provenance_array_bytes':int(q.nbytes),'exposed_definition':'Occupied voxel faces adjacent to empty voxels in frozen union; material boundaries are not exposed. Includes all exterior-facing and cavity-facing facets. Lower interface uses stored halo. Top first hit is orthographic +Y occupancy, not camera-projected screen visibility.'},'interpretation':['All six measured-tile materials survive source assignment, compilation, priority composition and actual top first hit. There is no categorical collapse within measured tile surfaces.','Palette medoids originated from six brightness-ordered source groups, then every region was reassigned by nearest median RGB. That method does not guarantee equal region counts or equal voxel/screen areas.','Roof support is authored using top_tile_00; combining support with measured tiles can make the total roof palette materially darker and less balanced even though the measured tiles preserve all six colors.','All exposed voxel normals are axis-aligned. +Y/+-X/+-Z proportions quantify stepped geometry; they do not demonstrate a specific lighting failure without comparing actual lit/unshaded views.','Small adjacent RGB separation can be visually masked by illumination, tone mapping, shadow and view distance; this diagnostic does not attribute image differences to those causes.','The previously established actual global art FAIL remains unchanged; no visual success is inferred from palette survival or voxel counts.'],'source_and_input_sha256':before,'inputs_unchanged':all(sha(ROOT/p)==h for p,h in before.items()),'resource_limits':{'address_space_mib':256,'cpu_seconds':45},'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':round(time.monotonic()-t0,4)}
assert report['inputs_unchanged']
source_side=collections.defaultdict(collections.Counter);visible_side=collections.defaultdict(collections.Counter)
for r in region_rows:
    source_side[r['side']][r['material_id']]+=1;visible_side[r['side']][r['material_id']]+=r['top_first_hit_cells']
roof_top=part_top['measured_tile_regions']+part_top['thin_roof_support']
roof_normals=normal_part[part_ids['measured_tile_regions']]+normal_part[part_ids['thin_roof_support']]
report['source_regions_by_side']=nested(source_side)
report['actual_tile_top_first_hit_by_side']=nested(visible_side)
report['actual_tile_and_support_top_first_hit_by_material']=stats(roof_top)
report['exposed_axis_faces_tiles_and_support']=faces(roof_normals,pitch)
report['support_fraction_of_tile_and_support_top_first_hit_pct']=round(100*sum(part_top['thin_roof_support'].values())/sum(roof_top.values()),5)
(HERE/'palette_normals.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');(HERE/'regions.json').write_text(json.dumps(region_rows,indent=2,sort_keys=True)+'\n')
assert sum(p.stat().st_size for p in HERE.iterdir() if p.is_file())<500000
print(json.dumps({k:report[k] for k in ['source_assigned_regions','tile_actual_top_first_hit_by_material','compiled_patch_cells_by_part','actual_upper_union_top_first_hit_by_part','exposed_axis_faces_by_part','rgb_separation','peak_rss_kib','elapsed_seconds','inputs_unchanged']},indent=2))
