"""Genera los íconos de Cosecha (web, PWA y lanzador de la APK) a partir de src/marca/racimo_simbolo.svg.

Uso: python src/marca/generar_iconos.py      (requiere playwright con Chromium o PW_CANAL=msedge, y pillow)
"""
import io, os, re
from PIL import Image
from playwright.sync_api import sync_playwright

D = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(D))
FONDO = '#0F3D2E'
simb = open(os.path.join(D, 'racimo_simbolo.svg'), encoding='utf-8').read()
cuerpo = re.search(r'<svg[^>]*>(.*)</svg>', simb, re.S).group(1)

def svg(rx, despl, esc, fondo=True):
    bg = f'<rect width="512" height="512" rx="{rx}" fill="{FONDO}"/>' if fondo else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">{bg}'
            f'<g transform="translate({despl} {despl}) scale({esc})">{cuerpo}</g></svg>')

ICONO = svg(112, 56.0, 1.0)            # ícono redondeado (app, visor, lanzador)
MASK = svg(0, 92.0, 0.82)              # maskable: símbolo dentro de la zona segura
FRENTE = svg(0, 112.0, 0.72, False)    # primer plano del ícono adaptable de Android (transparente)
for nombre, txt in (('sv_icono.svg', ICONO), ('sv_maskable.svg', MASK)):
    open(os.path.join(D, nombre), 'w', encoding='utf-8').write(txt)
open(os.path.join(D, 'sv_simbolo.svg'), 'w', encoding='utf-8').write(simb)
open(os.path.join(RAIZ, 'icons', 'sv_icono.svg'), 'w', encoding='utf-8').write(ICONO)

canal = {'channel': os.environ['PW_CANAL']} if os.environ.get('PW_CANAL') else {}
with sync_playwright() as pw:
    nav = pw.chromium.launch(**canal)
    pg = nav.new_page(viewport={'width': 512, 'height': 512})
    def png(txt):
        pg.set_content(f'<html><body style="margin:0;background:transparent">{txt}</body></html>')
        return Image.open(io.BytesIO(pg.locator('svg').screenshot(omit_background=True))).convert('RGBA')
    ico, mask, frente = png(ICONO), png(MASK), png(FRENTE)
    nav.close()

def guardar(im, tam, *rutas):
    r = im.resize((tam, tam), Image.LANCZOS)
    for ruta in rutas:
        os.makedirs(os.path.dirname(ruta), exist_ok=True); r.save(ruta, optimize=True)

for carpeta in (D, os.path.join(RAIZ, 'icons')):
    guardar(ico, 192, os.path.join(carpeta, 'icon-192.png'))
    guardar(ico, 512, os.path.join(carpeta, 'icon-512.png'))
    guardar(mask, 192, os.path.join(carpeta, 'icon-maskable-192.png'))
    guardar(mask, 512, os.path.join(carpeta, 'icon-maskable-512.png'))
    guardar(mask, 180, os.path.join(carpeta, 'apple-touch-icon.png'))

# Lanzador de Android (normal, redondo y adaptable)
redondo = Image.new('RGBA', mask.size, (0, 0, 0, 0))
from PIL import ImageDraw
m = Image.new('L', mask.size, 0); ImageDraw.Draw(m).ellipse((0, 0, mask.size[0] - 1, mask.size[1] - 1), fill=255)
redondo.paste(mask, (0, 0), m)
RES = os.path.join(RAIZ, 'apk', 'android', 'app', 'src', 'main', 'res')
for d, t in (('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)):
    guardar(ico, t, os.path.join(RES, f'mipmap-{d}', 'ic_launcher.png'))
    guardar(redondo, t, os.path.join(RES, f'mipmap-{d}', 'ic_launcher_round.png'))
    guardar(frente, round(t * 2.25), os.path.join(RES, f'mipmap-{d}', 'ic_launcher_foreground.png'))
print('Íconos generados.')

# Pantallas de inicio (splash) de la APK: se reemplaza el ícono anterior por el nuevo, en el mismo lugar y tamaño.
import glob
for ruta in glob.glob(os.path.join(RES, 'drawable*', 'splash.png')):
    im = Image.open(ruta).convert('RGBA'); W, H = im.size; px = im.load(); fondo = px[0, 0]
    xs, ys = [], []
    for y in range(0, int(H * 0.62)):
        for x in range(W):
            r, g, b, a = px[x, y]
            if abs(r - 0x0F) < 10 and abs(g - 0x3D) < 12 and abs(b - 0x2E) < 12: xs.append(x); ys.append(y)
    if not xs: print('sin ícono:', ruta); continue
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys); t = max(x1 - x0, y1 - y0) + 1
    from PIL import ImageDraw as _D
    _D.Draw(im).rectangle((x0 - 2, y0 - 2, x0 + t + 1, y0 + t + 1), fill=fondo)
    nuevo = ico.resize((t, t), Image.LANCZOS); im.alpha_composite(nuevo, (x0, y0))
    im.convert('RGB').save(ruta, optimize=True)
print('Splash actualizados.')
