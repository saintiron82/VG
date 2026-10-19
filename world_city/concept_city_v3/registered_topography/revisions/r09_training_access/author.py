"""Recovered r09: bounded native training strip through the unchanged common compiler.
The lost post-backup r09 bytes are not reproduced or claimed by hash.
"""
import copy,hashlib,json,math,time
from pathlib import Path
from voxel_character.common import coordinate_planes
from world_city.concept_city_v3.assemblies.property.registered.audit import candidate_budget
from world_city.runtime_city.checks import placement as geo
HERE=Path(__file__).resolve().parent;CITY=HERE.parents[2];ROOT=CITY.parents[1]
def clean(p):return p if len(p)>=3 and geo.polygon_area(p)>1e-8 else None
SOURCE=CITY/'assemblies/landscape/registered/training/generated/registered_training_ground_3de01a02f6cd.master.json'
PACK_PATH=CITY/'assemblies/landscape/registered/training/resolved_placements.json'
PACK=json.loads(PACK_PATH.read_bytes());SOURCE_MASTER=json.loads(SOURCE.read_bytes())
ORIGIN=[-330,18,-180];PITCH=.125;GUARD=.125;CAP=300000
SURFACE=PACK['external_access_surfaces'][0]
TRIANGLES=SURFACE['triangulated_top_surface']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def hull(points):
 ps=sorted(set(map(tuple,points)))
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 lower=[];upper=[]
 for p in ps:
  while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
  lower.append(p)
 for p in reversed(ps):
  while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
  upper.append(p)
 return [list(p) for p in lower[:-1]+upper[:-1]]
def rect(b):return [[b[0],b[1]],[b[2],b[1]],[b[2],b[3]],[b[0],b[3]]]
def vertical(poly,lo,hi):return dict(shape=dict(kind='extrusion',polygon=[[x-ORIGIN[0],-(z-ORIGIN[2])] for x,z in poly],z_min=lo-ORIGIN[1],z_max=hi-ORIGIN[1]),transform=dict(basis=[[1,0,0],[0,0,1],[0,-1,0]]))
def tops(render):
 out=[]
 for g in render['groups']:
  for q in g['quads']:
   a=[q[1][i]-q[0][i] for i in range(3)];b=[q[2][i]-q[0][i] for i in range(3)]
   if a[2]*b[0]-a[0]*b[2]>1e-10:
    out.append(dict(polygon_xz_m=[[p[0]+ORIGIN[0],p[2]+ORIGIN[2]] for p in q],y_m=q[0][1]+ORIGIN[1],material=g['material']))
 return out

def coarse_master():
 m=copy.deepcopy(SOURCE_MASTER);ops=m['components'][0]['operations'];removed=[r['id'] for r in ops if r['id'].startswith('r1_access_skin_')];assert len(removed)==44
 m['components'][0]['operations']=[r for r in ops if r['id'] not in removed];m['id']='registered_training_r09_recovered_coarse';m['revision']=9
 m['metadata'].update(recovery='Reconstructed from verified version5 source; earlier r09 artifact was lost.',removed_operations=removed,original_master_sha256=sha(SOURCE),world_origin_m=ORIGIN)
 return m

