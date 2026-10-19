from finish_pack import *
def cells_from_faces(mesh,pitch):
 events=collections.defaultdict(list)
 for g in mesh['groups']:
  for q in g['quads']:
   if not all(abs(v[1]-q[0][1])<1e-8 for v in q):continue
   sign=face_y_normal(q)
   if abs(sign)<1e-9:continue
   lo=[round(min(v[j]for v in q)/pitch)for j in (0,2)];hi=[round(max(v[j]for v in q)/pitch)for j in (0,2)];y=round(q[0][1]/pitch)
   for x in range(lo[0],hi[0]):
    for z in range(lo[1],hi[1]):events[x,z].append((y,1 if sign<0 else -1))
 cells=set()
 for (x,z),ev in events.items():
  depth=0;previous=None
  for y,ds in sorted(ev):
   if depth>0 and previous is not None:
    for yy in range(previous,y):cells.add((x,yy,z))
   depth+=ds;previous=y
  assert depth==0
 assert len(cells)==mesh['cell_count'],(len(cells),mesh['cell_count'])
 return cells

def components(cells,neighbors):
 rest=set(cells);sizes=[]
 while rest:
  seed=rest.pop();queue=[seed];n=0
  while queue:
   x,y,z=queue.pop();n+=1
   for dx,dy,dz in neighbors:
    q=x+dx,y+dy,z+dz
    if q in rest:rest.remove(q);queue.append(q)
  sizes.append(n)
 return sorted(sizes,reverse=True)
def main():
 pack=load(HERE/'resolved_placements.json');rows=[]
 for asset in pack['assets'][:3]:
  mesh=load(ROOT/asset['cache']['path']);p=asset['pitch_m'];cells=cells_from_faces(mesh,p);f6=components(cells,[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]);f26=components(cells,[(x,y,z)for x in[-1,0,1]for y in[-1,0,1]for z in[-1,0,1]if(x,y,z)!=(0,0,0)]);rows.append({'asset_id':asset['id'],'native_cell_count':len(cells),'face_connected_component_sizes':f6,'corner_connected_component_sizes':f26,'edge_or_corner_only_connection':len(f6)!=len(f26),'voxel_count_matches_native_cache':True})
 write(HERE/'volume_connectivity_tests.json',{'pack':ref(HERE/'resolved_placements.json'),'rows':rows,'all_pass':all(not r['edge_or_corner_only_connection']for r in rows),'method':'Reconstruct exact vertical occupied intervals from outward horizontal cache faces, verify native cell count, then compare6-neighbor face components against26-neighbor edge/corner components. Separate source boundary spans and gates are allowed; edge-only joins are not.'});print(rows)
if __name__=='__main__':main()
