"""Compare exact local top values between the R7 palette base and tested R8."""
import json
from . import author as a

def run():
 folder=a.HERE/'estate_public_caps_r01';source=folder/'actual_public_profiles.json';d=json.loads(source.read_bytes());out=folder/'tested_scene_parity.json'
 if out.exists():raise SystemExit('Preserve parity')
 ledger=a.CITY/'traversal_r5/revisions/r06_r8_precinct/network_contact_stations_r01/failure_stations_faces.json';l=json.loads(ledger.read_bytes());tested=a.ROOT/l['scene']['path'] if not l['scene']['path'].startswith('/')else __import__('pathlib').Path(l['scene']['path'])
 if a.sha(tested)!=l['scene']['sha256']:raise ValueError('Changed actual tested scene')
 windows=[r['polygon_xz_m']for r in d['records']];baseline=a.TriangleIndex(a.load_scene(),windows);actual=a.TriangleIndex(json.loads(tested.read_bytes()),windows);b={a.canonical_sha(r['vertices_xyz_m']):r for r in baseline.rows};q={a.canonical_sha(r['vertices_xyz_m']):r for r in actual.rows};relevant=set()
 for p in windows:relevant.update(a.canonical_sha(r['vertices_xyz_m'])for r in baseline.covering(p));relevant.update(a.canonical_sha(r['vertices_xyz_m'])for r in actual.covering(p))
 mismatches=[h for h in relevant if h not in b or h not in q];matches=[dict(vertices_xyz_m=b[h]['vertices_xyz_m'],base_material=b[h]['material'],base_triangle_index=b[h]['triangle_index'],tested_material=q[h]['material'],tested_triangle_index=q[h]['triangle_index'],triangle_sha256=h)for h in sorted(relevant)if h in b and h in q];result=dict(schema='riverstone.r17.local_actual_scene_top_parity.v1',base_scene=dict(path=str(a.SCENE_PATH.relative_to(a.ROOT)),sha256=a.SCENE_SHA256),tested_scene=dict(path=str(tested.relative_to(a.ROOT)),sha256=a.sha(tested)),contact_profiles_sha256=a.sha(source),exact_matching_source_triangles=matches,unmatched_triangle_hashes=mismatches,status='PASS'if not mismatches else'FAILED',scope='Every positive-area actual top triangle covering the finite cap/traffic clips. Native placements and unrelated surfaces are outside this parity claim.',activation=False);out.write_text(json.dumps(result,separators=(',',':'))+'\n');print(result['status'],len(matches),len(mismatches),a.sha(out))
if __name__=='__main__':run()
