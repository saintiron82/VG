"""Read-only semantic rectangular-window inventory for the 50 active house types."""
import collections,json,re,sys
from pathlib import Path
from revise_windows import load,rect
import adapter as a
HERE=Path(__file__).resolve().parent;H=HERE.parent

def run():
    paths=[H/'generated/active_catalog.json',H.parent/'house_extensions/generated/active_catalog.json'];catalog={r['asset_key']:r for p in paths for r in load(p)['assets']};assets=[];total=0
    for key,record in sorted(catalog.items()):
        source=load(a.ROOT/record['source_master_path']);rows=[];pending=[];posts=[]
        for c in source['components']:
            ops={o['id']:o for o in c['operations']}
            for op in ops.values():
                if re.fullmatch(r'(post|timber_post)_[0-9]+',op['id']) and op['shape']['kind']=='box':
                    lo,hi=rect(op);posts.append({'component':c['id'],'operation':op['id'],'width_m':hi[0]-lo[0],'part':op['part']})
                if op['action']!='cut' or not re.fullmatch(r'(window_[0-9]+|shop_opening|work_bay)_aperture',op['id']):continue
                base=op['id'][:-9];required=[base+s for s in ('_glass','_left','_right','_sill','_lintel')]
                if any(n not in ops for n in required) or any(ops[n]['shape']['kind']!='box' for n in required) or op['shape']['kind']!='box':
                    pending.append({'component':c['id'],'aperture':op['id'],'reason':'unsupported_frame_glass_association_or_shape'});continue
                lo,hi=rect(op);l,r,b,t=[rect(ops[base+s]) for s in ('_left','_right','_sill','_lintel')];clear=[r[0][0]-l[1][0],t[0][1]-b[1][1]];span=[hi[0]-lo[0],hi[1]-lo[1]]
                rows.append({'component':c['id'],'aperture':op['id'],'aperture_span_m':span,'frame_face_width_m':l[1][0]-l[0][0],'frame_clear_span_m':clear,'glass_aperture_ratio_after_frame':max(0,clear[0])*max(0,clear[1])/(span[0]*span[1]),'operations':required})
        total+=len(rows);assets.append({'asset_key':key,'source_master_path':record['source_master_path'],'source_sha256':record['source_sha256'],'authored_master_path':record.get('emitted_master_path'),'authored_master_sha256':record.get('emitted_master_sha256'),'window_count':len(rows),'supported_rectangular_windows':rows,'structural_posts':posts,'pending_features':pending,'revision_status':'PENDING_COMMON_WINDOW_REVISION' if rows else 'NO_RECOGNIZED_WINDOW_PENDING_SEMANTIC_REVIEW','full_compile_old_proportions':'ON_HOLD'})
    report={'schema':'riverstone.house_window_revision.inventory.v1','active_house_types':len(assets),'types_with_recognized_windows':sum(bool(r['window_count']) for r in assets),'recognized_windows_in_type_sources':total,'actual_city_placement_window_count':None,'assets':assets,'pending_type_count':sum(bool(r['pending_features']) for r in assets),'catalog_inputs':[{'path':str(p.relative_to(a.ROOT)),'sha256':a.sha(p)} for p in paths],'no_source_or_runtime_mutation':True,'full_compile_queue':'STOPPED_BY_LATEST_WINDOW_REVISION_REQUEST'}
    out=HERE/'generated/house_window_inventory.r01.json';a.write(out,report);print(json.dumps({k:v for k,v in report.items() if k!='assets'}))
if __name__=='__main__':run()
