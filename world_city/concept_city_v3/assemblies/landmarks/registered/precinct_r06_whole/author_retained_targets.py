"""Reproducible named-entry target screen; final ownership needs exact graph proof."""
from build_ledger import *
def main():
 profile=CITY/'validation/landmark_recovery_r1/recovered_rendered_profiles_r2.json';d=load(profile)
 parts=[r['polygon_xz_m']for key in ('approaches','landings')for r in d[key]['triangles']if r['group_id']in('castle','cathedral','monastery','castle_public_landing','cathedral_public_landing','monastery_public_landing')]
 target=b.mask(parts);np.savez_compressed(HERE/'retained_target_mask.npz',target=target)
 write('retained_target_source.json',dict(source=ref(profile),groups=['castle','cathedral','monastery'],screen_grid_m2=b.area(target),policy='A conservative target screen only. A final route requires actual R7 full-width support, native-body and bank clearances, and the positive-length XYZ entry graph to a named public road.'))
if __name__=='__main__':main()
