"""R02: one continuous finite arrival/junction top plus exact closed perimeter sides."""
from __future__ import annotations
import json,math,hashlib,sys,copy
from pathlib import Path
import numpy as np
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;ROOT=H.parents[5];sys.path.insert(0,str(ROOT))
from world_city.runtime_city.checks import placement as g
from world_city.concept_city_v3.review_geometry import DomainCut,fan,clean
from world_city.concept_city_v3.registered_integration.r9.landward_gates.build_corridors import Ground,plane,ph,up,area3,cut3,xz
C=ROOT/'world_city/concept_city_v3';BASE=C/'evidence/r8_final110_runtime_r01/scene.json';SHA='2d53ca4a99572f1a3383a847b6ae5f93dda78fb7e721af8a6a15b78de4d7f1c2'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def ch(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(n,x):(H/n).write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def rect(a,b,c,d):return [[a,b],[c,b],[c,d],[a,d]]
def grids(a,b,step,extra=()):return sorted({a,b,*extra,*[a+step*k for k in range(1,math.ceil((b-a)/step))if a+step*k<b]})
def source_rows():return read(H.parent/'context.json')['sites']['abbey']['surface_rows']

def build():
 assert sha(BASE)==SHA
 ctx=read(H.parent/'context.json')['sites']['abbey'];rows=ctx['surface_rows'];ground=Ground(rows);plan=read(C/'registered_source/plan.json');road=next(r for r in plan['roads']if r['id']=='WEST_MONASTERY_EDGE');a,b,c=road['resolved_world_xyz_m'][9:12];xmin=-259.;xmax=c[0];zmin=a[2];zmax=-.5;owner=rect(xmin,zmin,xmax,zmax)
 # Existing public road's unchanged north/east station heights anchor the ramps.
 yn=ground.at(xz(a));ye=ground.at(xz(c));xturn=b[0];zflat=-9.5
 def desired(p):
  x,z=p;north=yn+(8-yn)*min(1,max(0,(z-zmin)/(zflat-zmin)));east=8+(ye-8)*min(1,max(0,(x-xturn)/(xmax-xturn)));street=min(8,north,east);f=min(1,max(0,(x+253)/4));return 8*(1-f)+street*f
 xs=grids(xmin,xmax,.5,[-253.,-249.,xturn]);zs=grids(zmin,zmax,.5,[zflat,b[2]])
 tops=[];nodes={(x,z):[x,desired([x,z]),z]for x in xs for z in zs}
 for x0,x1 in zip(xs,xs[1:]):
  for z0,z1 in zip(zs,zs[1:]):
   v=[nodes[x0,z0],nodes[x1,z0],nodes[x1,z1],nodes[x0,z1]]
   tops.extend([up([v[0],v[1],v[2]]),up([v[0],v[2],v[3]])])
 topground=Ground([dict(material='ground_stone',triangle_index=i,triangle=t)for i,t in enumerate(tops)])
 def height(p):return topground.at(p)
 assert sum(g.intersection_area(owner,r['polygon_xz_m'])for r in ctx['floors'])<1e-7,'Canonical owner must not cover native court floors'
 # Exact finite clipping preserves every outside source fragment on its plane.
 edits=[];source_mats=set();water=[];tiny=[]
 def usable(t,kind,meta):
  ar=area3(t)
  if ar<1e-12:return False
  aa=np.asarray(t,dtype=np.float32);n=np.cross(aa[1]-aa[0],aa[2]-aa[0]);dd=np.asarray(t);nd=np.cross(dd[1]-dd[0],dd[2]-dd[0]);ok=np.dot(n,n)>0 and np.dot(n,nd)>0
  if not ok:
   assert ar<1e-5,(kind,ar,meta);tiny.append(dict(kind=kind,area_m2=ar,metadata=meta,triangle=t))
  return ok
 for r in rows:
  t=r['triangle'];p=[xz(v)for v in t]
  if max(v[0]for v in p)<xmin or min(v[0]for v in p)>xmax or max(v[1]for v in p)<zmin or min(v[1]for v in p)>zmax:continue
  if r['material']=='water':
   if g.intersection_area(p,owner)>1e-9:water.append(r)
   continue
  parts=cut3(t,owner);repl=[tt for q in parts for tt in fan(q)if area3(tt)>1e-10]
  if area3(t)-sum(area3(q)for q in repl)<1e-8:continue
  repl=[tt for k,tt in enumerate(repl)if usable(tt,'outside_source_fragment',[r['material'],r['triangle_index'],k])]
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_xyz_m=t,source_triangle_sha256=ch(t),replacement_triangles_xyz_m=repl));source_mats.add(r['material'])
 assert not water
 # Close the four actual outer boundaries. Subdivide at original source-face
 # intersections and every canonical top knot. At each segment use the exact
 # selected outside source plane; no thin visual overlay or double-sided faces.
 banks=[];closure=[];source_edges=[]
 for r in ground.rows:
  for p,q in zip(r['polygon'],r['polygon'][1:]+r['polygon'][:1]):source_edges.append((p,q))
 for side,(aa,bb)in enumerate(zip(owner,owner[1:]+owner[:1])):
  dx,dz=bb[0]-aa[0],bb[1]-aa[1];den=dx*dx+dz*dz;length=math.sqrt(den);cuts={0.,1.}
  for x in xs:
   if abs(dx)>1e-12:
    t=(x-aa[0])/dx
    if 0<t<1:cuts.add(t)
  for z in zs:
   if abs(dz)>1e-12:
    t=(z-aa[1])/dz
    if 0<t<1:cuts.add(t)
  for p,q in source_edges:
   ux,uz=q[0]-p[0],q[1]-p[1];det=dx*uz-dz*ux
   if abs(det)>1e-12:
    t=((p[0]-aa[0])*uz-(p[1]-aa[1])*ux)/det;s=((p[0]-aa[0])*dz-(p[1]-aa[1])*dx)/det
    if -1e-9<s<1+1e-9 and 0<t<1:cuts.add(t)
   else:
    for v in [p,q]:
     if g.point_segment_distance(v,aa,bb)<1e-8:
      t=((v[0]-aa[0])*dx+(v[1]-aa[1])*dz)/den
      if 0<t<1:cuts.add(t)
  ordered=sorted(cuts)
  for t0,t1 in zip(ordered,ordered[1:]):
   if (t1-t0)*length<1e-7:continue
   p=[aa[0]+t0*dx,aa[1]+t0*dz];q=[aa[0]+t1*dx,aa[1]+t1*dz];mid=[(p[k]+q[k])/2 for k in [0,1]]
   # Sample just outside to select the retained source face on the correct side.
   outward=[dz/length,-dx/length];probe=[mid[k]+outward[k]*1e-6 for k in [0,1]]
   found=[r for i in ground.idx.candidates([probe])if g.point_in_convex_polygon(probe,(r:=ground.rows[i])['polygon'],1e-8)]
   if found:
    roads=[r for r in found if r['material']=='road'];old=max(roads or found,key=lambda r:ph(r['plane'],probe));pl=old['plane'];oldref=dict(material=old['material'],triangle_index=old['triangle_index'])
   else:
    assert any(g.point_in_convex_polygon(mid,r['polygon_xz_m'],1e-5)for r in ctx['floors']+ctx['bodies']),('No retained outside support',side,p,q);pl=(0,0,8);oldref=dict(native_owner='R06_ABBEY_GATE_R05:herb')
   yp,yq=ph(pl,p),ph(pl,q);hp,hq=height(p),height(q);d0,d1=hp-yp,hq-yq;sections=[(p,q,yp,yq,hp,hq)]
   if d0*d1<-1e-12:
    t=d0/(d0-d1);v=[p[k]+t*(q[k]-p[k])for k in [0,1]];yv=yp+t*(yq-yp);sections=[(p,v,yp,yv,hp,yv),(v,q,yv,yq,yv,hq)]
   for pp,qq,y0,y1,h0,h1 in sections:
    if max(abs(h0-y0),abs(h1-y1))<1e-7:continue
    quad=[[pp[0],y0,pp[1]],[pp[0],h0,pp[1]],[qq[0],h1,qq[1]],[qq[0],y1,qq[1]]]
    tri=[tt for tt in fan(quad)if usable(tt,'perimeter_side',[side,t0,t1])];banks+=tri;closure.append(dict(side=side,from_xz_m=pp,to_xz_m=qq,old_y_m=[y0,y1],new_y_m=[h0,h1],source=oldref,triangles=tri))
 # Grid top is continuous by construction; exact 3D shared edges have equal heights.
 edges={}
 for i,t in enumerate(tops):
  for p,q in zip(t,t[1:]+t[:1]):
   k=tuple(sorted((tuple(xz(p)),tuple(xz(q)))));edges.setdefault(k,[]).append([p,q])
 outeredges=0
 for k,rs in edges.items():
  assert len(rs)in [1,2]
  if len(rs)==2:
   heights={tuple(xz(v)):v[1]for v in rs[0]};assert all(abs(heights[tuple(xz(v))]-v[1])<1e-12 for v in rs[1])
  else:
   outeredges+=1;assert all(abs(v[0]-xmin)<1e-8 or abs(v[0]-xmax)<1e-8 or abs(v[2]-zmin)<1e-8 or abs(v[2]-zmax)<1e-8 for v in rs[0])
 assert all(usable(t,'canonical_top',i)for i,t in enumerate(tops));assert sum(r['area_m2']for r in tiny)<1e-5,tiny
 s=read(BASE);append={'ground_stone':[v for t in tops for v in t],'bank':[v for t in banks for v in t]};own=dict(id='R10_ABBEY_CANONICAL_ARRIVAL_JUNCTION_R02',polygon_xz_m=owner,ownership_polygons_xz_m=[owner],core_polygons_xz_m=[owner],access='unrestricted_public',public_road_id='WEST_MONASTERY_EDGE',waiting_pocket_area_m2=16.,native_court_owner='R06_ABBEY_GATE_R05:herb',continuous_top=True,explicit_closed_perimeter_sides=True)
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R10_ABBEY_CONTINUOUS_ARRIVAL_R02',status='source_ready_runtime_and_visual_pending',base_scene=ref(BASE),base_scene_sha256=SHA,source_surface_hashes={m:ch(s['surfaces'][m])for m in source_mats},surface_edits=edits,appended_surfaces=append,removed_foundation_proxy_ids=[],ownership=[own],summary=dict(source_triangle_edits=len(edits),removed_bank_faces=sum(e['material']=='bank'for e in edits),appended_top_triangles=len(tops),appended_closed_side_triangles=len(banks),owned_area_m2=g.polygon_area(owner),waiting_pocket_area_m2=16.,water_edits=0,native_building_edits=0,retirements=0,float32_removed_slivers=len(tiny),float32_removed_area_m2=sum(r['area_m2']for r in tiny)))
 write('surface_patch.json',patch);write('closure_ledger.json',dict(status='CONTINUOUS_TOP_AND_CLOSED_PERIMETER_SOURCE_PASS',top_grid_x=xs,top_grid_z=zs,top_internal_edges=sum(len(v)==2 for v in edges.values()),top_outer_edges=outeredges,internal_height_jump_count=0,perimeter_closure=closure,float32_slivers=tiny,old_failure_preserved=ref(C/'evidence/r10_functional_r01/R10_ABBEY_PUBLIC_GATE_EYE.png'),diagnosis='r01 source-face-local shoulder interpolation inherited the old bench/road discontinuity after removing222 bank faces. R02 removes inherited internal jumps and closes all retained outer height changes with true oriented side geometry.'))
 oldpack=read(H.parent/'candidate_r01/pack.json');write('pack.json',oldpack);write('ground_ownership.json',dict(owners=[own],public_private_transition=read(H.parent/'candidate_r01/ground_ownership.json')['public_private_transition']));print(json.dumps(patch['summary'],indent=2))
if __name__=='__main__':build()
