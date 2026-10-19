#!/usr/bin/env python3
"""Independent r04 whole-cell material ownership proof, not geometry sampling."""
from validate_exterior import *
import collections,copy,gc,sys
sys.dont_write_bytecode=True
from PIL import Image
sys.path.insert(0,str(ROOT))
from voxel_character.common import core
OLD=ARCH/'roof_repair_r03';D=OLD/'edge_surface_diagnostic_r01';F=ARCH/'foundation_repair_r01';SOURCE=ROOT/'world_city/reference/house_quality_photos_20261019/six_views_r01/generated_candidate_r03.png'
FROZEN='c5354c21ca7a12589f6a8ee0bd73ca9046c120a43914b0502b1fc88d96c120ca'
def require(v,reason):
 if not v:raise ValueError(reason)
def pins():
 require(sha(OLD/'roof_repaired.render.json.gz')==FROZEN,'Frozen r03 changed');wanted=dict(read(R/'plan.json')['source_dependencies'])
 for n in ['plan.json','cache_plan.json','compile.json','roof_patch.master.json.gz','upper_union_arrays.npz']:wanted[str((R/n).relative_to(ROOT))]=sha(R/n)
 for p,h in wanted.items():require(sha(ROOT/p)==h,'Input pin mismatch: '+p)
 return wanted

def source_pixel_evidence(image,box,palette):
 u,v,U,V=box;pixels=image[v:V,u:U].astype(float)
 require(pixels.shape==(V-v,U-u,3) and U>u and V>v,'Source support box outside raster')
 red=(pixels[...,0]>pixels[...,1]*1.7)&(pixels[...,1]>pixels[...,2]*1.2)&(pixels[...,0]>80)
 if not red.all():return None
 median=np.median(pixels.reshape(-1,3),axis=0);nearest=int(np.argmin(((palette-median)**2).sum(1)))
 return median,nearest

