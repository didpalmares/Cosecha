"""Inicio gráfico de la jornada (labor y zona con dibujos), lote automático por GPS (se activan las palmas del lote al entrar),
aviso de lote fuera de la zona y sin preguntas de transitabilidad. GitHub simulado; cartografía ficticia."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, BASE
import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else BASE + '/index.html'
CAPTURA = _os.environ.get('CAPTURA_INICIO', '')
errores, dialogos = [], []
ok = True

def check(nombre, cond, extra=''):
    global ok
    print(('OK   ' if cond else 'FALLA') + ' ' + nombre + (' · ' + str(extra) if extra != '' else ''))
    ok = ok and bool(cond)

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    ctx.add_init_script(INIT_VOZ)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('console', lambda m: m.type == 'error' and '404' not in m.text and errores.append('console: ' + m.text))
    pg.on('dialog', lambda d: (dialogos.append(d.message), d.accept()))
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined' && typeof abrirInicioCosecha==='function'", timeout=30000)
    time.sleep(1.5)

    # Tres lotes cuadrados de 100 m: A1 y A2 en la zona Z1, B1 en la Z2. Palmas cada 9 m sobre la línea 1 de cada lote.
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario',labores:['corte','recoleccion']};
      const lg=document.getElementById('login');if(lg)lg.hidden=true;
      const m=1/111320,x0=-78.7,y0=1.7;window.__m=m;
      const cuad=(nom,zona,dx)=>{const a=x0+dx*m,b=y0,c=a+100*m,d=b+100*m;
        return {type:'Feature',_caja:[a,b,c,d],properties:{_lote:nom,Lote:nom,ZonaCosecha:zona,Programa:'TT'},geometry:{type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]}};};
      S.lotes={type:'FeatureCollection',features:[cuad('A1','Z1',0),cuad('A2','Z1',110),cuad('B1','Z2',220)]};
      CARTO.lotes={A1:{n:10},A2:{n:10},B1:{n:10}};
      const chunk=(dx,pref)=>Array.from({length:10},(_,i)=>[pref+(i+1),1,i+1,1,x0+(dx+50)*m,y0+(5+i*9)*m]);
      const CH={A1:chunk(0,'a'),A2:chunk(110,'b'),B1:chunk(220,'c')};
      leerChunk=async l=>CH[l]||[];
      window.__gps=(dx,dy)=>{S.gps={lat:y0+dy*m,lng:x0+dx*m,acc:4,t:Date.now()};};
      __gps(50,5);
    }""")

    # ---------- Pantalla de inicio ----------
    pg.evaluate("abrirInicioCosecha()")
    pg.wait_for_selector('#iniLab [data-lab]')
    if CAPTURA:
        time.sleep(.8); pg.screenshot(path=CAPTURA.replace('.png','_0.png'))
        print('cubre:', pg.evaluate("(()=>{const b=document.querySelector('#iniLab [data-lab=recoleccion]').getBoundingClientRect();const e=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return e?(e.id||e.className||e.tagName):null})()"))
    labs = pg.eval_on_selector_all('#iniLab [data-lab]', 'bs=>bs.map(b=>[b.dataset.lab,b.textContent.trim(),!!b.querySelector("svg")])')
    check('Inicio: una tarjeta con dibujo y nombre por cada labor del usuario', [x[0] for x in labs] == ['corte', 'recoleccion'] and all(x[2] for x in labs)
          and 'CORTE' in labs[0][1] and 'palín' in labs[0][1] and 'RECOLECCIÓN' in labs[1][1] and 'búfalo' in labs[1][1].lower(), labs)
    zonas = pg.eval_on_selector_all('#iniZona [data-zona]', 'bs=>bs.map(b=>[b.dataset.zona,b.textContent.trim(),!!b.querySelector("svg polygon")])')
    check('Inicio: zonas Z1 y Z2 con su mapa y número de lotes', [z[0] for z in zonas] == ['Z1', 'Z2'] and all(z[2] for z in zonas)
          and 'ZONA 1' in zonas[0][1] and '2 lotes' in zonas[0][1], zonas)
    check('Inicio: la voz pide labor y zona', any('labor' in d.lower() for d in pg.evaluate("window.__dichos||[]")))
    pg.evaluate("S.zonaSel='';document.querySelectorAll('#iniZona .on').forEach(b=>b.classList.remove('on'))")
    pg.eval_on_selector('#iniLab [data-lab="recoleccion"]','b=>b.click()')
    check('Sin zona elegida no se puede iniciar', pg.evaluate("$('#iniOk').disabled"))
    pg.eval_on_selector('#iniZona [data-zona="Z1"]','b=>b.click()')
    check('Labor y zona marcadas', pg.evaluate("S.laborSel==='recoleccion'&&S.zonaSel==='Z1'&&!$('#iniOk').disabled"))
    if CAPTURA:
        pg.screenshot(path=CAPTURA, full_page=False)
    pg.evaluate("motivoNoIniciar=()=>''")
    pg.eval_on_selector('#iniOk','b=>b.click()')
    pg.wait_for_function("!!S.jornada", timeout=8000)
    j = pg.evaluate("({labor:S.jornada.labor,zona:S.jornada.zona})")
    check('Jornada iniciada con la labor y la zona elegidas', j == {'labor': 'recoleccion', 'zona': 'Z1'}, j)

    # ---------- Lote automático ----------
    pg.evaluate("revisarLoteGPS()"); time.sleep(.6)
    sel = pg.evaluate("S.jornada.seleccion.map(x=>x.lote)")
    check('Al estar dentro de A1, el lote se agrega solo y sus palmas se activan', sel == ['A1'] and pg.evaluate("S.palmas&&S.palmas.features.length") == 10, sel)
    check('Sin preguntar transitabilidad (no se abre ninguna hoja)', pg.is_hidden('#hoja') or 'Transitabilidad' not in (pg.text_content('#hojaTitulo') or ''))
    tr = pg.evaluate("S.jornada.transito")
    check('Tramo de A1 abierto con su hora, sin transitabilidad', len(tr) == 1 and tr[0]['lote'] == 'A1' and tr[0]['entrada'] == '' and tr[0]['t_entrada'], tr)
    check('Aviso grande y por voz del lote', any('Lote' in d for d in pg.evaluate("window.__dichos||[]")))
    pg.evaluate("void(window.__p=sumarCodigo('R','boton'))"); pg.evaluate("window.__p"); time.sleep(.2)
    check('R en A1 se registra en la palma más cercana', pg.evaluate("S.registros.filter(r=>r.lote==='A1').length") == 1)

    pg.evaluate("__gps(160,5)"); pg.evaluate("void(window.__p=sumarCodigo('R','nfc'))"); pg.evaluate("window.__p"); time.sleep(.4)
    sel = pg.evaluate("S.jornada.seleccion.map(x=>x.lote)")
    tr = pg.evaluate("S.jornada.transito")
    check('Al pasar a A2: se agrega, se cierra A1 y se abre A2', sel == ['A1', 'A2'] and tr[0]['t_salida'] and tr[1]['lote'] == 'A2' and not tr[1]['t_salida'], tr)
    check('R en A2 se registra sin preguntas', pg.evaluate("S.registros.filter(r=>r.lote==='A2').length") == 1)

    pg.evaluate("__gps(270,5)"); pg.evaluate("revisarLoteGPS()"); time.sleep(.6)
    sel = pg.evaluate("S.jornada.seleccion")
    check('Lote de otra zona (B1): se agrega marcado fuera de zona', sel[-1]['lote'] == 'B1' and sel[-1].get('fuera_zona') is True, sel[-1])
    check('Aviso «no es de su zona»', any('no es de su zona' in d for d in pg.evaluate("window.__dichos||[]")))

    if CAPTURA:
        pg.evaluate("__gps(160,5);pintarPolBar()"); time.sleep(4); pg.evaluate("cerrarHoja()"); time.sleep(.6); pg.screenshot(path=CAPTURA.replace('.png','_barra.png'))
    check('Barra con el dibujo de la labor y los botones con dibujo', pg.evaluate("!!document.querySelector('#polInfo .pol-lab svg')&&!!document.querySelector('#polBar [data-c=R] svg')&&!!document.querySelector('#polD svg')"))
    check('Sin botón «Finalizar lote»', pg.is_hidden('#polFin'))
    check('Exportación con la zona', pg.evaluate("geoJornada(S.jornada,[],[],new Date().toISOString(),null).jornada.zona") == 'Z1')
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
