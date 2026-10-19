"""Replay the bounded source, ownership, preview and supplemental-side gates."""
import json,math,time
from . import author as a
from . import audit,audit_ownership,audit_preview,audit_profile_interfaces
def run():
 audit.run();audit_ownership.run();audit_preview.run();audit_profile_interfaces.run()
 bounds=[-530,-530,530,656];start=time.monotonic();s=a.supplemental_side_records(bounds)
 result=dict(bounds_xz_m=bounds,author_sha256=a.R04.sha(a.HERE/'author.py'),side_helper_sha256=a.recovered_corner.SIDE_HELPER_SHA256,side_count=len(s),elapsed_s=time.monotonic()-start,all_heights_finite=all(math.isfinite(v) for r in s for p in r['vertices_xyz_m'] for v in p))
 assert result['all_heights_finite']
 (a.HERE/'supplemental_preflight.json').write_text(json.dumps(result,indent=2)+'\n')
 (a.HERE/'contract.json').write_text(json.dumps(a.build_contract(),indent=2)+'\n')
 print('CONTRACT',a.R04.sha(a.HERE/'contract.json'),'AUTHOR',a.R04.sha(a.HERE/'author.py'),flush=True)
if __name__=='__main__':run()