def prepare_context():
 olddata=np.load(OLD/'upper_union_arrays.npz');old=olddata['materials'];newdata=np.load(R/'upper_union_arrays.npz');new=newdata['materials'];names=olddata['material_names'].tolist();master=read(R/'roof_patch.master.json.gz');legacy=read(OLD/'roof_patch.master.json.gz');palette=legacy['materials'];ids={n:i for i,n in enumerate(names)}
 require(old.shape==new.shape==(148,400,328),'Source array bounds changed')
 for key in ['origin_cell_xyz','pitch_m','material_names','join_y_m']:require(np.array_equal(olddata[key],newdata[key]),'Source grid metadata changed: '+key)
 require(master['materials']==palette and list(palette)==names,'Source palette expanded/reordered')
 require(sha(SOURCE)=='552b0bd61eba3c3f5bee98a6b3a5fac085362dc8804e049e325db55fb902ec93','Source raster changed')
 image=np.asarray(Image.open(SOURCE).convert('RGB'));coef=read(ARCH/'roof_repair_r01/tile_measurement_r01/tile_regions.json')['conditional_mapping']['coefficients'];slope=read(ARCH/'roof_repair_r02/roof_patch.master.json.gz')['metadata']['measured_gable_slope'];rgb=np.array([[int(palette[f'top_tile_{i:02d}'][j:j+2],16) for j in (0,2,4)] for i in range(6)])
 topy=np.full((400,328),-1,np.int16);topmat=topy.copy();front=np.full((148,400),-1,np.int16);back=front.copy()
 for iy,row in enumerate(old):
  occupied=row>=0;valid=occupied.any(1);back[iy,valid]=np.argmax(occupied[valid],1);front[iy,valid]=327-np.argmax(occupied[valid,::-1],1);topy[occupied]=iy+300;topmat[occupied]=row[occupied]
 expected=[];rejected=collections.Counter();pale_rejected=collections.Counter();pale_before=0
 for ix in range(400):
  for iz in list(range(4,16))+list(range(312,324)):
   mid=int(topmat[ix,iz]);y=int(topy[ix,iz]);x,z=ix-200,iz-164
   if not(0<=mid<15):continue
   pale=mid<=4;pale_before+=int(pale);X,Y=(x+.5)*PITCH,(y+.5)*PITCH;line=13.875-slope*abs(X);reason=None
   u0=(x*PITCH-coef['tx'])/coef['sx'];u1=((x+1)*PITCH-coef['tx'])/coef['sx'];v0=(z*PITCH-coef['tz'])/coef['sz'];v1=((z+1)*PITCH-coef['tz'])/coef['sz'];box=[math.floor(u0),math.floor(v0),math.ceil(u1),math.ceil(v1)]
   if not(.25<abs(X)<6 and line-.65<=Y<=line+.1875):reason='outside_roof_band_or_ridge'
   elif iz in (int(front[y-300,ix]),int(back[y-300,ix])):reason='F_or_B_first_hit_color_conflict'
   elif not(613<=u0<u1<=922 and 787<=v0<v1<=977):reason='outside_conditional_roof_rectangle'
   elif u0<908 and u1>868 and v0<849 and v1>795:reason='chimney_holdout_overlap'
   else:
    evidence=source_pixel_evidence(image,box,rgb)
    if evidence is None:reason='TOP_footprint_mixed_or_shadow_or_antialias'
   if reason:
    rejected[reason]+=1;pale_rejected[reason]+=int(pale);continue
   med,pid=evidence
   expected.append({'cell_xyz':[x,y,z],'old_material':names[mid],'proposed_material':f'top_tile_{pid:02d}','whole_TOP_pixel_support_box':box,'conditional_TOP_footprint_uv':[u0,v0,u1,v1],'source_TOP_median_rgb':med.tolist(),'palette_sample_rgb':rgb[pid].tolist(),'original_pale':bool(pale),'F_B_first_hit_unchanged':True})
 records=read(D/'eligible_cell_proposals.json');check_records(records,expected);require(len(expected)==2609,'Authorized selected count mismatch')
 proposal=read(D/'material_ownership_proposal.json');require(pale_before==2383 and sum(r['original_pale'] for r in expected)==1656 and sum(pale_rejected.values())==727,'Pale cell accounting mismatch');require(dict(rejected)==proposal['rejected_counts'] and dict(pale_rejected)==proposal['pale_rejected_counts'],'Deferred source counts changed')
 selected={tuple(r['cell_xyz']):r['proposed_material'] for r in expected};require(len(selected)==2609,'Duplicate source cell')
 return {'old':old,'new':new,'names':names,'ids':ids,'master':master,'palette':palette,'selected':selected,'expected_records':expected,'front':front,'back':back,'pale_rejected':dict(pale_rejected),'rejected':dict(rejected),'pale_before':pale_before}

def check_records(records,expected):require(records==expected,'Selected source cell/pixel footprint/color evidence differs from independent oracle')

