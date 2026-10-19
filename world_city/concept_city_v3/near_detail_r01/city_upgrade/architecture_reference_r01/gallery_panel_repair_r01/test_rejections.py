"""Retained deliberately bad fixtures; no mutation of real artifacts."""
from repair_common import *
import time
def run():
 start=time.monotonic();compiled=read(O/'local_union.compiled.json.gz');good={tuple(r[:3]):r[5] for r in compiled['cells']};a=baseline();names=list(compiled['materials']);old={p:names[m] for p,m in inherited_cells(a).items()};labels=np.load(A/'railing_measurement_r01/pixel_masks.npz')['labels'];owner=mask_owner(labels);results=[]
 def check_delta(candidate,old=old):
  bad={p for p in set(old)|set(candidate) if old.get(p)!=candidate.get(p)}-owner
  assert not bad,'Changed cells outside positive/aperture owner: '+str(sorted(bad)[:3])
 def expect_reject(name,witness,check):
  try:check()
  except AssertionError as e:results.append({'case':name,'fixture':witness,'expected':'REJECT','actual':'REJECT','reason':str(e)})
  else:raise AssertionError('Negative fixture falsely accepted: '+name)
 check_delta(good)
 # Legitimate rear wall is outside the finite aperture interval and must survive.
 yy,xx=np.argwhere(labels==2)[0];x,y=coords(int(yy),int(xx));wall=(x,y,123);wallmat=names[value(a,wall)];extended_old={**old,wall:wallmat};bad={**good,wall:wallmat};bad.pop(wall)
 expect_reject('rear_wall_endpoint_deletion',{'deleted_xyz':wall,'material':wallmat},lambda:check_delta(bad,extended_old))
 unknown=next((*coords(int(y),int(x)),159) for y,x in np.argwhere(np.isin(labels,[3,4,5])) if (*coords(int(y),int(x)),159) in good);bad=dict(good);bad.pop(unknown)
 expect_reject('unknown_pixel_carve',{'deleted_xyz':unknown,'source_label':int(labels[495-unknown[1]-250,unknown[0]+256-152])},lambda:check_delta(bad))
 # Aperture constraints reject a hidden plate anywhere in the finite protected recess.
 def aperture_clear(candidate):
  for yy,xx in np.argwhere(labels==2):
   x,y=coords(int(yy),int(xx))
   for z in range(124,160):assert (x,y,z) not in candidate,'Annotated finite aperture blocked at '+str((x,y,z))
 yy,xx=np.argwhere(labels==2)[0];x,y=coords(int(yy),int(xx));blocked=(x,y,157);bad=dict(good);bad[blocked]='pixel_07';expect_reject('aperture_hidden_backplate',{'added_xyz':blocked},lambda:aperture_clear(bad))
 # No whole-ray empty assertion: preserved wall stays occupied and test stops at124.
 aperture_clear(good);assert wallmat
 actual=[]
 for g in read(O/'owned_surface.json.gz')['groups']:
  for q in g['quads']:actual.extend(faces(q,g['material']))
 expected=expected_faces(good)
 def exact_surface(fs):
  fs=list(fs);unique=set(fs);assert len(unique)==len(fs),'Duplicate oriented material faces';assert unique==expected,'Missing or extra oriented material exterior faces'
 exact_surface(actual)
 witness=next(f for f in actual if f[2] in (-105,-40,-104) or f[3] in (203,204,242))
 bad=list(actual);bad.remove(witness);expect_reject('partial_face_boundary_seam',{'removed_unit_face':witness},lambda:exact_surface(bad))
 bad=list(actual)+[actual[0]];expect_reject('duplicate_composition_face',{'duplicated_unit_face':actual[0]},lambda:exact_surface(bad))
 # Missing halo creates an internal cap at an owned-region boundary.
 internal=next((axis,sign,*p,mat) for p,mat in good.items() if bounds_contains(p) for axis in range(3) for sign in [-1,1] if not bounds_contains(tuple(p[i]+(sign if i==axis else 0) for i in range(3))) and tuple(p[i]+(sign if i==axis else 0) for i in range(3)) in good)
 bad=list(actual)+[internal];expect_reject('omitted_halo_artificial_cap',{'added_unit_face':internal},lambda:exact_surface(bad))
 mutation=read(O/'mutation_case.json')
 def source_changes(before,after):assert before!=after,'Source-raster mutation ignored by pipeline'
 source_changes(mutation['original_payload_hash'],mutation['mutated_payload_hash'])
 expect_reject('source_pixel_mutation_noop',{'source_xy':mutation['source_xy'],'falsified_mutant_payload':mutation['original_payload_hash']},lambda:source_changes(mutation['original_payload_hash'],mutation['original_payload_hash']))
 # Domain mutation is not repaired by convenient clipping: protected side/deck remains frozen.
 outside=(-106,220,159);bad=dict(good);bad.pop(outside,None)
 if outside not in good:bad[outside]='pixel_07'
 expect_reject('unrelated_owner_edit',{'changed_xyz':outside},lambda:check_delta(bad))
 result={'schema':'riverstone.gallery_panel_repair.negative_fixtures.v1','status':'PASS','negative_case_count':len(results),'retained_bad_fixtures':results,'positive_controls':['Exact actual owner delta accepted','Exact common-mesher material exterior accepted','Finite aperture interval clear with real rear wall retained','Real source-pixel mutation changes payload'],'elapsed_seconds':time.monotonic()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 save('negative_fixtures.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':run()
