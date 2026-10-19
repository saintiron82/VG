"""Finalize the already-tested identity-only candidate after a manifest-local NameError."""
from build_relocation_id_r02 import *
def main():
 out=CANON;snap=out/'source_snapshot';assert not(out/'FROZEN.json').exists();report=read(out/'adapter_regression.json');assert report['resolved_source_id_count']==0 and report['resolved_new_id_count']==1;assert read(H/'adapter_r02_pass/composition.json')['status']=='PASS_SOURCE_IDENTITY_AND_COMPOSITION';shutil.copy2(H/'build_relocation_id_r02.py',snap/'build_relocation_id_r02.py')
 (snap/'reproduce.py').write_text('''"""Run the frozen identity-only transform into a new output folder."""
import sys,types,json,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
S=Path(__file__).resolve().parent;F=S.parent;H=F.parent
m=json.loads((F/'FROZEN.json').read_bytes())
for n,h in m['files'].items():assert hashlib.sha256((F/n).read_bytes()).hexdigest()==h,n
a=types.ModuleType('frozen_clergy_id_transform');a.__file__=str(H/'build_relocation_id_r02.py');exec(compile((S/'build_relocation_id_r02.py').read_bytes(),str(S/'build_relocation_id_r02.py'),'exec'),a.__dict__)
out=Path(sys.argv[1]).resolve()if len(sys.argv)>1 else H/'candidate_r02_replayed';a.produce(out);r={n:dict(identical=(out/n).read_bytes()==(F/n).read_bytes(),sha256=a.sha(out/n))for n in ['surface_patch.json','pack.json','index.json','routes.json']};assert all(v['identical']for v in r.values());a.write(out/'reproduction_result.json',r);print(json.dumps(r,indent=2))
''')
 m=read(out/'reproducibility_manifest.json');m['reproduction_call']='PYTHONDONTWRITEBYTECODE=1 python '+str((snap/'reproduce.py').relative_to(ROOT))+' [new_absent_output_directory]';m['source_snapshot_corrected_before_freeze']='Manifest-only undefined local old fixed; initial error log preserved. Geometry and identity-transform replay already passed.';write(out/'reproducibility_manifest.json',m)
 deps=[OLD/'FROZEN.json',H/'build_relocation_id_r02.py',ROOT/'world_city/concept_city_v3/registered_integration/r9/integrate_packs.py',ROOT/'world_city/concept_city_v3/preview_r9/VisualAddendum.gd'];frozen=dict(status='FROZEN_ACTUAL_PYTHON_COMPOSITION_PASS_RUNTIME_AND_VIEW_PENDING',base_scene=read(OLD/'FROZEN.json')['base_scene'],files={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()},source_dependencies=[ref(p)for p in deps]);write(out/'FROZEN.json',frozen);print(json.dumps({n:ref(out/n)for n in ['surface_patch.json','pack.json','index.json','routes.json']},indent=2))
if __name__=='__main__':main()
