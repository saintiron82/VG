"""Encode the timestamped actual Godot frames, with explicitly labelled3x speed."""
from pathlib import Path
import json,hashlib,subprocess
C=Path(__file__).resolve().parents[2];E=C/'evidence/visual_drawbridge_operation_r03'
d=json.loads((E/'runtime.json').read_bytes());fs=d['video_frames'];assert fs and all(f['error']==0 for f in fs);assert d['bridge_fixture_record']['state']=='ROAD_OPEN' and d['bridge_fixture_record']['complete'] and not d['bridge_fixture_record']['halt_reason'];assert (E/'exit.txt').read_text().strip()=='0'
start=fs[0]['time_ms'];end=d['operation_events'][-1]['record']['time_ms'];lines=['ffconcat version 1.0']
for i,f in enumerate(fs):
 p=Path(f['path']);assert p.is_file();nxt=fs[i+1]['time_ms'] if i+1<len(fs) else max(end,f['time_ms']+200);dur=(nxt-f['time_ms'])/1000;assert dur>0
 lines+=['file '+str(p),'option framerate 1000','duration '+str(dur)]
last=E/'operation_road_restored.png';lines+=['file '+str(last),'option framerate 1000','duration 3','file '+str(last),'option framerate 1000'];(E/'capture.ffconcat').write_text('\n'.join(lines)+'\n')
filters=['setpts=PTS/3','scale=1280:-2','fps=24','drawbox=x=0:y=0:w=iw:h=76:color=black@0.70:t=fill',"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Actual Godot capture - 3x speed - guarded test scene':x=18:y=12:fontsize=21:fontcolor=white"]
labels={'ROAD_OPEN':'Road restored; navigation admission closed','ROAD_DRAIN':'Road admission closed; waiting for pedestrian to leave','LIFTING':'Span clear; road barriers locked; lifting leaves','NAVIGATION_OPEN':'Full rigged vessel admitted through the open span','NAVIGATION_DRAIN':'No new vessel admission; waiting for complete rig exit','LOWERING':'Vessel fully outside; restoring road deck','ROAD_BARRIERS_OPENING':'Deck restored; opening road barriers'}
segments=[]
for f in fs:
 t=(f['time_ms']-start)/3000;s=f['state']
 if not segments or segments[-1][2]!=s:segments.append([t,t,s])
 segments[-1][1]=t
for i,(a,b,s) in enumerate(segments):
 b=segments[i+1][0] if i+1<len(segments) else (end-start)/3000+1
 label=labels.get(s,s.replace('_',' ').capitalize());filters.append("drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='"+label+"':x=18:y=43:fontsize=20:fontcolor=white:enable='between(t,"+str(a)+","+str(b)+")'")
filters += ["drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Yellow capsule and orange cart are test actors. City-wide NPC registration is pending.':x=18:y=h-30:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.65"]
cmd=['ffmpeg','-y','-f','concat','-safe','0','-i',str(E/'capture.ffconcat'),'-vf',','.join(filters),'-an','-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(E/'bridge_guarded_cycle_3x.mp4')]
with (E/'encode.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();record={'source':'Actual Godot gl_compatibility / llvmpipe viewport frames','frame_count':len(fs),'first_capture_ms':start,'last_capture_ms':fs[-1]['time_ms'],'encoding_speed_multiplier':3,'source_real_span_s':(end-start)/1000,'file':str(E/'bridge_guarded_cycle_3x.mp4'),'sha256':sha(E/'bridge_guarded_cycle_3x.mp4'),'bytes':(E/'bridge_guarded_cycle_3x.mp4').stat().st_size,'runtime_sha256':sha(E/'runtime.json'),'scene_sha256':sha(E/'scene.json'),'no_generated_or_interpolated_game_geometry':True,'retained_source_frames':True,'limits':['Closed-world registered actor fixture only; city-wide NPC/navigation not complete.','No moving-native-bridge collider or structural/hydraulic certification.','Surrounding focused scene predates the new southern road.']};(E/'video_evidence.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
