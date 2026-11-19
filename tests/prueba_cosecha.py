"""Registro de cosecha: botones C/M/V/S/F a la palma existente más cercana (10 m), combinaciones,
F máximo 1 por palma, existencia 0 excluida, transitabilidad de entrada y salida del lote y deshacer. GitHub simulado."""
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

    # Dos lotes: L1 con palmas cada 9 m (la 3 es existencia 0) y L2 a 200 m.
    pg.evaluate("""async()=>{
      SES={u:'op1',nombre:'Operario Uno',rol:'operario'};
      const f=(id,lote,ln,num,lat,lng,existe=true)=>({type:'Feature',geometry:{type:'Point',coordinates:[lng,lat]},
        properties:{_id:id,_lote:lote,_linea:ln,_num:num,_existe:existe}});
      const m=1/111320;
      S.palmas={type:'FeatureCollection',features:[f('P1','L1',1,1,1.7,-78.7),f('P2','L1',1,2,1.7+9*m,-78.7),f('P3','L1',1,3,1.7+18*m,-78.7,false),
        f('Q1','L2',1,1,1.7+200*m,-78.7)]};
      S.idx=new Map(S.palmas.features.map(x=>[x.properties._id,x]));
      if(typeof indexar==='function')try{indexar();}catch(e){}
      S.jornada={id:'J1',evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),estado:'activa',seleccion:[],labor:'cosecha'};
      await dbPut('jornadas',S.jornada);
      actualizarJornadaUI();
      window.__gps=(metrosN)=>{S.gps={lat:1.7+metrosN*m,lng:-78.7,acc:4,t:Date.now()};};
    }""")

    def tocar(c, transito=None):
        pg.evaluate(f"void(window.__p=sumarCodigo('{c}','boton'))")
        if transito:
            pg.wait_for_selector(f'#hojaCuerpo [data-t="{transito}"]', timeout=5000)
            pg.eval_on_selector(f'#hojaCuerpo [data-t="{transito}"]', 'b=>b.click()')
        pg.evaluate("window.__p")
        time.sleep(.15)

    def reg(pid):
        return pg.evaluate(f"(()=>{{const r=S.hechos.get('{pid}');return r?{{c:r.cosechados,m:r.maduros,v:r.verdes,s:r.sobremaduros,f:r.fruto_suelto,rac:r.racimos,cond:r.cond,n1:r.n1,cod:r.n1_codigo,tr:r.transitabilidad,est:r.estado}}:null}})()")

    check('Barra visible con jornada activa', pg.is_visible('#polBar'))

    # Sin GPS no registra
    pg.evaluate("S.gps=null")
    tocar('C')
    check('Sin GPS: no registra', reg('P1') is None)

    # Junto a P1 (1 m): pide transitabilidad de entrada y suma
    pg.evaluate("__gps(1)")
    tocar('C', 'Poco transitable')
    tocar('C'); tocar('M'); tocar('V')
    r = reg('P1')
    check('P1 = 2C + 1M + 1V', r and (r['c'], r['m'], r['v'], r['s'], r['f']) == (2, 1, 1, 0, 0) and r['n1'] == '2C + 1M + 1V'
          and r['rac'] == 3 and r['cod'] == 'V' and r['est'] == 'cosecha' and r['cond'] == '', r)
    check('Transitabilidad de entrada en el registro', r and r['tr'] == 'Poco transitable', r)
    tramo = pg.evaluate("S.jornada.transito")
    check('Tramo del lote L1 abierto', len(tramo) == 1 and tramo[0]['lote'] == 'L1' and tramo[0]['entrada'] == 'Poco transitable' and not tramo[0]['salida'], tramo)

    # F (fruto suelto) se combina con los racimos, pero máximo 1 por palma
    tocar('F'); tocar('F')
    check('F se suma una sola vez (máximo 1)', reg('P1')['f'] == 1 and reg('P1')['c'] == 2 and reg('P1')['n1'] == '2C + 1M + 1V + F', reg('P1'))

    # Deshacer quita la F (la segunda F no se registró)
    pg.evaluate("deshacerPol()"); time.sleep(.2)
    check('Deshacer: P1 queda 2C + 1M + 1V', (reg('P1')['c'], reg('P1')['m'], reg('P1')['v'], reg('P1')['f']) == (2, 1, 1, 0), reg('P1'))

    # P2 (a 9 m): S y luego C se combinan
    pg.evaluate("__gps(9.5)")
    tocar('S'); tocar('C')
    r2 = reg('P2')
    check('P2 = 1C + 1S (los códigos se combinan)', r2 and r2['s'] == 1 and r2['c'] == 1 and r2['n1'] == '1C + 1S' and r2['cod'] == 'S' and r2['est'] == 'cosecha', r2)

    # P3 existencia 0: con GPS encima, debe ir a la palma existente más cercana (P2), no a P3
    pg.evaluate("__gps(18)")
    tocar('V')
    check('Existencia 0 nunca se registra', reg('P3') is None)

    # Lejos de todo (100 m): no registra
    pg.evaluate("__gps(100)")
    n0 = pg.evaluate("S.registros.length")
    tocar('C')
    check('C más de 10 m de cualquier palma: no registra', pg.evaluate("S.registros.length") == n0)

    # Cambio de lote: pide salida de L1 y entrada a L2
    pg.evaluate("__gps(200)")
    pg.evaluate("void(window.__p=sumarCodigo('C','nfc'))")
    pg.wait_for_selector('#hojaCuerpo [data-t="No transitable"]', timeout=5000)
    titulo1 = pg.text_content('#hojaTitulo')
    pg.eval_on_selector('#hojaCuerpo [data-t="No transitable"]', 'b=>b.click()')
    pg.wait_for_function("document.querySelector('#hojaTitulo').textContent.includes('entrada')", timeout=5000)
    titulo2 = pg.text_content('#hojaTitulo')
    pg.eval_on_selector('#hojaCuerpo [data-t="Transitable"]', 'b=>b.click()')
    pg.evaluate("window.__p"); time.sleep(.2)
    tramo = pg.evaluate("S.jornada.transito")
    check('Cambio de lote: salida de L1 y entrada a L2', 'salida' in titulo1 and 'L1' in titulo1 and 'L2' in titulo2
          and tramo[0]['salida'] == 'No transitable' and tramo[1]['lote'] == 'L2' and tramo[1]['entrada'] == 'Transitable', tramo)
    check('Q1 = 1C (fuente NFC)', reg('Q1') and reg('Q1')['c'] == 1 and pg.evaluate("S.hechos.get('Q1').fuente") == 'nfc')

    # Formulario manual de la palma: existencia 0 bloqueada
    rg = pg.evaluate("reglaDiagnostico(S.idx.get('P3'))")
    check('Formulario: existencia 0 bloqueada', not rg['ok'] and 'existencia 0' in rg['motivo'], rg.get('motivo'))

    # Botón Finalizar lote
    pg.eval_on_selector('#polFin', 'b=>b.click()')
    pg.eval_on_selector('#hojaCuerpo [data-t="Poco transitable"]', 'b=>b.click()'); time.sleep(.3)
    tramo = pg.evaluate("S.jornada.transito")
    check('Finalizar lote: salida de L2', tramo[1]['salida'] == 'Poco transitable' and pg.is_hidden('#polFin'), tramo[1])

    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
