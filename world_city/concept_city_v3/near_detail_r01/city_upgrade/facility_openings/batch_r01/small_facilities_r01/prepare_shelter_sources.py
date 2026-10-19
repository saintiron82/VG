"""Explicit revision-local inputs for the frozen zero-window source adapter."""
from pathlib import Path
import sys,resource
HERE=Path(__file__).resolve().parent;B=HERE.parent
sys.path.insert(0,str(B/'native_pitch_v1'))
import prepare_native_sources_r03 as implementation
if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
    implementation.HERE=HERE/'shelter_sources'
    rules=implementation.a.load(implementation.HERE/'rules.json')
    assert implementation.a.sha(__file__)==rules['invocation_reference']['sha256']
    implementation.main()
