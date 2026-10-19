"""Bind the exact bounded native-owned R18 emission revision for final replay."""
import hashlib,json,pathlib,sys
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(H));import catalog,emission_revision
R18=ROOT/'world_city/concept_city_v3/registered_topography/revisions/public_corridors_r18'
def read(p):return json.loads(p.read_bytes())
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def main():
 base=H/'route_catalog_41_noble_r03.json';d=read(base);oldref=d['activation_requirements']['finite_public_field'];old=read(catalog.source(oldref));path=R18/'finite_field_candidate_r07_native_bound.json';review_path=R18/'native_emission_revision_r07_review.json';assert ref(path)['sha256']=='d807f13a82e2639e1e9c7ff37ce8750b60d783b80cee9205fe1ffe8344239683';assert ref(review_path)['sha256']=='def8ef990cabec6104929651df6133bafa0c65164f457b7bd00a8dfc8b2881ea';review=read(review_path);assert review['candidate']==ref(path);check=emission_revision.validate(old,read(path),review)
 for row in review['sources']:catalog.source(row)
 d['sources'].update(prior_noble_catalog=ref(base),r18_revised_finite_owners=ref(path),r18_emission_revision_review=ref(review_path))
 d['activation_requirements'].update(finite_public_field=ref(path),finite_public_emission_revision=dict(previous=oldref,review=ref(review_path)))
 d['source_candidate_accounting']['r18_native_emission_revision']=dict(previous=oldref,current=ref(path),review=ref(review_path),**check['summary'],removed_native_area_by_owner_m2=review['removed_native_area_by_owner_m2'])
 d['limits'].append('R18 revision removes only declared native-owned terminal/shoulder overlaps. Every unaffected original owner triangle remains a verbatim activation requirement; field planes and design-grade exceptions are unchanged.')
 expanded=catalog.validate(d);out=H/'route_catalog_ready_r04.json';write(out,d);write(H/'catalog_ready_report.json',dict(status='SOURCE_BOUND_AWAITING_EXACT_JOINT_SCENE',catalog=ref(out),expanded_cases=len(expanded),native_pack_sets=len(d['activation_requirements']['native_packs']),required_collision_contracts=len(d['activation_requirements']['collision_contracts']),r18_emission_revision=check['summary']));print(json.dumps(read(H/'catalog_ready_report.json'),indent=2))
if __name__=='__main__':main()
