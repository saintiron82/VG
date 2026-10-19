"""r04: exact source-bound material transfer, unchanged voxel occupancy."""
from pathlib import Path
import argparse,gc,gzip,hashlib,json,os,resource,sys,time,collections
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from PIL import Image
R=next(p for p in Path(__file__).resolve().parents if(p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(R))
from voxel_character.common import core,prepared_sampling_v3 as sampler,render_data
H=Path(__file__).resolve().parent;A=H.parent;OLD=A/'roof_repair_r03';F=A/'foundation_repair_r01';Q=A/'reconstruction_proof_r01';P=.03125;JOIN=9.5
D=OLD/'edge_surface_diagnostic_r01';IMAGE=R/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(R)),'sha256':sha(p)}
def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def write(n,v):
 p=H/n;assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);b=json.dumps(v,separators=(',',':'),allow_nan=False).encode();b=gzip.compress(b,mtime=0)if p.suffix=='.gz'else b;assert sum(x.stat().st_size for x in H.rglob('*')if x.is_file())+len(b)<5_000_000;p.write_bytes(b);return ref(p)
def pins():
 paths=[IMAGE,D/'material_ownership_proposal.json',D/'eligible_cell_proposals.json',OLD/'upper_union_arrays.npz',OLD/'roof_repaired.render.json.gz',OLD/'roof_patch.master.json.gz',OLD/'composition.json',F/'foundation_repaired.render.json.gz',F/'foundation_arrays.npz',F/'foundation_revised.master.json.gz',A/'roof_repair_r01/tile_measurement_r01/tile_regions.json',Path(core.__file__),Path(sampler.__file__),Path(render_data.__file__),Path(render_data.mesh.__file__)]
 return {str(p.relative_to(R)):sha(p)for p in paths}
