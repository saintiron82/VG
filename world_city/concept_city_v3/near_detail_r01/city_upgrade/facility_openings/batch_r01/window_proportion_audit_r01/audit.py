"""Exact authored opening/frame proportions; no geometry changes or compilation.

Projected glass areas concern same-window features only. Whole-building
occlusion, source filled-surround films and viewport visibility stay separate.
"""
import collections,gzip,hashlib,itertools,json,math,resource,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent;ROOT=B.parents[5];U=B.parent.parent
sys.path[:0]=[str(B.parent),str(B/'sampler_v2'),str(U/'house_rules')]
import author as a
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook

def ref(path):return {'path':str(Path(path).resolve().relative_to(ROOT)),'sha256':a.sha(path)}
def area(poly):return abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>2 else 0.
def clip(poly,axis,bound,sign):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  ip=sign*(p[axis]-bound)>=-1e-12;iq=sign*(q[axis]-bound)>=-1e-12
  if ip:out.append(p)
  if ip!=iq:
   t=(bound-p[axis])/(q[axis]-p[axis]);out.append([p[j]+t*(q[j]-p[j]) for j in range(2)])
 return out

def intersection_area(poly,r):
 for axis,bound,sign in [(0,r[0],1),(1,r[1],1),(0,r[2],-1),(1,r[3],-1)]:
  poly=clip(poly,axis,bound,sign)
  if not poly:return 0.
 return area(poly)

def unoccluded(poly,rects):
 if not rects:return area(poly)
 lo=[min(p[j] for p in poly) for j in [0,1]];hi=[max(p[j] for p in poly) for j in [0,1]]
 xs=sorted({lo[0],hi[0]}|{min(hi[0],max(lo[0],r[j])) for r in rects for j in [0,2]});ys=sorted({lo[1],hi[1]}|{min(hi[1],max(lo[1],r[j])) for r in rects for j in [1,3]});total=0.
 for x0,x1 in zip(xs,xs[1:]):
  for y0,y1 in zip(ys,ys[1:]):
   x,y=(x0+x1)/2,(y0+y1)/2
   if not any(r[0]<x<r[2] and r[1]<y<r[3] for r in rects):total+=intersection_area(poly,[x0,y0,x1,y1])
 return total

