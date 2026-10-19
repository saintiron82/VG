"""Independent full exterior oracle from source labels + frozen baseline/roof."""
import sys,hashlib,json,gzip,time,resource,os
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
O=Path(__file__).resolve().parent;A=O.parent
sys.path.insert(0,str(A/'roof_repair_r04/validation_r01'))
from candidate_oracle import CandidateOracle
from validate_render import stream_render
from validate_exterior import audit_render,adapter_order,ref,read,sha,np,PITCH
class GalleryOracle(CandidateOracle):
 def __init__(self):
  super().__init__(A/'foundation_repair_r01/foundation_arrays.npz',A/'roof_repair_r04/upper_union_arrays.npz')
  d=np.load(A/'railing_measurement_r01/pixel_masks.npz');self.labels=d['labels'];crop=d['source_rgb'];pal=d['palette']
  self.mi=np.argmin(((crop.astype(float)[:,:,None,:]-pal[None,None,:,:])**2).sum(3),axis=2)
  self.offset=len(self.names);self.names += [f'measured_wood_{i}' for i in range(3)]
 def values(self,x,y,z):
  x,y,z=np.broadcast_arrays(x,y,z);out=super().values(x,y,z)
  xx=x+104;yy=245-y;valid=(xx>=0)&(xx<64)&(yy>=0)&(yy<48)&(z>=156)&(z<160)
  indices=np.where(valid)
  if len(indices[0]):
   lab=self.labels[yy[indices],xx[indices]];positive=(lab==1);known=positive|(lab==2)
   selected=tuple(i[known] for i in indices);out[selected]=-1
   solid=positive&(z[indices]>=158);selected=tuple(i[solid] for i in indices)
   out[selected]=self.offset+self.mi[yy[selected],xx[selected]]
  return out
def run():
 start=time.monotonic();candidate=O/'gallery_repaired.render.json.gz';report=read(O/'composition.json');assert sha(candidate)==report['render']['sha256']
 oracle=GalleryOracle();adapter,order=adapter_order();render=stream_render(candidate)
 checked=audit_render(render,oracle,{n:i for i,n in enumerate(oracle.names)},order,extra_interfaces={(0,-105),(0,-39),(1,203),(1,243),(2,155),(2,161),(2,158),(2,124)})
 assert checked['outward_CCW_matches_actual_solid_exterior'],checked
 original=read(A/'roof_repair_r04/roof_patch.master.json.gz')['materials'];base=read(A/'foundation_repair_r01/foundation_revised.master.json.gz')['materials'];base.update(original)
 data=np.load(A/'railing_measurement_r01/pixel_masks.npz');base.update({f'measured_wood_{i}':''.join(f'{int(c):02x}' for c in rgb) for i,rgb in enumerate(data['palette'])})
 assert render['materials']==base and list(base)==oracle.names
 checked.update(status='TECHNICAL_PASS',candidate_render=ref(candidate),source_labels=ref(A/'railing_measurement_r01/pixel_masks.npz'),validator=ref(Path(__file__)),frozen_roof_oracle=ref(A/'roof_repair_r04/upper_union_arrays.npz'),base_arrays=ref(A/'foundation_repair_r01/foundation_arrays.npz'),source_driven_expected_materials=True,all_original_palette_entries_preserved=True,actual_view_gate='PENDING_PARENT',production_gate_open=False,elapsed_seconds=time.monotonic()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 target=O/'independent_exterior_validation.json';assert not target.exists();target.write_text(json.dumps(checked,indent=2));print(json.dumps(checked),flush=True)
if __name__=='__main__':run()
