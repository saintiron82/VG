"""Reuse completed original-face cuts; replace only sealed public emission."""
import json,math
from .author_direct_tops import HERE,ref
from ..r17_district_batches import author as a
def read(p,expected=None):
 if expected is not None and a.sha(p)!=expected:raise ValueError('Changed input '+str(p))
 return json.loads(p.read_bytes())
def main():
 dest=HERE/'public_top_r03_native_bound';dest.mkdir(exist_ok=True);assert not(dest/'surface_patch.json').exists()
 p=HERE/'public_top_r02_partitionfix/surface_patch.json';patch=read(p)
 source=HERE/'finite_field_candidate_r07_native_bound.json';d=read(source,'d807f13a82e2639e1e9c7ff37ce8750b60d783b80cee9205fe1ffe8344239683');revision=d['report']['native_ownership_revision']
 assert revision['all_removed_pieces_are_inherited_source_holes']
 old_cuts=a.canonical_sha(patch['surface_edits']);old_private=a.canonical_sha(patch['appended_surfaces']['ground_stone'])
 patch['appended_surfaces']['road']=[v for r in d['records']for t in r['triangles_xyz_m']for v in t];patch['id']='R18_NATIVE_BOUND_PUBLIC_TOPS_R03';patch['status']='CANDIDATE_PUBLIC_NATIVE_OWNERSHIP_PENDING_JOINT_BOUNDARY_AND_RUNTIME'
 patch['source_references'] += [ref(p),ref(source),ref(HERE/'native_emission_revision_r07_review.json'),ref(HERE/'bind_native_top_revision.py')]
 assert old_cuts==a.canonical_sha(patch['surface_edits'])and old_private==a.canonical_sha(patch['appended_surfaces']['ground_stone'])
 private=[r for r in read(HERE/'public_top_r01/physical_owners.json')['owners']if r['kind']=='nonwalking_private_cap_remainder']
 owners=[dict(r,kind='canonical_public_surface',material='road')for r in d['records']]+private
 report=dict(status='PASS_BOUNDED_EMISSION_REBIND_PENDING_BOUNDARY',source_refs=patch['source_references'],original_face_cuts_unchanged=True,private_cap_remainders_unchanged=len(private),public_records=len(d['records']),native_exclusion_area_m2=revision['removed_native_area_m2'],all_removed_emission_inside_existing_holes=True,upward=all(a.normal_y(t)>0 for r in d['records']for t in r['triangles_xyz_m']),activation=False)
 for name,value in [('surface_patch.json',patch),('emission_binding_review.json',report),('physical_owners.json',dict(source_refs=patch['source_references'],owners=owners))]:(dest/name).write_text(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n')
 print({k:v for k,v in report.items()if k!='source_refs'},flush=True)
if __name__=='__main__':main()
