"""Apply only at an idle compiler boundary, then run native regression tests."""
from pathlib import Path
p=Path(__file__).with_name('layered_compile.py');s=p.read_text()
if 'self.instance_bounds={}' not in s:
    s=s.replace('self.items=[];paint_bounds=[]','self.items=[];paint_bounds=[];self.instance_bounds={}')
    s=s.replace('            self.items.append((instance,component,t,ops))',"            self.instance_bounds[instance['id']]=([min(o[3][j] for o in ops) for j in range(3)],[max(o[4][j] for o in ops) for j in range(3)]) if ops else None\n            self.items.append((instance,component,t,ops))")
    needle='        for instance,component,t,ops in self.items:\n            retained='
    s=s.replace(needle,"        for instance,component,t,ops in self.items:\n            span=self.instance_bounds[instance['id']]\n            if span is None or any(span[1][j]<=world_lo[j] or span[0][j]>=world_hi[j] for j in range(3)):continue\n            retained=")
if 'import chunk_enumeration' not in s:
    s=s.replace('import render_only_retention','import render_only_retention\nimport chunk_enumeration')
    s=s.replace("    chunk_count=math.prod(len(r) for r in starts)","    chunk_plan=chunk_enumeration.enumerate_paint_chunks(fine_source,origin,edge,a.core.EPS)\n    owned_lows=chunk_plan.pop('owned_lows');chunk_count=len(owned_lows)\n    wall_limit=rules.get('wall_time_limit_seconds',900)\n    a.fail(type(wall_limit)is int and 0<wall_limit<=1800,'layer_wall_time_limit_contract')")
    s=s.replace("header['storage_mode']='render_only_transient_cells' if render_only else 'retained_layered_cells'", "header['storage_mode']='render_only_transient_cells' if render_only else 'retained_layered_cells'\n    header['chunk_enumeration_sha256']=a.sha(chunk_enumeration.__file__)\n    header['chunk_enumeration']=chunk_plan")
    s=s.replace('signal.alarm(900)','signal.alarm(wall_limit)')
    s=s.replace('enumerate(itertools.product(*starts))','enumerate(owned_lows)')
    s=s.replace("'wall_time_limit_seconds':900", "'wall_time_limit_seconds':wall_limit,'chunk_enumeration':chunk_plan")
    s=s.replace("'polygon_crop_guard':polygon_crop_guard.__file__,'retention':render_only_retention.__file__,", "'polygon_crop_guard':polygon_crop_guard.__file__,'retention':render_only_retention.__file__,'chunk_enumeration':chunk_enumeration.__file__,")
p.write_text(s)
