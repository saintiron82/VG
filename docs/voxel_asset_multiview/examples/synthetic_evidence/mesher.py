"""Greedy surface mesher for sparse rigid voxel parts; no image processing."""
def greedy_faces(voxels):
 cells={(int(x),int(y),int(z)):c for x,y,z,c in voxels};planes={}
 for p,color in cells.items():
  for axis in range(3):
   u=(axis+1)%3;v=(axis+2)%3
   for sign in (-1,1):
    q=list(p);q[axis]+=sign
    if tuple(q) in cells:continue
    key=(axis,sign,p[axis]+(sign>0),color)
    planes.setdefault(key,set()).add((p[u],p[v]))
 faces=[]
 for (axis,sign,plane,color),mask in sorted(planes.items()):
  while mask:
   a,b=min(mask,key=lambda t:(t[1],t[0]));w=1
   while (a+w,b) in mask:w+=1
   h=1
   while all((a+x,b+h) in mask for x in range(w)):h+=1
   for j in range(h):
    for i in range(w):mask.remove((a+i,b+j))
   corners=[]
   for uu,vv in [(a,b),(a+w,b),(a+w,b+h),(a,b+h)]:
    p=[0,0,0];p[axis]=plane;p[(axis+1)%3]=uu;p[(axis+2)%3]=vv;corners.append(p)
   if sign<0:corners.reverse()
   faces.append((corners,color))
 return faces
