"""Bounded actual-pixel causality test of the hair field, with other priors frozen.
This does not test arbitrary background edits or whole-character/common output.
"""
from couple_head_field import *

def run():
 start=time.monotonic();m,a,src,q,b=inputs();q=with_head(q);validate(m,a,src)
 old,axes,masks,stats=field_from_inputs(m,a,src,q,b)
 stored=np.load(BASE/'generated/coupled_head_field.npz')['field']
 same=np.array_equal(old.astype(np.float16),stored)
 mut=src.copy();box=[210,375,218,383];mut[box[1]:box[3],box[0]:box[2]]=[255,0,0]
 mm,aa=before.measure(mut);validate(mm,aa,mut)
 new,axes2,masks2,stats2=field_from_inputs(mm,aa,mut,q,b)
 actual=new.astype(np.float16)!=stored
 def sdf(h):return (ndi.distance_transform_edt(h)-ndi.distance_transform_edt(~h)).astype(np.float32)*SCALE
 delta=sdf(masks['front_hair_confident'])-sdf(masks2['front_hair_confident'])
 X,Y=np.meshgrid(axes[0],axes[1],indexing='ij');v=C['views']['front'];co=np.array([(v['sole_y']-Y/SCALE-.5).ravel(),(v['axis_u']+X/SCALE-v['crop'][0]-.5).ravel()])
 changed=np.abs(ndi.map_coordinates(delta,co,order=1,mode='constant',cval=0)).reshape(X.shape)>0
 # Gaussian sigma .65, truncate4 has finite radius3 source cells. Signed distance
 # dependency itself may extend beyond the changed64px; no claim of fixed ROI.
 scope=ndi.binary_dilation(changed,structure=np.ones((7,7),bool))
 outside=int((actual&~scope[:,:,None]).sum())
 rejected={}
 for name,meas,pixels in [('missing_measurement',None,src),('wrong_source',m,mut)]:
  try:validate(meas,a,pixels);rejected[name]=False
  except ValueError as e:rejected[name]=str(e)
 result={'scope':'Hair field under frozen body/head/costume prior. Does not prove whole-character appearance or common compiler output.','same_stored_float16_field_bit_exact':same,'variant_actual_changed_pixels':int(np.any(src!=mut,axis=2).sum()),'variant_box':box,'variant_raw_pixel_sha256':rawsha(mut),'changed_front_confident_hair_pixels':int((masks['front_hair_confident']!=masks2['front_hair_confident']).sum()),'changed_field_nodes':int(actual.sum()),'changed_inside_outside_nodes':int(((old>0)!=(new>0)).sum()),'outside_declared_signed_distance_and3cell_curvature_dependency_nodes':outside,'side_measured_masks_exact':all(np.array_equal(a[k],aa[k])for k in a if k.startswith('side_')),'required_input_rejections':rejected,'foreground_causality_limit':'This edit remains foreground. The inherited foreground flood is fixed to approved pixels, so arbitrary background-edit causal coverage is not claimed.','source_geometry_repair':False,'script_sha256':sha(__file__),'field_sha256':sha(BASE/'generated/coupled_head_field.npz'),'seconds':time.monotonic()-start,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
 result['limited_regression_pass']=bool(same and actual.any() and outside==0 and result['side_measured_masks_exact'] and all(rejected.values()))
 write(BASE/'evidence/coupled_regression.json',result);print(json.dumps(result))
if __name__=='__main__':threading.Thread(target=guard,daemon=True).start();run()
