"""Exact inherited cells + labelled owner cuts + measured positives via common core."""
from repair_common import *
import copy,time,traceback
def make_master(a,crop,labels,pal):
 materials=read(A/'foundation_repair_r01/foundation_revised.master.json.gz')['materials'];names=list(materials)
 panel=measured.make_source(crop,labels,pal);materials.update(panel['materials']);ops=[]
 # Lossless run compression of frozen original coarse cells, queried at native pitch.
 for y in range(HALO_LO[1],HALO_HI[1]):
  for x in range(HALO_LO[0],HALO_HI[0]):
   z=HALO_LO[2]
   while z<HALO_HI[2]:
    m=value(a,(x,y,z))
    if m<0:z+=1;continue
    z0=z;z+=1
    while z<HALO_HI[2] and value(a,(x,y,z))==m:z+=1
    ops.append({'id':f'inherited_x{x}_y{y}_z{z0}_{z}','part':'retained_coarse','action':'paint','material':names[m],'shape':{'kind':'box','min':[x*P,y*P,z0*P],'max':[(x+1)*P,(y+1)*P,z*P]}})
 for yy in range(48):
  xx=0
  while xx<64:
   if labels[yy,xx] not in (1,2):xx+=1;continue
   start=xx;lab=int(labels[yy,xx]);xx+=1
   while xx<64 and int(labels[yy,xx])==lab:xx+=1
   x,y=coords(yy,start);xh,_=coords(yy,xx)
   ops.append({'id':f'known_owner_label{lab}_source_y{250+yy}_x{152+start}_{152+xx}','part':'retained_coarse','action':'cut','shape':{'kind':'box','min':[x*P,y*P,156*P],'max':[xh*P,(y+1)*P,160*P]}})
 ops+=panel['components'][0]['operations']
 return {'schema':core.SCHEMA,'id':'gallery_panel_repair_r01_bounded_union','revision':1,'grid_origin':[0,0,0],'axes':{'up':'+Y','front':'+Z','right':'+X'},'materials':materials,'components':[{'id':'bounded_union','parts':[{'id':'retained_coarse','pivot':[0,0,0]},{'id':'measured_railing_positive','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'original_world_placement','component':'bounded_union'}],'assembly_cuts':[],'constraints':[{'id':'nonempty_local_union','kind':'nonempty'}],'metadata':{'source_image':ref(IMAGE),'mask_source':ref(A/'railing_measurement_r01/pixel_masks.npz'),'base_arrays':ref(A/'foundation_repair_r01/foundation_arrays.npz'),'front_plane_m':5,'wood_thickness_prior_m':.0625,'old_skin_interval_m':[4.875,5],'known_aperture_clearance_interval_m':[3.875,5],'rear_wall_preserved_below_m':3.875,'change_owner':'Only source labels1 positive wood and2 annotated aperture, z156..159 native cells. Unknown classes unchanged.','halo_bounds_native':{'min':HALO_LO,'max':HALO_HI},'mesher_owned_bounds_native':{'min':OWN_LO,'max':OWN_HI},'diagnostic_only':True,'production_gate_open':False}}
def common_compile(master):return core.compile_master(master,{'pitch':P},max_candidate_cells=100000,max_output_cells=40000)
def cellmap(c):return {tuple(r[:3]):r[5] for r in c['cells']}
def run():
 started=time.monotonic();assert sha(BASE)==BASE_SHA and sha(IMAGE)==IMAGE_SHA
 data=np.load(A/'railing_measurement_r01/pixel_masks.npz');saved=data['labels'];crop=np.asarray(Image.open(IMAGE).convert('RGB'))[250:298,152:216].copy();labels,holes=measured.classify(crop);assert np.array_equal(labels,saved);pal=data['palette'];a=baseline()
 master=make_master(a,crop,labels,pal);source_ref=save('local_union.master.json.gz',master)
 t=time.monotonic();c=common_compile(master);compile_s=time.monotonic()-t;actual=cellmap(c);names=list(master['materials']);old={p:names[m] for p,m in inherited_cells(a).items()};owner=mask_owner(labels);changed={p for p in set(old)|set(actual) if old.get(p)!=actual.get(p)};assert changed<=owner
 expected=dict(old)
 for p in owner:expected.pop(p,None)
 panel=measured.make_source(crop,labels,pal);pc=common_compile(panel);positives=cellmap(pc);expected.update(positives);assert expected==actual
 assert sum(labels.ravel()==1)==1941 and len(positives)==3882 and sum(labels.ravel()==2)==43
 unknown={(*coords(int(y),int(x)),z) for y,x in np.argwhere(np.isin(labels,[3,4,5])) for z in range(156,160)}
 assert all(old.get(p)==actual.get(p) for p in unknown)
 # Finite ray tests: native prism z124..159 only; legitimate wall z123 is retained.
 rays=[]
 for yy,xx in np.argwhere(labels==2):
  x,y=coords(int(yy),int(xx));before=[];after=[]
  for z in range(124,160):
   if value(a,(x,y,z))>=0:before.append(z)
   occupied=(x,y,z) in actual if bounds_contains((x,y,z),HALO_LO,HALO_HI) else value(a,(x,y,z))>=0
   if occupied:after.append(z)
  assert not after and value(a,(x,y,123))>=0
  rays.append({'source_xy':[152+int(xx),250+int(yy)],'world_ray_xy_m':[(x+.5)*P,(y+.5)*P],'tested_z_native_half_open':[124,160],'before_blocked_z_cells':before,'after_blocked_z_cells':after,'retained_rear_wall_z123_material':names[value(a,(x,y,123))]})
 repeat=common_compile(master);assert repeat['cells']==c['cells'] and repeat['payload_hash']==c['payload_hash'];del repeat
 # Mutate original source RGB, rerun classification and full common compilation.
 source_xy=(163,266);mx,my=source_xy;mutcrop=crop.copy();mutcrop[my-250,mx-152]=[255,0,255];ml,_=measured.classify(mutcrop);assert labels[my-250,mx-152]==1 and ml[my-250,mx-152]==5
 mutmaster=make_master(a,mutcrop,ml,pal);mc=common_compile(mutmaster);mut=cellmap(mc);diff={p for p in set(actual)|set(mut) if actual.get(p)!=mut.get(p)};x,y=coords(my-250,mx-152);assert diff and all(p[:2]==(x,y) and 156<=p[2]<160 for p in diff)
 save('mutation_case.json',{'source_xy':source_xy,'replacement_rgb':[255,0,255],'source_old_label':1,'source_new_label':5,'old_rgb':crop[my-250,mx-152].tolist(),'mutated_crop_sha256':hashlib.sha256(mutcrop.tobytes()).hexdigest(),'original_master_hash':c['master_hash'],'mutated_master_hash':mc['master_hash'],'original_payload_hash':c['payload_hash'],'mutated_payload_hash':mc['payload_hash'],'changed_cells':[{'xyz':p,'before':actual.get(p),'after':mut.get(p)} for p in sorted(diff)],'interpretation':'Unknown state restores inherited coarse occupancy at that pixel, rather than inventing a new opening.','original_source_unchanged':sha(IMAGE)==IMAGE_SHA})
 del mc,mutmaster,mut
 t=time.monotonic();mesh=render_data.make_render_data(c);mesh_s=time.monotonic()-t;actual_faces=set();duplicates=0;owned_groups=[]
 for g in mesh['groups']:
  qs=[]
  for q in g['quads']:
   _,inside=partition_quad(q)
   if inside is None:continue
   qs.append(inside)
   for f in faces(inside,g['material']):duplicates+=int(f in actual_faces);actual_faces.add(f)
  if qs:owned_groups.append({'material':g['material'],'quads':qs})
 exterior=expected_faces(actual);assert duplicates==0 and actual_faces==exterior
 local_ref=save('local_union.compiled.json.gz',c);mesh_ref=save('local_union.render.json.gz',mesh)
 patch_ref=save('owned_surface.json.gz',{'groups':owned_groups,'quad_count':sum(len(g['quads']) for g in owned_groups),'owned_bounds_native':{'min':OWN_LO,'max':OWN_HI},'halo_bounds_native':{'min':HALO_LO,'max':HALO_HI},'common_mesh':mesh_ref})
 delta=[{'xyz':p,'before':old.get(p),'after':actual.get(p),'source_xy':[p[0]+256,495-p[1]],'source_label':int(labels[495-p[1]-250,p[0]+256-152])} for p in sorted(changed)]
 delta_ref=save('owner_delta.json.gz',{'cell_pitch_m':P,'native_cell_material_changes':delta,'change_owner_count':len(owner),'unchanged_outside_change_owner':True,'frozen_outside_local_halo':'Preserved by source reference and exact streamed surface composition.'})
 save('aperture_rays.json',{'count':len(rays),'ray_results':rays,'all_43_finite_rays_clear':True,'rear_wall_not_deleted':True,'depth_is_inherited_prior_not_measured':True})
 report={'schema':'riverstone.gallery_panel_repair.common_proof.v1','status':'TECHNICAL_PASS_PENDING_ACTUAL_VIEWS','master':source_ref,'compiled':local_ref,'local_render':mesh_ref,'owned_surface':patch_ref,'delta':delta_ref,'source_image':ref(IMAGE),'core':ref(Path(core.__file__)),'mesher':ref(Path(render_data.mesh.__file__)),'exporter':ref(Path(render_data.__file__)),'native_positive_pixels':1941,'annotated_aperture_pixels':43,'before_blocked_aperture_pixels':sum(bool(r['before_blocked_z_cells']) for r in rays),'after_blocked_aperture_pixels':0,'measured_positive_cells':len(positives),'bounded_union_cells':len(actual),'change_owner_cells':len(owner),'changed_native_cells':len(changed),'removed_native_cells':len(set(old)-set(actual)),'added_native_cells':len(set(actual)-set(old)),'material_changed_existing_cells':sum(p in old and p in actual for p in changed),'outside_owner_cells_equal':True,'unknown_classes_native_cells_preserved':len(unknown),'native_material_faces':len(exterior),'duplicate_faces':duplicates,'repeatability_exact_cells_and_payload':True,'source_pixel_mutation_changed_cells':len(diff),'sample_calls':4,'common_mesher_calls':1,'compile_seconds':compile_s,'mesh_seconds':mesh_s,'elapsed_seconds':time.monotonic()-started,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'complete_railing_claim':False,'roof_resampled':False,'production_gate_open':False,'actual_six_view_gate':'PENDING_PARENT'}
 save('build_report.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException as e:
  save('failed_build_case.json',{'error':repr(e),'traceback':traceback.format_exc()});raise
