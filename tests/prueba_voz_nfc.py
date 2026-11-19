"""Registro por voz y tarjetas NFC (labor Recolección): frases («dos racimos», «erre», «deshacer», «repetir», «descargue» dos veces)
→ racimos (R) de la palma más cercana con fuente «voz» y descargue del viaje (D) confirmado con la segunda frase; lecturas NFC
(texto «R», «cos:r», «D») con fuente «nfc», antirrebote por tarjeta, retiro y nuevo toque, tarjeta desconocida o de Polinización
rechazada, Web NFC simulado (botón «Activar NFC») y grabación de tarjetas R / D en admin.html."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, BASE
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else BASE + '/index.html'
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)

# Web NFC simulado: NDEFReader.scan() deja el lector en window.__ndef para disparar lecturas.
INIT_NFC = """
window.NDEFReader=class{scan(){window.__ndef=this;return Promise.resolve();}write(m,o){window.__escrito={m,o:{overwrite:o&&o.overwrite}};return Promise.resolve();}};
window.__leerNdef=(txt,serial)=>window.__ndef&&window.__ndef.onreading({serialNumber:serial,message:{records:[{recordType:'text',encoding:'utf-8',data:new TextEncoder().encode(txt)}]}});
"""
errores = []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True, args=['--use-fake-ui-for-media-stream'])
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900}, permissions=['microphone'])
    ctx.add_init_script(INIT_VOZ + INIT_NFC)
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=200, content_type='application/json', body='{}'))
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.on('dialog', lambda d: (errores.append('DIALOGO: ' + d.message), d.dismiss()))
    pg.goto(URL)
    pg.wait_for_function("typeof S!=='undefined'&&typeof sumarCodigo==='function'&&typeof nfcLeido==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      document.querySelector('#login').hidden=true;SES={u:'op1',nombre:'Operario Uno',rol:'operario'};
      const m=1/111320,f=(id,num,lat)=>({type:'Feature',geometry:{type:'Point',coordinates:[-78.7,lat]},properties:{_id:id,_lote:'L1',_linea:1,_num:num,_existe:true}});
      S.palmas={type:'FeatureCollection',features:[f('P1',1,1.7),f('P2',2,1.7+40*m)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));
      if(typeof indexar==='function')try{indexar();}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),estado:'activa',seleccion:[],labor:'recoleccion',viaje:0,descargues:[],
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      await dbPut('jornadas',S.jornada);actualizarJornadaUI();
      window.__gps=n=>{S.gps={lat:1.7+n*m,lng:-78.7,acc:4,t:Date.now()};};__gps(1);}""")

    def reg(pid):
        return pg.evaluate(f"(()=>{{const r=S.hechos.get('{pid}');return r?{{r:r.racimos,cod:r.n1_codigo,f:(r.pasadas||[]).map(x=>x.f)}}:null}})()")
    def rac(pid): return (reg(pid) or {}).get('r', 0)
    def nd(): return pg.evaluate("S.jornada.descargues.length")
    def dichos(): return pg.evaluate("window.__dichos")
    def listo(t=10):
        fin = time.time() + t
        while time.time() < fin:
            if pg.evaluate("!RV.hablando&&!!window.__srOn&&RV.nh===0"): return True
            time.sleep(0.05)
        return False
    def decir(txt, t=10):
        """Dice la frase y espera la respuesta hablada de la app; devuelve lo último que dijo."""
        assert listo(), 'el micrófono no quedó escuchando'
        n0 = len(dichos())
        assert pg.evaluate(f"window.__hablar({txt!r})"), 'sin micrófono: ' + txt
        fin = time.time() + t
        while time.time() < fin and len(dichos()) <= n0: time.sleep(0.05)
        listo(); time.sleep(0.1)
        return dichos()[-1] if len(dichos()) > n0 else ''
    def esperar(cond_js, t=5):
        fin = time.time() + t
        while time.time() < fin:
            if pg.evaluate(cond_js): return True
            time.sleep(0.05)
        return False

    # ---------- Voz ----------
    check('Botón «Registro por voz» visible', pg.is_visible('#btDxVoz') and pg.get_attribute('#btDxVoz', 'aria-label') == 'Registro por voz')
    pg.click('#btDxVoz')
    esperar("window.__dichos.join(' ').includes('Registro por voz activado')")
    check('Activa y escucha', listo() and pg.evaluate("PV.on"), dichos()[-1:])
    act = next((x for x in dichos() if 'Registro por voz activado' in x), '')
    check('El aviso de activación da un ejemplo de cosecha (racimo), no de Polinización', 'racimo' in act.lower() and 'dos A, una P' not in act, act)
    d = decir('dos racimos')
    r = reg('P1')
    check('«dos racimos» → 2R', r and r['r'] == 2 and r['cod'] == 'R', r)
    check('Fuente «voz» en cada pasada', r and r['f'] == ['voz'] * 2, r and r['f'])
    check('Confirma solo una vez con el estado final', 'racimos' in d and sum('P1:' in x for x in dichos()[-2:]) == 1, d)
    d = decir('erre')
    check('«erre» → +1R', rac('P1') == 3, d)
    d = decir('repetir')
    check('«repetir» repite la última confirmación', 'racimos' in d and d == pg.evaluate("VOZ.ultimoPol"), d)
    d = decir('deshacer')
    check('«deshacer» quita el último racimo', rac('P1') == 2 and 'Deshecho' in d, d)
    d = decir('3 r')
    check('Número en cifras: «3 r» → +3R', rac('P1') == 5, d)
    d = decir('un racimo y dos ere')
    check('«un racimo y dos ere» → +1R +2R', rac('P1') == 8, (reg('P1'), d))
    n_antes = pg.evaluate("S.registros.length"); r0 = reg('P1')
    d = decir('hola qué tal')
    check('Frase sin código: no registra y avisa', reg('P1') == r0 and 'No entendí' in d and 'racimo o descargue' in d, d)
    d = decir('once racimos')
    check('Más de diez no registra', reg('P1') == r0 and 'diez' in d, d)
    # La palma P2 (40 m) queda fuera del radio; al acercarse, «verde» la marca y luego C se combina
    pg.evaluate("__gps(39.5)")
    d = decir('racimo')
    check('«racimo» → R en la palma más cercana (P2)', reg('P2') and rac('P2') == 1 and rac('P1') == 8, (reg('P2'), d))
    v0 = pg.evaluate("S.jornada.viaje")
    d = decir('descargue')
    check('«descargue» la primera vez: pide confirmar, no registra', nd() == 0 and 'otra vez' in d, d)
    d = decir('descargue')
    check('«descargue» otra vez: registra el viaje con sus racimos (fuente voz)', nd() == 1 and pg.evaluate("S.jornada.descargues[0].racimos") == v0
          and pg.evaluate("S.jornada.descargues[0].fuente") == 'voz' and pg.evaluate("S.jornada.viaje") == 0 and 'descargado' in d, (v0, d))
    # Mientras la app habla, el micrófono está en pausa: lo que «oiga» no se registra
    pg.evaluate("void decir('Prueba de pausa del micrófono con la palabra racimo')")
    esperar("RV.hablando")
    check('Micrófono en pausa mientras la app habla', pg.evaluate("!window.__srOn") and not pg.evaluate("window.__hablar('racimo')"))
    listo()
    pg.click('#btDxVoz'); time.sleep(0.3)
    check('Desactivar registro por voz', not pg.evaluate("PV.on") and not pg.evaluate("RV.on"))

    # ---------- NFC ----------
    pg.evaluate("__gps(1)")
    check('Web NFC sin permiso: muestra «Activar NFC»', pg.text_content('#polNfc') == 'Activar NFC', pg.text_content('#polNfc'))
    pg.click('#polNfc'); esperar("NFC.estado==='listo'")
    check('Tras tocar: «NFC listo»', pg.text_content('#polNfc') == 'NFC listo', pg.text_content('#polNfc'))
    a0 = rac('P1')
    r1 = pg.evaluate("nfcLeido({texto:'R',id:'04AA'})")
    esperar(f"S.hechos.get('P1').racimos==={a0 + 1}")
    check('Tarjeta «R» suma 1R con fuente nfc', rac('P1') == a0 + 1 and reg('P1')['f'][-1] == 'nfc' and r1 == 'ok', (r1, reg('P1')))
    r2 = pg.evaluate("nfcLeido({texto:'R',id:'04AA'})"); time.sleep(0.4)
    check('Misma tarjeta sin retirarla (rebote): ignorada', r2 == 'repetida' and rac('P1') == a0 + 1, r2)
    pg.evaluate("nfcRetirada({id:'04AA'})")
    r3 = pg.evaluate("nfcLeido({texto:'R',id:'04AA'})")
    esperar(f"S.hechos.get('P1').racimos==={a0 + 2}")
    check('Retirada y acercada de nuevo: cuenta otra vez', r3 == 'ok' and rac('P1') == a0 + 2, r3)
    pg.evaluate("nfcLeido({texto:'cos:r',id:'04BB'})")
    esperar(f"S.hechos.get('P1').racimos==={a0 + 3}")
    check('Tarjeta «cos:r» también suma 1R', rac('P1') == a0 + 3, reg('P1'))
    time.sleep(1.6)
    r4 = pg.evaluate("nfcLeido({texto:'cos:r',id:'04BB'})")
    esperar(f"S.hechos.get('P1').racimos==={a0 + 4}")
    check('Misma tarjeta después de 1,5 s: cuenta', r4 == 'ok' and rac('P1') == a0 + 4, r4)
    r_ant = reg('P1')
    r5 = pg.evaluate("nfcLeido({texto:'X',id:'04CC'})"); time.sleep(0.3)
    check('Tarjeta desconocida: no registra', r5 == 'desconocida' and reg('P1') == r_ant, r5)
    r6 = pg.evaluate("nfcLeido({texto:'V',id:'04CD'})"); time.sleep(0.3)
    r7 = pg.evaluate("nfcLeido({texto:'pol:A',id:'04CE'})"); time.sleep(0.3)
    r8 = pg.evaluate("nfcLeido({texto:'cos:C',id:'04CF'})"); time.sleep(0.3)
    check('Tarjetas de Polinización («V», «pol:A») y de la versión anterior («cos:C») rechazadas sin registrar', r6 == r7 == r8 == 'desconocida' and reg('P1') == r_ant
          and 'Use tarjetas R o D' in pg.evaluate("VOZ.ultimoPol||''"), (r6, r7, r8, pg.evaluate("VOZ.ultimoPol")))
    b0 = rac('P1')
    pg.evaluate("__leerNdef('R','04:DD')")
    esperar(f"S.hechos.get('P1').racimos==={b0 + 1}")
    check('Web NFC: lectura de texto «R» suma 1R', rac('P1') == b0 + 1, reg('P1'))
    pg.evaluate("__leerNdef('R','04:DD')"); time.sleep(0.4)
    check('Web NFC: rebote de la misma tarjeta ignorado', rac('P1') == b0 + 1, reg('P1'))
    v0 = pg.evaluate("S.jornada.viaje")
    pg.evaluate("nfcLeido({texto:'D',id:'04EE'})"); time.sleep(0.6)
    check('Tarjeta «D» la primera vez: pide pasarla otra vez', nd() == 1 and 'otra vez' in pg.evaluate("VOZ.ultimoPol||''"), pg.evaluate("VOZ.ultimoPol"))
    pg.evaluate("nfcLeido({texto:'D',id:'04EE'})")
    esperar("S.jornada.descargues.length===2")
    check('Tarjeta «D» otra vez: descargue del viaje con fuente nfc', nd() == 2 and pg.evaluate("S.jornada.descargues[1].racimos") == v0 and pg.evaluate("S.jornada.descargues[1].fuente") == 'nfc', v0)
    cods = pg.evaluate("['R','r',' cos:R ','COS://r','D','cos:d','C','V','pol:A','cos:X','RD',''].map(codigoNfc)")
    check('Interpretación: códigos de tarjeta R y D (con o sin «cos:»)', cods == ['R', 'R', 'R', 'R', 'D', 'D', None, None, None, None, None, None], cods)

    # ---------- Administración: grabar tarjetas ----------
    adm = ctx.new_page()
    adm.on('pageerror', lambda e: errores.append('admin: ' + str(e)))
    adm.goto(BASE + '/admin.html')
    adm.click('#tabs [data-t="nfc"]')
    check('Admin: pestaña «Grabar tarjetas NFC» con los 2 códigos (R y D)', adm.is_visible('#nfc') and adm.locator('#nfcCods [data-c]').count() == 2
          and 'Racimo' in adm.text_content('#nfcCods') and 'Descargue del viaje' in adm.text_content('#nfcCods') and adm.is_hidden('#nfcNo'))
    check('Admin: GRABAR deshabilitado hasta elegir código', adm.is_disabled('#nfcGrabar'))
    adm.click('#nfcCods [data-c="D"]'); adm.click('#nfcGrabar')
    adm.wait_for_function("document.querySelector('#nfcMsg').classList.contains('bien')", timeout=5000)
    esc = adm.evaluate("window.__escrito")
    check('Admin: graba un registro NDEF de texto «D» (sin prefijo)', esc and esc['m']['records'][0]['recordType'] == 'text' and esc['m']['records'][0]['data'] == 'D'
          and esc['o']['overwrite'] is True and 'Descargue' in adm.text_content('#nfcMsg'), esc)
    sin = nav.new_context(service_workers='block')
    adm2 = sin.new_page(); adm2.goto(BASE + '/admin.html'); adm2.click('#tabs [data-t="nfc"]')
    check('Admin sin Web NFC (escritorio): aviso para usar Chrome en Android', adm2.is_visible('#nfcNo') and 'Android' in adm2.text_content('#nfcNo') and adm2.is_disabled('#nfcLeer'))
    sin.close()

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
