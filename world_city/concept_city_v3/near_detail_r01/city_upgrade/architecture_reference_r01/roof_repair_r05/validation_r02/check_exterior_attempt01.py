"""Reuses frozen independent plane oracle against the new actual common-mesh render."""
import sys,time,resource,json
from pathlib import Path
H=Path(__file__).resolve().parents[1];A=H.parent
sys.path.insert(0,str(A/'roof_repair_r04/validation_r01'))
from candidate_oracle import CandidateOracle,audit_render,adapter_order,read,ref,save
import numpy as np

def main():
 start=time.monotonic();oracle=CandidateOracle(A/'foundation_repair_r01/foundation_arrays.npz',H/'upper_union_arrays.npz');render=read(H/'roof_repaired.render.json.gz');comp=read(H/'composition.json');adapter,order=adapter_order();seams=[(2,c['owned_z_cells'][1])for c in comp['chunks'][:-1]];report=audit_render(render,oracle,{n:i for i,n in enumerate(oracle.names)},order,extra_interfaces=seams)
 report.update(schema='riverstone.roof_r05.independent_exterior.v1',render=ref(H/'roof_repaired.render.json.gz'),union=ref(H/'upper_union_arrays.npz'),reused_oracle=ref(A/'roof_repair_r04/validation_r01/validate_exterior.py'),godot_adapter=ref(adapter),geometry_sampling_calls=0,mesher_calls=0,elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 save(H/'validation_r02/exterior.json',report);print(json.dumps(report));assert report['outward_CCW_matches_actual_solid_exterior']and report['artificial_interface_unit_faces']==0
if __name__=='__main__':main()
