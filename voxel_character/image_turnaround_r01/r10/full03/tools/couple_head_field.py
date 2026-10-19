"""Recompute hair occlusion from the exact selected head trial, not an old head."""
from field_source import *

def validate(m,a,src):
 if not m or m.get('schema')!='riverstone.full02.independent_measurement.v1':raise ValueError('Independent measured input mandatory')
 if rawsha(src)!=m['actual_pixel_sha256']:raise ValueError('Wrong source pixels')
 if digest({k:rawsha(v)for k,v in a.items()})!=m['array_digest']:raise ValueError('Wrong measured masks')

def with_head(q):
 delta=np.load(BASE/'generated/head_interval_trial.npz')
 class Overlay:
  def __getitem__(self,k):return delta[k]if k in delta.files else q[k]
 return Overlay()

def run():
 t=time.monotonic();m,a,src,q,b=inputs();validate(m,a,src);q=with_head(q);field,axes,masks,stats=field_from_inputs(m,a,src,q,b);out=BASE/'generated/coupled_head_field.npz';stored=field.astype(np.float16);np.savez_compressed(out,field=stored,x=axes[0],y=axes[1],z=axes[2]);err=abs(stored.astype(np.float32)-field);report={'status':'COUPLED_HEAD_HAIR_SOURCE_CANDIDATE_NOT_ART_APPROVED','body_costume_base_sha256':A['fixed_source_sha256'],'head_source_sha256':sha(BASE/'generated/head_interval_trial.npz'),'head_measurement_sha256':sha(BASE/'evidence/head_interval_measurement.json.gz'),'image_measurement_sha256':sha(ROOT/A['fixed_measurement']),'field_source_sha256':sha(out),'field_generator_sha256':sha(Path(__file__).with_name('field_source.py')),'coupling_generator_sha256':sha(__file__),'source_guard':'Independent actual pixels and measured masks required; hidden depth remains prior','stats':stats,'near_surface_quantization_error_m':float(err[abs(field)<.01].max()),'seconds':time.monotonic()-t,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024};write(BASE/'evidence/coupled_source.json',report);print(json.dumps(report));before.disk()
if __name__=='__main__':threading.Thread(target=guard,daemon=True).start();run()
