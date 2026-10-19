import copy,json,gzip
from pathlib import Path
from window_revision_contract import validate
H=Path(__file__).resolve().parent;R=H.parents[3]
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
side=load(H/'facility_openings/batch_r01/cathedral_layout_b2/source_revision.json');rev=side['source_revision']
original=load(R/rev['original_master_path']);revised=load(R/rev['revised_master_path'])
base={'name':'exact_B2_positive','revision':rev,'original':original,'revised':revised,'expected':True};fixtures=[base]
def first(r):return next(op for c in r['revised']['components']for op in c['operations']if op['id']==rev['allowed_operation_ids'][0])
def bad(name,fn):
 r=copy.deepcopy(base);r.update(name=name,expected=False);fn(r);fixtures.append(r)
bad('unapproved_kind',lambda r:r['revision'].__setitem__('change_kind','arbitrary'))
bad('unlisted_window',lambda r:r['revision']['allowed_operation_ids'].pop())
bad('duplicate_allowed',lambda r:r['revision']['allowed_operation_ids'].append(rev['allowed_operation_ids'][0]))
bad('changed_x',lambda r:first(r)['transform']['translation'].__setitem__(0,20))
bad('changed_y',lambda r:first(r)['transform']['translation'].__setitem__(1,1))
bad('changed_basis',lambda r:first(r)['transform']['basis'][0].__setitem__(0,2))
bad('changed_material',lambda r:first(r).__setitem__('material','slate'))
bad('new_fill_cut',lambda r:r['revised'].setdefault('assembly_cuts',[]).append({'id':'unauthorized'}))
bad('no_actual_move',lambda r:r.__setitem__('revised',copy.deepcopy(original)))
bad('missing_no_fill_proof',lambda r:r['revision']['unchanged_structure_proof'].__setitem__('no_fill_operations_added',False))
rows=[]
for r in fixtures:
 try:validate(r['revision'],r['original'],r['revised']);accepted=True
 except (AssertionError,KeyError,TypeError):accepted=False
 rows.append({'name':r['name'],'accepted':accepted,'expected':r['expected'],'pass':accepted==r['expected']})
out=H/'evidence';(out/'window_revision_fixtures_r01.json').write_text(json.dumps(fixtures,separators=(',',':'))+'\n')
report={'all_pass':all(r['pass']for r in rows),'tests':rows};(out/'window_revision_python_r01.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert report['all_pass']
