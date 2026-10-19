"""Coordinate-specific before/r01/r02 diagnosis of the failed eye-view side incisions."""
from build_repair import *
def merged(patch):
 rows=source_rows();ed={(e['material'],e['triangle_index']):e for e in patch['surface_edits']};result=[]
 for r in rows:
  e=ed.get((r['material'],r['triangle_index']));result.extend([dict(r,triangle=t)for t in e['replacement_triangles_xyz_m']]if e else[r])
 for m,vs in patch['appended_surfaces'].items():
  result.extend(dict(material=m,triangle_index=k//3,triangle=vs[k:k+3])for k in range(0,len(vs),3))
 return Ground(result)
def main():
 old=Ground(source_rows());one=merged(read(H.parent/'candidate_r01/surface_patch.json'));two=merged(read(H/'candidate_r02/surface_patch.json'));profiles=[]
 for z in [-9.7,-9.4,-9,-6,-5.5,-5.2]:
  pts=[[x/100,z]for x in range(-25800,-24700)];rows=[];jumps=[]
  for p in pts:
   try:rows.append(dict(xz_m=p,base_y_m=old.at(p),r01_y_m=one.at(p),r02_y_m=two.at(p)))
   except ValueError:continue
  for a,b in zip(rows,rows[1:]):
   if abs(a['r01_y_m']-b['r01_y_m'])>.05:jumps.append(dict(from_xz_m=a['xz_m'],to_xz_m=b['xz_m'],base_step_m=b['base_y_m']-a['base_y_m'],r01_step_m=b['r01_y_m']-a['r01_y_m'],r02_step_m=b['r02_y_m']-a['r02_y_m']))
  profiles.append(dict(z_m=z,r01_internal_discontinuities=jumps,max_r01_step_at_001m_m=max(abs(a['r01_y_m']-b['r01_y_m'])for a,b in zip(rows,rows[1:])),max_r02_step_at_001m_m=max(abs(a['r02_y_m']-b['r02_y_m'])for a,b in zip(rows,rows[1:]))))
 write('failed_view_coordinate_diagnosis.json',dict(failed_view=ref(C/'evidence/r10_functional_r01/R10_ABBEY_PUBLIC_GATE_EYE.png'),r01_patch=ref(H.parent/'candidate_r01/surface_patch.json'),r02_patch=ref(H/'candidate_r02/surface_patch.json'),profiles=profiles,diagnosis='R01 removed finite bank faces while inherited source-face shoulder heights stayed discontinuous. These coordinates diagnose actual internal top jumps, not only missing numeric microtriangles. R02 canonical top is continuous; exposed outer steps are closed by oriented physical sides.'))
 print(json.dumps(profiles,indent=2))
if __name__=='__main__':main()
