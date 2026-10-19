"""Check one pinned existing common geometry; never compile or approve an asset."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time
from build_audit import REPO, file_record

sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('multiview_contract',REPO/'voxel_character/common/validation/multiview_contract.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    prefix='voxel_character/image_turnaround_r01/generated/violet_curved04/'
    paths={'master':(prefix+'master.json.gz','master'),'compiled':(prefix+'compiled.cells.json.gz','compiled'),
           'render_mesh':(prefix+'character.render.json','render_mesh'),
           'compiler_source':('voxel_character/common/core.py','compiler_source'),
           'exporter_source':('voxel_character/common/render_data.py','exporter_source'),
           'mesher_source':('voxel_character/tools/mesh.py','mesher_source')}
    start=time.monotonic()
    rows={key:{**file_record(path,kind),'kind':kind} for key,(path,kind) in paths.items()}
    artifacts=v.Artifacts(rows,REPO)
    diagnostics=v.common_geometry({'common':{key:key for key in paths}},artifacts,complex_asset=False)
    result={'schema':'riverstone.multiview.native_geometry_probe.v1','asset_snapshot':'violet_curved04',
            'read_only':True,'new_compile_or_render':False,'geometry_binding_pass':True,
            'full_multiview_contract_evaluated':False,'complex_semantic_review_evaluated':False,
            'automatic_art_acceptance':False,'asset_complete':False,'coverage_claim_allowed':False,
            'visual_review_status':'pending','source_artifacts':rows,'diagnostics':diagnostics,
            'elapsed_seconds':round(time.monotonic()-start,6),'max_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
            'scope':'Native master/compiled/mesh binding and exact occupied boundary/material/normal check only. No new likeness assessment.'}
    with args.output.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('geometry_binding_pass','full_multiview_contract_evaluated','elapsed_seconds','max_rss_mib')}))

if __name__=='__main__':main()
