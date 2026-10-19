"""Exact old-to-new finite owner accounting; no geometric tolerance repair."""
import collections,hashlib,json
def canonical_sha(v):return hashlib.sha256(json.dumps(v,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def triangles(records):return collections.Counter(tuple(tuple(p)for p in t)for r in records for t in r['triangles_xyz_m'])
def validate(previous,current,review):
 old={r['id']:r for r in previous['records']};new={r['id']:r for r in current['records']};changes={r['previous_owner_id']:r for r in review['changed']}
 assert len(old)==len(previous['records'])and len(new)==len(current['records'])and len(changes)==len(review['changed'])
 assert set(changes)<=set(old)
 unchanged=[r for rid,r in old.items()if rid not in changes];claimed={r['id']for r in unchanged}
 for r in unchanged:assert new.get(r['id'])==r,'Unaffected finite owner changed: '+r['id']
 for rid,change in changes.items():
  before=old[rid];assert canonical_sha(before)==change['previous_owner_sha256'];assert before['plane_y_xz_m']==change['plane_y_xz_m'];assert before['polygon_xz_m']==change['previous_polygon_xz_m']
  for nid in change['retained_record_ids']:
   assert nid not in claimed;claimed.add(nid);after=new[nid];assert after.get('previous_owner_id')==rid;assert after['plane_y_xz_m']==before['plane_y_xz_m'];assert after['source_triangle_index']==before['source_triangle_index'];assert after['source_gradient']==before['source_gradient']
 assert claimed==set(new),'Unaccounted current finite owner'
 assert len(unchanged)==review['unchanged_records']and len(changes)==review['changed_previous_records']
 assert previous['report']['exceptions']==current['report']['exceptions']and review['previous_grade_exception_records_unchanged']
 assert review['all_removals_inside_original_source_holes']and not review['nonhole_removals']
 return dict(unchanged=unchanged,retired_triangles=triangles(previous['records'])-triangles(current['records']),summary=dict(unchanged_owner_records=len(unchanged),changed_previous_owner_records=len(changes),current_owner_records=len(new),unchanged_triangle_instances=sum(triangles(unchanged).values()),retired_triangle_instances=sum((triangles(previous['records'])-triangles(current['records'])).values()),unchanged_heights_and_grade_exceptions=True,all_removals_inside_declared_native_source_holes=True))
