"""Geometric floor-support diagnostic; original failed physics result retained."""
import json,pathlib,math
import numpy as np
O=pathlib.Path(__file__).resolve().parent;P=O/'junction_replay_r01';data=json.load(open(P/'evidence/replay_r01/capsule.json'));r=next(x for x in data['routes'] if x['id']=='SEAM_03:A1:B-1_REVERSE');geom=json.load(open(P/'geometry/SEAM_03.json'));prep=json.load(open(P/'prepared.json'));inp=next(x for x in prep['routes'] if x['id']==r['id']);faces=geom['source_face_indices'];origin=np.array(geom['local_origin_proof']['applied_origin_xyz_m']);tri=np.array(geom['triangles'])+origin
samples={0:r['spawn_position']}
for x in r['position_samples']:samples[x['frame']]=x['capsule_center']
for x in r['waypoint_reached_frames']:samples[x['walk_physics_frame']]=x['position']
samples=sorted(samples.items());path=[p for f,p in samples]
def intervals(a,b,tri,tolerance_m=0):
 A=tri[:,0];U=tri[:,1]-A;V=tri[:,2]-A;det=U[:,0]*V[:,2]-V[:,0]*U[:,2];valid=abs(det)>1e-16;dd=np.where(valid,det,1)
 def bary(p):
  X=np.array(p)-A;u=(X[:,0]*V[:,2]-V[:,0]*X[:,2])/dd;v=(U[:,0]*X[:,2]-X[:,0]*U[:,2])/dd;return u,v
 u0,v0=bary(a);u1,v1=bary(b);y0=A[:,1]+u0*U[:,1]+v0*V[:,1];y1=A[:,1]+u1*U[:,1]+v1*V[:,1];lo=np.zeros(len(tri));hi=np.ones(len(tri))
 # Clip f(t)>=0 for barycentric and an observed ground-height band.
 eu=tolerance_m*np.linalg.norm(V[:,[0,2]],axis=1)/abs(dd);ev=tolerance_m*np.linalg.norm(U[:,[0,2]],axis=1)/abs(dd);ew=tolerance_m*np.linalg.norm((U-V)[:,[0,2]],axis=1)/abs(dd)
 for f0,f1 in [(u0+eu,u1+eu),(v0+ev,v1+ev),(1-u0-v0+ew,1-u1-v1+ew),(y0-.75,y1-.75),(1.25-y0,1.25-y1)]:
  dv=f1-f0;flat=abs(dv)<1e-16;valid &= ~(flat&(f0<0));pos=dv>1e-16;neg=dv< -1e-16;lo=np.where(pos,np.maximum(lo,-f0/np.where(pos,dv,1)),lo);hi=np.where(neg,np.minimum(hi,-f0/np.where(neg,dv,1)),hi)
 valid &= (hi>=lo)&(hi>=0)&(lo<=1);rows=sorted((max(0,float(lo[i])),min(1,float(hi[i])),int(i)) for i in np.nonzero(valid)[0]);merged=[]
 for low,high,i in rows:
  if merged and low<=merged[-1][1]+1e-12:merged[-1][1]=max(merged[-1][1],high);merged[-1][2].append(i)
  else:merged.append([low,high,[i]])
 gaps=[];end=0.
 for low,high,ids in merged:
  if low>end+1e-12:gaps.append((end,low))
  end=max(end,high)
 if end<1-1e-12:gaps.append((end,1.))
 return gaps,rows
reports=[]
for label,t,tol in [('world_double',tri,0),('actual_float32_vertex_mesh',tri.astype(np.float32).astype(float),0),('world_double_10nanometre_numeric_diagnostic',tri,1e-8),('float32_10micrometre_numeric_diagnostic',tri.astype(np.float32).astype(float),1e-5)]:
 for pathlabel,pts in [('authored_waypoint_polyline',inp['points']),('interpolated_recorded_capsule_centers',path)]:
  gaps=[];length=0.
  for j,(a,b) in enumerate(zip(pts,pts[1:])):
   aa=np.array(a);bb=np.array(b);dist=float(np.linalg.norm((bb-aa)[[0,2]]));length+=dist
   if dist<1e-10:continue
   missing,_=intervals(aa,bb,t,tol)
   for lo,hi in missing:
    gaps.append({'segment':j,'length_xz_m':(hi-lo)*dist,'start_xyz':(aa+lo*(bb-aa)).tolist(),'end_xyz':(aa+hi*(bb-aa)).tolist(),'frame_interval':[samples[j][0],samples[j+1][0]] if pathlabel.startswith('interpolated') else None})
  reports.append({'geometry':label,'edge_distance_tolerance_m':tol,'path':pathlabel,'tested_horizontal_length_m':length,'uncovered_intervals':gaps,'sum_uncovered_xz_m':sum(g['length_xz_m'] for g in gaps),'largest_uncovered_xz_m':max((g['length_xz_m'] for g in gaps),default=0)})
# Query nearest retained triangle seams around the main turn and preserve IDs.
turn=np.array(inp['points'][2]);xz=tri[:,:,[0,2]];centers=xz.mean(axis=1);near=np.argsort(np.linalg.norm(centers-turn[[0,2]],axis=1))[:20]
out={'schema':'riverstone.r10.single_ray_miss_diagnostic.v1','status':'FAIL_RETAINED_CAUSE_NOT_PROVEN','failed_case_id':r['id'],'observed':{k:r[k] for k in ['ground_ray_miss_frames','not_on_floor_frames','max_not_on_floor_streak','status','min_feet_y_m','max_feet_y_m','obstacle_contact_ids']},'actual_sample_ground_y_m':[x['ground_y_m'] for x in r['position_samples']],'local_origin_proof':geom['local_origin_proof'],'coverage':reports,'near_turn_faces':[{'crop_face_index':int(i),'source':faces[i],'vertices_world_xyz_m':tri[i].tolist()} for i in near],'interpretation':['All recorded samples have groundY≈1 and the capsule stayed on floor; the isolated ray miss has no exact per-frame position record in the unchanged controller.','Coverage test uses exact projected source triangles in a0.75–1.25m ground-height band; a geometric gap is only a candidate cause, not proof of the missing ray frame.','Interpolated recorded positions are diagnostic approximations between logged frames. They do not replace an actual strict runtime pass.','Do not edit terrain or weaken acceptance until a real unsupported interval is localized.']};(O/'ray_miss_diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'coverage':reports},indent=2))
