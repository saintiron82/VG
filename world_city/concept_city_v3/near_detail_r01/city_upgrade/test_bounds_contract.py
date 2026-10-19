import copy, json
from pathlib import Path
from bounds_contract import validate
H=Path(__file__).resolve().parent;R=H.parents[3]
warehouse=H/'facility_openings/batch_r01/composed/working_r01_bank_loft_store/working_r01_bank_loft_store.manifest.json'
m=json.loads(warehouse.read_text());c=m['bounds_contract'];proof=json.loads((R/c['cell_envelope_proof_path']).read_text())
base={'name':'warehouse_positive','contract':c,'fine':c['composed_render_bounds'],'coarse':c['coarse_render_bounds'],'source_sha':m['source_master_sha256'],'proof':proof,'expected':True}
fixtures=[base]
def bad(name, mutate):
    row=copy.deepcopy(base);row['name']=name;row['expected']=False;mutate(row);fixtures.append(row)
bad('inflated_envelope',lambda r:r['contract']['voxel_cell_envelope']['max'].__setitem__(1,10.85))
bad('too_large_pitch',lambda r:r['contract']['voxel_cell_envelope'].__setitem__('pitch_m',.5))
bad('zero_pitch',lambda r:r['contract']['voxel_cell_envelope'].__setitem__('pitch_m',0))
bad('wrong_origin',lambda r:r['contract']['voxel_cell_envelope'].__setitem__('grid_origin_m',[.01,0,0]))
bad('wrong_sampling',lambda r:r['contract']['voxel_cell_envelope'].__setitem__('sampling','corner'))
bad('outside_envelope',lambda r:r['contract']['voxel_cell_envelope'].__setitem__('outside_envelope_vertices',1))
bad('concealed_analytic_excess',lambda r:r['contract'].__setitem__('outside_analytic_aabb_vertices',0))
bad('wrong_excess',lambda r:r['contract']['voxel_cell_envelope'].__setitem__('max_excess_from_analytic_m',0))
bad('missing_proof',lambda r:r.__setitem__('proof',{}))
bad('wrong_proof_source',lambda r:r['proof'].__setitem__('source_master_sha256','0'*64))
bad('cropped_shapes',lambda r:r['proof'].__setitem__('source_shapes_cropped',True))
bad('unoccupied_witness',lambda r:r['proof']['source_canonical_replay'][0].__setitem__('every_witness_source_and_canonical_occupied',False))
bad('wrong_witness_count',lambda r:r['proof'].__setitem__('source_occupied_boundary_cell_count',1))
bad('witness_outside_halfopen',lambda r:r['proof']['source_canonical_replay'][0]['witness_cells'][0].__setitem__(0,0))
bad('unbound_payload',lambda r:r['proof']['source_canonical_replay'][0].__setitem__('source_payload_sha256',''))
for path in [H/'facility_openings/batch_r01/composed/c3_property_ordinary_r2_b10bcfbba43136a4/c3_property_ordinary_r2_b10bcfbba43136a4.manifest.json',H/'facility_openings/composed_runtime/registered_cathedral_nave_aisles_transept.r05.candidate.manifest.json']:
    if not path.exists():continue
    v=json.loads(path.read_text());p=v['bounds_contract'];fixtures.append({'name':v['asset_key']+'_analytic_positive','contract':p,'fine':p['composed_render_bounds'],'coarse':p['coarse_render_bounds'],'source_sha':v['source_master_sha256'],'proof':{},'expected':True})
rows=[]
for r in fixtures:
    try:validate(r['contract'],r['fine'],r['coarse'],r['source_sha'],r['proof']);accepted=True
    except (AssertionError,KeyError,TypeError,ValueError,OverflowError):accepted=False
    rows.append({'name':r['name'],'expected':r['expected'],'accepted':accepted,'pass':accepted==r['expected']})
out=H/'evidence';(out/'source_bounds_fixtures_r01.json').write_text(json.dumps(fixtures,indent=2)+'\n')
report={'all_pass':all(r['pass'] for r in rows),'tests':rows};(out/'source_bounds_python_r01.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert report['all_pass']
