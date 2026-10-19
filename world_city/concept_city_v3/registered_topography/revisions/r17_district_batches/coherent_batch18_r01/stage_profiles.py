"""Stage exact solved private fields for one atomic eighteen-holding batch."""
import json
from .screen import HERE,write
from .. import author as a
SOURCE=HERE.parent/'contour_bulk_r01';CONT=HERE.parent/'entry_continuation_r01'
def run():
 request=json.loads((CONT/'coherent_datum_rebind_request_r02.json').read_bytes());selected=set(request['matched_next_batch_holding_ids']);original=json.loads((SOURCE/'private_profiles_summary_r02.json').read_bytes());changed={r['id']:r for r in json.loads((CONT/'coherent_datum_summary_r01.json').read_bytes())['rows']if r['datum_changes']};changed['PRIVATE_GROUP:BLOCK_010:R8_C006']={'path':str((CONT/'local_grade_options/PRIVATE_GROUP_BLOCK_010_R8_C006_15.json').relative_to(a.ROOT))};out=HERE/'profiles';out.mkdir(exist_ok=True);rows=[]
 for row in original['groups']:
  if not set(row['holding_ids'])<=selected:continue
  source=a.ROOT/row['path'];base=json.loads(source.read_bytes());new=dict(base);refs=[dict(path=str(source.relative_to(a.ROOT)),sha256=a.sha(source))]
  if row['id']in changed:
   cp=a.ROOT/changed[row['id']]['path'];candidate=json.loads(cp.read_bytes());result=dict(candidate['result']);assert result['status']=='FINITE_PROFILE_WITH_COHERENT_DATUM_CANDIDATE';result['source_candidate_status']=result['status'];result['status']='PASSED_FINITE_TRIANGLE_GRADE';result['grade_limit']=.15 if row['id']=='PRIVATE_GROUP:BLOCK_010:R8_C006'else .12;new['result']=result;refs.append(dict(path=str(cp.relative_to(a.ROOT)),sha256=a.sha(cp)));new['native_datum_rebind_pending']=True
  else:assert new['result']['status']=='PASSED_FINITE_TRIANGLE_GRADE'
  new['status']='PASSED_FINITE_TRIANGLE_GRADE';new['source_references']=refs;new['activation']=False;path=out/(row['id'].replace(':','_')+'.json');assert not path.exists();path.write_text(json.dumps(new,separators=(',',':'))+'\n');rows.append(dict(id=row['id'],holding_ids=row['holding_ids'],status=new['status'],path=str(path.relative_to(a.ROOT)),sha256=a.sha(path)))
 assert {h for r in rows for h in r['holding_ids']}==selected
 write('private_profiles_summary_r02.json',dict(groups=rows,accepted_candidate_holding_ids=sorted(selected),source_request=dict(path=str((CONT/'coherent_datum_rebind_request_r02.json').relative_to(a.ROOT)),sha256=a.sha(CONT/'coherent_datum_rebind_request_r02.json')),activation=False))
 write('resolved_public_inputs_r01.json',json.loads((SOURCE/'resolved_public_inputs_r01.json').read_bytes()));print('groups',len(rows),'holdings',len(selected))
if __name__=='__main__':run()