def check_master_compile(ctx,master=None,compiled=None):
 master=ctx['master'] if master is None else master;require(master['materials']==ctx['palette'],'Source palette changed');meta=master['metadata'];require(meta['per_face_color_override'] is False and meta['occupancy_unchanged'] is True and meta['brightness_to_height'] is False,'Whole-cell material-only policy changed')
 require(master['grid_origin']==[0,0,0] and master['axes']=={'up':'+Y','front':'+Z','right':'+X'},'Grid/axes changed')
 require(master['assembly_cuts']==[] and master['instances']==[{'id':'TOP_surface_ownership','component':'TOP_surface_ownership'}],'Unexpected assembly transform/cut')
 expanded={};ops={}
 for comp in master['components']:
  require(comp['id']=='TOP_surface_ownership','Unexpected component')
  for op in comp['operations']:
   require(op['action']=='paint' and op['part']=='source_TOP_material_ownership' and set(op)=={'id','part','action','material','shape'},'Unexpected source material operation')
   sh=op['shape'];require(sh['kind']=='box' and set(sh)=={'kind','min','max'},'Unexpected source geometry');lo=[round(n/PITCH) for n in sh['min']];hi=[round(n/PITCH) for n in sh['max']];require(all(lo[i]*PITCH==sh['min'][i] and hi[i]*PITCH==sh['max'][i] for i in range(3)),'Off-lattice source box');require(hi[0]==lo[0]+1 and hi[1]==lo[1]+1 and hi[2]>lo[2],'Non-run source box');require(op['id'] not in ops,'Duplicate operation');ops[op['id']]=op
   for z in range(lo[2],hi[2]):
    point=(lo[0],lo[1],z);require(point not in expanded,'Overlapping source boxes');expanded[point]=(op['material'],op['id'])
 require({p:v[0] for p,v in expanded.items()}==ctx['selected'] and len(expanded)==2609,'Common box source cell set differs from authorized cells');require(len(ops)==738,'Unexpected run count')
 compilation=read(R/'compile.json')
 if compiled is None:
  p=ROOT/compilation['delta']['path'];require(sha(p)==compilation['delta']['sha256'],'Compiled delta hash mismatch');compiled=read(p)
 require(compiled['valid'] and compiled['pitch']==PITCH and compiled['grid_origin']==[0,0,0],'Compiled metadata');require(core.digest(master)==compiled['master_hash'] and core.digest(compiled['cells'])==compiled['payload_hash'],'Compiled provenance mismatch');actual={}
 for x,y,z,instance,part,material,feature in compiled['cells']:
  point=(x,y,z);require(point not in actual,'Duplicate compiled cell');require(instance=='TOP_surface_ownership' and part=='source_TOP_material_ownership','Wrong compiled ownership');actual[point]=(material,feature)
 require(actual==expanded and len(compiled['cells'])==2609==compilation['cells'],'Actual common compile differs from explicit source boxes')
 return {'common_boxes':len(ops),'compiled_cells':len(actual),'selected_cell_set_equals_common_box_expansion':True,'selected_cell_set_equals_actual_common_compile':True,'whole_cell_material_ownership':True,'per_face_override':False}

def check_array(ctx,new=None):
 old=ctx['old'];new=ctx['new'] if new is None else new;rows=collections.defaultdict(dict)
 for (x,y,z),m in ctx['selected'].items():rows[y-300][x+200,z+164]=ctx['ids'][m]
 changed=0;fb=0;oldhash=hashlib.sha256();newhash=hashlib.sha256()
 for iy in range(148):
  before=old[iy];after=new[iy];require(np.array_equal(before>=0,after>=0),'Occupancy changed');oldhash.update(np.packbits(before>=0).tobytes());newhash.update(np.packbits(after>=0).tobytes())
  for hits in [ctx['front'][iy],ctx['back'][iy]]:
   xx=np.flatnonzero(hits>=0);zz=hits[xx];require(np.array_equal(before[xx,zz],after[xx,zz]),'FRONT/BACK first-hit material changed');fb+=len(xx)
  wanted=before.copy()
  for (ix,iz),material in rows[iy].items():wanted[ix,iz]=material
  require(np.array_equal(after,wanted),'Actual cell changes differ from authorized source material set');changed+=int((before!=after).sum())
 require(changed==2609 and oldhash.digest()==newhash.digest(),'Material change count or geometry mismatch')
 return {'cells_checked':int(old.size),'changed_cell_set_exactly_2609':True,'changed_cells':changed,'occupancy_identical':True,'occupancy_sha256':newhash.hexdigest(),'FRONT_BACK_first_hits_checked':fb,'FRONT_BACK_first_hit_materials_identical':True,'lower_join_halo_exact':np.array_equal(old[:4],new[:4]),'all_unselected_material_cells_unchanged':True,'source_bounds_unchanged':True,'palette_unchanged':True}

