"""Source topology correction only: consistent outward closed-loft indices.
Positions, measurements, costume, hair field and resource-failure evidence stay fixed.
"""
from field_source import *

def counts(f):
 e=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]);key=np.sort(e,axis=1);u,inv,n=np.unique(key,axis=0,return_inverse=True,return_counts=True);sign=np.where(e[:,0]<e[:,1],1,-1);s=np.bincount(inv,weights=sign,minlength=len(u));return {'boundary_edges':int((n==1).sum()),'nonmanifold_edges':int((n>2).sum()),'same_direction_shared_edges':int(((n==2)&(s!=0)).sum())}

def fixed(profile):
 v,old=before.loft(profile);n=before.A['volumes']['angular_samples'];rows=len(profile['sections']);f=[]
 for r in range(rows-1):
  for j in range(n):
   k=(j+1)%n;f.extend([[r*n+j,(r+1)*n+k,(r+1)*n+j],[r*n+j,r*n+k,(r+1)*n+k]])
 for r,sgn in [(0,1),(rows-1,-1)]:
  center=rows*n+(0 if sgn>0 else 1)
  for j in range(n):f.append([center,r*n+(j+1)%n,r*n+j]if sgn>0 else[center,r*n+j,r*n+(j+1)%n])
 return v,np.array(f,int)

def run():
 m,a,src,q,b=inputs();delta={};reports=[]
 for i,p in enumerate(m['profiles']):
  v,f=fixed(p);assert np.array_equal(v,q[f'v{i}']);old=q[f'f{i}'];delta[f'f{i}']=f;delta[f'c{i}']=before.surface_rgb(v,f,src,a,p['id']);reports.append({'part':p['id'],'before':counts(old),'after':counts(f),'changed_triangle_winding':int(np.any(f!=old,1).sum()),'position_changed':False,'signed_volume_m3':float(np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6)})
 np.savez_compressed(BASE/'generated/loft_orientation_delta.npz',**delta);write(BASE/'evidence/loft_winding_audit.json',{'source_sha256':A['fixed_source_sha256'],'script_sha256':sha(__file__),'delta_sha256':sha(BASE/'generated/loft_orientation_delta.npz'),'parts':reports,'cause':'Winding hypothesis rejected if changed_triangle_winding is zero. Report actual counts; do not infer a correction from this test.','shape_positions_changed':False,'costume_or_hair_field_changed':False});print(json.dumps(reports))
if __name__=='__main__':run()
