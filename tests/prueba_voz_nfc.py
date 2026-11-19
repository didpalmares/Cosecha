"""Registro por voz y tarjetas NFC: frases («dos ce un maduro», «sobremaduro», «fruto suelto», «deshacer», «repetir») → conteos de la palma
más cercana con fuente «voz»; lecturas NFC (texto «cos:C», «COS:m») con fuente «nfc», antirrebote de 1,5 s por tarjeta,
retiro y nuevo toque, tarjeta desconocida o de Polinización rechazada y Web NFC simulado (botón «Activar NFC»)."""
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
      S.jornada={id:'J1',evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),estado:'activa',seleccion:[],labor:'cosecha',
        transito:[{lote:'L1',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      await dbPut('jornadas',S.jornada);actualizarJornadaUI();
      window.__gps=n=>{S.gps={lat:1.7+n*m,lng:-78.7,acc:4,t:Date.now()};};__gps(1);}""")

    def reg(pid):
        return pg.evaluate(f"(()=>{{const r=S.hechos.get('{pid}');return r?{{c:r.cosechados,m:r.maduros,v:r.verdes,s:r.sobremaduros,fs:r.fruto_suelto,cond:r.cond,f:(r.pasadas||[]).map(x=>x.f)}}:null}})()")
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
    d = decir('dos ce un maduro')
    r = reg('P1')
    check('«dos ce un maduro» → 2C + 1M', r and (r['c'], r['m'], r['v'], r['s'], r['fs']) == (2, 1, 0, 0, 0), r)
    check('Fuente «voz» en cada pasada', r and r['f'] == ['voz'] * 3, r and r['f'])
    check('Confirma solo una vez con el estado final', '2 cosechados, un maduro dejado' in d and sum('cosechado' in x for x in dichos()[-2:]) == 1, d)
    d = decir('sobremaduro')
    check('«sobremaduro» → 1S', reg('P1')['s'] == 1, d)
    d = decir('fruto suelto')
    check('«fruto suelto» → F (una sola vez)', reg('P1')['fs'] == 1 and 'fruto suelto' in d, d)
    d = decir('fruto suelto')
    check('«fruto suelto» otra vez: no suma (máximo 1)', reg('P1')['fs'] == 1 and 'ya tiene fruto suelto' in d, d)
    d = decir('repetir')
    check('«repetir» repite la última confirmación', 'ya tiene fruto suelto' in d, d)
    d = decir('deshacer')
    check('«deshacer» quita el último registro (F)', (reg('P1')['c'], reg('P1')['m'], reg('P1')['s'], reg('P1')['fs']) == (2, 1, 1, 0) and 'Deshecho' in d, d)
    d = decir('eme')
    check('Letra dicha como palabra: «eme» → M', reg('P1')['m'] == 2, d)
    d = decir('3 c')
    check('Número en cifras: «3 c» → +3C', reg('P1')['c'] == 5, d)
    d = decir('sobre maduro un be')
    check('«sobre maduro un be» → +1S +1V (no confunde con M)', (reg('P1')['c'], reg('P1')['m'], reg('P1')['v'], reg('P1')['s']) == (5, 2, 1, 2), (reg('P1'), d))
    n_antes = pg.evaluate("S.registros.length"); r0 = reg('P1')
    d = decir('hola qué tal')
    check('Frase sin código: no registra y avisa', reg('P1') == r0 and 'No entendí' in d and 'C, M, V, S o F' in d, d)
    d = decir('once ce')
    check('Más de diez no registra', reg('P1') == r0 and 'diez' in d, d)
    # La palma P2 (40 m) queda fuera del radio; al acercarse, «verde» la marca y luego C se combina
    pg.evaluate("__gps(39.5)")
    d = decir('verde')
    check('«verde» → V en la palma más cercana', reg('P2') and reg('P2')['v'] == 1, (reg('P2'), d))
    d = decir('una ce')
    check('C después de V: se combina', reg('P2')['c'] == 1 and reg('P2')['v'] == 1, d)
    # Mientras la app habla, el micrófono está en pausa: lo que «oiga» no se registra
    pg.evaluate("void decir('Prueba de pausa del micrófono con la palabra cosechado')")
    esperar("RV.hablando")
    check('Micrófono en pausa mientras la app habla', pg.evaluate("!window.__srOn") and not pg.evaluate("window.__hablar('c')"))
    listo()
    pg.click('#btDxVoz'); time.sleep(0.3)
    check('Desactivar registro por voz', not pg.evaluate("PV.on") and not pg.evaluate("RV.on"))

    # ---------- NFC ----------
    pg.evaluate("__gps(1)")
    check('Web NFC sin permiso: muestra «Activar NFC»', pg.text_content('#polNfc') == 'Activar NFC', pg.text_content('#polNfc'))
    pg.click('#polNfc'); esperar("NFC.estado==='listo'")
    check('Tras tocar: «NFC listo»', pg.text_content('#polNfc') == 'NFC listo', pg.text_content('#polNfc'))
    a0 = reg('P1')['c']
    r1 = pg.evaluate("nfcLeido({texto:'cos:C',id:'04AA'})")
    esperar(f"S.hechos.get('P1').cosechados==={a0 + 1}")
    check('Tarjeta «cos:C» suma 1C con fuente nfc', reg('P1')['c'] == a0 + 1 and reg('P1')['f'][-1] == 'nfc' and r1 == 'ok', (r1, reg('P1')))
    r2 = pg.evaluate("nfcLeido({texto:'cos:C',id:'04AA'})"); time.sleep(0.4)
    check('Misma tarjeta sin retirarla (<1,5 s): ignorada', r2 == 'repetida' and reg('P1')['c'] == a0 + 1, r2)
    pg.evaluate("nfcRetirada({id:'04AA'})")
    r3 = pg.evaluate("nfcLeido({texto:'cos:C',id:'04AA'})")
    esperar(f"S.hechos.get('P1').cosechados==={a0 + 2}")
    check('Retirada y acercada de nuevo: cuenta otra vez', r3 == 'ok' and reg('P1')['c'] == a0 + 2, r3)
    p0 = reg('P1')['m']
    pg.evaluate("nfcLeido({texto:'COS:m',id:'04BB'})")
    esperar(f"S.hechos.get('P1').maduros==={p0 + 1}")
    check('Tarjeta «COS:m» suma 1M', reg('P1')['m'] == p0 + 1, reg('P1'))
    time.sleep(1.6)
    r4 = pg.evaluate("nfcLeido({texto:'COS:m',id:'04BB'})")
    esperar(f"S.hechos.get('P1').maduros==={p0 + 2}")
    check('Misma tarjeta después de 1,5 s: cuenta', r4 == 'ok' and reg('P1')['m'] == p0 + 2, r4)
    r_ant = reg('P1')
    r5 = pg.evaluate("nfcLeido({texto:'X',id:'04CC'})"); time.sleep(0.3)
    check('Tarjeta desconocida: no registra', r5 == 'desconocida' and reg('P1') == r_ant, r5)
    r6 = pg.evaluate("nfcLeido({texto:'V',id:'04CD'})"); time.sleep(0.3)
    r7 = pg.evaluate("nfcLeido({texto:'pol:A',id:'04CE'})"); time.sleep(0.3)
    check('Tarjetas de Polinización («V», «pol:A») rechazadas sin registrar', r6 == 'desconocida' and r7 == 'desconocida' and reg('P1') == r_ant
          and 'C, M, V, S o F' in pg.evaluate("VOZ.ultimoPol||''"), (r6, r7, pg.evaluate("VOZ.ultimoPol")))
    b0 = reg('P1')['s']
    pg.evaluate("__leerNdef('cos:S','04:DD')")
    esperar(f"S.hechos.get('P1').sobremaduros==={b0 + 1}")
    check('Web NFC: lectura de texto «cos:S» suma 1S', reg('P1')['s'] == b0 + 1, reg('P1'))
    pg.evaluate("__leerNdef('cos:S','04:DD')"); time.sleep(0.4)
    check('Web NFC: rebote de la misma tarjeta ignorado', reg('P1')['s'] == b0 + 1, reg('P1'))
    cods = pg.evaluate("['cos:C','COS:m',' cos:V ','COS://s','cos:F','C','V','pol:A','pol:V','cos:X','cos:CM',''].map(codigoNfc)")
    check('Interpretación: códigos de tarjeta (prefijo «cos:» obligatorio)', cods == ['C', 'M', 'V', 'S', 'F', None, None, None, None, None, None, None], cods)

    # ---------- Administración: grabar tarjetas ----------
    adm = ctx.new_page()
    adm.on('pageerror', lambda e: errores.append('admin: ' + str(e)))
    adm.goto(BASE + '/admin.html')
    adm.click('#tabs [data-t="nfc"]')
    check('Admin: pestaña «Grabar tarjetas NFC» con los 5 códigos', adm.is_visible('#nfc') and adm.locator('#nfcCods [data-c]').count() == 5
          and 'Racimo cosechado' in adm.text_content('#nfcCods') and adm.is_hidden('#nfcNo'))
    check('Admin: GRABAR deshabilitado hasta elegir código', adm.is_disabled('#nfcGrabar'))
    adm.click('#nfcCods [data-c="S"]'); adm.click('#nfcGrabar')
    adm.wait_for_function("document.querySelector('#nfcMsg').classList.contains('bien')", timeout=5000)
    esc = adm.evaluate("window.__escrito")
    check('Admin: graba un registro NDEF de texto «cos:S»', esc and esc['m']['records'][0]['recordType'] == 'text' and esc['m']['records'][0]['data'] == 'cos:S'
          and esc['o']['overwrite'] is True and 'sobremaduro' in adm.text_content('#nfcMsg'), esc)
    sin = nav.new_context(service_workers='block')
    adm2 = sin.new_page(); adm2.goto(BASE + '/admin.html'); adm2.click('#tabs [data-t="nfc"]')
    check('Admin sin Web NFC (escritorio): aviso para usar Chrome en Android', adm2.is_visible('#nfcNo') and 'Android' in adm2.text_content('#nfcNo') and adm2.is_disabled('#nfcLeer'))
    sin.close()

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
