"""Append six original full-chain goals without revising the frozen 481 cases."""
import argparse,copy,hashlib,importlib.util,json,pathlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());B=H.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def read(p):return json.loads(p.read_bytes())
def write(p,v):
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--protected-handoff',type=pathlib.Path,required=True);ap.add_argument('--accepted-protected-goals',nargs='+',required=True);args=ap.parse_args();hp=args.protected_handoff.resolve();assert hp.is_relative_to(ROOT);pp=H/'port_route_handoff_r02.json';oldp=B/'public_network_final_catalog_r01/route_catalog_481_r01.json';assert sha(oldp)=='d2883a4b6e86eceabae3e9a1e85ab7f53279a66652b0d05480b7bf54701d7e45';old=read(oldp);doc=copy.deepcopy(old);hand=read(hp);port=read(pp);new=hand['routes']+port['routes'];allowed={'MARKET_TO_CASTLE','MARKET_TO_CATHEDRAL','MARKET_TO_ABBEY','MARKET_TO_NOBLE','MARKET_TO_TRAINING'};assert set(args.accepted_protected_goals)<=allowed;expected=set(args.accepted_protected_goals)|{'PORT_TO_MARKET'};case_count=481+2*len(expected);output=H/('route_catalog_'+str(case_count)+'_r01.json')
 assert len(new)==len(expected) and{r['id']for r in new}=={'GOAL:'+x for x in expected};assert all(r.get('bidirectional')for r in new)
 doc['routes']+=copy.deepcopy(new);doc['sources'].update(predecessor_final481=ref(oldp),protected_primary_goal_addendum=ref(hp),port_primary_goal_addendum=ref(pp))
 for r in new:
  for i,s in enumerate(r['provenance']):doc['sources']['new_goal:'+r['id']+':provenance:'+str(i)]=s
  doc['sources']['new_goal:'+r['id']+':resolved_geometry']=r['resolved_geometry_proof']
 # Replace by ID explicitly, keeping the predecessor rows in a separate ledger.
 before=copy.deepcopy(old['coverage']['primary_network_goals']);doc['coverage']['primary_network_goals']=[dict(id=r['id'],status='accepted',route_ids=['GOAL:'+r['id']],source=ref(hp)if r['id']!='PORT_TO_MARKET'else ref(pp),runtime_status='pending_full_chain_replay')if r['id']in expected else r for r in before]
 doc['pending_final_activation']=[f'Actual replay of {2*len(expected)} added full-chain directions on final scene2d53ca4a; prior481 remains separately frozen.','Any corrected collision-frame recipe requires every affected case to be replayed; unaffected reuse needs exact transitive-input identity.']
 doc['vector_accounting']=dict(predecessor_catalog=ref(oldp),predecessor_cases=481,new_primary_goal_directions=2*len(expected),total_cases=case_count,original481_records_value_identical=doc['routes'][:len(old['routes'])]==old['routes'],primary_goal_count=7,source_accepted_primary_goals=1+len(expected),held_primary_goals=6-len(expected),retired_expectations=old['vector_accounting']['retired_expectations'])
 doc['limits']+=[f'This additive catalog has {case_count} cases. The initial481 run remains immutable. Only explicitly released goals are added; every other original goal keeps its held disposition until a verified handoff exists.']
 spec=importlib.util.spec_from_file_location('bound_final_catalog',B/'public_network_final_catalog_r01/catalog.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);rows=m.validate(doc);assert len(rows)==case_count
 write(output,doc);write(H/'goal_coverage_revision.json',dict(predecessor=ref(oldp),current=ref(output),before=before,after=doc['coverage']['primary_network_goals'],all481_predecessor_routes_value_identical=True,added_case_ids=[r['id']for r in rows if r['id'].removesuffix('_REVERSE')in{'GOAL:'+x for x in expected}]))
 print(json.dumps(dict(catalog=ref(output),cases=len(rows),new_directions=2*len(expected))))
if __name__=='__main__':main()
