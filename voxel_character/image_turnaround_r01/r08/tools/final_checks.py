"""Exact same-input artifact replay and preservation checks, no shape edits."""
from pathlib import Path
import json
from measured_cloth import ROOT,sha,read,write,build,budget

def run():
 p=ROOT/'generated/reproduced_region'
 if not p.exists():build(ROOT/'generated/measured/measurements.json',p)
 matches={name:sha(ROOT/'generated/region'/name)==sha(p/name) for name in ['master.json.gz','compiled.cells.json.gz','region.render.json.gz','calculated_surface.npz']}
 # npz contains ZIP timestamps, so only content hashes, not archive bytes,
 # are stable across wall-clock time. All authoritative master/cells/mesh
 # gzip files use a fixed mtime and are required to be byte-identical.
 assert all(matches[k] for k in ['master.json.gz','compiled.cells.json.gz','region.render.json.gz'])
 import numpy as np
 assert np.array_equal(np.load(p/'calculated_surface.npz')['vertices'],np.load(ROOT/'generated/region/calculated_surface.npz')['vertices'])
 r07=ROOT.parent/'r07';old=read(r07/'closure/closure_seal.json');preserved=[sha(r07/r['path'])==r['sha256'] for r in old['files']];assert all(preserved)
 report={'same_input_authoritative_gzip_files_byte_identical':{k:v for k,v in matches.items() if k.endswith('.gz')},'calculated_surface_arrays_exactly_equal':True,'r07_sealed_files_checked':len(preserved),'r07_sealed_files_unchanged':all(preserved),'disk_used_bytes_before_this_report':budget(),'approved_extra_bytes':15*1024**2,'final_check_code_sha256':sha(__file__),'status':'pipeline reproducibility verified; garment shape, structure and appearance not approved'}
 write(ROOT/'evidence/final_checks.json',report);print(json.dumps(report))
if __name__=='__main__':run()
