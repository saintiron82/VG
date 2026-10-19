"""Exact local coordinates for existing actual-scene triangle colliders.

Uses the common loader's existing placement translation. No triangles, winding,
controller settings, source geometry or acceptance thresholds are changed.
"""
import math
import numpy as np
from .runtime_precision import canonical

def zero_count(triangles):
 q=np.asarray(triangles,dtype=np.float64).reshape(-1,3,3).astype(np.float32)
 if not np.all(np.isfinite(q)):raise ValueError('Nonfinite collision vertices')
 cross=np.cross(q[:,1]-q[:,0],q[:,2]-q[:,0])
 if not np.all(np.isfinite(cross)):raise ValueError('Nonfinite collision normal')
 return int(np.all(cross==0,axis=1).sum())

def rebase(triangles,route_points,grid_m=16.):
 if not triangles or not route_points:raise ValueError('Actual triangles and route bounds are required')
 if not math.isfinite(grid_m)or grid_m<=0:raise ValueError('Invalid origin grid')
 if any(not math.isfinite(v)for p in route_points for v in p):raise ValueError('Nonfinite route point')
 origin=[float(round((min(p[i]for p in route_points)+max(p[i]for p in route_points))/(2*grid_m))*grid_m)for i in range(3)]
 local=[[[v[i]-origin[i]for i in range(3)]for v in t]for t in triangles]
 error=max(abs(v[i]-(w[i]+origin[i]))for t,u in zip(triangles,local)for v,w in zip(t,u)for i in range(3))
 original_zero=zero_count(triangles);local_zero=zero_count(local);reason=None
 if error!=0:reason='Integer local translation did not reconstruct all source doubles exactly'
 if local_zero>original_zero:reason='Local translation introduced an exact float32 degenerate face'
 proposed=origin[:]
 if reason:origin=[0.,0.,0.];local=[[v[:]for v in t]for t in triangles]
 proof=dict(schema='riverstone.actual_scene_local_origin.v1',origin_grid_m=grid_m,proposed_origin_xyz_m=proposed,applied_origin_xyz_m=origin,source_triangles_sha256=canonical(triangles),local_triangles_sha256=canonical(local),triangles=len(triangles),source_float32_zero_faces=original_zero,proposed_local_float32_zero_faces=local_zero,proposed_world_roundtrip_error_m=error,applied_world_roundtrip_error_m=0.,source_faces_order_and_winding_preserved=True,source_world_vertices_exact=True,removed_faces=0,added_faces=0,fallback_reason=reason,policy='Nearest 16 m route-bounds midpoint; existing rigid translation only. Fall back unchanged if double roundtrip is nonexact or new float32 zero faces appear. Actual replay remains required.')
 return local,origin,proof
