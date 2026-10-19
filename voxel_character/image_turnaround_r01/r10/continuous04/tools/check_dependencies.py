from continuous_pilot import *
p=read(BASE/'data/pilot_priors.json');m=load_measurement();checks={}
for dep in m['dependencies']:
    bad=copy.deepcopy(m);next(d for d in bad['dependencies'] if d['role']==dep['role'])['sha256']='0'*64
    try:build_from_measurement(bad,SOURCE,p);checks[dep['role']]=False
    except ValueError:checks[dep['role']]=True
badpixels=SOURCE.copy();badpixels[0,0]=0
try:build_from_measurement(m,badpixels,p);checks['different_pixels_rejected']=False
except ValueError:checks['different_pixels_rejected']=True
print(json.dumps(checks));assert all(checks.values())
