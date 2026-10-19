"""Publication metadata omitted."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
W, H = (1536, 1024)
im = Image.new('RGB', (W, H), '#fffdf7')
d = ImageDraw.Draw(im)
fontpath = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font = ImageFont.truetype(fontpath, 17)
small = ImageFont.truetype(fontpath, 10)
names = [('front', 'FRONT +Z', 12, 14, 0, 0), ('right', 'RIGHT +X', 10, 14, 1, 0), ('back', 'BACK -Z', 12, 14, 2, 0), ('left', 'LEFT -X', 10, 14, 0, 1), ('top', 'TOP +Y', 12, 10, 1, 1), ('bottom', 'BOTTOM -Y', 12, 10, 2, 1)]
views = {}
fiducials = []
for n, label, wm, hm, col, row in names:
    x0 = col * 512 + (512 - int(wm * 32)) // 2
    y1 = row * 512 + 496
    y0 = y1 - int(hm * 32)
    x1 = x0 + int(wm * 32)
    d.rectangle((col * 512 + 1, row * 512 + 1, col * 512 + 510, row * 512 + 510), outline='#687177', width=1)
    d.text((col * 512 + 18, row * 512 + 12), label, font=font, fill='#24313d')
    d.text((col * 512 + 240, row * 512 + 16), '1 cell = 0.125 m | 32 px/m', font=small, fill='#24313d')
    for x in range(x0, x1 + 1, 4):
        d.line((x, y0, x, y1), fill='#b8c2c6' if (x - x0) % 32 == 0 else '#e1e6e4', width=1)
    for y in range(y0, y1 + 1, 4):
        d.line((x0, y, x1, y), fill='#b8c2c6' if (y1 - y) % 32 == 0 else '#e1e6e4', width=1)
    d.rectangle((x0, y0, x1, y1), outline='#34434c', width=1)
    for i, (x, y, color) in enumerate([(x0 - 8, y0 - 8, '#e719a0'), (x1 + 8, y0 - 8, '#13baee'), (x0 - 8, y1 + 6, '#6acb16'), (x1 + 8, y1 + 6, '#ff7816')]):
        d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=color)
        fiducials.append({'id': n + '_' + str(i), 'center_px': [x, y], 'rgb': list(Image.new('RGB', (1, 1), color).getpixel((0, 0)))})
    views[n] = {'label': label, 'grid_bounds_px': [x0, y0, x1, y1], 'span_m': [wm, hm], 'pixels_per_meter': 32, 'cell_size_m': 0.125, 'cell_size_px': 4, 'mapping': 'u=(pixel_x-x0)/32-width/2; v=(y1-pixel_y)/32', 'projection_axes': {'front': ['+X', '+Y'], 'back': ['-X', '+Y'], 'right': ['-Z', '+Y'], 'left': ['+Z', '+Y'], 'top': ['+X', '-Z'], 'bottom': ['+X', '+Z']}[n]}
path = HERE / 'blank_six_view_grid.png'
im.save(path)
metadata = {'schema': 'riverstone.six_view_grid_template.v1', 'canvas_px': [W, H], 'template': {'path': str(path.name), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, 'views': views, 'registration_fiducials': fiducials, 'planned_dimensions_m': {'width': 12, 'depth': 10, 'height': 14}, 'planned_scale_not_photo_measurement': True, 'grid_cell_m': 0.125, 'planned_height_planes_m': {'foundation_top': 0.5, 'gallery_1': 3.5, 'gallery_2': 6.5, 'eaves': 9.5, 'ridge': 13.5, 'chimney_max': 14}, 'tolerances': {'canvas_exact': True, 'fiducial_max_error_px': 2, 'required_visible_fiducials': 24, 'no_unregistered_warp': True}, 'missing_depth': 'Gallery cavities/wall thickness/support depth need explicit measured side or annotated semantic-depth constraints.'}
(HERE / 'template.json').write_text(json.dumps(metadata, indent=2) + '\n')
print(metadata['template'])
print('24 exact fiducials, 6 same-scale views, template only')
