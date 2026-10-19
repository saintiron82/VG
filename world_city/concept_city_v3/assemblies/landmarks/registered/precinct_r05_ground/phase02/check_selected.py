from search_stair_fit import *
def main():
 data=load(HERE/'stair_fit_candidates.json');acc=load(HERE/'accessible_stair_candidates.json');h=load(HERE/'baseline_study.json')['holdings'][0];cut=DomainCut([{'polygon_xz_m':p}for p in h['polygon_parts_xz_m']]);scene=f.load_scene();idx=f.SurfaceIndex(scene,[h['bounds_xz_m']],margin=5);out=[]
 for c0 in acc['candidates'][:12]:
  for collar in[1.2,1.5,1.8,2.1]:
   c=dict(c0);d=c['inward_direction_xz'];origin=[c['road_edge_xz_m'][j]+d[j]*collar for j in(0,1)];p=local_rect(origin,d,3,c['total_source_length_m']);outside=sum(geo.polygon_area(q)for q in cut.subtract(p));hits=[{'id':r['id'],'area_m2':geo.intersection_area(p,r['polygon_xz_m'])}for r in data['native_support_reservations']if geo.positive_area_overlap(p,r['polygon_xz_m'],0)];clips=list(idx.cover(p));ys=[idx.height(r,*v)for r in clips for v in r['intersection_polygon_xz_m']];u=[-d[1],d[0]];edge_samples=[]
   for t in[-1.2,0,1.2]:
    q=[c['road_edge_xz_m'][j]+u[j]*t for j in(0,1)];rows=idx.at(*q);edge_samples.append({'xz_m':q,'y_m':max([idx.height(r,*q)for r in rows],default=None)})
   row={'riser_count':c['riser_count'],'collar_length_m':collar,'outside_area_m2':outside,'native_hits':hits,'support_uncovered_m2':geo.polygon_area(p)-sum(geo.polygon_area(r['intersection_polygon_xz_m'])for r in clips),'ground_range_m':[min(ys),max(ys)],'road_edge_samples':edge_samples,'maximum_collar_grade':max(abs(v['y_m']-c['lower_landing_y_m'])/collar for v in edge_samples),'candidate':dict(c,lower_landing_outer_edge_xz_m=origin,polygon_xz_m=p,upper_landing_xz_m=[origin[j]+d[j]*c['total_source_length_m']for j in(0,1)],collar_length_m=collar)};out.append(row)
 write(HERE/'selected_fit_review.json',{'rows':out});print([{k:v for k,v in r.items()if k!='candidate'}for r in out])
if __name__=='__main__':main()
