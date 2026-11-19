"""Hoja de vida de la palma con registros de cosecha: App (en la ficha de la palma, sin internet, oculta en auditoría) y
visor (ventana con el archivo central más lo cargado, sin duplicados, filtro «Con racimos (R)» y foto). GitHub simulado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, BASE
import sys, json, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)
HV = {'formato': 'cosecha-hoja-vida-1', 'lote': 'IT01', 'generado': '2026-11-16T10:00:00+00:00', 'palmas': {
  '501': {'lote': 'IT01', 'linea': '3', 'palma': '7', 'll': [1.5, -78.7], 'ev': [
    {'t': '2026-09-01T13:00:00Z', 'l': 'censo', 'x': '4R', 'n1': 'R', 'q': 'GOMEZ PEREZ ANDRES', 'id': 'd1'},
    {'t': '2026-10-20T13:00:00Z', 'l': 'censo', 'x': '1R', 'n1': 'R', 'q': 'TORRES ELVIS', 'id': 'd0'},
    {'t': '2026-11-10T13:00:00Z', 'l': 'censo', 'x': '3R', 'n1': 'R', 'q': 'LOPEZ DIAZ CARLOS', 'id': 'd2', 'f': 'jornadas/2026-11-10/J9_fotos.zip|f9.jpg'}]},
  '502': {'lote': 'IT01', 'linea': '4', 'palma': '2', 'll': [1.5002, -78.7], 'ev': [
    {'t': '2026-11-11T13:00:00Z', 'l': 'novedad', 'x': 'Sin registro', 'n1': '', 'q': 'LOPEZ DIAZ CARLOS', 'id': 'd5'}]}}}
IND = {'formato': 'cosecha-hoja-vida-1', 'generado': 'x', 'lotes': {'IT01': {'archivo': 'IT01.json', 'palmas': 2, 'eventos': 4, 'generado': HV['generado']}}}
def gh(route):
    u = route.request.url
    if 'palmas/hoja_vida/IT01.json' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps(HV))
    if 'palmas/hoja_vida/indice.json' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps(IND))
    route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')
errores = []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 1300, 'height': 900})
    ctx.route('https://api.github.com/**', gh)
    # ---------------- Visor ----------------
    vz = ctx.new_page(); vz.on('pageerror', lambda e: errores.append('visor: ' + str(e)[:200]))
    vz.goto(BASE + '/visor.html'); vz.wait_for_function("typeof hojaVidaVisor==='function'", timeout=30000); time.sleep(1)
    vz.evaluate("""()=>{document.querySelector('#login').hidden=true;document.querySelector('#app').hidden=false;mapa.invalidateSize();
      SES={u:'an1',nombre:'ANALISTA',rol:'analista',token:'tok',repo:{owner:'didpalmares',repo:'CosechaData',rama:'main'}};
      const j={id:'J9',ruta:'2026-11-16/J10.geojson',fecha:'2026-11-16',evaluador:'MORA RUIZ JAVIER',usuario:'op3',inicio:'2026-11-16T12:00:00Z',fin:'2026-11-16T13:00:00Z',hora_inicio:'07:00',hora_fin:'08:00',duracion_min:60,km:1,ha:1,palmas:10,metodo:'calle',
        n_paradas:0,min_paradas:0,min_mov:60,por_lote:[],densidad:115,app:'',lotes:new Set(['IT01']),paradas:[],track:null,header:{},secuencias:null,tiempos:{},vel:2,transito:[],diags:[]};
      const d=(id,h,x)=>normPol({tipo:'diagnostico',id,palma_id:'501',lote:'IT01',linea:3,palma:7,labor:'corte',...x,creado:h,lat:1.5,lng:-78.7,evaluador:'MORA RUIZ JAVIER',n_fotos:0,transitabilidad:'Transitable',fuente:'nfc'});
      j.diags=[d('d2','2026-11-10T13:00:00Z',{racimos:3}),d('d3','2026-11-16T12:30:00Z',{racimos:2})];
      JOR=[j];document.querySelector('#fDesde').value='2026-11-16';document.querySelector('#fHasta').value='2026-11-16';aplicarFiltros(true);window.__J=j;}""")
    # La ficha y la hoja de vida usan fuentePol (visor.html): si fallan, el resto de la prueba sigue
    try:
        vz.evaluate("popupDiag({...__J.diags[1],_j:__J})")
        vz.wait_for_selector('.ppHist', timeout=5000); check('Visor: botón «📋 Hoja de vida» en la ficha', 'Hoja de vida' in vz.inner_text('.ppHist'))
        vz.click('.ppHist')
    except Exception as e:
        check('Visor: botón «📋 Hoja de vida» en la ficha', False, str(e).splitlines()[0])
        try: vz.evaluate("verHistoriaPalma({...__J.diags[1],_j:__J})")
        except Exception as e2: print('     ', str(e2).splitlines()[0])
    try: vz.wait_for_selector('#hvCuerpo .ev', timeout=8000)
    except Exception as e: print('      sin hoja de vida:', str(e).splitlines()[0])
    T = vz.inner_text('#hvCuerpo'); n = vz.evaluate("document.querySelectorAll('#hvCuerpo .ev').length")
    check('Visor: une el archivo central con lo cargado sin duplicar (4 registros)', n == 4 and T.count('3R') == 1, n)
    check('Visor: el registro cargado trae transitabilidad y fuente', 'Transitabilidad: Transitable' in T and 'Fuente: Tarjeta NFC' in T, T[:300])
    orden = vz.evaluate("[...document.querySelectorAll('#hvCuerpo .ev b')].map(b=>b.innerText)")
    check('Visor: lo más reciente primero y el último registro manda', bool(orden) and orden[0] == 'Cosecha' and '2R' in vz.inner_text('#hvCuerpo .est') and 'Último registro' in vz.inner_text('#hvCuerpo .est'), orden)
    check('Visor: sin textos de diagnóstico', 'iagnóstico' not in T and 'Censo' not in T)
    check('Visor: registro con foto tiene «Ver foto»', vz.evaluate("document.querySelectorAll('#hvCuerpo [data-hvf]').length") == 1)
    check('Visor: la vista incluye el mapa con la palma marcada', vz.evaluate("!!HVP.mapa&&document.querySelector('#hvMapa .leaflet-container, #hvMapa.leaflet-container')!==null&&!!HVP.sel"))
    vz.evaluate("document.querySelector('#hvX').click()"); check('Visor: se cierra', vz.evaluate("document.querySelector('#hvPanel').hidden"))
    # Botón de la cabecera: lista por lote, filtros y mapa
    orden = vz.evaluate("[...document.querySelectorAll('header button')].map(b=>b.id).filter(Boolean)")
    check('Visor: botón 📋 HOJA DE VIDA en la cabecera', 'btHV' in orden and 'HOJA DE VIDA' in vz.inner_text('#btHV'), orden)
    vz.click('#btHV')
    try: vz.wait_for_selector('#hvLista .it', timeout=8000)
    except Exception as e: print('      sin lista:', str(e).splitlines()[0])
    li = [x.splitlines()[0] for x in vz.evaluate("[...document.querySelectorAll('#hvLista .it')].map(e=>e.innerText)")]
    check('Visor: lista las palmas con hoja de vida del lote', len(li) == 2 and 'L3' in li[0] and 'P7' in li[0], li)
    check('Visor: el mapa muestra las palmas', vz.evaluate("HVP.capa.getLayers().length") > 0)
    fil = vz.evaluate("[...document.querySelectorAll('#hvFil .chipf')].map(b=>b.dataset.f+':'+b.innerText)")
    check('Visor: filtros Todas y «Con racimos (R)» (sin críticas ni recuperación)', fil == ['todas:Todas', 'nap:Con racimos (R)'], fil)
    vz.click('#hvFil [data-f=nap]'); vz.wait_for_timeout(300)
    li = vz.evaluate("[...document.querySelectorAll('#hvLista .it')].map(e=>e.innerText)")
    check('Visor: filtro «Con racimos (R)» (último registro con R) deja solo la palma L3 P7', len(li) == 1 and 'L3' in li[0] and 'P7' in li[0], li)
    vz.click('#hvFil [data-f=todas]'); vz.wait_for_timeout(300); vz.fill('#hvQ', '3 9'); vz.wait_for_timeout(300)
    check('Visor: búsqueda por línea y palma', vz.evaluate("document.querySelectorAll('#hvLista .it').length") == 0)
    vz.fill('#hvQ', '3 7'); vz.wait_for_timeout(300); vz.evaluate("(document.querySelector('#hvLista .it')||{click(){}}).click()"); vz.wait_for_timeout(300)
    check('Visor: al elegir la palma muestra su hoja de vida', vz.evaluate("document.querySelectorAll('#hvCuerpo .ev').length") == 4)
    vz.click('#btGer'); vz.wait_for_timeout(200)
    check('Visor: otro botón de la cabecera cierra la vista', vz.evaluate("document.querySelector('#hvPanel').hidden"))
    vz.evaluate("alternarGerencia(false)")
    # Palma sin hoja de vida
    try: vz.evaluate("verHistoriaPalma({palma_id:'999',lote:'IT01',linea:1,palma:1,lat:1.5,lng:-78.7})")
    except Exception as e: print('     ', str(e).splitlines()[0])
    vz.wait_for_timeout(500)
    check('Visor: palma sin registros ni novedades no tiene hoja de vida', 'no tiene hoja de vida' in vz.inner_text('#hvCuerpo'))
    # ---------------- App ----------------
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errores.append('app: ' + str(e)[:200])); pg.on('dialog', lambda d: d.dismiss())
    pg.goto(BASE + '/index.html'); pg.wait_for_function("typeof mostrarHojaVida==='function'", timeout=30000); time.sleep(2)
    r = pg.evaluate("""async()=>{document.querySelector('#login').hidden=true;SES={u:'op1',nombre:'Operario',rol:'operario'};S.cfg.gh={...S.cfg.gh,token:'tok',owner:'didpalmares',repo:'CosechaData',rama:'main'};
      await cargarHojaVida();
      for(const [id,lin,num] of [['501','3','7'],['503','3','8']])S.idx.set(id,{type:'Feature',geometry:{type:'Point',coordinates:[-78.7,1.5]},properties:{_id:id,_lote:'IT01',_linea:lin,_num:num}});
      abrirPalma('501');await new Promise(r=>setTimeout(r,600));const c=document.querySelector('#hojaCuerpo');
      const hv=c.querySelector('.hv');const res={hay:!!hv,txt:hv?hv.innerText:'',n:hv?hv.querySelectorAll('.ev').length:0};
      cerrarHoja&&cerrarHoja();abrirPalma('503');await new Promise(r=>setTimeout(r,500));res.sinHV=!document.querySelector('#hojaCuerpo .hv');
      HV.mem.clear();Object.defineProperty(navigator,'onLine',{get:()=>false,configurable:true});
      cerrarHoja&&cerrarHoja();abrirPalma('501');await new Promise(r=>setTimeout(r,500));res.offline=!!document.querySelector('#hojaCuerpo .hv');
      Object.defineProperty(navigator,'onLine',{get:()=>true,configurable:true});
      AUD.ids=new Set(['501']);AUD.m={id:'A1',palmas:[]};cerrarHoja&&cerrarHoja();abrirPalma('501');await new Promise(r=>setTimeout(r,500));res.aud=!document.querySelector('#hojaCuerpo .hv');
      return res;}""")
    check('App: la ficha de la palma muestra la hoja de vida con todos los registros', r['hay'] and r['n'] == 3 and 'GOMEZ' in r['txt'] and '3R' in r['txt'] and 'Cosecha' in r['txt'], r['txt'][:200])
    check('App: «Último registro» y número de registros', 'Último registro' in r['txt'] and 'Registros: 3' in r['txt'], r['txt'][:200])
    check('App: palma sin novedades no muestra hoja de vida', r['sinHV'])
    check('App: funciona sin internet (copia guardada)', r['offline'])
    check('App: oculta en palmas de auditoría', r['aud'])
    check('Sin errores de JavaScript', not errores, errores[:4])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
