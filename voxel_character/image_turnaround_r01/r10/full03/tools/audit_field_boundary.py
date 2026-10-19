"""Read-only finite-domain closure diagnostic; never repairs signed components."""
from field_source import *

def run():
 q=np.load(BASE/'generated/coupled_head_field.npz');f=q['field'];axes=[q[k]for k in ['x','y','z']];faces={}
 for axis,name in enumerate('xyz'):
  for side,index in [('min',0),('max',-1)]:
   a=np.take(f,index,axis=axis);faces[name+'_'+side]={'coordinate_m':float(axes[axis][index]),'positive_nodes':int((a>0).sum()),'total_nodes':a.size,'max_field_m':float(a.max())}
 result={'source_field_sha256':sha(BASE/'generated/coupled_head_field.npz'),'script_sha256':sha(__file__),'boundary_faces':faces,'positive_boundary_is_closed_source_proof':False,'finding':'Positive field touches finite domain boundaries. Renderer outside-domain negative samples can make these truncations appear as flat caps. Opaque-body allowance is one-sided depth and does not bound hidden hair extent. No extension, filling, component deletion or repair applied.','status':'FAIL_FINITE_DOMAIN_CLOSURE'}
 write(BASE/'evidence/field_boundary_audit.json',result);print(json.dumps(result))
if __name__=='__main__':run()
