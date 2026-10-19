"""Sequential bounded common sampling and exact native geometry checks."""
from author_plan import *
import time,resource,os
from voxel_character.common import coordinate_planes,render_data,core

def projected(q,pose,yaw):return[world([v[0],v[2]],[pose[0],pose[2]],yaw)for v in q]
def face_y_normal(q):
 u=[q[1][j]-q[0][j]for j in range(3)];v=[q[2][j]-q[0][j]for j in range(3)];return u[2]*v[0]-u[0]*v[2]
def main():
 start=time.monotonic();plan=load(HERE/'design_plan.json');scene=f.load_scene();windows=[box([p for q in h['polygon_parts_xz_m']for p in q])for h in plan['holdings']];idx=f.SurfaceIndex(scene,windows,margin=5);ni=geo._SpatialIndex(8)
 for i,r in enumerate(plan['native_reservations']):ni.add(i,r['polygon_xz_m'])
 assets=[];placements=[];bearings=[];tops=[];tests=[];only=os.getenv('COMPILE_ONLY');prior=load(HERE/'native_geometry.json')if only else None;prior_tests=load(HERE/'native_tests.json')if only else None;compiler_runs=0
 for spec in plan['sources']:
  if only and spec['id']!=only:
   aa=next(a for a in prior['assets']if a['id']==spec['id']);assert aa['source']==spec['source'];assert ref(ROOT/aa['cache']['path'])==aa['cache'];pp=next(p for p in prior['placements']if p['asset_key']==aa['id']);assets.append(aa);placements.append(pp);bearings.extend(r for r in prior['actual_bearing_footprints']if r['placement_id']==pp['id']);tops.extend(r for r in prior['native_upward_faces']if r['placement_id']==pp['id']);tests.append(next(r for r in prior_tests['rows']if r['asset_id']==aa['id']));continue
  compiler_runs+=1
  t=time.monotonic();source=load(ROOT/spec['source']['path']);pitch=spec['pitch_m'];compiled=coordinate_planes.compile_master(source,{'pitch':pitch},max_candidate_cells=600000,max_output_cells=200000);assert compiled['valid'],compiled.get('constraints');assert compiled['candidate_cells']<=spec['estimate']['candidate_cells_exact_aabb_visits']*1.05;mesh=render_data.make_render_data(compiled);cp=HERE/'cache'/f"{source['id']}.pitch_{pitch}.render.json";write(cp,mesh);asset={'id':source['id'],'source':spec['source'],'cache':ref(cp),'pitch_m':pitch,'master_hash':core.digest(source),'candidate_cells':compiled['candidate_cells'],'output_cells':len(compiled['cells']),'quad_count':mesh['quad_count'],'bounds':mesh['bounds'],'seconds':time.monotonic()-t};assets.append(asset);pose=spec['position_m'];yaw=spec['yaw_rad'];pid='PHASE02:'+spec['role']+':'+str(len(placements));placements.append({'id':pid,'asset_key':asset['id'],'source':asset['source'],'cache':asset['cache'],'position_m':pose,'yaw_rad':yaw,'scale':[1,1,1],'role':spec['role']});support=[];contact=[];cellset={tuple(c[:3])for c in compiled['cells']}
  for group in mesh['groups']:
   for qi,q in enumerate(group['quads']):
    if not all(abs(v[1]-q[0][1])<1e-8 for v in q):continue
    normal=face_y_normal(q);p=projected(q,pose,yaw);y=pose[1]+q[0][1]
    if normal>0:tops.append({'placement_id':pid,'polygon_xz_m':p,'top_y_m':y,'material':group['material']});continue
    if normal>=0 or (group['material'].startswith('timber') and q[0][1]>.001):continue # Gate leaves are hinge supported; stone supports retain every elevation.
    coverage=idx.cover(p);area=sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in coverage);ys=[idx.height(r,*v)for r in coverage for v in r['intersection_polygon_xz_m']];row={'id':pid+':bearing:'+str(len(bearings)),'placement_id':pid,'polygon_xz_m':p,'bottom_y_m':y,'source_ground_min_m':min(ys)if ys else None,'source_ground_max_m':max(ys)if ys else None,'native_area_m2':geo.polygon_area(p),'source_support_covered_area_m2':area,'minimum_embed_m':min(ys)-y if ys else None};bearings.append(row);support.append(row)
    for i in ni.candidates(p):
     ar=geo.intersection_area(p,plan['native_reservations'][i]['polygon_xz_m'])
     if ar>1e-7:contact.append({'bearing_id':row['id'],'existing_native_id':plan['native_reservations'][i]['id'],'area_m2':ar})
  unsupported=[r for r in support if r['minimum_embed_m']is None or r['minimum_embed_m']<-.001 or abs(r['native_area_m2']-r['source_support_covered_area_m2'])>1e-6];checks={'asset_id':asset['id'],'common_constraints_pass':compiled['valid'],'candidate_cells':compiled['candidate_cells'],'unsupported_bearings':unsupported,'existing_native_contacts':contact,'native_support_area_m2':sum(r['native_area_m2']for r in support),'minimum_embed_m':min([r['minimum_embed_m']for r in support if r['minimum_embed_m']is not None],default=None)}
  if spec['role']=='real_neighborhood_stair':
   expected=[(r['z_interval_m'][0],r['z_interval_m'][1],r['top_local_y_m'])for r in source['extensions']['sections']];profile=[]
   for lo,hi,Y in expected:
    z=(lo+hi)/2;j=math.floor(z/pitch);heights=[]
    for x in np.arange(-1.125,1.2,pitch):
     i=math.floor(x/pitch);ys=[c[1]for c in cellset if c[0]==i and c[2]==j];heights.append((max(ys)+1)*pitch)
    profile.append({'z_interval_m':[lo,hi],'expected_local_top_m':Y,'sampled_native_top_range_m':[min(heights),max(heights)]})
   checks['stair_profile']=profile;checks['all_treads_exact']=all(abs(r['sampled_native_top_range_m'][0]-r['expected_local_top_m'])<1e-8 and abs(r['sampled_native_top_range_m'][1]-r['expected_local_top_m'])<1e-8 for r in profile);assert checks['all_treads_exact'];checks['separate_controller_required']=True
  else:
   slice_cells={(c[0],c[2])for c in cellset if c[1]==1};xs=[x for x,z in slice_cells];zs=[z for x,z in slice_cells];im=np.zeros((max(zs)-min(zs)+1,max(xs)-min(xs)+1),bool)
   for x,z in slice_cells:im[z-min(zs),x-min(xs)]=True
   n4=ndimage.label(im)[1];n8=ndimage.label(im,np.ones((3,3)))[1];checks.update(face_connected_slice_components=n4,edge_connected_slice_components=n8,edge_only_fragments=n4!=n8)
  tests.append(checks);write(HERE/'native_tests.json',{'rows':tests,'status':'running bounded checks','total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss});print(asset['id'],compiled['candidate_cells'],'support errors',len(unsupported),'contacts',len(contact),checks.get('face_connected_slice_components'),checks.get('edge_connected_slice_components'),flush=True);assert not unsupported,unsupported[:3];assert not contact,contact[:3];assert not checks.get('edge_only_fragments')
 write(HERE/'native_geometry.json',{'assets':assets,'placements':placements,'actual_bearing_footprints':bearings,'native_upward_faces':tops,'sources':plan['sources'],'base_scene':plan['base_scene']});write(HERE/'native_tests.json',{'rows':tests,'status':'bounded native source/support checks pass; routes, patch and actual view pending','all_pass':True,'compiler_runs_this_pass':compiler_runs,'total_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss});print(ref(HERE/'native_geometry.json'))
if __name__=='__main__':main()
