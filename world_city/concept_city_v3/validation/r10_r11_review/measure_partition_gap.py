exec((__import__('pathlib').Path(__file__).parent/'isolate_partition.py').read_text().split("report={'bounds'")[0])
rs=b.surface_domains(bounds,False);box=[[320,304],[336,304],[336,320],[320,320]];parts=[box]
for r in rs:
 clip=tidy(r['polygon_xz_m']);parts=[tidy(t) for p in parts for t in g.convex_difference(tidy(p),clip) if area(t)>1e-10]
print('GAP',sum(area(p) for p in parts),len(parts))
report=dict(bounds=bounds,uncovered_area_m2=sum(area(p) for p in parts),uncovered_polygons_xz_m=parts,method='Subtract every finite owner polygon from the exact16m tile; remove coincident consecutive vertices only, no region expansion or snapping.',r11_author_sha256=sha(pathlib.Path(b.__file__)))
(H/'partition_gap_320_304.json').write_text(json.dumps(report,indent=2)+'\n')
