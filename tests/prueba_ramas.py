"""Formulario incorporado de la cosecha: una sola rama (R: Racimo), el mismo en la App y en ramas_base.json (admin), con un
contador de racimos en el formulario de la palma (sin enfermedades, síntomas, cirugía ni producción)."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, INIT_VOZ, PLANTACION, TMP, BASE
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)
errores, alertas = [], []
with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 412, 'height': 900})
    ctx.route('https://api.github.com/**', lambda r: r.fulfill(status=404, body='{}'))
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errores.append(str(e)[:200])); pg.on('dialog', lambda d: (alertas.append(d.message), d.dismiss()))
    pg.goto(BASE + '/index.html'); pg.wait_for_function("typeof abrirFormulario==='function'", timeout=30000); time.sleep(2)
    pg.evaluate("""async()=>{document.querySelector('#login').hidden=true;SES={u:'op1',nombre:'Operario Uno',rol:'operario'};
      const j={id:'JR',estado:'activa',evaluador:'Operario Uno',usuario:'op1',inicio:new Date().toISOString(),seleccion:[{lote:'IT01'}],densidad:115,buffer:5,km:0,sync:'pendiente',
        labor:'corte',viaje:0,descargues:[],alces:[],transito:[{lote:'IT01',entrada:'Transitable',t_entrada:new Date().toISOString(),salida:'',t_salida:''}]};
      await dbPut('jornadas',j);S.jornada=j;S.cfg.jornadaActiva='JR';S.gps={lat:1.70002,lng:-78.70,acc:4,t:Date.now()};
      for(const [id,n] of [['P1',1],['P2',2]])S.idx.set(id,{type:'Feature',geometry:{type:'Point',coordinates:[-78.70,1.70]},properties:{_id:id,_lote:'IT01',_linea:5,_num:n,_existe:true}});}""")
    t = pg.evaluate("""async()=>{const base=await (await fetch('ramas_base.json',{cache:'no-store'})).json();
      return {ramas:RAMAS.map(x=>x.c+'|'+x.n1),n1s:N1S.map(x=>x.c),prob:PROBLEMAS.map(x=>x.id),color:COLOR_N1.R,base:base.ramas.map(x=>x.c+'|'+x.n1),baseColor:(base.enfermedades.R||{}).color};}""")
    check('Formulario incorporado: una sola rama «R: Racimo»', t['ramas'] == ['R|R: Racimo'] and t['n1s'] == ['R'] and t['prob'] == ['R'], t)
    check('ramas_base.json (editor de admin) coincide con la App: R y su color', t['base'] == t['ramas'] and t['baseColor'] == t['color'] == '#00c853', t)
    f = pg.evaluate("""(async()=>{await abrirFormulario({palma_id:'P1'});const frm=document.querySelector('#frm');
      return {n1:frm.querySelectorAll('input[name=n1]').length,sint:frm.querySelectorAll('input[name=sintomas]').length,cont:[...frm.querySelectorAll('.pol-cont')].map(x=>x.dataset.k),
        txt:frm.innerText,val:document.querySelector('#cnt_racimos').textContent};})()""")
    check('Formulario de la palma: un contador de racimos (R) en 0', f['cont'] == ['racimos'] and f['val'] == '0' and 'RACIMOS' in f['txt'].upper(), f['cont'])
    check('Formulario sin enfermedad, síntomas, cirugía ni producción', f['n1'] == 0 and f['sint'] == 0 and not any(x in f['txt'] for x in ['Cirugía', 'Producción', 'Síntoma', 'Raíces']), f['txt'][:200])
    # Sin racimos: no guarda
    pg.evaluate("guardarRegistro(document.querySelector('#frm'))"); time.sleep(.4)
    check('Sin racimos: avisa «Registre al menos un racimo (R).» y no guarda', 'Registre al menos un racimo (R).' in alertas and pg.evaluate("S.registros.length") == 0, alertas)
    alertas.clear()
    # + + + − = 2 racimos
    r = pg.evaluate("""async()=>{const q=s=>document.querySelector(s);for(let i=0;i<3;i++)q('#frm [data-mas=racimos]').click();q('#frm [data-menos=racimos]').click();
      const v=q('#cnt_racimos').textContent;const id=F.r.id;await guardarRegistro(q('#frm'));const r=S.registros.find(x=>x.id===id);
      return {v,guardado:!!r,racimos:r&&r.racimos,n1:r&&r.n1,cod:r&&r.n1_codigo,prob:r&&r.problemas,estado:r&&r.estado,labor:r&&r.labor,fuente:r&&r.fuente,color:r&&colorReg(r),tr:r&&r.transitabilidad};}""")
    check('Contador: 3 × «+» y 1 × «−» = 2', r['v'] == '2', r['v'])
    check('Guarda 2R (código R, estado cosecha, labor de la jornada, fuente formulario)', r['guardado'] and r['racimos'] == 2 and r['n1'] == '2R' and r['cod'] == 'R' and r['prob'] == ['R']
          and r['estado'] == 'cosecha' and r['labor'] == 'corte' and r['fuente'] == 'formulario' and r['tr'] == 'Transitable', r)
    check('Color del registro: el de R', r['color'] == '#00c853', r['color'])
    # Editar: el contador abre con los racimos guardados y el «−» no baja de 0
    e = pg.evaluate("""async()=>{const r=S.registros.find(x=>x.palma_id==='P1');await abrirFormulario(r);const q=s=>document.querySelector(s);const v0=q('#cnt_racimos').textContent;
      for(let i=0;i<4;i++)q('#frm [data-menos=racimos]').click();return {v0,v1:q('#cnt_racimos').textContent};}""")
    check('Editar: abre con 2 y «−» no baja de 0', e == {'v0': '2', 'v1': '0'}, e)
    pg.evaluate("cerrarHoja()")
    check('Sin errores de JavaScript ni alertas inesperadas', not errores and not alertas, (errores + alertas)[:3])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
