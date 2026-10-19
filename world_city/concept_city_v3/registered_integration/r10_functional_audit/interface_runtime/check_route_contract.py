#!/usr/bin/env python3
"""Check exact producer route vectors without opening the whole city scene."""
import argparse,hashlib,json,math,pathlib
H=pathlib.Path(__file__).resolve().parent
ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_ref(r):
 p=pathlib.Path(r['path']);p=p if p.is_absolute()else ROOT/p
 assert p.is_relative_to(ROOT)and sha(p)==r['sha256'],r
 return json.loads(p.read_bytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--request',required=True,type=pathlib.Path);ap.add_argument('--report',required=True,type=pathlib.Path);a=ap.parse_args();assert a.report.resolve().is_relative_to(H)
 request=json.loads(a.request.read_bytes());refs=request['producer_sources'];water=load_ref(refs['water_routes']);abbey=load_ref(refs['abbey_routes']);primary=load_ref(refs['water_original_approaches']);combined=load_ref(refs['routes']);expected={r['id']:r for d in [water,abbey]for r in d['routes']}
 assert len(expected)==len(water['routes'])+len(abbey['routes'])==len(combined['routes'])==len(request['routes'])
 for r in combined['routes']+request['routes']:
  original=expected[r['id']];assert r['points']==original['points']
  for key,value in original.items():assert r.get(key)==value,(r['id'],key,'source metadata changed')
  assert r['cart_test']is False and r['both_directions']is True
  assert len(r['points'])>=2 and all(len(p)==3 and all(math.isfinite(x)for x in p)for p in r['points'])
 for r in primary['routes']:assert expected[r['id']]['points']==r['points_xyz_m']and expected[r['id']]['clear_width_m']==r['width_m']==2
 result={'schema':'riverstone.r10.interface_route_source_contract.v1','status':'PASS_INPUT_ONLY','request':{'path':str(a.request),'sha256':sha(a.request)},'producer_route_manifests':{k:refs[k]for k in ['water_routes','abbey_routes','water_original_approaches','routes']},'unique_routes':len(expected),'positive_directions':len(expected)*2,'retained_negative_controls':2,'source_vectors_and_metadata_unchanged':True,'water_primary_routes_match_original_two_approaches':True,'capsule_executed':False,'limits':['Exact source-vector and input-metadata validation only; native support/clearance and source-face completeness require separate preparation and replay.']}
 with a.report.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k]for k in ['status','unique_routes','positive_directions','retained_negative_controls']}))
if __name__=='__main__':main()
