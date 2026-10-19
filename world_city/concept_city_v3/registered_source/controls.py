"""Image-anchored local corrections and explicitly inferred access controls."""
import json,math,hashlib
from pathlib import Path
HERE=Path(__file__).parent;CITY=HERE.parent
SOURCE=CITY/'image_registration/controls.json'
RAW=json.loads(SOURCE.read_text())
MODEL=RAW['camera_model']
def inverse(pixel,y):
 s=MODEL['scale_px_per_m'];t=math.radians(MODEL['yaw_degrees']);e=math.radians(MODEL['elevation_degrees']);cx,cy=MODEL['offset_pixel_xy']
 a=(pixel[0]-cx)/s;b=((pixel[1]-cy)/s+math.cos(e)*y)/math.sin(e)
 return [round(math.cos(t)*a+math.sin(t)*b,6),y,round(-math.sin(t)*a+math.cos(t)*b,6)]
# These image-space corrections use the same visible wall/garden boundaries.
# Shared retaining-wall foot vertices get one common height on both owners.
ESTATE_REFINEMENTS={
 'E1':{'pixels':[[442,139],[518,150],[504,212],[434,216]],'ys':[16]*4,'reason':'Move the inferred west edge east of the visible castle curtain; original E1 trace overlapped the castle.'},
 'E3':{'pixels':[[630,162],[727,174],[716,233],[640,233],[628,237]],'ys':[15,15,12,12,15],'reason':'Shared E3/E6 garden wall foot at image y233 and datum12; E3 interior bench remains15.'},
 'E6':{'pixels':[[640,233],[716,233],[744,225],[770,273],[662,305]],'ys':[12]*5,'reason':'Same shared E3/E6 wall vertices; no duplicate ownership across the visible dividing wall.'},
 'E5':{'pixels':[[519,242],[635,242],[627,305],[523,305],[514,305]],'ys':[13,13,10,10,10],'reason':'Shared E5/E7 garden wall foot at image y305 and datum10; E5 interior bench remains13.'},
 'E7':{'pixels':[[523,305],[627,305],[606,355],[551,379]],'ys':[10]*4,'reason':'Same shared E5/E7 edge; the earlier top triangle was an overlapping occlusion inference.'}}
ROAD_REFINEMENTS={'NOBLE_RISE':{'pixels':[[394,368],[380,321],[380,273],[389,225],[434,220],[466,220]],'reason':'Follow the visible west estate-wall exterior with full-width clearance; the first narrow-edge trace still overlapped E4.'}}
# Authored local connectors are visible-alignment hypotheses, not newly traced
# measurements. Their image coordinates make every adjustment reviewable.
INFERRED=[
 ('WEST_MONASTERY_EDGE',5,[[380,369],[370,444],[414,450],[514,530],[583,632],[529,650]],'Connect west ends around the monastery east enclosure; gate edge is shared with the public lane.'),
 ('CASTLE_APPROACH',6,[[380,369],[365,340],[365,307],[365,262],[311,249]],'Bent military approach on the training-ground edge to castle south gate.'),
 ('NOBLE_PUBLIC_TIE',4,[[394,368],[380,369]],'Short occluded tie between the traced noble rise and upper contour.'),
 ('NORTH_BACK_LANE',4,[[466,220],[508,230],[508,335],[526,389],[551,392],[616,367],[686,326],[757,302],[780,280],[808,212],[817,164],[906,175]],'Estate service lane follows the visible west E5 gap and E7/E6 exterior; the narrower E3/E5 garden seam cannot hold a cart lane.'),
 ('NORTH_WATERKEEPER',4,[[630,153],[716,158],[817,164]],'Northern house/service frontage below the reservoir bank, with an explicit full-width stand-off from E3.'),
 ('RESERVOIR_SERVICE',3,[[716,168],[735,148],[735,128]],'Inferred controlled access through the north wall to the separately enclosed basin.'),
 ('CENTRAL_WEST_RADIAL',5,[[526,403],[474,472],[612,526],[644,614],[650,732]],'Bent mixed-town cross street following the visible housing grain.'),
 ('CIVIC_WEST_APPROACH',5,[[716,399],[745,440],[797,463]],'Occluded civic approach beside the hall complex.'),
 ('MARKET_WEST_EDGE',6,[[797,463],[845,536],[837,536]],'Reserved west market cart edge; exact width is authored.'),
 ('MARKET_EAST_EDGE',6,[[941,453],[1014,472],[1068,505],[999,541],[926,560]],'Reserved east/south market cart edge along the traced open square.'),
 ('MARKET_PROCESSION',7,[[930,530],[935,485],[941,453]],'Civic procession corridor across the square; stall placement must exclude it.'),
 ('SOUTH_MERCHANT_LINK',4,[[737,590],[733,648],[769,719],[789,794]],'Short bent route through southern merchant blocks to the wall service lane.'),
 ('EAST_RADIAL',5,[[1213,392],[1195,468],[1229,616],[1270,693],[1282,747]],'Craft cross street; canal crossing must receive an explicit bridge.'),
 ('POOR_NORTH_CROSS',3.4,[[1195,468],[1293,505],[1412,520]],'Connected upper poor-quarter lane within the visible street grain.'),
 ('POOR_SOUTH_CROSS',3.2,[[1229,616],[1326,606],[1416,590]],'Lower poor-quarter short cross lane and shared-workcourt access.'),
 ('EAST_WALL_SERVICE',4,[[1341,430],[1390,452],[1412,520],[1416,590],[1379,672],[1322,735],[1248,770],[1125,789],[1019,798],[952,811]],'Narrow connected wall service route following the visible curved southeast frontage.'),
 ('SOUTH_WALL_SERVICE',4,[[529,650],[546,704],[650,732],[789,794],[952,811]],'Curved inner wall service route; it is separate from the external working quay.'),
 ('PORT_BRIDGE_TIE',6,[[925,841],[958,854]],'Short external quay tie at the bridge north landing.'),
 ('CLERGY_EAST_GATE',4,[[1341,430],[1365,385],[1378,354]],'Clergy service gate connection at the east enclosure.')]

def build_controls():
 data={'schema':'riverstone.registered_source.controls.v1','source_registration_path':str(SOURCE.relative_to(HERE.parents[2])),'source_registration_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'roads':[],'estate_edge_refinements':ESTATE_REFINEMENTS,'road_edge_refinements':ROAD_REFINEMENTS}
 for q in RAW['roads']:
  refine=ROAD_REFINEMENTS.get(q['id']);data['roads'].append({'id':q['id'],'registration_control_id':q['id'],'trace_pixel_xy':refine['pixels'] if refine else q['trace_pixel_xy'],'original_trace_pixel_xy':q['trace_pixel_xy'],'width_m':q['design_width_m'],'observed_vs_inferred':refine['reason'] if refine else 'Traced visible street alignment; occluded spans and width remain authored hypotheses.','evidence_kind':'locally_refined_traced_control' if refine else 'traced_control'})
 for identity,width,pixels,reason in INFERRED:
  data['roads'].append({'id':identity,'registration_control_id':None,'trace_pixel_xy':pixels,'width_m':width,'observed_vs_inferred':reason,'evidence_kind':'inferred_image_aligned_connector'})
 return data
if __name__=='__main__':(HERE/'road_controls.json').write_text(json.dumps(build_controls(),indent=2)+'\n')
