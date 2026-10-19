"""Reuse the exact CPU common-quad rasterizer; no appearance edits."""
from pathlib import Path
import importlib.util,sys,json,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'r07';spec=importlib.util.spec_from_file_location('shared_cpu_render',ROOT/'tools/render_compiled.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer);renderer.ROOT=OUT
for aid in sys.argv[1:]:
 used=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
 if used+1200000>10*1024**2:raise RuntimeError('r07 additional 10MiB budget would be exceeded')
 views=[renderer.render(aid,0,0,'voxel_front'),renderer.render(aid,math.radians(40),math.radians(8),'voxel_three_quarter'),renderer.render(aid,math.radians(90),0,'voxel_side'),renderer.render(aid,math.pi,0,'voxel_rear')];(OUT/'generated'/aid/'voxel_render_provenance.json').write_text(json.dumps(views,indent=2)+'\n')
