"""Small default-conform8m regression at the repaired material boundary."""
from pathlib import Path
exec((Path(__file__).parent/'check_material_r13.py').read_text().split('inputs={};seals=[]')[0])
rows=[];issues=[]
for x in range(312,344,8):
 for z in range(296,328,8):
  bounds=[x,z,x+8,z+8];a=prior.surface_domains(bounds);b=m.surface_domains(bounds);old=partition(a);new=partition(b)
  before=collections.defaultdict(list);after=collections.defaultdict(list)
  for r in a:before[identity(r)].append(r['polygon_xz_m'])
  for r in b:after[identity(r)].append(r['polygon_xz_m'])
  assert before.keys()==after.keys()
  diff=sum(uncovered(before[k],after[k])+uncovered(after[k],before[k]) for k in before)
  row=dict(bounds=bounds,before=old,after=new,owner_symmetric_difference_m2=diff);rows.append(row)
  if abs(new['area_m2']-64)>1e-6 or new['overlap_m2']>1e-6 or diff>1e-7:issues.append(row)
report=dict(schema='riverstone.material_export_grid_regression.v1',status='pass_conformed_finite_owner_grid' if not issues else 'failed',r13_source_sha256=sha(m.__file__),r13_contract_sha256=sha(m.HERE/'material_contract.json'),checker_sha256=sha(__file__),tile_pitch_m=8,conform=True,tiles=rows,issues=issues,limits=['Finite consumer records only; final renderer floor clipping and triangle material output are not inspected here.'])
(H/'r13_export_grid_regression.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(rows),'tiles',len(issues),'issues')
