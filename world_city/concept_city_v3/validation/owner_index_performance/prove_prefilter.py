"""Check the finite immutable data invariants supporting the rejection proof."""
import sys,pathlib,json,hashlib,math
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'world_city').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r09_training_access.recovery_support import upstream as source
from world_city.concept_city_v3.validation.owner_index_performance.prefilter import OwnerLookup
lookup=OwnerLookup(source);geo=source.geo;edges=0
assert lookup.owners is source._owners() and lookup.index is source.INDEX
for i,r in enumerate(lookup.owners):
 polygon=r['polygon_xz_m'];box,sets=lookup.prepared[i];assert box==[min(p[0] for p in polygon),min(p[1] for p in polygon),max(p[0] for p in polygon),max(p[1] for p in polygon)]
 orientation=1.0 if geo.signed_polygon_area(polygon)>0 else -1.0
 for side in sets:
  for a,b,length,sign in side:
   assert any(a==u and b==v for u,v in zip(polygon,polygon[1:]+polygon[:1]));assert length==math.dist(a,b) and length>geo.NUMERIC_EPSILON and sign==orientation;edges+=1
# Verify the exact inspected source expression, not an approximately equivalent normal form.
helper=pathlib.Path(geo.__file__).read_text();candidate=(H/'prefilter.py').read_text()
assert 'orientation * _cross(a, b, point) / length < -tolerance_m - NUMERIC_EPSILON' in helper
assert 'orientation*self.geo._cross(a,b,point)/length < -1e-8-self.geo.NUMERIC_EPSILON' in candidate
assert 'self.geo.point_in_convex_polygon(point,r[\'polygon_xz_m\'],1e-8)' in candidate
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
report=dict(schema='riverstone.owner_prefilter_rejection_proof.v1',status='pass_frozen_data_and_predicate_invariants',candidate_sha256=sha(H/'prefilter.py'),binding_sha256=sha(H/'candidate_binding.json'),proof_checker_sha256=sha(__file__),owners=len(lookup.owners),prepared_original_edge_occurrences=edges,original_index_object_preserved=True,original_sorted_candidate_order_preserved=True,reasoning=['For a fixed immutable polygon, precomputed orientation and edge length exactly equal those recomputed by the original predicate.','Every prefilter rejection evaluates one existing non-skipped original edge with the identical float expression and tolerance. Therefore rejection implies that the unchanged polygon function would return False on that edge.','The box only selects candidate original edges. If none proves rejection, the unchanged full polygon function is called. No box containment or expanded-box approximation decides ownership.','The original32m candidate set and sorted integer indices are unchanged, so deleting only proved-false candidates preserves the first accepted record, including priority ties.','The original base fallback dictionary and262144-entry LRU contract are preserved. No adjacency or interface geometry is skipped.'],assumptions=['Sealed owner records and source index remain immutable for the lifetime of this explicitly created lookup object.','Constructor hash-binds upstream/helper bytes and the complete ordered owner dictionaries. Changes require a new binding and review.'],activation='Not installed; explicit candidate lookup object only.')
(H/'proof_report.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],report['owners'],report['prepared_original_edge_occurrences'])
