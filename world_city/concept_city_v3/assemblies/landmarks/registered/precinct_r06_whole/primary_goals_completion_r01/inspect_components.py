from find_branches import *
from scipy.ndimage import label,distance_transform_edt
out=[]
for group in ['castle','cathedral','monastery']:
 r=load(O/(group+'_branch_search_r03.json'));gr=np.load(O/(group+'_branch_grid_r03.npz'));a=gr['clear'];xs,zs=gr['xs'],gr['zs'];labs,n=label(a);end=r['selected_exterior_standing_xz_m'];ei=(round((end[1]-zs[0])/.25),round((end[0]-xs[0])/.25));cl=labs[ei];component=labs==cl;coords=np.argwhere(component);print(group,'end component',cl,len(coords),'bounds',xs[coords[:,1].min()],zs[coords[:,0].min()],xs[coords[:,1].max()],zs[coords[:,0].max()]);dist,inds=distance_transform_edt(~component,return_indices=True);other=a&~component;iz,ix=np.unravel_index(np.argmin(np.where(other,dist,np.inf)),a.shape);zz,xx=inds[:,iz,ix];gap=[[float(xs[xx]),float(zs[zz])],[float(xs[ix]),float(zs[iz])]];print('nearest other',gap,'gap',dist[iz,ix]*.25,'label',labs[iz,ix]);out.append(dict(group=group,screen_nearest_gap_xz_m=gap,screen_gap_m=float(dist[iz,ix]*.25),terminal_component_pixels=len(coords)))
write('component_gap_diagnostic.json',dict(rows=out))
