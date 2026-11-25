"""Labores de cosecha: Corte (R por palma), Recolección (R por palma + D descargue del viaje con doble pasada),
Corte y recolección (R + D) y Alce (R en el acopio del sendero, sin palma). Existencia 0 excluida, entrada al lote sin preguntas,
deshacer, tarjetas NFC «R»/«D» y exportación de descargues y acopios. GitHub simulado."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, BASE
import json, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else BASE + '/index.html'
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
    pg.wait_for_function("typeof S!=='undefined' && typeof sumarCodigo==='function' && !!document.querySelector('#polBar')", timeout=30000)
    time.sleep(1.5)

    # Lote L1 con palmas cada 9 m (la 3 es existencia 0) y un sendero a 60 m (fuera de las palmas).
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario',labores:['corte','recoleccion','alce']};
      const f=(id,lote,ln,num,lat,lng,existe=true)=>({type:'Feature',geometry:{type:'Point',coordinates:[lng,lat]},
        properties:{_id:id,_lote:lote,_linea:ln,_num:num,_existe:existe}});
      const m=1/111320;window.__m=m;
      S.palmas={type:'FeatureCollection',features:[f('P1','L1',1,1,1.7,-78.7),f('P2','L1',1,2,1.7+9*m,-78.7),f('P3','L1',1,3,1.7+18*m,-78.7,false)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));
      if(typeof indexar==='function')try{indexar();}catch(e){}
      window.__jornada=async(labor,id)=>{S.jornada={id,evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),estado:'activa',seleccion:[],labor,viaje:0,descargues:[],alces:[]};
        S.hechos=new Map();DESHACER.length=0;await dbPut('jornadas',S.jornada);actualizarJornadaUI();pintarPolBar();};
      window.__gps=(metrosN)=>{S.gps={lat:1.7+metrosN*m,lng:-78.7,acc:4,t:Date.now()};};
    }""")

    def tocar(c, transito=None, fuente='boton'):
        pg.evaluate(f"void(window.__p=sumarCodigo('{c}','{fuente}'))")
        if transito:
            pg.wait_for_selector(f'#hojaCuerpo [data-t="{transito}"]', timeout=5000)
            pg.eval_on_selector(f'#hojaCuerpo [data-t="{transito}"]', 'b=>b.click()')
        pg.evaluate("window.__p")
        time.sleep(.15)

    def rac(pid):
        return pg.evaluate(f"(()=>{{const r=S.hechos.get('{pid}');return r?{{r:r.racimos,n1:r.n1,cod:r.n1_codigo,lab:r.labor,tr:r.transitabilidad}}:null}})()")

    # ---------- Labores del usuario ----------
    check('Labores del usuario (admin)', pg.evaluate("misLabores()") == ['corte', 'recoleccion', 'alce'])
    check('Paquete anterior («cosecha») = todas las labores',
          pg.evaluate("(()=>{const s=SES;SES={...s,labores:['cosecha']};const l=misLabores();SES=s;return l})()") == ['corte', 'recoleccion', 'corte_recoleccion', 'alce'])

    # ---------- CORTE: solo R ----------
    pg.evaluate("__jornada('corte','J1')")
    check('Corte: barra visible, sin botón D', pg.is_visible('#polBar') and pg.is_hidden('#polD') and pg.is_visible('#polBar [data-c="R"]'))
    pg.evaluate("S.gps=null"); tocar('R')
    check('Sin GPS: no registra', rac('P1') is None)
    pg.evaluate("__gps(1)")
    tocar('R'); tocar('R'); tocar('R')
    r = rac('P1')
    check('Corte: P1 = 3R', r and r['r'] == 3 and r['n1'] == '3R' and r['cod'] == 'R' and r['lab'] == 'corte', r)
    tocar('D')
    check('Corte: D no aplica', pg.evaluate("(S.jornada.descargues||[]).length") == 0 and 'no se registra descargue' in (pg.evaluate("VOZ.ultimoPol") or ''))
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Deshacer: P1 = 2R', rac('P1')['r'] == 2, rac('P1'))
    pg.evaluate("__gps(18)"); tocar('R')
    check('Existencia 0 nunca se registra (va a P2)', rac('P3') is None and rac('P2') and rac('P2')['r'] == 1)
    pg.evaluate("__gps(100)"); n0 = pg.evaluate("S.registros.length"); tocar('R')
    check('A más de 10 m de una palma: no registra', pg.evaluate("S.registros.length") == n0)

    # ---------- RECOLECCIÓN: R + D con doble pasada ----------
    pg.evaluate("__jornada('recoleccion','J2')")
    check('Recolección: botón D visible', pg.is_visible('#polD'))
    pg.evaluate("__gps(1)")
    tocar('R'); tocar('R')
    pg.evaluate("__gps(9.5)"); tocar('R', fuente='nfc')
    check('Viaje abierto = 3R', pg.evaluate("S.jornada.viaje") == 3)
    pg.evaluate("__gps(30)")
    tocar('D', fuente='nfc')
    check('D: la primera pasada pide confirmar', pg.evaluate("S.jornada.descargues.length") == 0 and 'otra vez' in pg.evaluate("VOZ.ultimoPol"))
    tocar('D', fuente='nfc')
    d = pg.evaluate("S.jornada.descargues")
    check('D: la segunda pasada registra el descargue (3R, punto GPS)', len(d) == 1 and d[0]['racimos'] == 3 and d[0]['n'] == 1 and d[0]['fuente'] == 'nfc'
          and abs(d[0]['lat'] - (1.7 + 30 / 111320)) < 1e-6 and pg.evaluate("S.jornada.viaje") == 0, d)
    tocar('D'); tocar('D')
    check('D con el viaje vacío: no registra', pg.evaluate("S.jornada.descargues.length") == 1)
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Deshacer el descargue: el viaje vuelve a 3R', pg.evaluate("S.jornada.descargues.length") == 0 and pg.evaluate("S.jornada.viaje") == 3)
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Deshacer un R: el viaje baja a 2R', pg.evaluate("S.jornada.viaje") == 2)
    tocar('D'); time.sleep(.1)
    pg.evaluate("DESC.t=Date.now()-9000")   # más de 8 s: la segunda pasada vuelve a pedir confirmación
    tocar('D')
    check('D: pasadas separadas más de 8 s no confirman', pg.evaluate("S.jornada.descargues.length") == 0)
    tocar('D')
    check('D confirmado (2R)', pg.evaluate("S.jornada.descargues.length") == 1 and pg.evaluate("S.jornada.descargues[0].racimos") == 2)

    # ---------- CORTE Y RECOLECCIÓN: R + D ----------
    pg.evaluate("__jornada('corte_recoleccion','J3')")
    check('Corte y recolección: botón D visible', pg.is_visible('#polD'))

    # ---------- ALCE: R en el acopio, sin palma ----------
    pg.evaluate("__jornada('alce','J4')")
    check('Alce: barra visible, sin D', pg.is_visible('#polBar') and pg.is_hidden('#polD'))
    pg.evaluate("__gps(60)")
    n0 = pg.evaluate("S.registros.length")
    tocar('R'); tocar('R')
    pg.evaluate("__gps(65)"); tocar('R')          # 5 m: mismo acopio
    pg.evaluate("__gps(120)"); tocar('R')         # 55 m más allá: acopio nuevo
    a = pg.evaluate("S.jornada.alces")
    check('Alce: 2 acopios (3R y 1R), sin registros de palma', [x['racimos'] for x in a] == [3, 1] and pg.evaluate("S.registros.length") == n0, a)
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Alce: deshacer quita el acopio de 1R', [x['racimos'] for x in pg.evaluate("S.jornada.alces")] == [3])

    # ---------- Exportación ----------
    pg.evaluate("__jornada('recoleccion','J5')")
    pg.evaluate("S.jornada.descargues=[{id:'d1',n:1,racimos:4,t:new Date().toISOString(),hora:'08:00',lat:1.7,lng:-78.7,acc:3,lote:'L1',fuente:'boton'}];"
                "S.jornada.alces=[{id:'a1',n:1,racimos:4,lat:1.7,lng:-78.7,acc:3,lote:'L1',t_ini:'',t_fin:'',hora:'09:00',fuente:'nfc'}]")
    g = pg.evaluate("(()=>{const g=geoJornada(S.jornada,[],[],new Date().toISOString(),null);return {j:g.jornada,t:g.features.map(f=>f.properties.tipo)}})()")
    check('GeoJSON: labor, viajes y features de descargue y alce', g['j']['labor'] == 'recoleccion' and g['j']['viajes'] == 1 and g['j']['racimos_descargados'] == 4
          and 'descargue' in g['t'] and 'alce' in g['t'], g)

    # ---------- Tarjetas NFC ----------
    t = pg.evaluate("['R','r','cos:R','D',' d ','A','V','pol:A','C'].map(codigoNfc)")
    check('NFC: «R» y «D» se aceptan; A, V, C y las de Polinización no', t == ['R', 'R', 'R', 'D', 'D', None, None, None, None], t)

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