def xy_polygon(shape):
 if shape['kind']=='box':lo,hi=shape['min'],shape['max'];return [[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]
 assert shape['kind']=='extrusion';return shape['polygon']
def bbox(poly):return [min(p[j] for p in poly) for j in [0,1]]+[max(p[j] for p in poly) for j in [0,1]]
def dims(b):return [b[2]-b[0],b[3]-b[1]]
def rnd(value):return round(value,8)

def measure(row,source,lookup):
 op,t,_=lookup[(row['component'],row['instance'],row['glass']['id'])];assert a.core.digest(op)==row['glass']['operation_sha256'];assert op['shape']['kind'] in ['box','extrusion'];poly=xy_polygon(op['shape']);gb=bbox(poly);W,H=dims(gb);raw=area(poly);feature=[];masks=collections.defaultdict(list);facewidth=[];outer=[]
 for f in row['associated_features']:
  fo,ft,_=lookup[(row['component'],row['instance'],f['id'])];assert a.core.digest(fo)==f['operation_sha256'];assert ft==t,'Feature needs independent local projection contract';fb=bbox(xy_polygon(fo['shape']));role=f['role'];rec={'id':fo['id'],'sha256':f['operation_sha256'],'role':role,'shape_kind':fo['shape']['kind'],'material':fo['material'],'xy_bounds_m':list(map(rnd,fb))}
  if role=='window_frame_sill':
   outer.append(fb)
   if not row['source_frame_is_filled_panel']:
    assert fo['shape']['kind']=='box';width=min(dims(fb));facewidth.append(width);rec['face_width_m']=rnd(width);masks['frame'].append(fb)
  elif role in ['mullion','shutter']:
   assert fo['shape']['kind']=='box';masks[role].append(fb);rec['face_width_m']=rnd(min(dims(fb)))
  feature.append(rec)
 envelope=[min(r[0] for r in outer),min(r[1] for r in outer),max(r[2] for r in outer),max(r[3] for r in outer)] if outer else gb
 frame_area=unoccluded(poly,masks['frame']);bar_area=unoccluded(poly,masks['frame']+masks['mullion']);visible=unoccluded(poly,masks['frame']+masks['mullion']+masks['shutter']);shutter_overlap=raw-unoccluded(poly,masks['shutter'])
 ap=row.get('associated_aperture');apdims=None
 if ap:
  apo,apt,_=lookup[(row['component'],row['instance'],ap['id'])];assert a.core.digest(apo)==ap['operation_sha256'] and apo['action']=='cut' and apt==t;apdims=dims(bbox(xy_polygon(apo['shape'])))
 bands=[gb[0]-envelope[0],gb[1]-envelope[1],envelope[2]-gb[2],envelope[3]-gb[3]]
 clear=None
 if masks['frame']:
  lx,ly,hx,hy=gb
  for r in masks['frame']:
   cx,cy=(r[0]+r[2])/2,(r[1]+r[3])/2
   if dims(r)[0]<dims(r)[1]:
    if cx<(gb[0]+gb[2])/2:lx=max(lx,r[2])
    else:hx=min(hx,r[0])
   else:
    if cy<(gb[1]+gb[3])/2:ly=max(ly,r[3])
    else:hy=min(hy,r[1])
  clear=[max(0,hx-lx),max(0,hy-ly)]
 flags=[]
 if facewidth and max(facewidth)/min(W,H)>=.25:flags.append('frame_face_at_least_quarter_of_short_opening')
 if frame_area/raw<.5-1e-9:flags.append('frame_alone_leaves_under_half_nominal_glass_area')
 if clear and min(clear)<.5-1e-9:flags.append('frame_inner_short_dimension_under_0_5m')
 return {'asset_key':row['asset_key'],'component':row['component'],'instance':row['instance'],'glass_operation':op['id'],'glass_operation_sha256':row['glass']['operation_sha256'],'source_profile':row['source_profile'],'city_placements':row['city_asset_placement_count'],'opening_kind':'actual_component_cut' if ap else 'painted_panel_without_source_aperture','aperture_width_height_m':list(map(rnd,apdims)) if apdims else None,'pane_width_height_m':[rnd(W),rnd(H)],'outer_surround_width_height_m':list(map(rnd,dims(envelope))),'surround_bbox_border_left_bottom_right_top_m':list(map(rnd,bands)),'frame_face_widths_m':list(map(rnd,facewidth)),'frame_inner_width_height_m':list(map(rnd,clear)) if clear else None,'pane_projected_area_m2':rnd(raw),'after_frame_projected_area_m2':rnd(frame_area),'after_frame_and_bars_area_m2':rnd(bar_area),'after_window_features_area_m2':rnd(visible),'frame_retained_area_fraction':rnd(frame_area/raw),'glass_area_fraction_of_surround_envelope':rnd(raw/(math.prod(dims(envelope)))),'window_feature_visible_area_fraction':rnd(visible/raw),'mullion_widths_m':[r['face_width_m'] for r in feature if r['role']=='mullion'],'shutter_projected_overlap_m2':rnd(shutter_overlap),'shutter_state_geometry':('absent' if not masks['shutter'] else 'outside_pane_open_position' if shutter_overlap<1e-9 else 'covers_almost_all_pane_closed_position' if shutter_overlap/raw>.95 else 'partially_covers_pane'),'source_glass_exists':True,'open_unfilled_window_claimed':False,'source_filled_surround_not_a_real_aperture':row['source_frame_is_filled_panel'],'review_flags':flags,'features':feature,'structural_operations_policy':'Only exact associated frame/bar/shutter operation IDs are measured; body beams/posts/buttresses and all source cuts are excluded from alteration. Projected areas do not certify whole-assembly visibility.'}

def main():
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));start=time.monotonic();audit=U/'house_extensions/facility_opening_audit/asset_audit.json';faces=audit.parent/'window_faces.jsonl.gz';assets=a.load(audit)['assets'];rows=collections.defaultdict(list)
 for line in gzip.open(faces,'rt'):r=json.loads(line);rows[r['asset_key']].append(r)
 cfg=a.load(U/'house_rules/shared_output_budget.v2.json');identity={'driver':ref(__file__),'source_asset_audit':ref(audit),'source_window_audit':ref(faces),'frozen_author':ref(a.__file__),'common_core':ref(a.core.__file__)};book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/p for p in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);key='facility_window_proportion_audit:r01';scopes=[{'directory':str(HERE.relative_to(ROOT)),'prefix':''}];book.reserve(key,scopes,2000000,identity);book.acquire_writer(key);w=rio.ReservedWriter(book,key,B,scopes,ROOT)
 try:
  measurements=[];reports=[]
  for asset in assets:
   path=ROOT/asset['source_master_path'];assert a.sha(path)==asset['source_sha256'];source=a.load(path);lookup={(c,i,o['id']):(o,t,bb) for c,i,o,t,bb in a.source_inventory(source)};out=[measure(row,source,lookup) for row in rows[asset['asset_key']]];measurements+=out
   group=collections.Counter((r['source_profile'],tuple(r['pane_width_height_m']),tuple(r['frame_face_widths_m']),tuple(r['frame_inner_width_height_m'] or []),tuple(r['mullion_widths_m']),r['window_feature_visible_area_fraction'],r['shutter_state_geometry']) for r in out);profiles=[{'profile':k[0],'pane_width_height_m':k[1],'frame_face_widths_m':k[2],'frame_inner_width_height_m':k[3] or None,'mullion_widths_m':k[4],'window_feature_visible_area_fraction':k[5],'shutter_state_geometry':k[6],'source_window_count':n} for k,n in group.items()]
   reports.append({'asset_key':asset['asset_key'],'source_master_path':asset['source_master_path'],'source_master_sha256':asset['source_sha256'],'city_placements':asset['city_placements'],'source_window_count':len(out),'review_window_count':sum(bool(r['review_flags']) for r in out),'frame_044_window_count':sum(any(abs(x-.44)<1e-7 for x in r['frame_face_widths_m']) for r in out),'review_flag_counts':dict(collections.Counter(f for r in out for f in r['review_flags'])),'source_profiles':dict(collections.Counter(r['source_profile'] for r in out)),'profiles':profiles})
  w.write(HERE/'window_measurements.json.gz',{'schema':'riverstone.facility.window_proportion_measurements.v1','scope':'Exact source operation local XY dimensions and same-window projected geometry only; neither cache sampling nor global visibility.','windows':measurements});summary={'schema':'riverstone.facility.window_proportion_audit.v1','identity':identity,'asset_count':len(assets),'assets_with_windows':sum(bool(r['source_window_count']) for r in reports),'source_window_count':len(measurements),'city_instanced_window_count':sum(r['city_placements'] for r in measurements),'profile_window_counts':dict(collections.Counter(r['source_profile'] for r in measurements)),'profile_asset_counts':{p:len({r['asset_key'] for r in measurements if r['source_profile']==p}) for p in sorted({r['source_profile'] for r in measurements})},'assets_with_044_frame':sum(r['frame_044_window_count']>0 for r in reports),'windows_with_044_frame':sum(r['frame_044_window_count'] for r in reports),'review_assets':sum(r['review_window_count']>0 for r in reports),'review_windows':sum(r['review_window_count'] for r in reports),'review_flag_counts':dict(collections.Counter(f for r in measurements for f in r['review_flags'])),'shutter_state_counts':dict(collections.Counter(r['shutter_state_geometry'] for r in measurements)),'review_thresholds_not_design_approval':{'frame_face_to_short_opening_at_least':.25,'frame_retained_projected_area_below':.5,'frame_inner_short_dimension_below_m':.5},'measurement_path':str((HERE/'window_measurements.json.gz').relative_to(ROOT)),'measurement_sha256':a.sha(HERE/'window_measurements.json.gz'),'assets':reports,'source_modified':False,'compile_calls':0,'new_candidate_activation':'Paused pending shared source-revision frame/opening/shutter rules; original and prior outputs retained.','elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};w.write(HERE/'audit.json',summary);book.release(key,identity,'72 original facility masters measured without source changes or sampling; new window candidates remain paused.');print(json.dumps({k:v for k,v in summary.items() if k not in ['identity','assets']}),flush=True)
 finally:w.close()
if __name__=='__main__':main()