def fine_master(coarse_tops):
 m={k:copy.deepcopy(SOURCE_MASTER[k]) for k in ('schema','axes','grid_origin','materials')};m.update(id='registered_training_r09_recovered_fine',revision=9,components=[],instances=[],metadata=dict(recovery='New deterministic recovered candidate; no old hash equivalence claimed',source_pack_sha256=sha(PACK_PATH),world_origin_m=ORIGIN,world_grid_origin_m=[0,0,0],pitch_m=PITCH,source_surface=SURFACE,guard_linf_m=GUARD,skin_depth_m=.5,construction='Vertical-sided finite wedges; local-instance cuts against exact triangle footprint and persisted coarse top rectangles. No alternate mesher.'))
 for i,t in enumerate(TRIANGLES):
  tri=t['vertices_xyz_m'];xz=[[p[0],p[2]] for p in tri];p=tri[0];a=[tri[1][j]-p[j] for j in range(3)];b=[tri[2][j]-p[j] for j in range(3)];det=a[0]*b[2]-a[2]*b[0];gx=(a[1]*b[2]-a[2]*b[1])/det;gz=(a[0]*b[1]-a[1]*b[0])/det;g=math.hypot(gx,gz);u=[gx/g,gz/g] if g>1e-12 else [1,0];v=[-u[1],u[0]]
  expanded=hull([[x+dx,z+dz] for x,z in xz for dx in (-GUARD,GUARD) for dz in (-GUARD,GUARD)])
  us=[(q[0]-p[0])*u[0]+(q[1]-p[2])*u[1] for q in expanded];vs=[(q[0]-p[0])*v[0]+(q[1]-p[2])*v[1] for q in expanded];lo,hi=min(us),max(us);vlo,vhi=min(vs),max(vs)
  poly=[[lo,g*lo-.5],[hi,g*hi-.5],[hi,g*hi],[lo,g*lo]]
  op=dict(id='r09_plane_'+str(i),part='solid',action='paint',material='stone_dark',shape=dict(kind='extrusion',polygon=poly,z_min=vlo,z_max=vhi),transform=dict(basis=[[u[0],0,v[0]],[0,1,0],[u[1],0,v[1]]],translation=[p[j]-ORIGIN[j] for j in range(3)]));ops=[op]
  cover=hull([[p[0]+s*u[0]+t*v[0],p[2]+s*u[1]+t*v[1]] for s in (lo,hi) for t in (vlo,vhi)])
  outside=[q for cut in geo.convex_difference(cover,expanded) if(q:=clean(cut))]
  cuts=outside[:]
  for f in coarse_tops:
   q=clean(geo.convex_intersection(cover,f['polygon_xz_m']))
   if q:cuts.append(q)
  for j,q in enumerate(cuts):ops.append(dict(id='r09_vertical_cut_'+str(i)+'_'+str(j),part='solid',action='cut',**vertical(q,p[1]+g*lo-.5,p[1]+g*hi)))
  key='wedge_'+str(i);m['components'].append(dict(id=key,parts=[dict(id='solid',pivot=[0,0,0])],operations=ops));m['instances'].append(dict(id=key,component=key))
 return m

def compile_one(m,pitch):
 from voxel_character.common import render_data
 b=candidate_budget(m,pitch);assert b['within_candidate_cap'];mp=HERE/'sources'/(m['id']+'.master.json');write(mp,m)
 print(json.dumps(dict(stage='budget_before_compile',asset=m['id'],**b)),flush=True)
 start=time.monotonic();c=coordinate_planes.compile_master(m,{'pitch':pitch},max_candidate_cells=CAP,max_output_cells=100000);assert c['valid'];r=render_data.make_render_data(c);rp=HERE/'cache'/(m['id']+'.render.json');write(rp,r);cp=HERE/'cache'/(m['id']+'.compiled.json');write(cp,c)
 record=dict(asset_key=m['id'],master_path=str(mp),master_file_sha256=sha(mp),compiled_asset_ref=str(rp),render_sha256=sha(rp),compiled_cells_path=str(cp),compiled_cells_sha256=sha(cp),sampling_resource={'pitch':pitch},pitch_m=pitch,bounds=r['bounds'],cell_count=r['cell_count'],quad_count=r['quad_count'],common_master_hash=c['master_hash'],common_payload_hash=c['payload_hash'])
 result=dict(asset=m['id'],candidate_cells=c['candidate_cells'],occupied_cells=r['cell_count'],quad_count=r['quad_count'],elapsed_s=round(time.monotonic()-start,3),budget=b);print(json.dumps(result),flush=True);return record,r,c,result

def run():
 coarse=coarse_master();a,r,c,report=compile_one(coarse,.5);fine=fine_master(tops(r));write(HERE/'preflight.json',dict(reconstruction_note='Original post-checkpoint r09 source and caches were lost during executor reset. This new candidate is reconstructed from verified version5 baseline and must receive fresh independent checks.',original_training_pack_sha256=sha(PACK_PATH),coarse=report['budget'],fine=candidate_budget(fine,PITCH),scope_m2=sum(geo.polygon_area(p) for p in SURFACE['polygon_regions_xz_m']),no_citywide_compile=True));b,s,d,report2=compile_one(fine,PITCH);write(HERE/'cache/manifest.json',dict(assets={a['asset_key']:a,b['asset_key']:b},coarse_asset=a['asset_key'],fine_asset=b['asset_key'],origin_m=ORIGIN));write(HERE/'compile_report.json',dict(status='compiled_reconstructed_candidate',results=[report,report2]));return a,b
if __name__=='__main__':run()
