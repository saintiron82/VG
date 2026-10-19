"""Compose direct finite public owners using bounded common geometry helpers.

Compact traffic-minus-native masks cut old tops. The already audited owners
provide new triangles verbatim. Failures are retained as a batch report.
"""
import collections,json,math,sys,time
from .height_field import HERE
from . import public_domain as d,finite_geometry_r03 as g
from ..r17_district_batches import author as a

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def index(polys):
 out=a.geo._SpatialIndex(8)
 for i,p in enumerate(polys):out.add(i,p)
 return out
def fan(poly,plane):
 vs=[[v[0],a.common.height(plane,v),v[1]]for v in poly];out=[]
 for i in range(1,len(vs)-1):
  t=[vs[0],vs[i],vs[i+1]];ny=a.normal_y(t)
  if ny:out.append(t if ny>0 else[t[0],t[2],t[1]])
 return out
def main():
 start=time.monotonic();src=HERE/sys.argv[1];dest=HERE/sys.argv[2];dest.mkdir(exist_ok=True);assert not(dest/'surface_patch.json').exists()
 data=json.loads(src.read_bytes());report=data['report'];scene=a.load_scene();mp=a.ROOT/report['ownership_inputs']['path'];assert a.sha(mp)==report['ownership_inputs']['sha256'];cache=json.loads(mp.read_bytes())
 for r in report['source_refs']:
  if a.sha(a.ROOT/r['path'])!=r['sha256']:raise ValueError('Changed public source dependency')
 masks=[r['polygon_xz_m']for r in cache['masks']]+[r['polygon_xz_m']for r in report.get('common_cap_transition',{}).get('supplemental_native_exclusions',[])]
 traffic=d.polygons();ti=index(traffic);mi=index(masks);old=a.TriangleIndex(scene,traffic);edits=[];partitions=[];fail=[];maxerr=0.
 print('Source tops',len(old.rows),'owner records',len(data['records']),flush=True)
 for n,r in enumerate(old.rows):
  p=r['polygon_xz_m'];cuts=g.union([q for j in sorted(ti.candidates(p))if(q:=g.clip(p,traffic[j]))]);cuts=g.subtract(cuts,[masks[j]for j in sorted(mi.candidates(p))])
  if not cuts:continue
  rest=g.subtract([p],cuts);before=g.area(p);after=math.fsum(g.area(q)for q in rest);removed=math.fsum(g.area(q)for q in cuts);err=abs(before-after-removed);maxerr=max(maxerr,err)
  if err>1e-7:fail.append(dict(kind='source_partition',material=r['material'],triangle_index=r['triangle_index'],area_error_m2=err))
  edits.append(dict(material=r['material'],triangle_index=r['triangle_index'],source_triangle_sha256=r['source_triangle_sha256'],replacement_triangles_xyz_m=[t for q in rest for t in fan(q,r['plane_y_xz_m'])]));partitions.append(dict(material=r['material'],triangle_index=r['triangle_index'],removed_area_m2=removed,partition_error_m2=err))
  if n and n%5000==0:print('Cut source',n,'failures',len(fail),'seconds',time.monotonic()-start,flush=True)
 caps_path=a.CITY/'assemblies/property/registered/public_lane_repairs_r01/baseline/cap_columns.json';caps=json.loads(caps_path.read_bytes());holes=[c['polygon_xz_m']for r in caps['records']for c in r['candidate_columns']];hi=index(holes);private=[]
 for r in caps['records']:
  for j,c in enumerate(r['candidate_columns']):
   y=max(x['world_y_interval_m'][1]for x in c['cells'])
   for k,p in enumerate(g.subtract([c['polygon_xz_m']],c['traffic_clip_polygons_xz_m'])):private.append(dict(id=f"{r['property_id']}:PRIVATE_CAP_REMAINDER:{j}:{k}",polygon_xz_m=p,plane_y_xz_m=[0,0,y],triangles_xyz_m=fan(p,[0,0,y]),kind='nonwalking_private_cap_remainder',material='ground_stone'))
 owners=[dict(r,kind='canonical_public_surface',material='road')for r in data['records']]+private;coverage=[];append=collections.defaultdict(list)
 for n,r in enumerate(owners):
  p=r['polygon_xz_m'];covers=[old.rows[j]['polygon_xz_m']for j in old.index.candidates(p)]+[holes[j]for j in hi.candidates(p)];missing=g.subtract([p],covers);gap=math.fsum(g.area(q)for q in missing)
  if gap>1e-7:fail.append(dict(kind='source_hole',owner_id=r['id'],area_m2=gap,polygons_xz_m=missing))
  coverage.append(dict(id=r['id'],area_m2=g.area(p),source_hole_area_m2=gap));append[r['material']].extend(v for t in r['triangles_xyz_m']for v in t)
  if n and n%8000==0:print('Owner support',n,'failures',len(fail),'seconds',time.monotonic()-start,flush=True)
 down=[(m,k//3)for m,vs in append.items()for k in range(0,len(vs),3)if a.normal_y(vs[k:k+3])<=0]
 refs=[ref(src),ref(mp),ref(caps_path),ref(HERE/'finite_geometry_r03.py')]
 patch=dict(schema='riverstone.frozen_scene_patch.v1',id='R18_DIRECT_CANONICAL_PUBLIC_TOPS',status='TOP_CANDIDATE_PENDING_JOINT_SIDE_AND_RUNTIME',base_scene_sha256=a.SCENE_SHA256,source_surface_hashes={m:a.canonical_sha(scene['surfaces'][m])for m in sorted({r['material']for r in edits})},surface_edits=edits,appended_surfaces=dict(append),removed_foundation_proxy_ids=[],source_references=refs,design_grade_exceptions=dict(source=ref(src),finite_area_m2=report['exception_area_m2'],source_triangle_count=report['exception_source_triangles']))
 result=dict(status='PASS_TOP_SOURCE_PARTITION'if not fail and not down else'HELD_TOP_SOURCE_PARTITION',source_refs=refs,source_top_edits=len(edits),owner_records=len(owners),max_partition_error_m2=maxerr,failures=fail,downward=down,coverage=coverage,partitions=partitions,elapsed_s=time.monotonic()-start,activation=False)
 for name,value in [('surface_patch.json',patch),('top_review.json',result),('physical_owners.json',dict(source_refs=refs,owners=owners))]:(dest/name).write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n')
 print({k:v for k,v in result.items()if k not in('coverage','partitions','failures','downward','source_refs')},'failures',len(fail),flush=True)
if __name__=='__main__':main()
