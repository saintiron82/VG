"""Fix only source-reference path resolution after the retained zero-route guard rejection."""
import copy,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def main():
    original=json.loads((H/'prepared.json').read_text());d=copy.deepcopy(original)
    for source in d['sources'].values():
        path=pathlib.Path(source['path']);path=path if path.is_absolute() else ROOT/path
        assert sha(path)==source['sha256'];source['path']=str(path)
    d['sources']['relative_path_preflight']=ref(H/'prepared.json')
    d['implementation_hashes'][str(pathlib.Path(__file__).relative_to(ROOT))]=sha(pathlib.Path(__file__))
    for key in ['routes','assets','placements','buildings','coverage','assumptions']:assert d[key]==original[key]
    with (H/'prepared_runtime.json').open('x') as f:json.dump(d,f,separators=(',',':'),allow_nan=False);f.write('\n')
    error=json.loads((H/'evidence/north_initial.json').read_text());assert len(error['routes'])==0
    evidence={'schema':'riverstone.source_path_binding_correction.v1','original_prepared':ref(H/'prepared.json'),
              'retained_guard_rejection':ref(H/'evidence/north_initial.json'),'corrected_prepared':ref(H/'prepared_runtime.json'),
              'geometry_and_routes_verbatim':True,'reason':'The unchanged controller requires absolute source paths. Relative references were verified against the original expected hashes, then resolved under the exact repository root. No content hash was changed.'}
    with (H/'evidence/path_binding_correction.json').open('x') as f:json.dump(evidence,f,indent=2);f.write('\n')
    print(json.dumps({'prepared':ref(H/'prepared_runtime.json')}))
if __name__=='__main__':main()
