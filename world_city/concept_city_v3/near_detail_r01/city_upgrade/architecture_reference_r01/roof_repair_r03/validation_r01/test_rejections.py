#!/usr/bin/env python3
"""Adversarial mutations of real r03 inputs in memory; files are never changed."""
from validate_delta import *
from test_surface_rejections import surface_tests

def main():
 t=time.monotonic();before=pins();ctx=source_proof();plan=read(R/'plan.json');master=read(R/'roof_patch.master.json.gz');tests={}
 def reject(name,call):
  try:call()
  except (ValueError,AssertionError) as e:tests[name]={'rejected':True,'reason':str(e)}
  else:raise AssertionError('Mutation accepted: '+name)
  gc.collect()
 def change_cell(name,point,material,label=None):
  def mutate(a,l,p):
   require(a[point]!=material,'Fixture is not a mutation');a[point]=material
   if label is not None:l[point]=label
  reject(name,lambda:cell_proof(ctx,mutate))
 # Derive actual fixture cells without retaining a second large candidate.
 a=np.load(R/'upper_union_arrays.npz')['materials'];lab=np.load(R/'delta_ownership_arrays.npz')['delta_class'];old=np.load(OLD/'upper_union_arrays.npz')['materials'];restored=above=background=body=None
 X=(np.arange(400)-200+.5)*PITCH
 for iy in range(4,148):
  if restored is None and (lab[iy]==1).any():restored=(iy,*np.argwhere(lab[iy]==1)[0].tolist())
  if background is None and ((lab[iy]==2)&(a[iy]<0)).any():background=(iy,*np.argwhere((lab[iy]==2)&(a[iy]<0))[0].tolist())
  if body is None and ((lab[iy]==0)&(a[iy]>=0)&(a[iy]<15)).any():body=(iy,*np.argwhere((lab[iy]==0)&(a[iy]>=0)&(a[iy]<15))[0].tolist())
  source=np.zeros((400,328),bool);source[8:392,4:324]=ctx['occ'][(iy+300)//4].repeat(4,0).repeat(4,1);m=source&(a[iy]<0)&(old[iy]<0)&((iy+300+.5)*PITCH>=ctx['ridge']-ctx['slope']*abs(X)[:,None]-.1875)
  if above is None and m.any():above=(iy,*np.argwhere(m)[0].tolist())
 require(all(p is not None for p in (restored,above,background,body)),'Missing real mutation fixture');oldvalue=int(a[restored]);bodyvalue=int(a[body]);blade=(int(np.flatnonzero(a[:,restored[1],restored[2]]>=0)[-1])+1,restored[1],restored[2]);require(blade[0]<148 and a[blade]<0,'Missing above-roof blade cell');del a,old,lab;gc.collect()
 change_cell('restore_outside_original_occupied_source',(4,0,0),3,1)
 change_cell('restore_above_existing_backing_plane',above,3,1)
 change_cell('restore_top_blade',blade,oldvalue,1)
 change_cell('source_background_as_foreground',background,3)
 change_cell('other_body_material_change',body,(bodyvalue+1)%15)
 change_cell('restored_source_wrong_material',restored,(oldvalue+1)%15)
 def bad_plan(name,mutate):
  p=copy.deepcopy(plan);mutate(p);reject(name,lambda:source_proof(p,master))
 def bad_master(name,mutate):
  m=copy.deepcopy(master);mutate(m);reject(name,lambda:source_proof(plan,m))
 bad_plan('observed_tile_source_boundary_shift',lambda p:p['tile_source_links'][0]['horizontal_footprint_xz'].__setitem__(0,p['tile_source_links'][0]['horizontal_footprint_xz'][0]-.03125))
 bad_plan('edge_wrong_source_pixel',lambda p:p['edge_source_links'][0]['source_pixel_uv'].__setitem__(0,p['edge_source_links'][0]['source_pixel_uv'][0]+1))
 bad_plan('restore_support_plane_expansion',lambda p:p.__setitem__('backing_bottom_offset_m',-.125))
 def hidden(m):
  o=copy.deepcopy(m['components'][0]['operations'][0]);o['id']='unobserved_under_occluder';o['transform']['translation']=[4.5,12.,-3.];m['components'][0]['operations'].append(o)
 bad_master('hidden_occluder_fill',hidden)
 bad_master('wrong_shadow_material',lambda m:m['components'][0]['operations'][0].__setitem__('material','top_tile_05' if m['components'][0]['operations'][0]['material']!='top_tile_05' else 'top_tile_04'))
 bad_master('thickened_or_brightness_driven_roof',lambda m:m['components'][0]['operations'][0]['shape']['polygon'][0].__setitem__(1,-.125))
 bad_master('source_crop_expansion',lambda m:m['components'][0]['operations'][1]['shape']['max'].__setitem__(0,m['components'][0]['operations'][1]['shape']['max'][0]-.03125))
 tests.update(surface_tests());require(all(sha(ROOT/p)==h for p,h in before.items()),'Input mutation persisted')
 report={'schema':'riverstone.roof_repair_r03.adversarial_validation.v1','status':'PASS','negative_tests':tests,'negative_tests_count':len(tests),'actual_cell_fixture_coordinates_yxz':{'restored':restored,'above_plane':above,'top_blade':blade,'source_background':background,'other_body':body},'all_mutations_in_memory_only':True,'source_files_unchanged':True,'sampling_calls':0,'mesher_calls':0,'address_space_limit_mib':256,'cpu_limit_seconds':60,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-t,'validator':ref(Path(__file__))}
 save(HERE/'adversarial_validation.json',report);print(json.dumps(report,sort_keys=True))
if __name__=='__main__':main()
