"""Trazabilidad (Fase 1): ficha NFC del acopio (grabación protegida contra tarjetas R/D), alce contado contra la ficha,
conteo doble en Corte y recolección, copia de la jornada por QR (se genera, se lee con jsQR y se reconstruye) y tablero
del supervisor (racimos de corte y recolección, cuadre por lote y acopios sin alzar). GitHub simulado; cartografía ficticia."""
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
    pg.wait_for_function("typeof S!=='undefined' && typeof ofrecerFicha==='function' && typeof qrcode==='function' && typeof jsQR==='function'", timeout=30000)
    time.sleep(1.5)
    pg.evaluate("""async()=>{
      SES={u:'rec1',nombre:'Recolector Uno',rol:'supervisor',labores:['corte','recoleccion','alce']};
      const lg=document.getElementById('login');if(lg)lg.hidden=true;
      const m=1/111320,x0=-78.7,y0=1.7;window.__m=m;
      const cuad=(nom,zona,dx)=>{const a=x0+dx*m,b=y0,c=a+100*m,d=b+100*m;
        return {type:'Feature',properties:{_lote:nom,Lote:nom,ZonaCosecha:zona,Programa:'TT'},geometry:{type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]}};};
      S.lotes={type:'FeatureCollection',features:[cuad('A1','Z1',0)]};CARTO.lotes={A1:{n:10}};
      const CH={A1:Array.from({length:10},(_,i)=>['a'+(i+1),1,i+1,1,x0+50*m,y0+(5+i*9)*m])};leerChunk=async l=>CH[l]||[];
      window.__gps=(dx,dy)=>{S.gps={lat:y0+dy*m,lng:x0+dx*m,acc:4,t:Date.now()};};__gps(50,5);
      window.NDEFReader=class{async scan(){}async write(){}};   // Web NFC presente: la ficha se puede grabar
    }""")
    clic = lambda sel: pg.eval_on_selector(sel, 'b=>b.click()')
    sumar = lambda c: (pg.evaluate(f"void(window.__p=sumarCodigo('{c}','boton'))"), pg.evaluate("window.__p"), time.sleep(.15))

    # ---------- Recolección: ficha del acopio ----------
    pg.evaluate("abrirInicioCosecha()"); pg.wait_for_selector('#iniLab [data-lab]')
    clic('#iniLab [data-lab="recoleccion"]'); clic('#iniZona [data-zona="Z1"]')
    pg.evaluate("motivoNoIniciar=()=>''"); clic('#iniOk'); pg.wait_for_function("!!S.jornada", timeout=8000)
    pg.evaluate("cerrarHoja();revisarLoteGPS()"); time.sleep(.6)
    for dy in (5, 14, 23):
        pg.evaluate(f"__gps(50,{dy})"); sumar('R')
    # La grabación: 1.ª vez se acerca la tarjeta R por error (no se graba encima), 2.ª vez la ficha
    pg.evaluate("""()=>{window.__fichas=[];let k=0;grabarFichaNfc=async t=>{__fichas.push(t);await esperar(150);
        if(k++===0)throw new Error('ES_CODIGO:R');return {ok:true,id:'04A1B2'};};}""")
    pg.evaluate("__gps(50,40)"); sumar('D'); sumar('D')
    pg.wait_for_selector('#fichaMsj', timeout=4000)
    check('Al confirmar el descargue se pide la ficha del acopio', 'ACERQUE LA FICHA' in pg.text_content('#hojaCuerpo') and pg.is_visible('#fichaNo'))
    if CAPTURA:
        time.sleep(.5); pg.screenshot(path=CAPTURA.replace('.png', '_ficha.png'))
    pg.wait_for_function("S.jornada.descargues[0].ficha", timeout=6000)
    d = pg.evaluate("S.jornada.descargues[0]")
    fichas = pg.evaluate("__fichas")
    check('Tarjeta R acercada por error: aviso y no se graba encima', any('tarjeta erre' in x for x in pg.evaluate("window.__dichos||[]")))
    check('Ficha grabada con acopio, lote, racimos y recolector', len(fichas) == 2 and fichas[1].startswith('ACO|' + d['aco'] + '|A1|3|rec1|'), fichas)
    check('El descargue queda con la ficha (UID) y su id de acopio', d['ficha']['uid'] == '04A1B2' and len(d['aco']) == 12, d.get('ficha'))
    try: pg.wait_for_function("!document.querySelector('#fichaMsj')||$('#hoja').classList.contains('oculto')", timeout=4000); cerrada = True
    except Exception: cerrada = False
    check('La hoja de la ficha se cierra sola', cerrada)
    # Un segundo viaje sin ficha (SIN FICHA)
    pg.evaluate("()=>{grabarFichaNfc=()=>new Promise(()=>{});}")
    pg.evaluate("__gps(50,60)"); sumar('R'); sumar('R'); sumar('D'); sumar('D')
    pg.wait_for_selector('#fichaNo', timeout=4000); clic('#fichaNo'); time.sleep(.3)
    check('SIN FICHA: el acopio queda solo con su GPS', pg.evaluate("S.jornada.descargues.length===2&&!S.jornada.descargues[1].ficha&&!FICHA.activa"))
    geo = pg.evaluate("geoJornada(S.jornada,S.registros.filter(r=>r.jornada_id===S.jornada.id),[],new Date().toISOString(),null)")
    fd = [f['properties'] for f in geo['features'] if f['properties'].get('tipo') == 'descargue']
    check('Exportación: descargue con acopio_id y ficha', fd[0]['acopio_id'] == d['aco'] and fd[0]['ficha'] is True and fd[1]['ficha'] is False, fd)
    check('Exportación: racimos de recolección por lote', geo['jornada']['racimos_recoleccion'] == 5 and geo['jornada']['racimos_corte'] == 0
          and geo['jornada']['racimos_por_lote']['A1']['r'] == 5, geo['jornada'].get('racimos_por_lote'))

    # ---------- Copia por QR (recolector) ----------
    pg.evaluate("cerrarHoja()"); time.sleep(.3)
    fr = pg.evaluate("compartirJornada(S.jornada)")
    pg.wait_for_selector('#qrCaja svg')
    check('Compartir: QR en pantalla con los racimos de recolección', pg.is_visible('#qrCaja svg') and 'Racimos de recolección' in pg.text_content('#hojaCuerpo'))
    if CAPTURA:
        time.sleep(.4); pg.screenshot(path=CAPTURA.replace('.png', '_qr.png'))
    # El QR dibujado se lee con jsQR (como lo hará la cámara del supervisor)
    leido = pg.evaluate("""async()=>{const svg=document.querySelector('#qrCaja svg').outerHTML;
      const img=new Image();img.src='data:image/svg+xml;base64,'+btoa(svg);await img.decode();
      const c=document.createElement('canvas');c.width=600;c.height=600;const x=c.getContext('2d');x.fillStyle='#fff';x.fillRect(0,0,600,600);x.drawImage(img,0,0,600,600);
      const d=x.getImageData(0,0,600,600);const r=jsQR(d.data,600,600);return r&&r.data;}""")
    check('El QR de la pantalla se lee con la cámara (jsQR)', bool(leido) and leido.startswith('CQ1|') and leido in fr, (leido or '')[:30])
    copia_rec = fr
    pg.evaluate("cerrarHoja()")

    # ---------- Alce con la ficha (mismo celular, otra labor) ----------
    pg.evaluate("S.jornada.labor='alce';S.jornada.alces=[];S.jornada.descargues=[];SES={...SES,u:'alc1',nombre:'Alcero Uno'};S.jornada.evaluador='Alcero Uno';S.jornada.usuario='alc1'")
    pg.evaluate(f"NFC.modo='nativo';nfcLeido({{texto:{repr(fichas[1])},id:'04A1B2',t:Date.now()}})"); time.sleep(.4)
    check('Alcero toca la ficha: anuncia los racimos del acopio', any('Acopio con ficha' in x for x in pg.evaluate("window.__dichos||[]")))
    pg.evaluate("__gps(52,41)")
    for _ in range(3): sumar('R')
    a = pg.evaluate("S.jornada.alces[0]")
    check('Los R van al acopio de la ficha y se cuentan contra ella', a['racimos'] == 3 and a['esperados'] == 3 and a['ficha']['id'] == d['aco'] and a['lote'] == 'A1', a)
    check('Al completar: «Acopio 1 completo: 3 de 3»', any('completo: 3 de 3' in x for x in pg.evaluate("window.__dichos||[]")))
    sumar('R')
    check('Un racimo de más: aviso de diferencia con la ficha', any('la ficha dice 3' in x for x in pg.evaluate("window.__dichos||[]")))
    fr_alc = pg.evaluate("compartirJornada(S.jornada)"); pg.evaluate("cerrarHoja()")

    # ---------- Supervisor: recibe las copias y ve el tablero ----------
    pg.evaluate("localStorage.removeItem('cos_copias');QRR.partes={};QRR.recibidas=[]")
    for f in copia_rec + fr_alc:
        pg.evaluate(f"procesarTextoQR({repr(f)})")
    time.sleep(.3)
    # Copia de un cortero en «Corte y recolección» (conteo doble), armada como la arma su celular
    pg.evaluate("""async()=>{const tel=Date.now()-3600e3,j={id:'jcr',labor:'corte_recoleccion',inicio:new Date(tel).toISOString(),inicio_real:new Date(tel+900e3).toISOString(),
        fin:new Date(tel+1800e3).toISOString(),fin_real:new Date(tel+2700e3).toISOString(),hora:{fuente:'gps',desfase_s:900},hora_fin:{fuente:'gps',desfase_s:900},
        evaluador:'Cortero Dos',usuario:'cr2',descargues:[],alces:[]};window.__jcr=j;
      const regs=[{jornada_id:'jcr',racimos:2,lote:'A1'},{jornada_id:'jcr',racimos:1,lote:'B7'}];
      const o={...copiaJornada(j),...(()=>{const r=racimosDeJornada(j,regs);return {rc:r.corte,rr:r.recoleccion,lotes:r.lotes};})()};
      for(const f of await framesCopia(o))await procesarTextoQR(f);}""")
    n = pg.evaluate("Object.keys(copiasSup()).length")
    check('Se recibieron las 3 copias (recolector, alcero, cortero-recolector)', n == 3, n)
    t = pg.evaluate("(()=>{const r=abrirTablero();return {tot:r.tot,lot:r.lot,pend:r.pend.length};})()")
    pg.wait_for_selector('#tsOper')
    check('Tablero: total de racimos de corte y de recolección (conteo doble)', t['tot']['rc'] == 3 and t['tot']['rr'] == 8 and t['tot']['ra'] == 4, t['tot'])
    filas = pg.eval_on_selector_all('#tsOper tr', 'rs=>rs.map(r=>r.textContent)')
    check('Resumen por operario con R corte y R recolección', any('Cortero Dos' in x and 'Corte y recolección' in x and '33' in x.replace(' ','') for x in filas) and 'Total' in filas[-1], filas)
    check('Cuadre por lote: A1 cortados, recolectados y alzados', t['lot']['A1'] == {'c': 2, 'r': 7, 'a': 4}, t['lot'])
    hc = pg.evaluate("(()=>{const c=copiaJornada(__jcr);return {ini:c.ini,fin:c.fin,hf:c.hf,ds:c.ds,iniReal:hhmm(__jcr.inicio_real),finReal:hhmm(__jcr.fin_real)};})()")
    check('Copia con hora real (GPS): inicio y fin corregidos, fuente y desfase', hc['ini'] == hc['iniReal'] and hc['fin'] == hc['finReal'] and hc['hf'] == 'gps' and hc['ds'] == 900, hc)
    al = pg.text_content('#tsAlertas')
    check('Tablero: alerta de hora desfasada más de 10 min (⏰ 15 min atrasada)', '⏰ Cortero Dos' in al and '15 min atrasada' in al, al)
    check('Tablero: marca ⏰ en la fila del operario', any('Cortero Dos' in x and '⏰' in x for x in filas), filas)
    check('Acopio sin alzar: el viaje 2 (sin ficha, sin alce cerca)', t['pend'] == 1 and 'Acopio sin alzar' in pg.text_content('#tsAlertas'))
    if CAPTURA:
        time.sleep(.4); pg.screenshot(path=CAPTURA.replace('.png', '_tablero.png'), full_page=True)
    clic('#tsMapa'); time.sleep(.5)
    check('Ver en el mapa: marcador del acopio sin alzar', pg.evaluate("!!CAPA_PEND&&CAPA_PEND.getLayers().length===1"))
    check('Menú del supervisor: Recibir jornadas y Tablero', pg.evaluate("menu(),!!$('#mRecib')&&!!$('#mTab')&&!!$('#mComp')"))
    pg.evaluate("cerrarHoja()")
    check('Sin errores de JavaScript', not errores, errores[:3])
    nav.close()

print('RESULTADO:', 'TODO OK' if ok else 'HAY FALLAS')
sys.exit(0 if ok else 1)
