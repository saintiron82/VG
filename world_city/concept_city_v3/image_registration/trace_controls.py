"""Manual, reviewable controls read from the approved concept pixels.
The SVG is an annotation layer; the supplied raster remains unchanged.
World positions are projection hypotheses, never a claim of exact inversion.
"""
from pathlib import Path
import json,math,hashlib,base64
import numpy as np
from scipy.optimize import least_squares
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]; W,H=1536,1024
IMAGE=ROOT/'world_city/reference/revision_03/city_social_water_concept.png'
# Ground/threshold anchors, not tower spire tips. Elevations remain game design priors.
ANCHORS=[
 ('castle', [310,210],[-300,24,-250],24),('cathedral',[1155,273],[250,14,-230],14),
 ('market',[935,485],[20,4,40],4),('monastery',[310,548],[-270,8,120],8),
 ('reservoir',[735,128],[0,16,-335],16),('south_gate',[950,810],[120,2.2,380],2.2),
 ('port_west',[430,772],[-180,2.2,360],2.2)]
POLYGONS=[
 ('WALL','outer_wall_ground_trace',0,'#f3de59',[[234,112],[411,81],[516,110],[653,151],[753,151],[870,136],[987,117],[1157,89],[1253,145],[1345,211],[1405,292],[1445,381],[1481,500],[1492,605],[1453,701],[1360,776],[1120,822],[936,821],[705,784],[546,753],[361,708],[218,674],[132,577],[85,475],[95,320],[120,234],[180,183]]),
 ('CASTLE','castle_precinct',24,'#ef8d62',[[178,116],[241,83],[403,67],[441,165],[425,221],[311,249],[183,206]]),
 ('TRAIN','exercise_ground',18,'#e9bc79',[[110,247],[209,224],[381,263],[392,310],[278,333],[112,294]]),
 ('NOBLE','contiguous_noble_quarter',12,'#bd87e9',[[428,123],[575,139],[684,158],[761,199],[800,278],[686,310],[567,382],[465,398],[394,368],[375,317],[393,249]]),
 ('CLERGY','cathedral_clergy_precinct',14,'#f3b5e7',[[964,153],[1124,123],[1283,166],[1365,252],[1378,354],[1275,383],[1110,341],[985,289],[947,229]]),
 ('MARKET','market_stalls_and_civic_space',4,'#ffdd65',[[797,463],[855,443],[929,449],[1014,472],[1068,505],[999,541],[926,560],[845,536]]),
 ('MONASTERY','monastery_terraces',8,'#87d394',[[127,429],[279,411],[405,453],[497,528],[562,629],[511,692],[368,707],[210,664],[129,589],[103,511]]),
 ('POOR','poor_craft_canal_quarter',2.5,'#d9a178',[[1074,476],[1170,438],[1347,440],[1438,516],[1456,633],[1405,724],[1290,762],[1132,745],[1008,694],[981,595]]),
 ('PORT','working_river_frontage',2.2,'#9adae5',[[220,674],[361,708],[546,753],[705,784],[936,821],[936,854],[710,855],[515,827],[330,768],[185,716]]),
 ('BASIN','reservoir_water_edge',16,'#5de2ff',[[680,108],[724,94],[773,109],[788,124],[750,143],[698,134]]),
 ('CLOISTER','cathedral_cloister',14,'#dbbcff',[[1165,236],[1275,219],[1325,268],[1288,307],[1170,280]]),
 ('CEMETERY','clergy_burial_ground',14,'#c6d7a4',[[968,209],[1054,192],[1069,259],[1013,285]]),
 ('COMMON','wooded_common',9,'#8be788',[[116,349],[330,384],[352,432],[139,412]])]
ESTATES=[
 ('E1',16,[[423,125],[518,140],[504,212],[408,204]]),
 ('E2',16,[[526,149],[623,162],[617,230],[514,223]]),
 ('E3',15,[[630,162],[727,174],[716,238],[628,237]]),
 ('E4',13,[[397,235],[500,248],[489,322],[389,299]]),
 ('E5',13,[[519,242],[635,242],[627,303],[514,329]]),
 ('E6',12,[[644,229],[744,225],[770,273],[662,305]]),
 ('E7',10,[[523,304],[626,306],[606,355],[551,379]])]
