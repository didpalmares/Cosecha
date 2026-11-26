"""Inicio: sin tarjeta «Corte y recolección»; CORTE + RECOLECCIÓN juntas solo con el PIN del supervisor (si no, se recomienda
una labor). Racimos de la jornada arriba (píldora), marcador del descargue en el mapa y BORRAR TARJETA (Web NFC simulado).
GitHub simulado; cartografía ficticia."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, BASE
import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else BASE + '/index.html'
CAPTURA = _os.environ.get('CAPTURA_INICIO', '')
errores = []
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
    pg.on('dialog', lambda d: d.accept())
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined' && typeof abrirInicioCosecha==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario',labores:['corte','recoleccion','corte_recoleccion','alce']};
      const lg=document.getElementById('login');if(lg)lg.hidden=true;
      const m=1/111320,x0=-78.7,y0=1.7;window.__m=m;
      const cuad=(nom,zona,dx)=>{const a=x0+dx*m,b=y0,c=a+100*m,d=b+100*m;
        return {type:'Feature',properties:{_lote:nom,Lote:nom,ZonaCosecha:zona,Programa:'TT'},geometry:{type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]}};};
      S.lotes={type:'FeatureCollection',features:[cuad('A1','Z1',0)]};CARTO.lotes={A1:{n:10}};
      const CH={A1:Array.from({length:10},(_,i)=>['a'+(i+1),1,i+1,1,x0+50*m,y0+(5+i*9)*m])};leerChunk=async l=>CH[l]||[];
      window.__gps=(dx,dy)=>{S.gps={lat:y0+dy*m,lng:x0+dx*m,acc:4,t:Date.now()};};__gps(50,5);
    }""")

    # ---------- Labores: sin tarjeta combinada ----------
    pg.evaluate("abrirInicioCosecha()"); pg.wait_for_selector('#iniLab [data-lab]')
    labs = pg.eval_on_selector_all('#iniLab [data-lab]', 'bs=>bs.map(b=>b.dataset.lab)')
    check('Tarjetas: Corte, Recolección y Alce (sin «Corte y recolección»)', labs == ['corte', 'recoleccion', 'alce'], labs)
    clic = lambda sel: pg.eval_on_selector(sel, 'b=>b.click()')
    clic('#iniLab [data-lab="corte"]'); clic('#iniZona [data-zona="Z1"]')
    check('Una labor: se puede iniciar sin PIN', pg.evaluate("S.laborSel==='corte'&&!$('#iniOk').disabled&&$('#iniPin').hidden"))
    clic('#iniLab [data-lab="recoleccion"]')
    marc = pg.eval_on_selector_all('#iniLab .on', 'bs=>bs.map(b=>b.dataset.lab)')
    check('Corte + Recolección: las dos marcadas, pide PIN y recomienda una labor', marc == ['corte', 'recoleccion'] and pg.is_visible('#iniPin')
          and 'UNA sola labor' in pg.text_content('#iniPin') and pg.evaluate("$('#iniOk').disabled"), marc)
    check('Voz recomienda una sola labor', any('una sola labor' in d for d in pg.evaluate("window.__dichos||[]")))
    if CAPTURA:
        time.sleep(.5); pg.screenshot(path=CAPTURA.replace('.png', '_pin.png'))
    pg.fill('#iniPinTx', '1234'); clic('#iniPinOk')
    check('PIN incorrecto: no permite', pg.evaluate("$('#iniOk').disabled&&!S.pinDoble") and 'incorrecto' in pg.text_content('#iniPinMsj'))
    pg.fill('#iniPinTx', '9999'); clic('#iniPinOk')
    check('PIN 9999: permite Corte y recolección', pg.evaluate("S.laborSel==='corte_recoleccion'&&!$('#iniOk').disabled"))
    clic('#iniLab [data-lab="alce"]')
    check('Alce no se combina: queda solo Alce', pg.eval_on_selector_all('#iniLab .on', 'bs=>bs.map(b=>b.dataset.lab)') == ['alce'] and pg.is_hidden('#iniPin'))
    clic('#iniLab [data-lab="corte"]'); clic('#iniLab [data-lab="recoleccion"]'); pg.fill('#iniPinTx', '9999'); clic('#iniPinOk')
    pg.evaluate("motivoNoIniciar=()=>''"); clic('#iniOk')
    pg.wait_for_function("!!S.jornada", timeout=8000)
    check('Jornada iniciada como Corte y recolección', pg.evaluate("S.jornada.labor") == 'corte_recoleccion')
    pg.evaluate("abrirInicioCosecha()"); time.sleep(.3)
    check('Al volver a abrir el inicio, el PIN se pide de nuevo', pg.evaluate("S.labSet.length===0&&!S.pinDoble&&$('#iniOk').disabled"))
    pg.evaluate("cerrarHoja()"); time.sleep(.3)

    # ---------- Racimos de la jornada arriba ----------
    pg.evaluate("revisarLoteGPS()"); time.sleep(.6)
    for _ in range(3):
        pg.evaluate("void(window.__p=sumarCodigo('R','boton'))"); pg.evaluate("window.__p"); time.sleep(.15)
    pg.evaluate("__gps(50,14)")
    pg.evaluate("void(window.__p=sumarCodigo('R','boton'))"); pg.evaluate("window.__p"); time.sleep(.3)
    check('Píldora de la jornada: 4 RACIMOS', pg.is_visible('#pjMini') and pg.text_content('#pjMini .pjRacN') == '4' and 'RACIMOS' in pg.text_content('#pjMini'),
          pg.text_content('#pjMini'))

    # ---------- Marcador del descargue ----------
    pg.evaluate("__gps(50,30)")
    for _ in range(2):
        pg.evaluate("void(window.__p=sumarCodigo('D','boton'))"); pg.evaluate("window.__p"); time.sleep(.2)
    mk = pg.evaluate("Array.from(document.querySelectorAll('.mk-desc')).map(e=>e.textContent.trim())")
    check('Descargue: marcador en el mapa con el viaje y los racimos', len(mk) == 1 and '4 R' in mk[0] and '1' in mk[0], mk)
    check('El total de racimos de la jornada no cambia al descargar', pg.text_content('#pjMini .pjRacN') == '4')
    if CAPTURA:
        pg.evaluate("mapa.setView([S.jornada.descargues[0].lat,S.jornada.descargues[0].lng],19)"); time.sleep(1.2)
        pg.screenshot(path=CAPTURA.replace('.png', '_desc.png'))

    # ---------- Borrar tarjeta (Web NFC simulado) ----------
    pg.evaluate("""()=>{window.__esc=[];window.NDEFReader=class{async write(m,o){__esc.push(m);}async scan(){}};
      SES={...SES,rol:'admin'};}""")
    time.sleep(1.5); pg.evaluate("cerrarHoja();panelGrabarNfc()")
    try: pg.wait_for_selector('#grbBorrar', timeout=5000)
    except Exception: print('hoja:', pg.text_content('#hojaTitulo'))
    check('Panel de grabar: botón BORRAR TARJETA', pg.is_visible('#grbBorrar'))
    clic('#grbBorrar'); time.sleep(.5)
    esc = pg.evaluate("__esc")
    check('Borrar escribe un mensaje NDEF vacío', len(esc) == 1 and esc[0]['records'][0]['recordType'] == 'empty' and 'borrada' in pg.text_content('#grbMsg'), esc)

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
