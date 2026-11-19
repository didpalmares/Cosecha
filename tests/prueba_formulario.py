"""Formulario de registro editable (incorporado: una rama R «Racimo»): admin.html → config/ramas.json → App y visor. GitHub simulado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, PLANTACION, TMP, BASE
import sys, time, json, os, base64
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
D = TMP
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)
EST = {'cfg': None, 'sha': None, 'puts': 0, 'offline': False}
def gh(route):
    req = route.request; u = req.url
    if '/contents/config/ramas.json' in u:
        if req.method == 'PUT':
            b = json.loads(req.post_data); EST['cfg'] = json.loads(base64.b64decode(b['content']).decode('utf-8')); EST['puts'] += 1; EST['sha'] = 'sha%d' % EST['puts']
            return route.fulfill(status=200, content_type='application/json', body=json.dumps({'content': {'sha': EST['sha']}}))
        if EST['cfg'] is None or EST['offline']: return route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')
        if 'raw' in (req.headers.get('accept') or ''): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['cfg']))
        return route.fulfill(status=200, content_type='application/json', body=json.dumps({'sha': EST['sha'], 'content': base64.b64encode(json.dumps(EST['cfg']).encode()).decode()}))
    route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')
errores = []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 1300, 'height': 950})
    ctx.route('https://api.github.com/**', gh)
    ad = ctx.new_page(); ad.on('pageerror', lambda e: errores.append('admin: ' + str(e)[:200])); dl = []
    ad.on('dialog', lambda d: (dl.append(d.message), d.accept()))
    ad.goto(BASE + '/admin.html'); ad.wait_for_function("typeof entradaUsuario==='function'", timeout=20000)
    paq = ad.evaluate("""async()=>{const dkRaw=rnd(32),dk=await llaveDatos(dkRaw);
      return {formato:FORMATO,id:'p',creado:'',repo:{owner:'didpalmares',repo:'CosechaData',rama:'main'},kdf:{alg:'PBKDF2-SHA256',iter:ITER},token:await cifrar(dk,enc.encode('github_pat_prueba')),
        carto:{archivo:'carto.enc',version:'v1'},usuarios:[await entradaUsuario(dk,dkRaw,'admin1','Ana Admin','admin','Clave1234',{})]};}""")
    f = os.path.join(D, 'acceso_form.json'); open(f, 'w', encoding='utf-8').write(json.dumps(paq))
    ad.click('#tabs button[data-t=editar]'); ad.set_input_files('#eArchivo', f); ad.fill('#eUser', 'admin1'); ad.fill('#eClave', 'Clave1234'); ad.click('#eAbrir')
    ad.wait_for_selector('#ePanel:not([hidden])', timeout=60000); time.sleep(1)
    check('Sin formulario publicado: muestra «incorporado»', 'incorporado' in ad.inner_text('#rVer'), ad.inner_text('#rVer'))
    ad.click('#rAbrir'); ad.wait_for_selector('#rEditor:not([hidden])', timeout=10000)
    n = ad.evaluate("[...document.querySelectorAll('#rEditor .rEnf')].map(b=>b.querySelector('[data-e=c]').value).join()")
    check('Editor carga el formulario incorporado (una rama: R)', n == 'R', n)
    # Cambios: renombrar R, color de R, nueva enfermedad NEM (tipo novedad) con dos opciones, otra nueva que se elimina, subir NEM
    gi = lambda c: ad.evaluate(f"[...document.querySelectorAll('#rEditor .rEnf')].findIndex(b=>b.querySelector('[data-e=c]').value==='{c}')")
    box = lambda c: f"#rEditor .rEnf[data-g='{gi(c)}']"
    ad.fill(box('R') + ' [data-e=n1]', 'R: RACIMO DE FRUTO')
    ad.evaluate(f"(()=>{{const i=document.querySelector(\"{box('R')} [data-e=color]\");i.value='#123456';}})()")
    ad.click('#rAddE'); time.sleep(.2)
    nb = box('NUEVA')
    ad.fill(nb + ' [data-e=c]', 'NEM'); ad.fill(nb + ' [data-e=n1]', 'Nematodos'); ad.select_option(nb + ' [data-e=tipo]', 'novedad')
    ad.locator(nb + ' [data-k=n2]').fill('CON AGALLAS')
    ad.locator(nb + ' [data-k=s]').fill('Raíces con agallas'); ad.locator(nb + ' [data-k=cir]').uncheck(); ad.locator(nb + ' [data-k=rai]').check()
    ad.click('#rAddE'); time.sleep(.2)
    nb = box('NUEVA'); ad.fill(nb + ' [data-e=c]', 'TMP'); ad.fill(nb + ' [data-e=n1]', 'Temporal')
    ad.click(box('TMP') + ' [data-delg]'); time.sleep(.2)
    ad.click(box('NEM') + ' [data-mov="-1"]'); time.sleep(.15)
    # Validación: opción repetida
    ad.click(box('NEM') + ' [data-addo]'); time.sleep(.2)
    ops = ad.locator(box('NEM') + ' .rOp'); ops.nth(ops.count() - 1).locator('[data-k=n2]').fill('CON AGALLAS')
    ad.click('#rGuardar'); time.sleep(.5)
    check('Valida opciones repetidas', 'repetida' in ad.inner_text('#rMsg') and EST['puts'] == 0, ad.inner_text('#rMsg'))
    ops = ad.locator(box('NEM') + ' .rOp'); ops.nth(ops.count() - 1).locator('[data-k=n2]').fill('SIN AGALLAS')
    ad.click('#rGuardar')
    try: ad.wait_for_function("document.querySelector('#rMsg').textContent.includes('guardado')", timeout=10000)
    except Exception: pass
    check('Guarda el formulario con el código incorporado «R» (1 letra)', EST['puts'] == 1, ad.inner_text('#rMsg'))
    if EST['cfg'] is None:   # sin formulario guardado no se puede seguir con la App ni el visor
        print('RESULTADO: HAY FALLAS'); nav.close(); sys.exit(1)
    c = EST['cfg']; cods = list(dict.fromkeys(x['c'] for x in c['ramas']))
    check('Guarda config/ramas.json en el repositorio de datos', EST['puts'] == 1 and c['formato'] == 'cosecha-ramas-1' and c['version'], c.get('version'))
    check('Cambios guardados: nombre, color, enfermedad nueva con 2 opciones y la eliminada no queda',
          any(x['c'] == 'R' and x['n1'] == 'R: RACIMO DE FRUTO' for x in c['ramas']) and c['enfermedades']['R']['color'] == '#123456'
          and [x.get('n2') for x in c['ramas'] if x['c'] == 'NEM'] == ['CON AGALLAS', 'SIN AGALLAS']
          and any(x['c'] == 'NEM' and x['n1'] == 'NEMATODOS' and x['s'] == ['Raíces con agallas'] and x['rai'] and not x['cir'] for x in c['ramas'])
          and c['enfermedades']['NEM']['tipo'] == 'novedad' and 'TMP' not in cods and 'TMP' not in c['enfermedades'], c['ramas'])
    check('Reordenar: Nematodos subió un puesto', cods == ['NEM', 'R'], cods)
    check('Versión publicada visible', c['version'] in ad.inner_text('#rVer'))
    # ---- App ----
    alertas = []
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errores.append('app: ' + str(e)[:200])); pg.on('dialog', lambda d: (alertas.append(d.message), d.dismiss()))
    pg.goto(BASE + '/index.html'); pg.wait_for_function("typeof cargarRamas==='function'", timeout=30000); time.sleep(2)
    r = pg.evaluate("""async()=>{document.querySelector('#login').hidden=true;SES={u:'op',nombre:'Op',rol:'operario'};S.cfg.gh={...S.cfg.gh,token:'tok',owner:'didpalmares',repo:'CosechaData',rama:'main'};
      const aplicado=await cargarRamas();
      const j={id:'JF',estado:'activa',evaluador:'Op',usuario:'op',labor:'corte',inicio:new Date().toISOString(),seleccion:[{lote:'IT01'}],densidad:115,buffer:5,km:0,sync:'pendiente',
        transito:[{lote:'IT01',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};await dbPut('jornadas',j);S.jornada=j;
      S.idx.set('PF',{type:'Feature',geometry:{type:'Point',coordinates:[-78.7,1.7]},properties:{_id:'PF',_lote:'IT01',_linea:1,_num:1}});S.gps={lat:1.70002,lng:-78.7,acc:4,t:Date.now()};
      await abrirFormulario({palma_id:'PF'});const frm=document.querySelector('#frm');
      const conts=[...frm.querySelectorAll('.pol-cont')].map(x=>x.dataset.k+'='+x.querySelector('b').textContent);
      await guardarRegistro(frm);const vacio=S.registros.some(x=>x.palma_id==='PF');
      frm.querySelector('[data-mas=racimos]').click();frm.querySelector('[data-mas=racimos]').click();
      await guardarRegistro(frm);const reg=S.registros.find(x=>x.palma_id==='PF');
      return {aplicado,conts,vacio,racimos:reg&&reg.racimos,n1:reg&&reg.n1,estado:reg&&reg.estado,color:reg&&colorReg(reg),colorR:COLOR_N1.R,
        prob:PROBLEMAS.find(x=>x.id==='NEM'),probR:PROBLEMAS.find(x=>x.id==='R'),version:S.ramasVersion};}""")
    check('App: aplica el formulario publicado', r['aplicado'] and r['version'] == c['version'], r['version'])
    check('App: el registro de la palma es un solo contador de racimos (R)', r['conts'] == ['racimos=Racimo'], r['conts'])
    check('App: sin racimos no guarda y avisa', not r['vacio'] and 'Registre al menos un racimo (R).' in alertas, alertas)
    check('App: guarda 2R con el color publicado para R', r['racimos'] == 2 and r['n1'] == '2R' and r['estado'] == 'cosecha' and r['colorR'] == '#123456' and r['color'] == '#123456', r)
    check('App: nombres en PROBLEMAS (exportes y filtros)', r['prob'] and r['prob']['n'] == 'Nematodos' and r['probR'] and r['probR']['n'] == 'R: racimo de fruto', (r['prob'], r['probR']))
    EST['offline'] = True
    r2 = pg.evaluate("async()=>{RAMAS.splice(0,RAMAS.length,...RAMAS.filter(x=>x.c!=='NEM'));const a=await cargarRamas();return {a,nem:RAMAS.some(x=>x.c==='NEM')};}")
    check('App: sin conexión usa el formulario guardado', r2['a'] and r2['nem'], r2)
    EST['offline'] = False
    # ---- Visor ----
    vz = ctx.new_page(); vz.on('pageerror', lambda e: errores.append('visor: ' + str(e)[:200]))
    vz.goto(BASE + '/visor.html'); vz.wait_for_function("typeof cargarRamasVisor==='function'", timeout=30000)
    v = vz.evaluate("async()=>{SES={token:'t',repo:{owner:'didpalmares',repo:'CosechaData',rama:'main'}};await cargarRamasVisor();return {n:PROBLEMAS.NEM,c:COLOR_N1.R,r:PROBLEMAS.R};}")
    check('Visor: nombres y colores del formulario', v['n'] == 'Nematodos' and v['c'] == '#123456' and v['r'] == 'R: racimo de fruto', v)
    check('Sin errores de JavaScript ni alertas', not errores, errores[:4])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