ROADS=[
 ('UPPER_CONTOUR',7,[[380,369],[526,403],[653,348],[757,302],[843,282],[891,313],[955,339],[1066,367],[1213,392],[1341,430]]),
 ('MARKET_CONTOUR',6,[[370,444],[474,472],[604,448],[716,399],[810,374],[892,379],[992,400],[1094,430],[1195,468]]),
 ('LOWER_CONTOUR',5,[[529,650],[644,614],[737,590],[792,550],[837,536],[926,560],[1036,557],[1134,586],[1229,616]]),
 ('SOUTH_MARKET_AXIS',8,[[952,811],[943,768],[928,722],[903,687],[876,638],[876,593],[901,554],[930,530]]),
 ('MARKET_NORTH',6,[[941,453],[927,420],[936,382],[924,350],[897,309],[872,279],[861,233],[882,198],[906,175]]),
 ('CATHEDRAL_APPROACH',6,[[955,339],[984,310],[1014,287],[1054,275]]),
 ('NOBLE_RISE',5,[[394,368],[386,321],[406,273],[432,226],[466,220]]),
 ('PORT_QUAY',8,[[215,702],[360,745],[542,789],[709,818],[925,841]]),
 ('MAIN_BRIDGE',7,[[950,810],[958,854],[971,904],[983,969]])]
WATER=[
 ('SPRING_VISIBLE',2,[[503,3],[501,28],[531,54],[552,75],[608,96],[678,112]],'clean_raw_water_inference'),
 ('NORTHERN_CHANNEL_VISIBLE',2,[[784,120],[832,135],[868,157],[889,185],[906,215],[933,249]],'network_role_not_proven_from_image'),
 ('CRAFT_CANAL_VISIBLE',6,[[930,572],[1004,599],[1104,653],[1207,696],[1282,747],[1340,767]],'industrial_route_hypothesis'),
 ('EAST_CHANNEL_VISIBLE',6,[[1398,448],[1422,486],[1434,529],[1432,567],[1450,598],[1433,666],[1375,733],[1340,767],[1350,814]],'industrial_route_hypothesis'),
 ('RIVER_NORTH_SHORE',90,[[0,680],[185,716],[330,768],[515,827],[710,855],[936,854],[1143,843],[1330,809],[1536,748]],'river_boundary')]
def project(points,p):
 s,yaw,elev,cx,cy=p; q=np.asarray(points,float);x,y,z=q[:,0],q[:,1],q[:,2]
 return np.column_stack([cx+s*(math.cos(yaw)*x-math.sin(yaw)*z),cy+s*(math.sin(elev)*math.sin(yaw)*x-math.cos(elev)*y+math.sin(elev)*math.cos(yaw)*z)])
def fit():
 xyz=[a[2] for a in ANCHORS];uv=np.array([a[1] for a in ANCHORS]); f=lambda p:(project(xyz,p)-uv).ravel()
 result=least_squares(f,[1.4,.05,.7,800,490],bounds=([.5,-1,.25,-1000,-1000],[3,1,1.3,2500,2500]))
 return result.x
P=fit()
def inverse(pixel,y):
 s,theta,elev,cx,cy=P;A=np.array([[s*math.cos(theta),-s*math.sin(theta)],[s*math.sin(elev)*math.sin(theta),s*math.sin(elev)*math.cos(theta)]])
 x,z=np.linalg.solve(A,[pixel[0]-cx,pixel[1]-cy+s*math.cos(elev)*y]);return [round(float(x),4),y,round(float(z),4)]
