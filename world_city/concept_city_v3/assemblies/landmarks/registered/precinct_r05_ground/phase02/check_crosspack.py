from author_plan import *
def main():
 a=load(HERE/'resolved_placements.json');idx=geo._SpatialIndex(8);hits=[]
 for i,r in enumerate(a['actual_bearing_footprints']):
  for j in idx.candidates(r['polygon_xz_m']):
   q=a['actual_bearing_footprints'][j]
   if r['placement_id']==q['placement_id']:continue
   ar=geo.intersection_area(r['polygon_xz_m'],q['polygon_xz_m'])
   if ar>1e-8:hits.append({'a':r['id'],'b':q['id'],'area_m2':ar})
  idx.add(i,r['polygon_xz_m'])
 write(HERE/'new_native_crosspack_tests.json',{'pack':ref(HERE/'resolved_placements.json'),'different_placement_soil_bearing_contacts':hits,'all_pass':not hits,'method':'Exact convex intersection of every native soil-bearing piece across distinct new placement IDs.'});print('hits',hits[:10]);assert not hits
if __name__=='__main__':main()
