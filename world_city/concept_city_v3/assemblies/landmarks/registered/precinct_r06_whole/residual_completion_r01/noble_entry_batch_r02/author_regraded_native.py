"""Source-authored finite noble terminal skins with exact public-column cuts."""
from pathlib import Path
import sys,json,copy,math,argparse,time,importlib.util,collections
OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1];sys.path.insert(0,str(BASE))
from resolve_pack import *
from author_native import estimate_candidates
from world_city.concept_city_v3.assemblies.property.registered.r1.author import append_surface
from world_city.concept_city_v3.registered_topography.revisions.public_corridors_r18 import finite_geometry_r03 as fg
OUT=Path(__file__).resolve().parent;OLD=OUT.with_name('noble_entry_batch_r01')
spec=importlib.util.spec_from_file_location('old_native_author',OLD/'author_native_entries.py');oldauthor=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldauthor)

def write(name,obj):
 p=OUT/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def cut(master,pose,poly,lo,hi,label):
 master['components'][0]['operations'].append(dict(id=label,part='solid',action='cut',shape=dict(kind='extrusion',polygon=[[x-pose[0],-(z-pose[2])]for x,z in poly],z_min=lo-pose[1],z_max=hi-pose[1]),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]])))
def refine_shared_xy_joins(ops,triangles):
 # An explicitly stepped interface has duplicate XYZ knots but identical XZ
 # edges. Overlap source prisms only at shared XZ edges by half a native cell;
 # the visible high-side envelope then covers both within-cell field values.
 counts=collections.Counter()
 def key(a,c):return tuple(sorted((round(p[0],7),round(p[2],7))for p in(a,c)))
 for t in triangles:
  vs=t['vertices_xyz_m']
  for a,c in zip(vs,vs[1:]+vs[:1]):counts[key(a,c)]+=1
 result=copy.deepcopy(ops);ledger=[]
 for op,t in zip(result,triangles):
  poly=op['shape']['polygon'];vs=t['vertices_xyz_m'];center=np.mean(poly,axis=0);lines=[];offsets=[]
  for k,(a,c)in enumerate(zip(poly,poly[1:]+poly[:1])):
   a=np.array(a);c=np.array(c);d=c-a;n=np.array([-d[1],d[0]])/np.linalg.norm(d)
   if np.dot(center-a,n)<0:n=-n
   off=.0625 if counts[key(vs[k],vs[(k+1)%len(vs)])]>1 else 0.;lines.append((n,float(np.dot(n,a))-off));offsets.append(off)
  refined=[]
  for k in range(len(poly)):
   n0,h0=lines[(k-1)%len(poly)];n1,h1=lines[k];v=np.linalg.solve(np.array([n0,n1]),[h0,h1]);delta=v-np.array(poly[k]);length=float(np.linalg.norm(delta));v=np.array(poly[k])+delta*min(1.,.125/max(length,1e-30));refined.append(v.tolist())
  op['shape']['polygon']=refined;ledger.append(dict(operation_id=op['id'],shared_xy_edge_offsets_m=offsets,maximum_vertex_join_extension_m=.125,original_polygon=poly,refined_polygon=refined))
 return result,ledger

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--solutions',required=True);ap.add_argument('--inputs',default=str(OUT/'tail_solve_inputs.json'));ap.add_argument('--public-records',required=True);ap.add_argument('--owners',default='E1,E2,E3,E4,E5,E6,E7');args=ap.parse_args();solutions=Path(args.solutions).resolve();inp=load(Path(args.inputs).resolve());publicpath=Path(args.public_records).resolve();public=load(publicpath)['records'];pi=geo._SpatialIndex(4)
 for i,r in enumerate(public):
  if fg.area(r['polygon_xz_m'])>1e-12:pi.add(i,r['polygon_xz_m'])
 oldpack=load(OLD/'resolved_native_candidate.json');assets=[];placements=[];ledgers=[];owners=copy.deepcopy(oldpack['owners']);started=time.monotonic()
 for owner in owners:
  eid=owner['owner_id'];entry=next(r for r in inp['owners']if r['owner_id']==eid)
  base=next(p for p in oldpack['placements']if p['owner_id']==eid and p['role']=='retained_base');assets.append(next(a for a in oldpack['assets']if a['id']==base['asset_key']));placements.append(copy.deepcopy(base))
  old=next(p for p in oldpack['placements']if p['owner_id']==eid and p['role']=='fine_access')
  if eid=='E3'or eid not in args.owners.split(','):assets.append(next(a for a in oldpack['assets']if a['id']==old['asset_key']));placements.append(copy.deepcopy(old));ledgers.append(dict(owner_id=eid,status='UNCHANGED_NO_PUBLIC_OVERLAP',source=old['source'],cache=old['cache']));continue
  proposalpath=solutions/(eid+'_proposal.json');proposal=load(proposalpath);result=proposal['result'].get('result',proposal['result']);assert result['status']=='PASSED_FINITE_TRIANGLE_GRADE',(eid,result['status']);assert result['maximum_fixed_error_m']<1e-7 and result['maximum_gradient']<=(.3500001 if eid=='E2'else.2500001)
  triangles=[t for t in result['triangles']if fg.area(t['polygon_xz_m'])>1e-10];assert abs(sum(fg.area(t['polygon_xz_m'])for t in triangles)-proposal['result'].get('domain_area_m2',result.get('finite_domain_area_m2')))<1e-7
  bias=.03125 if result['maximum_gradient']>.1200001 else 0.
  triangles=copy.deepcopy(triangles)
  for t in triangles:
   for v in t['vertices_xyz_m']:v[1]+=bias
   t['physical_to_visible_source_top_bias_m']=bias
  s=copy.deepcopy(load(ROOT/old['source']['path']));pose=old['position_m'];oldys=[v[1]+pose[1]for g in load(ROOT/old['cache']['path'])['groups']for q in g['quads']for v in q];newys=[v[1]for t in triangles for v in t['vertices_xyz_m']];lo=min(oldys+newys)-1;hi=max(oldys+newys)+1
  cut(s,pose,entry['window_polygon_xz_m'],lo,hi,'R02_retire_exact_old_terminal_window')
  temp=copy.deepcopy(s);temp['components'][0]['operations']=[];temp=append_surface(temp,dict(id='R02_CANONICAL_PUBLIC_PRIORITY:'+eid,triangulated_top_surface=triangles),[pose[0],pose[2]],pose[1]);ops,joins=refine_shared_xy_joins(temp['components'][0]['operations'],triangles)
  for op in ops:op['id']='R02_finite_terminal_'+op['id'];s['components'][0]['operations'].append(op)
  # Repeat the original exact source-domain column boundary after painting
  # the new profile; cuts are source operations, never cache mutations.
  ext=owner['source_external_profile'];coords=entry['window_polygon_xz_m'];box=b.rect(min(q[0]for q in coords)-.5,min(q[1]for q in coords)-.5,max(q[0]for q in coords)+.5,max(q[1]for q in coords)+.5);sourcepolys=[q for reg in ext['polygon_regions_xz_m']for q in b.triangulate(reg)]
  for i,q in enumerate(fg.subtract([box],sourcepolys)):cut(s,pose,q,lo,hi,'R02_source_vertical_boundary:'+str(i))
  # Public traffic owns complete physical columns. Retire every native
  # 0.125 m cell column with positive projected area in the fixed public top.
  pitch=.125;w=entry['window_polygon_xz_m'];x0,z0,x1,z1=min(q[0]for q in w)-.25,min(q[1]for q in w)-.25,max(q[0]for q in w)+.25,max(q[1]for q in w)+.25;columns=[]
  for ix in range(math.floor((x0-pose[0])/pitch),math.ceil((x1-pose[0])/pitch)):
   for iz in range(math.floor((z0-pose[2])/pitch),math.ceil((z1-pose[2])/pitch)):
    q=b.rect(pose[0]+ix*pitch,pose[2]+iz*pitch,pose[0]+(ix+1)*pitch,pose[2]+(iz+1)*pitch)
    hits=[j for j in pi.candidates(q)if fg.area(fg.clip(q,public[j]['polygon_xz_m']))>1e-12]
    if hits:
     columns.append(dict(grid_xz=[ix,iz],polygon_xz_m=q,public_record_ids=[public[j]['id']for j in hits]));cut(s,pose,q,lo,hi,'R02_public_full_native_column:'+str(len(columns)))
  caprecords=load(CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json')['records']
  caprow=next((r for r in caprecords if r['property_id']==eid),None)
  if caprow:
   for i,col in enumerate(caprow['candidate_columns']):cut(s,pose,col['polygon_xz_m'],lo,hi,'R02_preserve_approved_full_cap_column:'+str(i))
  # Retained base remains authoritative even where terminal triangulation
  # touches the old base footprint. No base source operation is changed.
  basecache=load(ROOT/base['cache']['path']);basepolys=roof_rectangles(basecache,{g['material']for g in basecache['groups']})[0]
  for i,local in enumerate(basepolys):
   q=[[v[0]+pose[0],v[1]+pose[2]]for v in local];q=fg.clip(q,box)
   if q:cut(s,pose,q,lo,hi,'R02_retained_base_exclusion:'+str(i))
  s['id']='registered_precinct_noble_entry_r02_'+eid.lower()+'_fine_access';s['revision']=2;s['metadata'].update(derived_from_r01=old['source'],finite_tail_input=ref(Path(args.inputs).resolve()),finite_solve=ref(proposalpath),canonical_public=ref(publicpath),public_column_cuts=columns,new_profile_join_refinements=joins,native_sampling_top_bias_m=bias,access_mode='pedestrian_stair_only_no_cart'if eid=='E2'else'private_pedestrian_access',maximum_visible_native_tread_rise_m=.125,private_grade_limit=result['grade_limit'],finite_private_risers=proposal['result'].get('vertical_risers',[]),author=ref(Path(__file__)),runtime_ready=False)
  sr=write('masters/'+s['id']+'.json',s);estimate=estimate_candidates(s,.125);assert estimate['candidate_cells_exact_aabb_visits']<6500000,(eid,estimate);preflight=write('preflight/'+eid+'.json',dict(source=sr,estimate=estimate,max_candidate_cells=6500000,unchanged_base=base,source_profile=ref(proposalpath)));print(eid,'compile',estimate['candidate_cells_exact_aabb_visits'],flush=True);c=coordinate_planes.compile_master(s,{'pitch':.125},max_candidate_cells=6500000,max_output_cells=400000);assert c['valid'];m=render_data.make_render_data(c);cr=write('cache/'+s['id']+'.render.json',m);asset=dict(id=s['id'],property_id=eid,role='fine_access',source=sr,cache=cr,pitch_m=.125,master_hash=core.digest(s),candidate_cells=c['candidate_cells'],output_cells=len(c['cells']),preflight=preflight);assets.append(asset);placements.append(dict(old,id='R06_NOBLE_ENTRY_R02:'+eid+':fine_access',asset_key=s['id'],source=sr,cache=cr));ledgers.append(dict(owner_id=eid,status='SOURCE_RECOMPILED_FINITE_TAIL',old_fine=old,new_fine=placements[-1],finite_solve=ref(proposalpath),public_full_column_retirements=columns,window_polygon_xz_m=entry['window_polygon_xz_m'],source_candidate_cells=c['candidate_cells'],output_cells=len(c['cells'])));print(eid,'done',len(c['cells']),len(columns),flush=True)
 out=copy.deepcopy(oldpack);out.update(schema='riverstone.precinct.noble_entry_batch.v2',status='NATIVE_R02_CANDIDATE_GROUND_COLLISION_RUNTIME_PENDING',assets=assets,placements=placements,owners=owners,native_revision_ledger=ledgers,sources=dict(oldpack['sources'],supersedes_r01=ref(OLD/'resolved_native_candidate.json'),public_priority=ref(publicpath)),summary=dict(owners=7,placements=len(placements),seconds=time.monotonic()-started),activation=False,runtime_ready=False);write('resolved_native_candidate.json',out);print(out['summary'],flush=True)
if __name__=='__main__':main()