def record(id,role,y,color,pts):return {'id':id,'role':role,'trace_pixel_xy':pts,'trace_normalized_uv':[[round(x/W,7),round(y/H,7)] for x,y in pts],'world_xyz_m':[inverse(q,y) for q in pts],'assumed_height_m':y,'stroke':color,'evidence':'manual visible image boundary; occluded corners interpolated','world_status':'authored projection inference requiring terrain/access validation'}
def main():
 s,theta,elev,cx,cy=P;pred=project([a[2] for a in ANCHORS],P);anchors=[]
 for (id,uv,world,y),v in zip(ANCHORS,pred):anchors.append({'id':id,'image_pixel_xy':uv,'image_normalized_uv':[uv[0]/W,uv[1]/H],'current_world_xyz_m':world,'current_projected_pixel_xy':v.tolist(),'current_error_px':float(np.linalg.norm(v-uv)),'inferred_target_world_xyz_m':inverse(uv,y),'assumed_height_m':y})
 target=inverse([W/2,H/2],0);direction=[math.cos(elev)*math.sin(theta),math.sin(elev),math.cos(elev)*math.cos(theta)];camera={'position_m':[target[i]+1600*direction[i] for i in range(3)],'target_m':target,'ortho_size_m':H/s,'render_size_px':[W,H]}
 data={'schema':'riverstone.concept_image.registration.v1','source_image':str(IMAGE.relative_to(ROOT)),'source_image_sha256':hashlib.sha256(IMAGE.read_bytes()).hexdigest(),'image_size_px':[W,H],'method':'manual image control traces + five-parameter orthographic camera least-squares fit to existing ground anchors, then inverse XY at explicit assumed Y','limits':['Oblique generated painting is not a calibrated survey or exact single-camera projection.','World polygons and heights are design hypotheses. Occluded ground boundaries are not directly observed.','Water role/flow is not proved by blue pixels; hydraulics must be solved separately.','The first engine comparison keeps current geometry unchanged to expose registration error.'],'camera_model':{'scale_px_per_m':s,'yaw_degrees':math.degrees(theta),'elevation_degrees':math.degrees(elev),'offset_pixel_xy':[cx,cy]},'matched_engine_camera':camera,'anchor_rms_px':float(np.sqrt(np.mean(np.sum((pred-np.array([a[1] for a in ANCHORS]))**2,axis=1)))),'anchors':anchors,'polygons':[record(*v) for v in POLYGONS],'estates':[record(i,'noble_compound',y,'#ff9aff',pts) for i,y,pts in ESTATES],'roads':[dict(record(i,'visible_street_centerline',4,'#ffff89',pts),design_width_m=w) for i,w,pts in ROADS],'water':[dict(record(i,role,16 if i.startswith('SPRING') or i.startswith('NORTHERN') else 0,'#48edff',pts),design_width_m=w) for i,w,pts,role in WATER]}
 (HERE/'controls.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 img=base64.b64encode(IMAGE.read_bytes()).decode();svg=[f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1536" height="1024" viewBox="0 0 1536 1024"><image width="1536" height="1024" xlink:href="data:image/png;base64,{img}"/><style>text{{font-family:DejaVu Sans,sans-serif;font-size:16px;font-weight:bold;paint-order:stroke;stroke:#111;stroke-width:4px;stroke-linejoin:round}}polyline,polygon{{stroke-linejoin:round;stroke-linecap:round}}</style>']
 for v in data['polygons']+data['estates']:
  pts=v['trace_pixel_xy'];ss=' '.join(f'{x},{y}' for x,y in pts);c=v['stroke'];svg.append(f'<polygon points="{ss}" fill="{c}" fill-opacity="0.07" stroke="{c}" stroke-width="3"/>');x,y=pts[0];svg.append(f'<text x="{x+5}" y="{y-7}" fill="{c}">{v["id"]}</text>')
 for v in data['roads']+data['water']:
  pts=v['trace_pixel_xy'];ss=' '.join(f'{x},{y}' for x,y in pts);c=v['stroke'];svg.append(f'<polyline points="{ss}" fill="none" stroke="{c}" stroke-width="3" stroke-dasharray="8 4"/>')
 for a in anchors:
  x,y=a['image_pixel_xy'];svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="#fff" stroke="#111" stroke-width="2"/><text x="{x+12}" y="{y+4}" fill="#fff">{a["id"]}</text>')
 svg.append('</svg>');(HERE/'concept_controls.svg').write_text(''.join(svg));print(json.dumps({'anchor_rms_px':data['anchor_rms_px'],'camera':data['camera_model'],'controls':len(data['polygons'])+len(data['estates'])+len(data['roads'])+len(data['water'])},indent=2))
if __name__=='__main__':main()
