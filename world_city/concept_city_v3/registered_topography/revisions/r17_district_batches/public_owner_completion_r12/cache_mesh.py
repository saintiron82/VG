import json,collections,time
from pathlib import Path
from .. import author as a
from ..public_owner_completion_r05.solve import proxy as mesh
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
SOURCE=a.HERE/'public_owner_completion_r06/BLOCK_008_R8_C003_profile.json'
d=json.loads(SOURCE.read_bytes());fixed=d['court_fixed_regions']+d['incident_public_fixed_regions'];start=time.monotonic();parts,cells=mesh.grid_parts(d['private_domain_polygons_xz_m'],fixed,1.);points,tris,proof=mesh.topology(parts,[p for r in d['incident_public_fixed_regions']for p in r['polygon_xz_m']]);edges=collections.Counter(tuple(sorted((u,v)))for t in tris for u,v in zip(t,t[1:]+t[:1]));corners=[i for i,t in enumerate(tris)if sum(edges[tuple(sorted((u,v)))]==1 for u,v in zip(t,t[1:]+t[:1]))>=2];write(HERE/'source_topology.json',dict(vertices_xz_m=points,triangles=tris,topology_proof=proof,cell_partition_checks=cells,two_boundary_edge_triangles=corners,source=dict(path=str(SOURCE.relative_to(a.ROOT)),sha256=a.sha(SOURCE)),seconds=time.monotonic()-start));print('points',len(points),'triangles',len(tris),'corners',len(corners),'seconds',time.monotonic()-start,flush=True)
