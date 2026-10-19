from .. import author as a

def half(subject,u,v,sign,positive=True):
 out=[]
 if not subject:return out
 prev=subject[-1];pd=sign*a.geo._cross(u,v,prev)
 for cur in subject:
  cd=sign*a.geo._cross(u,v,cur);pi=pd>=0 if positive else pd<=0;ci=cd>=0 if positive else cd<=0
  if pi!=ci:
   t=pd/(pd-cd);out.append([prev[k]+t*(cur[k]-prev[k])for k in[0,1]])
  if ci:out.append(list(cur))
  prev,pd=cur,cd
 return out

def clip(subject,mask):
 out=subject;sign=1 if a.geo.signed_polygon_area(mask)>0 else -1
 for u,v in zip(mask,mask[1:]+mask[:1]):
  if u==v:continue
  out=half(out,u,v,sign)
  if not out:break
 return out

def difference(subject,mask):
 inner=subject;out=[];sign=1 if a.geo.signed_polygon_area(mask)>0 else-1
 for u,v in zip(mask,mask[1:]+mask[:1]):
  if u==v:continue
  q=half(inner,u,v,sign,False)
  if a.geo.polygon_area(q)>1e-14:out.append(q)
  inner=half(inner,u,v,sign,True)
  if not inner:break
 return out
