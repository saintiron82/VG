"""Bind immutable 481 vectors to the final topologically rebound source batch."""
from build_vectors import *
import argparse
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--binding',required=True);ap.add_argument('--binding-sha',required=True);ap.add_argument('--revision',default='r01');args=ap.parse_args();inp=H/'route_vectors_r01.json';d=read(inp);bp=ROOT/args.binding;binding=read(bp);assert sha(bp)==args.binding_sha;output=H/('route_catalog_481_'+args.revision+'.json');d['status']='READY_FOR_ACTUAL_SCENE_REPLAY';d['sources']['final_vector_predecessor']=ref(inp);d['sources']['final_atomic_binding']=ref(bp)
 for label,rr in [('patch',binding['patches']),('pack',binding['packs']),('contract',binding['collision_contracts']),('evidence',binding['evidence'])]:
  for i,r in enumerate(rr):d['sources']['final_'+label+'_'+str(i)]=r
 d['activation_requirements']=dict(atomic_binding=ref(bp),native_packs=binding['packs'],appended_surface_patches=binding['patches'],collision_contracts=binding['collision_contracts'],policy='All active emitted producers, final ordered native replacement resolution and declared contracts must match the actual authored scene. Exact public north/causeway row reconstruction and all unchanged prior private tops are mandatory.')
 d['pending_final_activation']=['Actual authored/runtime hashes and exact-zero plus ten-row collision-winding bindings','Exact-world local-origin extraction and actual combined 481-case replay'];d['limits'][-1]='Source-bound catalog is ready for strict actual-scene extraction. Runtime acceptance remains pending the single final combined replay; prior focused results are not summed.';write(output,d)
 import catalog
 assert len(catalog.validate(d))==481
 write(H/('source_binding_review_'+args.revision+'.json'),dict(status='SOURCE_BOUND_ACTUAL_SCENE_PENDING',catalog=ref(output),binding=ref(bp),original_vector_file=ref(inp),routes_value_identical=d['routes']==read(inp)['routes'],counts=dict(cases=481,patches=len(binding['patches']),packs=len(binding['packs']),contracts=len(binding['collision_contracts']))));print(json.dumps(dict(catalog=ref(output))))
if __name__=='__main__':main()