def main():
 t=time.monotonic();deps=pins();records=read(D/'eligible_cell_proposals.json');proposal=read(D/'material_ownership_proposal.json');assert len(records)==2609 and sha(OLD/'roof_repaired.render.json.gz')==proposal['render_sha256'];oldmaster=read(OLD/'roof_patch.master.json.gz');materials=oldmaster['materials'];names=list(materials);ids={n:i for i,n in enumerate(names)};image=np.asarray(Image.open(IMAGE).convert('RGB'));coef=read(A/'roof_repair_r01/tile_measurement_r01/tile_regions.json')['conditional_mapping']['coefficients'];pal=np.array([[int(materials[f'top_tile_{i:02d}'][j:j+2],16)for j in (0,2,4)]for i in range(6)])
 a=np.load(OLD/'upper_union_arrays.npz');m=a['materials'];assert a['material_names'].tolist()==names;top=np.full((400,328),-1,np.int16)
 for iy,row in enumerate(m):top[row>=0]=iy+300
 want={};runs=[]
 for r in records:
  x,y,z=r['cell_xyz'];iy,ix,iz=y-300,x+200,z+164;assert top[ix,iz]==y and names[int(m[iy,ix,iz])]==r['old_material'];assert r['old_material'].startswith('pixel_');hit=np.flatnonzero(m[iy,ix]>=0);assert iz not in (int(hit[0]),int(hit[-1]));assert(( -160<=z<-148)or(148<=z<160))
  u0=(x*P-coef['tx'])/coef['sx'];u1=((x+1)*P-coef['tx'])/coef['sx'];v0=(z*P-coef['tz'])/coef['sz'];v1=((z+1)*P-coef['tz'])/coef['sz'];box=[int(np.floor(u0)),int(np.floor(v0)),int(np.ceil(u1)),int(np.ceil(v1))];assert box==r['whole_TOP_pixel_support_box']
  u,v,U,V=box;pix=image[v:V,u:U].astype(float);rr,gg,bb=[pix[:,:,k]for k in range(3)];assert np.all((rr>gg*1.7)&(gg>bb*1.2)&(rr>80));med=np.median(pix.reshape(-1,3),axis=0);assert med.tolist()==r['source_TOP_median_rgb'];mid=int(np.argmin(((pal-med)**2).sum(1)));assert r['proposed_material']==f'top_tile_{mid:02d}';assert (x,y,z)not in want;want[x,y,z]=r['proposed_material']
 # Lossless z-run compression of the explicitly selected cells only.
 grouped=collections.defaultdict(list)
 for (x,y,z),mat in want.items():grouped[x,y,mat].append(z)
 ops=[]
 for (x,y,mat),zs in sorted(grouped.items()):
  zs.sort();start=last=zs[0]
  for z in zs[1:]+[None]:
   if z is not None and z==last+1:last=z;continue
   oid=f'top_owner_x{x}_y{y}_z{start}_{last+1}';ops.append({'id':oid,'part':'source_TOP_material_ownership','action':'paint','material':mat,'shape':{'kind':'box','min':[x*P,y*P,start*P],'max':[(x+1)*P,(y+1)*P,(last+1)*P]}});runs.append({'operation':oid,'cell_count':last-start+1,'source_cell_xyz_interval':[[x,y,start],[x+1,y+1,last+1]]})
   if z is not None:start=last=z
 master={'schema':core.SCHEMA,'id':'architecture_A_roof_material_ownership_r04_delta','revision':4,'axes':oldmaster['axes'],'grid_origin':[0,0,0],'materials':materials,'components':[{'id':'TOP_surface_ownership','parts':[{'id':'source_TOP_material_ownership','pivot':[0,0,0]}],'operations':ops}],'instances':[{'id':'TOP_surface_ownership','component':'TOP_surface_ownership'}],'assembly_cuts':[],'constraints':[{'id':'nonempty_delta','kind':'nonempty'}],'metadata':{'diagnostic_only':True,'production_gate_open':False,'material_only_existing_cells':True,'occupancy_unchanged':True,'source_TOP_appearance_not_calibrated_albedo':True,'original_global_registration_accepted':False,'brightness_to_height':False,'per_face_color_override':False,'source_cell_records':ref(D/'eligible_cell_proposals.json'),'remaining_pale_cells_deferred':727}}
 core.validate_master(master,P);mr=write('roof_patch.master.json.gz',master);pp=sampler.prepare_master(master,{'pitch':P});st=time.monotonic();c=sampler.compile_prepared(pp,cell_bounds={'min':[-200,304,-160],'max':[200,448,160]},max_candidate_cells=10000,max_output_cells=3000);assert c['valid'];actual={(r[0],r[1],r[2]):r[5]for r in c['cells']};assert actual==want and len(c['cells'])==2609
 cr=write('compiled/delta.json.gz',c);write('compile.json',{'status':'PASS_MATERIAL_ONLY_DELTA','delta':cr,'cells':len(c['cells']),'candidates':c['candidate_cells'],'operations':len(ops),'seconds':time.monotonic()-st,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'old_roof_cells_resampled':0});del c;gc.collect()
 oldhash=hashlib.sha256();newhash=hashlib.sha256();frontback_same=True;changed=0
 for iy,row in enumerate(m):
  oldhash.update(np.packbits(row>=0).tobytes());oldrow=row.copy()
  for (x,y,z),mat in want.items():
   if y-300==iy:row[x+200,z+164]=ids[mat];changed+=1
  newhash.update(np.packbits(row>=0).tobytes());occ=oldrow>=0
  for ix in np.flatnonzero(occ.any(1)):
   hits=np.flatnonzero(occ[ix]);assert row[ix,hits[0]]==oldrow[ix,hits[0]]and row[ix,hits[-1]]==oldrow[ix,hits[-1]],'F/B material changed'
 assert changed==2609 and oldhash.digest()==newhash.digest();np.savez_compressed(H/'upper_union_arrays.npz',materials=m,origin_cell_xyz=a['origin_cell_xyz'],pitch_m=P,material_names=np.asarray(names),join_y_m=JOIN)
 # Fixed r03 partitions; key includes exact halo material cells plus provenance.
 old=np.load(OLD/'upper_union_arrays.npz')['materials'];chunks=[]
 for i,record in enumerate(read(OLD/'composition.json')['chunks']):
  za,zb=record['halo_z_cells'];z0,z1=record['owned_z_cells'];sl=(slice(None),slice(None),slice(za+164,zb+164));before=hashlib.sha256(old[sl].tobytes()).hexdigest();after=hashlib.sha256(m[sl].tobytes()).hexdigest();cache=OLD/f'mesh_cache/chunk_{i:03d}.json.gz';cached=read(cache);assert cached['owned_z_cells']==[z0,z1]and cached['upper_union_sha256']==sha(OLD/'upper_union_arrays.npz')and cached['mesher_sha256']==sha(Path(render_data.mesh.__file__))
  chunks.append({'index':i,'owned_z_cells':[z0,z1],'halo_z_cells':[za,zb],'r03_halo_material_sha256':before,'r04_halo_material_sha256':after,'reuse_exact_cache':before==after,'original_cache':ref(cache),'record':record})
 write('cache_plan.json',{'schema':'riverstone.roof_color_delta.cache_plan.v1','source_render':ref(OLD/'roof_repaired.render.json.gz'),'source_union':ref(OLD/'upper_union_arrays.npz'),'new_union':ref(H/'upper_union_arrays.npz'),'common_mesher':ref(Path(render_data.mesh.__file__)),'palette_sha256':core.digest(materials),'chunks':chunks,'reused':sum(r['reuse_exact_cache']for r in chunks),'recomputed':sum(not r['reuse_exact_cache']for r in chunks),'halo_hash_includes_materials_not_only_occupancy':True})
 proof={'status':'PASS_EXACT_MATERIAL_DELTA','source_dependencies':deps,'master':mr,'source_cell_records':ref(D/'eligible_cell_proposals.json'),'run_count':len(ops),'cells_recolored':changed,'occupancy_hash_before':oldhash.hexdigest(),'occupancy_hash_after':newhash.hexdigest(),'FRONT_BACK_first_hit_materials_identical':frontback_same,'lower_and_foundation_unchanged':True,'geometry_bounds_unchanged':True,'palette_unchanged':True,'whole_voxel_materials_updated':True,'per_face_override':False,'deferred_pale_counts':proposal['pale_rejected_counts'],'deferred_pale_total':727,'same_cell_source_TOP_tests':True,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'common_core_changes':False,'cache_reused':sum(r['reuse_exact_cache']for r in chunks),'cache_recomputed':sum(not r['reuse_exact_cache']for r in chunks)}
 assert deps==pins();write('plan.json',proof);print(json.dumps(proof),flush=True)
if __name__=='__main__':
 resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(45,)*2);main()
