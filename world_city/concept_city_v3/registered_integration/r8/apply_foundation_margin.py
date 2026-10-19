"""Bind one measured E4 foundation wedge without changing its public court."""
import copy,json,sys
from pathlib import Path
from .build_scene import a,verify
from ...registered_topography.revisions.r17_district_batches import author as g
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def main(binding_path,destination):
 out=Path(destination);out.mkdir(parents=True,exist_ok=True);b=a.load(binding_path)
 cp=a.CITY/'registered_topography/revisions/r17_district_batches/private41_margin_closure_r01/closure_contract.json';c=a.load(cp,'27acdb04d4c5febbd31371870a1c4880410a934cb29533636d4cbd0eb317161d')
 target=c['rendered_top_suppression']['polygon_xz_m'];height=c['support_owner']['lower_plane_y_xz_m'][2];cut=0.;ledger=[];index=None
 for i,r in enumerate(b['patches']):
  p=verify(r)
  if p['id']=='R17_READY_18_INCREMENTAL_TOPS':index=i;break
 if index is None:raise ValueError('Expected source-bound private18 producer')
 source=copy.deepcopy(p)
 for material,vs in p['appended_surfaces'].items():
  if material=='bank':continue
  kept=[]
  for j in range(0,len(vs),3):
   tri=vs[j:j+3];poly=[[v[0],v[2]]for v in tri]
   if max(abs(v[1]-height)for v in tri)>1e-8 or g.normal_y(tri)<=0:kept+=tri;continue
   overlap=g.clip(poly,target)
   area=g.geo.polygon_area(overlap)if overlap else 0.
   if area<=1e-12:kept+=tri;continue
   parts=g.common.subtract([poly],[target]);remaining=sum(g.geo.polygon_area(q)for q in parts)
   if abs(g.geo.polygon_area(poly)-remaining-area)>1e-7:raise ValueError('Foundation wedge partition mismatch')
   kept.extend(v for q in parts for t in g.fan_upward([[x[0],height,x[1]]for x in q])for v in t);cut+=area;ledger.append(dict(material=material,appended_triangle_index=j//3,source_triangle_sha256=g.canonical_sha(tri),removed_area_m2=area))
  p['appended_surfaces'][material]=kept
 if abs(cut-c['review']['footprint_area_m2'])>1e-7:raise ValueError('Foundation suppression does not cover exactly its source footprint')
 p['appended_surfaces'].setdefault('bank',[]).extend(v for t in c['boundary_connection']['triangles_xyz_m']for v in t)
 p['native_foundation_margin_contract']=ref(cp);p['source_references']=p.get('source_references',[])+[ref(cp),ref(Path(__file__))]
 assert p['surface_edits']==source['surface_edits']
 q=out/'private18_with_foundation_margin.json';assert not q.exists();q.write_text(json.dumps(p,separators=(',',':'))+'\n');old=b['patches'][index];b['patches'][index]=ref(q)
 review=dict(status='PASS_EXACT_NONWALKING_FOUNDATION_MARGIN',contract=ref(cp),source_patch=old,replacement_patch=ref(q),suppressed_lower_top_area_m2=cut,retaining_triangles=2,retaining_area_m2=c['boundary_connection']['area_m2'],source_rows=ledger,walking_geometry_changed=False,native_geometry_changed=False)
 q=out/'review.json';q.write_text(json.dumps(review,indent=2)+'\n');b['evidence'].append(ref(q));(out/'binding.json').write_text(json.dumps(b,indent=2)+'\n');print('PASS foundation margin',cut,'m2',flush=True)
if __name__=='__main__':main(*sys.argv[1:])
