"""Prueba de «Recuperar mi historial» con GitHub simulado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, PLANTACION, TMP, BASE
import io, json, sys, time, zipfile, re
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)

def geo(jid, usuario, evaluador, fecha, labor='corte', fotos=None):
    h = {'id': jid, 'evaluador': evaluador, 'usuario': usuario, 'fecha': fecha, 'inicio': fecha + 'T13:00:00.000Z', 'fin': fecha + 'T20:00:00.000Z',
         'km': 4.2, 'palmas_visitadas': 300, 'ha_recorridas': 2.5, 'por_lote': [{'lote': 'IT01'}], 'lotes_seleccionados': [{'lote': 'IT01'}],
         'secuencias': [], 'tiempos': {}, 'archivo_fotos': (jid + '_fotos.zip') if fotos else None, 'sincronizado': fecha + 'T21:00:00.000Z', 'labor': labor}
    pt = {'type': 'Point', 'coordinates': [-78.7, 1.7]}
    feats = [{'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[-78.7, 1.7], [-78.701, 1.701]]},
              'properties': {'tipo': 'recorrido', 'tiempos': [h['inicio'], fecha + 'T13:01:00.000Z'], 'precision_m': [4, 5]}},
             {'type': 'Feature', 'geometry': pt,
              'properties': {'tipo': 'parada', 'n': 1, 'inicio': h['inicio'], 'fin': fecha + 'T13:10:00.000Z', 'duracion_min': 10, 'lote': 'IT01', 'clase': 'pausa'}}]
    if labor == 'alce':   # Alce: acopios del sendero, sin registros de palma
        h.update({'acopios_alzados': 1, 'racimos_alzados': 6})
        feats.append({'type': 'Feature', 'geometry': pt, 'properties': {'tipo': 'alce', 'jornada_id': jid, 'labor': 'alce', 'evaluador': evaluador, 'n': 1, 'racimos': 6,
                      't_ini': h['inicio'], 't_fin': h['inicio'], 'hora': '08:00', 'lote': 'IT01', 'precision_m': 3, 'fuente': 'nfc'}})
    else:
        pas = [{'c': 'R', 'f': 'nfc', 't': h['inicio']}] * 3
        feats.append({'type': 'Feature', 'geometry': pt, 'properties': {'tipo': 'diagnostico', 'id': 'R-' + jid, 'jornada_id': jid, 'palma_id': 'P1', 'lote': 'IT01', 'linea': 3, 'palma': 14,
                      'creado': h['inicio'], 'evaluador': evaluador, 'estado': 'cosecha', 'n1_codigo': 'R', 'nivel1': '3R', 'problemas': 'R', 'labor': labor, 'racimos': 3,
                      'fuente': 'nfc', 'pasadas': pas, 'transitabilidad': 'Transitable', 'observaciones': 'ok',
                      'fotos': '|'.join(f + '.jpg' for f in (fotos or [])), 'sincronizado': h['sincronizado']}})
        # Registro de una versión anterior (labor genérica «cosecha», solo el resumen): se toma como Corte
        feats.append({'type': 'Feature', 'geometry': pt, 'properties': {'tipo': 'diagnostico', 'id': 'V-' + jid, 'jornada_id': jid, 'palma_id': 'P2', 'lote': 'IT01', 'linea': 3, 'palma': 15,
                      'creado': h['inicio'], 'evaluador': evaluador, 'n1_codigo': 'R', 'nivel1': '2R', 'labor': 'cosecha', 'racimos': 2, 'fotos': '', 'sincronizado': h['sincronizado']}})
        if labor == 'recoleccion':
            h.update({'viajes': 1, 'racimos_descargados': 5})
            feats.append({'type': 'Feature', 'geometry': pt, 'properties': {'tipo': 'descargue', 'jornada_id': jid, 'labor': labor, 'evaluador': evaluador, 'n': 1, 'racimos': 5,
                          't': h['inicio'], 'hora': '08:00', 'lote': 'IT01', 'precision_m': 3, 'fuente': 'nfc'}})
    return json.dumps({'type': 'FeatureCollection', 'jornada': h, 'features': feats})

zb = io.BytesIO()
with zipfile.ZipFile(zb, 'w') as z: z.writestr('F1.jpg', b'\xff\xd8\xff\xe0FOTO1'); z.writestr('F2.jpg', b'\xff\xd8\xff\xe0FOTO2')
BLOBS = {'b1': geo('J1', 'op1', 'Operario Uno', '2026-11-10', labor='recoleccion', fotos=['F1', 'F2']).encode(), 'z1': zb.getvalue(),
         'b2': geo('J2', '', 'Operario Uno', '2026-11-11', labor='alce').encode(),
         'b3': geo('J3', 'op1', 'Operario Uno', '2026-11-12').encode(),
         'b4': geo('J4', 'op9', 'Otro Señor', '2026-11-12').encode()}
COMMITS = [
    {'sha': 'c1', 'commit': {'message': 'Cosecha · Operario Uno · jornada 2026-11-10 · 2 registro(s) · u:op1'}},
    {'sha': 'c2', 'commit': {'message': 'Cosecha · Operario Uno · jornada 2026-11-11 · alce'}},
    {'sha': 'c3', 'commit': {'message': 'Cosecha · Operario Uno · jornada 2026-11-12 · 2 registro(s) · u:op1'}},
    {'sha': 'c4', 'commit': {'message': 'Cosecha · Otro Señor · jornada 2026-11-12 · 2 registro(s) · u:op9'}},
    {'sha': 'c5', 'commit': {'message': 'Actualiza programación de cosecha'}}]
FILES = {'c1': [{'filename': 'jornadas/2026-11-10/J1.geojson', 'sha': 'b1', 'status': 'added'}, {'filename': 'jornadas/2026-11-10/J1_fotos.zip', 'sha': 'z1', 'status': 'added'}],
         'c2': [{'filename': 'jornadas/2026-11-11/J2.geojson', 'sha': 'b2', 'status': 'added'}],
         'c3': [{'filename': 'jornadas/2026-11-12/J3.geojson', 'sha': 'b3', 'status': 'added'}],
         'c4': [{'filename': 'jornadas/2026-11-12/J4.geojson', 'sha': 'b4', 'status': 'added'}]}
pedidos = []
def gh(route):
    u = route.request.url; pedidos.append(u.split('/repos/')[-1])
    m = re.search(r'/commits\?', u)
    if m:
        page = int(re.search(r'[?&]page=(\d+)', u).group(1))
        return route.fulfill(status=200, content_type='application/json', body=json.dumps(COMMITS if page == 1 else []))
    m = re.search(r'/commits/(\w+)$', u)
    if m: return route.fulfill(status=200, content_type='application/json', body=json.dumps({'sha': m.group(1), 'files': FILES.get(m.group(1), [])}))
    m = re.search(r'/git/blobs/(\w+)$', u)
    if m: return route.fulfill(status=200, content_type='application/octet-stream', body=BLOBS[m.group(1)])
    route.fulfill(status=404, body='{}')

errores = []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)+' '+(e.stack or '')[:400]))
    pg.on('console', lambda m: m.type == 'error' and errores.append('console: ' + m.text))
    pg.on('dialog', lambda d: d.dismiss())
    ctx.route('https://api.github.com/**', gh)
    pg.goto(BASE + '/index.html')
    pg.wait_for_function("typeof S!=='undefined'&&typeof dbPut==='function'", timeout=30000); time.sleep(2)
    pg.evaluate("""async()=>{document.querySelector('#login').hidden=true;
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};S.cfg.gh={...S.cfg.gh,token:'tok'};S.cfg.evaluador='Operario Uno';
      await dbPut('jornadas',{id:'J3',estado:'finalizada',sync:'sincronizado',evaluador:'Operario Uno',usuario:'op1',inicio:'2026-11-12T13:00:00.000Z',fin:'2026-11-12T20:00:00.000Z',km:9.9,local:true});
      panelHistorial();document.querySelector('#hDesde').value='2026-11-01';document.querySelector('#hHasta').value='2026-11-13';}""")
    pg.click('#hIr')
    pg.wait_for_function("(document.querySelector('#hMsg')||{}).textContent && !document.querySelector('#hIr').disabled", timeout=30000)
    msg = pg.evaluate("document.querySelector('#hMsg').textContent")
    check('Mensaje final', 'recuperada' in msg, msg)
    r = pg.evaluate("""async()=>{const js=Object.fromEntries((await dbAll('jornadas')).map(j=>[j.id,{sync:j.sync,imp:!!j.importada,km:j.km,labor:j.labor||null,par:(j.paradas||[]).length,D:(j.descargues||[]).length,A:(j.alces||[]).length}]));
      const rs=(await dbAll('registros')).map(r=>({id:r.id,j:r.jornada_id,sync:r.sync,fotos:r.fotos,r:r.racimos,lab:r.labor,n1:r.n1,cod:r.n1_codigo,f:r.fuente,pas:(r.pasadas||[]).length}));
      const fs=(await dbAll('fotos')).map(f=>f.id);const t1=(await puntosTrack('J1')).length;
      const pend=(await jornadasPorSincronizar()).map(j=>j.id);return {js,rs,fs,t1,pend};}""")
    js = r['js']
    check('J1 (u:op1, Recolección) importada con su labor, fotos y recorrido', js.get('J1', {}).get('imp') and js['J1']['labor'] == 'recoleccion' and sorted(r['fs']) == ['F1', 'F2'] and r['t1'] == 2 and js['J1']['par'] == 1, (js.get('J1'), r['fs'], r['t1']))
    check('J1: conserva el descargue (D) del viaje', js.get('J1', {}).get('D') == 1, js.get('J1'))
    check('J2 (Alce, solo por nombre) importada con su labor', js.get('J2', {}).get('imp') and js['J2']['labor'] == 'alce', js.get('J2'))
    check('J2: conserva el acopio alzado', js.get('J2', {}).get('A') == 1, js.get('J2'))
    check('J3 local no se sobrescribe', js['J3']['km'] == 9.9 and not js['J3']['imp'], js['J3'])
    check('J4 de otro usuario no se importa', 'J4' not in js)
    check('Commit de otro usuario no se consulta', not any('/commits/c4' in x for x in pedidos) and not any('/commits/c5' in x for x in pedidos))
    check('Registros importados quedan sincronizados (2 de J1; el Alce no tiene registros de palma)', all(x['sync'] == 'sincronizado' for x in r['rs']) and sorted(x['id'] for x in r['rs']) == ['R-J1', 'V-J1'], r['rs'])
    rj = {x['id']: x for x in r['rs']}
    check('Racimos, labor, fuente, pasadas y fotos se reconstruyen', rj.get('R-J1', {}).get('r') == 3 and rj['R-J1']['lab'] == 'recoleccion' and rj['R-J1']['n1'] == '3R'
          and rj['R-J1']['cod'] == 'R' and rj['R-J1']['f'] == 'nfc' and rj['R-J1']['pas'] == 3 and rj['R-J1']['fotos'] == ['F1', 'F2'], rj.get('R-J1'))
    check('Registro de la versión anterior (labor «cosecha»): se toma como Corte', rj.get('V-J1', {}).get('lab') == 'corte' and rj['V-J1']['r'] == 2 and rj['V-J1']['n1'] == '2R', rj.get('V-J1'))
    check('Importadas no se vuelven a enviar', r['pend'] == [], r['pend'])
    ro = pg.evaluate("""async()=>{const r=S.registros.find(x=>x.id==='R-J1');await abrirFormulario(r);return {sl:!!document.querySelector('#frm fieldset[disabled]'),tit:document.querySelector('#hojaTitulo').textContent,mini:document.querySelectorAll('#fotos img').length};}""")
    check('Registro importado se abre en solo lectura con sus fotos', ro['sl'] and ro['mini'] == 2, ro)
    # Segunda vez: no duplica
    pg.evaluate("panelHistorial();document.querySelector('#hDesde').value='2026-11-01';")
    pg.click('#hIr'); pg.wait_for_function("(document.querySelector('#hMsg')||{}).textContent && !document.querySelector('#hIr').disabled", timeout=30000)
    msg2 = pg.evaluate("document.querySelector('#hMsg').textContent")
    check('Segunda descarga: ya estaban', 'ya estaban' in msg2, msg2)
    pg.evaluate("cerrarHoja()")
    for v in ('diag','res','jor'):
        try:
            pg.evaluate(f"abrirBD('{v}')"); time.sleep(1.2)
        except Exception as e: errores.append(f'abrirBD {v}: {e}')
    txt = pg.evaluate("document.querySelector('#bd')?document.querySelector('#bd').innerText:''")
    check('Pantallas de datos abren con jornadas importadas', 'J1' in txt or '2026-11-10' in txt or 'IT01' in txt, txt[:120])
    pg.evaluate("abrirBD('jor')"); time.sleep(1.5)
    nc = pg.evaluate("document.querySelectorAll('#bdCuerpo .jor-card').length")
    check('Recorridos: aparecen las 3 jornadas (incluido el Alce importado)', nc == 3, nc)
    pg.evaluate("document.querySelector('#bdCuerpo [data-play=\"J1\"]').click()"); time.sleep(1.5)
    pl = pg.evaluate("({on:PLAY.on,vis:!document.querySelector('#play').hidden,sub:document.querySelector('#plSub').textContent})")
    check('Reproducir recorrido de jornada importada', pl['on'] and pl['vis'], pl['sub'])
    pg.evaluate("detenerPlay&&detenerPlay()")
    check('Barra plegada tiene HA', pg.evaluate("!!document.querySelector('#pjMini #pjMiniHa')"))
    check('Sin errores de JavaScript', not errores, errores[:5])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
