"""Separate retained common base and bounded fine native access skin."""
from pathlib import Path
import sys,json,copy,time
OUT=Path(__file__).resolve().parent;RES=OUT.parent;BASE=RES.parent;sys.path.insert(0,str(BASE))
from resolve_pack import *
from author_native import estimate_candidates
OUT=Path(__file__).resolve().parent;RES=OUT.parent

def write(name,obj):p=OUT/name;p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n');return ref(p)
def add_level_terminal(master,old):
 from world_city.concept_city_v3.assemblies.property.registered.r1.author import append_surface
 import math
 ext=load(RES/'common_entry_surface_audit.json')['row'];rows=ext['external_surface']['triangulated_top_surface'];end=ext['polyline_xz_m'][-1];prior=ext['polyline_xz_m'][-2];L=math.dist(end,prior);t=[(end[k]-prior[k])/L for k in (0,1)];n=[-t[1],t[0]]
 def point(d,u):return [end[k]+d*t[k]+u*n[k]for k in (0,1)]
 def oldheight(p):
  for row in rows:
   tri=row['vertices_xyz_m'];poly=[[v[0],v[2]]for v in tri]
   if geo.point_in_convex_polygon(p,poly,1e-7):return terrain.common.height(terrain.common.plane(tri),p)
  raise ValueError(('Outside explicit source approach',p))
 def v(d,u):
  p=point(d,u);mix=min(1,max(0,(d+4)/3));y=(1-mix)*oldheight(p)+mix*8 if mix<1 else 8;return [p[0],y,p[1]]
 ds=[-4+i*.5 for i in range(10)];us=[-1.5+i*.5 for i in range(7)];triangles=[]
 for da,db in zip(ds,ds[1:]):
  for ua,ub in zip(us,us[1:]):
   quad=[v(da,ua),v(db,ua),v(db,ub),v(da,ub)]
   for ids in ((0,1,2),(0,2,3)):
    tri=[quad[i]for i in ids];grade=math.hypot(*terrain.common.plane(tri)[:2]);assert grade<=.12+1e-8,grade;triangles.append({'kind':'R02_level_terminal_blend','vertices_xyz_m':tri,'source_grade':grade})
 domain=[point(-4,-1.5),point(.5,-1.5),point(.5,1.5),point(-4,1.5)];pose=old['position_m'];master['components'][0]['operations'].append({'id':'R02_replace_terminal_skin','part':'solid','action':'cut','shape':{'kind':'extrusion','polygon':[[q[0]-pose[0],-(q[1]-pose[2])]for q in domain],'z_min':-3,'z_max':2},'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
 temp=copy.deepcopy(master);temp['components'][0]['operations']=[];temp=append_surface(temp,{'id':'R02_COMMON_LEVEL_LANDING','triangulated_top_surface':triangles},[pose[0],pose[2]],pose[1])
 for op in temp['components'][0]['operations']:op['id']='R02_terminal_'+op['id'];master['components'][0]['operations'].append(op)
 master['metadata']['R02_level_public_terminal']={'floor_y_m':8,'source_domain_xz_m':domain,'blend_length_m':3,'level_last_length_m':1.5,'triangles':triangles,'maximum_full_triangle_grade':max(r['source_grade']for r in triangles)}
 write('level_terminal_source.json',master['metadata']['R02_level_public_terminal'])

def main():
 t=time.monotonic();projection=load(BASE/'actual_native_projection.json');old=next(p for p in projection['instances']if p['id']=='REGISTERED_LANDSCAPE:SITE_COMMON');asset=projection['assets'][old['asset_key']];master=load(ROOT/asset['source']['path']);ops=master['components'][0]['operations'];skin=[o for o in ops if o['id'].startswith('r1_access_skin_')];assert len(skin)==166;assets=[];cells={};original=None
 for role,pitch in [('retained_base',.5),('fine_access',.125)]:
  s=copy.deepcopy(master);s['id']='registered_precinct_r06_common_r02_'+role;s['revision']=1;s['components'][0]['operations']=[o for o in ops if not o['id'].startswith('r1_access_skin_')]if role=='retained_base'else copy.deepcopy(skin);s['metadata'].update(derived_from=asset['source'],native_pitch_m=pitch,author=ref(Path(__file__)),repair_role=role,mesh_scaling=False,runtime_ready=False)
  if role=='fine_access':
   add_level_terminal(s,old)
   full,_=roof_rectangles(load(ROOT/assets[0]['cache']['path']),{g['material']for g in load(ROOT/assets[0]['cache']['path'])['groups']});ext=load(RES/'common_entry_surface_audit.json')['row']['external_surface'];coords=[v for q in ext['polygon_regions_xz_m']for v in q];clip=b.rect(min(v[0]for v in coords)-old['position_m'][0]-.25,min(v[1]for v in coords)-old['position_m'][2]-.25,max(v[0]for v in coords)-old['position_m'][0]+.25,max(v[1]for v in coords)-old['position_m'][2]+.25);cuts=[]
   for q in full:
    q=geo.convex_intersection(q,clip)
    if geo.polygon_area(q)<=1e-8:continue
    cuts.append(q);s['components'][0]['operations'].append({'id':'retained_base_native_exclusion:'+str(len(cuts)),'part':'solid','action':'cut','shape':{'kind':'extrusion','polygon':[[v[0],-v[1]]for v in q],'z_min':-3,'z_max':2},'transform':{'basis':[[1,0,0],[0,0,1],[0,-1,0]]}})
   s['metadata']['retained_base_actual_native_exclusions_local_xz_m']=cuts
  sr=write('masters/'+s['id']+'.json',s);est=estimate_candidates(s,pitch);print('preflight',role,est['candidate_cells_exact_aabb_visits'],flush=True);assert est['candidate_cells_exact_aabb_visits']<600000;write(role+'_preflight.json',{'source':sr,'pitch_m':pitch,'estimate':est,'old_native':asset,'common_dependencies':[ref(ROOT/'voxel_character/common/coordinate_planes.py'),ref(ROOT/'voxel_character/common/render_data.py'),ref(ROOT/'voxel_character/common/core.py')]});c=coordinate_planes.compile_master(s,{'pitch':pitch},max_candidate_cells=600000,max_output_cells=200000);assert c['valid'];m=render_data.make_render_data(c);cr=write('cache/'+s['id']+'.render.json',m);assets.append({'id':s['id'],'role':role,'source':sr,'cache':cr,'pitch_m':pitch,'master_hash':core.digest(s),'bounds':m['bounds'],'candidate_cells':c['candidate_cells'],'output_cells':len(c['cells'])});cells[role]=c['cells'];print('compiled',role,c['candidate_cells'],len(c['cells']),flush=True)
 placements=[{'id':'R06_COMMON_R02:'+a['role'],'asset_key':a['id'],'source':a['source'],'cache':a['cache'],'position_m':old['position_m'],'yaw_rad':old.get('yaw_rad',0),'scale':[1,1,1],'role':a['role']}for a in assets];write('resolved_native_candidate.json',{'schema':'riverstone.precinct.common_entry.native_candidate.v1','assets':assets,'placements':placements,'replacement_ledger':{'existing_native_placements_removed':[old['id']],'retained_source_native':asset},'source_native_profile':ref(RES/'common_actual_native_profile.json'),'source_public_profile':ref(RES/'common_entry_surface_audit.json'),'status':'NATIVE_CANDIDATE_PENDING_FINITE_GROUND_SIDE_AND_WALK_CHECKS','activation':False,'runtime_ready':False,'seconds':time.monotonic()-t});print('complete',time.monotonic()-t)
if __name__=='__main__':main()
