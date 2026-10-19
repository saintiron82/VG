"""Create short, source-exact corner routes only; no terrain/asset edits."""
import json,math,pathlib,hashlib
import numpy as np
O=pathlib.Path(__file__).resolve().parent;ROOT=O.parents[4];B=ROOT/'world_city/concept_city_v3';S=B/'traversal_r5/revisions/r06_r8_precinct/case_input_certification_r04/selected_all493_bound_r02.json';D=json.load(open(S));routes={r['id']:r for r in D['routes']};P=json.load(open(O/'height_seam_priorities.json'))
def sha(p):return hashlib.file_digest(open(p,'rb'),'sha256').hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
def at(q,s,t):
 j=min(len(s)-2,max(0,int(np.searchsorted(s,t,side='right')-1)));u=(t-s[j])/max(s[j+1]-s[j],1e-12);return (q[j]+u*(q[j+1]-q[j])).tolist()
def clip(rid,p):
 q=np.array(routes[rid]['points']);v=np.diff(q,axis=0);h=v[:,[0,2]];ll=np.linalg.norm(h,axis=1);s=np.r_[0,np.cumsum(ll)];t=np.clip(np.sum((np.array(p)[[0,2]]-q[:-1,[0,2]])*h,axis=1)/np.maximum(ll**2,1e-12),0,1);x=q[:-1]+t[:,None]*v;j=np.linalg.norm(x[:,[0,2]]-np.array(p)[[0,2]],axis=1).argmin();sc=float(s[j]+t[j]*ll[j]);legs={}
 for side in [-1,1]:
  available=sc if side<0 else s[-1]-sc
  if available<3-1e-6:continue
  end=sc+side*min(4.,available);low,high=sorted([sc,end]);vals=[low]+[float(a) for a in s if low+1e-8<a<high-1e-8]+[high];pts=[at(q,s,a) for a in vals]
  if side>0:pts=list(reversed(pts)) # all legs endpoint -> seam
  legs[str(side)]={'points':pts,'distance_xz_m':abs(end-sc),'source_station_m':sc,'endpoint_station_m':end,'source_route_id':rid}
 return legs
out=[];groups=[]
for p in P['priorities']:
 au=p['route_ids_u'][0];bv=p['route_ids_v'][0];A=clip(au,p['xyz_u']);BB=clip(bv,p['xyz_v']);group=f"SEAM_{p['priority']:02d}";ids=[]
 for sa,a in A.items():
  for sb,b in BB.items():
   pts=a['points']+list(reversed(b['points']))
   # Keep two different authored Y hints at the same XZ junction explicit. The
   # unchanged controller ignores target Y after spawning; geometry determines feet.
   if math.dist(pts[len(a['points'])-1],pts[len(a['points'])])<1e-7:pts.pop(len(a['points']))
   name=f"{group}:A{sa}:B{sb}";ids.append(name)
   out.append({'id':name,'kind':'actual_scene_public_route','group':group,'points':pts,'both_directions':True,'bidirectional':True,'cart_test':False,'source_road_ids':sorted(set(routes[au].get('source_road_ids',[])+routes[bv].get('source_road_ids',[]))),'source_route_ids':[au,bv],'source_route_legs':[a,b],'minimum_allowed_feet_y_m':min(q[1] for q in pts)-1.,'minimum_allowed_feet_y_explicit':True,'bridge_state':'ROAD_OPEN','test_scope':'New transition between two separately certified source paths. Exact source XZ and per-leg waypoint Y hints; no terrain/collider/controller change. Actual feet continuity and corner clearance are the result to establish, not assumed.','authored_intersection_xyz':[p['xyz_u'],p['xyz_v']]})
 groups.append({**p,'group':group,'forward_route_ids':ids,'directional_cases':len(ids)*2,'leg_window_m':[3,4],'omitted_leg_sides_reason':'A source polyline ending within3m of its crossing cannot supply an invented continuation.'})
identity={'schema':'riverstone.frozen_scene_disjoint_patch_composition.v1','id':'R10_JUNCTION_AUDIT_IDENTITY_NO_EDITS','base_scene_sha256':D['sources']['scene']['sha256'],'status':'identity_no_terrain_or_native_edits','source_surface_hashes':{},'surface_edits':[],'appended_surfaces':{},'removed_foundation_proxy_ids':[]};ip=O/'identity_no_edits.json';ip.write_text(json.dumps(identity,indent=2)+'\n')
request={'schema':'riverstone.r10.junction_runtime_request.v1','status':'PREPARED_REQUEST_NOT_EXECUTED','base_scene':D['sources']['scene'],'finite_patch':ref(ip),'visual_index':ref(B/'registered_integration/r9/integration_r02/index.json'),'producer_sources':{'selected493':ref(S),'height_seams':ref(O/'height_seam_priorities.json'),'request_generator':ref(pathlib.Path(__file__))},'collision_margin_m':6,'routes':out,'junctions':groups,'gates':[],'cart_fixture':{'enabled':False,'reason':'This request is unchanged-controller pedestrian junction continuity only.'},'expected_positive_directional_cases':2*len(out),'expected_retained_negative_controls':2,'limits':['New turn vectors were not among the original493. No pass status until actual replay completes.','Exact r9 integration_r02, no gate candidate patch or copied whole-city scene.','Both original per-leg height hints are preserved even at a shared XZ. Traversal.gd sets target.y=body.position.y, so actual source collision controls feet.','Existing special collision contracts must be explicitly extracted if any crop intersects them; no omission or ad-hoc collider substitution permitted.']}
(O/'junction_runtime_request.json').write_text(json.dumps(request,indent=2)+'\n');print('forward',len(out),'directional',len(out)*2,'groups',[(x['group'],x['directional_cases']) for x in groups])
# Reuse the gate finite-crop preparer unchanged; redirect its owned-output root
# only. Its strict special-collision checks remain active. No heavy build here.
wrapper='''#!/usr/bin/env python3\n"""Use the unchanged R9 finite-crop preparer for local junction tests."""\nimport importlib.util,pathlib,sys\nsys.dont_write_bytecode=True\nH=pathlib.Path(__file__).resolve().parent\nROOT=H.parents[4]\np=ROOT/"world_city/concept_city_v3/registered_integration/r9/gate_runtime_validation/prepare.py"\ns=importlib.util.spec_from_file_location("gate_finite_preparer",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.H=H\nif __name__=="__main__":m.main()\n'''
(O/'prepare_junctions.py').write_text(wrapper)
for name in ['CartClearance.gd','CartClearance.tscn']:(O/name).write_bytes((B/'registered_integration/r9/gate_runtime_validation'/name).read_bytes())