def check_cache_plan(ctx,plan=None):
 plan=read(R/'cache_plan.json') if plan is None else plan;proof=read(HERE/'cache_identity_proof.json');require(proof['cache_identity_verified'] is True and proof['source_render']['sha256']==FROZEN,'Cache concatenation not proven')
 require(plan['source_render']==ref(OLD/'roof_repaired.render.json.gz') and plan['source_union']==ref(OLD/'upper_union_arrays.npz') and plan['new_union']==ref(R/'upper_union_arrays.npz'),'Cache plan source pin mismatch');require(core.digest(ctx['palette'])==plan['palette_sha256'],'Cache palette mismatch');require(sha(ROOT/plan['common_mesher']['path'])==plan['common_mesher']['sha256'],'Mesher changed')
 records=read(OLD/'composition.json')['chunks'];require(len(plan['chunks'])==len(records)==88,'Partition count changed');reuse=0;changes=[]
 for i,(r,p) in enumerate(zip(records,plan['chunks'])):
  za,zb=r['halo_z_cells'];old=hashlib.sha256(ctx['old'][:,:,za+164:zb+164].tobytes()).hexdigest();new=hashlib.sha256(ctx['new'][:,:,za+164:zb+164].tobytes()).hexdigest();require(p['index']==i and p['record']==r and p['owned_z_cells']==r['owned_z_cells'] and p['halo_z_cells']==r['halo_z_cells'],'Partition ownership changed')
  require(p['r03_halo_material_sha256']==old and p['r04_halo_material_sha256']==new,'Exact material halo hash mismatch');require(p['reuse_exact_cache']==(old==new),'Unsafe cache reuse');require(p['original_cache']==ref(OLD/f'mesh_cache/chunk_{i:03d}.json.gz'),'Cache pin changed');reuse+=int(old==new)
  if old!=new:changes.append(i)
 require(reuse==63 and len(changes)==25 and plan['reused']==reuse and plan['recomputed']==len(changes),'Cache reuse count mismatch')
 return {'exact_material_halo_hashes_checked':88,'safe_reused_partitions':reuse,'required_recomputed_partitions':len(changes),'recomputed_partition_indices':changes,'cache_source_render_exact_ordered_identity_verified':True}

def main():
 t=time.monotonic();before=pins();ctx=prepare_context();proof=check_array(ctx);compiler=check_master_compile(ctx);cache=check_cache_plan(ctx);require(all(sha(ROOT/p)==h for p,h in before.items()),'Inputs modified')
 report={'schema':'riverstone.roof_repair_r04.independent_material_delta.v1','status':'TECHNICAL_PASS','source_pixel_proof':{'eligible_cells_independently_rederived':2609,'whole_pixel_footprint_strict_terracotta':True,'coordinates_and_RGB_records_exact':True,'nearest_unchanged_six_source_palette':True,'original_pale_cells':2383,'recolored_pale_cells':1656,'deferred_pale_cells':727,'deferred_pale_counts':ctx['pale_rejected'],'all_rejected_counts':ctx['rejected'],'no_chimney_holdout_or_ridge_overlap':True,'source_appearance_not_calibrated_albedo':True},'array_proof':proof,'common_source_compile_proof':compiler,'cache_reuse_proof':cache,'input_files':before,'all_source_pins_unchanged':True,'sampling_calls':0,'mesher_calls':0,'address_space_limit_mib':256,'cpu_limit_seconds':60,'elapsed_seconds':time.monotonic()-t,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'validator':ref(Path(__file__)),'visual_acceptance':'PENDING_PARENT_ACTUAL_CAPTURE_REVIEW'}
 save(HERE/'material_delta_validation.json',report);print(json.dumps({k:v for k,v in report.items() if k!='input_files'},sort_keys=True))
if __name__=='__main__':main()
