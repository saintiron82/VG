"""Canonicalize only one-ULP conflicts in coincident float32 public-road vertices.
Native bridge decks and retained under-deck banks are outside this single-top
road domain. Never weld a substantive height discontinuity or add overlapping faces.
"""
import json,collections,numpy as np
from .build_corridors import H,ref
p=H/'surface_patch.json';patch=json.load(open(p));before=ref(p);vertices=patch['appended_surfaces']['road'];groups=collections.defaultdict(list)
for i,v in enumerate(vertices):
 q=np.asarray(v,dtype=np.float32);groups[(float(q[0]),float(q[2]))].append(i)
records=[]
for q,indices in groups.items():
 heights=[np.float32(vertices[i][1])for i in indices];unique=set(map(float,heights))
 if len(unique)<2:continue
 low=min(unique);high=max(unique);ulp=max(abs(float(np.spacing(np.float32(y))))for y in unique)
 assert high-low<=ulp*1.00001,('Real road height split cannot be welded',q,unique,ulp)
 selected=float(heights[0]);record=dict(float32_xz_m=list(q),original_vertices=[dict(vertex_index=i,xyz_m=vertices[i][:])for i in indices],original_float32_y_values=sorted(unique),canonical_y_m=selected,maximum_float32_change_m=high-low,local_float32_y_ulp_m=ulp)
 for i in indices:vertices[i][1]=selected
 records.append(record)
p.write_text(json.dumps(patch,separators=(',',':'))+'\n');(H/'road_vertex_canonicalization.json').write_text(json.dumps(dict(schema='riverstone.public_road.shared_float32_vertices.v1',scope='Only the single-height appended road top. Native bridge/deck and lower bank domains are excluded. Exact XZ unchanged; only existing one-ULP Y differences canonicalized, no faces added or retired.',source_before=before,source_after=ref(p),records=records),separators=(',',':'))+'\n');print('One-ULP shared road vertices canonicalized:',len(records))
