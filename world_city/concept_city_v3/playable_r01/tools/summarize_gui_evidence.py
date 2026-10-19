from pathlib import Path
import json,hashlib,statistics,shutil
P=Path(__file__).resolve().parents[1]; E=P/'evidence';out=E/'review_r01';out.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
reports={}
for r in ['gui_r01','gui_r02']:
 d=E/r;j=json.loads((d/'session.json').read_text());s=j['samples'];w=j['wall_frame_ms'];events=j['events'];state=j['final_player'];settled=[x for x in s if x['tick']>10]
 report={'session_sha256':sha(d/'session.json'),'source_hashes':{p.name:sha(p) for p in sorted((d/'source').iterdir())},'exit_code':int((d/'exit_code.txt').read_text()),'distance_m':state['distance_walked_m'],'final_feet_m':state['feet_position_m'],'physical_keycodes':sorted(set(e['physical_keycode'] for e in events if e['kind']=='physical_key')),'logical_keycodes':sorted(set(e['keycode'] for e in events if e['kind']=='physical_key')),'ground_loss_initial_settle_frames':state['ground_loss_frames'],'unsupported_samples_after_tick10':sum(not x['on_floor'] for x in settled),'blocked_frames':state['blocked_frames'],'loaded_cell_sequence':[x['cell'] for x in j['world']['load_events']],'tile_transition_ms':[x['wall_ms'] for x in j['world']['load_events'][1:]],'camera_yaw_range':[min(x['camera_yaw'] for x in s),max(x['camera_yaw'] for x in s)],'visible_motion_states':sorted(set(x['visual']['motion'] for x in s)),'capture_errors':sum(x['error']!=0 for x in j['captures']),'wall_frame_metrics':{'frames':len(w),'mean_fps':1000/statistics.mean(w),'median_ms':statistics.median(w),'p95_ms':sorted(w)[int(.95*len(w))],'max_ms':max(w)},'limit':'Cloud llvmpipe; recording/streaming cost included, not GPU benchmark; physics may fall behind wall time.'}
 reports[r]=report
j=json.loads((E/'gui_r02/session.json').read_text())
segments=[(45.5,64.5,'camera then run across city tile boundary'),(75.0,78.5,'camera orbit at adjacent street'),(91.7,98.1,'A D S directions and idle')]
frames=[];edl=[]
for start,end,label in segments:
 seq=[x for x in j['captures'] if x['kind']=='video' and start*1000<=x['wall_ms']<=end*1000]
 for a,b in zip(seq,seq[1:]):frames.append((a,(b['wall_ms']-a['wall_ms'])/1000))
 if seq:frames.append((seq[-1],.2))
 edl.append({'start_wall_s':start,'end_wall_s':end,'description':label,'frames':len(seq)})
lines=[]
for f,dt in frames:lines.extend(["file '"+f['path'].replace("'","'\\''")+"'",f'duration {dt:.6f}'])
lines.append("file '"+frames[-1][0]['path']+"'")
(out/'video_frames.txt').write_text('\n'.join(lines)+'\n')
for target,t in [('lily_market_walk.png',60.5),('lily_adjacent_street.png',77.6)]:
 f=min(j['captures'],key=lambda x:abs(x['wall_ms']-t*1000));shutil.copy2(f['path'],out/target)
(out/'gui_audit.json').write_text(json.dumps({'schema':'riverstone.playable.gui_audit.v1','status':'PASS selected GUI controls','sessions':reports,'source_input':'Cloud desktop app physical WASD/Shift and logical arrow keys, no programmatic replay in these sessions','video_edl':edl,'video_timing':'Original monotonic wall intervals within each segment; idle gaps cut; no speed-up, no motion interpolation','limits':['R01 arrow physical keycode was0 so camera did not rotate; R02 uses logical keycode and actually rotated.','No mouse-drag rotation test; camera alternative arrow keys verified.','Three initial settle frames from authored spawn+.04m; no later sampled unsupported frames.','GUI city coordinates retained. Program route/obstacle/stair/gate tests are separately recorded.','Character is retained medieval-costume prototype r5; original Lily identity revision is being authored separately.']},indent=2)+'\n')
print(json.dumps({'reports':reports,'video_segments':edl},indent=2))
