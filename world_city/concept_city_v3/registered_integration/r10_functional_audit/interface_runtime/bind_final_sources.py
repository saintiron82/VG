#!/usr/bin/env python3
"""Bind frozen focused suites to one parent-composed finite/native source."""
import argparse,copy,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def read(p):return json.loads(pathlib.Path(p).read_bytes())
def ref(p):
 p=pathlib.Path(p).resolve();assert p.is_relative_to(ROOT)
 return {'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2);f.write('\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--index',required=True,type=pathlib.Path);ap.add_argument('--patch',required=True,type=pathlib.Path);ap.add_argument('--ledger',required=True,type=pathlib.Path);ap.add_argument('--ownership',required=True,type=pathlib.Path);ap.add_argument('--clergy-routes',required=True,type=pathlib.Path);ap.add_argument('--tag',required=True);a=ap.parse_args();assert '/'not in a.tag and '..'not in a.tag
 base=read(H/'request_r01.json');base.update(finite_patch=ref(a.patch),visual_index=ref(a.index),gates=[])
 ledger=read(a.ledger);assert ledger['surface_patch_sha256']==base['finite_patch']['sha256']and ledger['visual_index_sha256']==base['visual_index']['sha256']
 full=H/'source_routes_final_r01.json';clergy=a.clergy_routes;join=H.parent/'network/market_join_probes/request.json';plans=[('interfaces',full,['capsule','cart']),('clergy',clergy,['capsule']),('market_join',join,['capsule','cart'])];reports=[]
 for name,p,kinds in plans:
  d=read(p);q=copy.deepcopy(base);q['routes']=copy.deepcopy(d['routes']);q['required_evidence_kinds']=kinds;q['producer_sources']={'routes':ref(p),'final_composition_ledger':ref(a.ledger),'source_ownership':ref(a.ownership)}
  q['producer_sources'].update(d.get('source_manifests',{}));q['producer_sources'].update(d.get('sources',{}));q['producer_sources'].update(d.get('producer_sources',{}))
  if 'cart_fixture'in d:assert d['cart_fixture']==base['cart_fixture'],'Fixture must remain byte-equivalent input fields'
  for original,r in zip(d['routes'],q['routes']):
   if name=='clergy':r['cart_test']=False;r['both_directions']=True
   if name=='market_join':assert r['both_directions']is False and r['cart_test']is True
   assert r['points']==original['points']
  directions=sum(2 if r.get('both_directions',True)else 1 for r in q['routes']);cart_directions=sum((2 if r.get('both_directions',True)else 1)for r in q['routes']if r.get('cart_test',False))
  q['test_scope']={'interfaces':'38 positive capsule directions: two existing water sites, abbey r03, low market draw and three delivery paths. Only delivery circuit and stop lane enable carts, four directions.','clergy':'Ten positive pedestrian directions along public approach, original road through, bounded turns and admitted gate standing point only; no building interior or cart claim.','market_join':'Two original operational port arrival/departure joining poses, without reversing them. Does not itself constitute an uninterrupted full port-to-market roundtrip replay.'}[name]
  target=H/(a.tag+'_'+name+'_request.json');write(target,q);reports.append({'suite':name,'request':ref(target),'capsule_cases':directions+2,'cart_cases':cart_directions+2 if 'cart'in kinds else 0,'shared_controls_each_kind':2})
 write(H/(a.tag+'_suite_manifest.json'),{'status':'BOUND_NOT_EXECUTED','composite_index':ref(a.index),'finite_patch':ref(a.patch),'suites':reports});print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
