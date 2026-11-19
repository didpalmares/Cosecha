"""Visor · cosecha de punta a punta: la App arma el GeoJSON de tres jornadas (el mismo que sincroniza): Corte (R por palma),
Recolección (R por palma + 2 descargues D) y Alce (2 acopios alzados), con fuente, pasadas y transitabilidad; el visor lo lee de
GitHub (simulado) y muestra colores y leyenda, ficha de la palma, filtro por labor, indicadores de Gerencia (🌴 Cosecha), tabla por
lote, mapa de acopios y transitabilidad por lote. Datos ficticios.

Uso: python tests/prueba_visor_cosecha.py   (dirección base con PRUEBAS_URL; Edge con PW_CANAL=msedge)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from comun import CANAL, BASE
import sys, time, json, re
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
ok = True
def check(n, c, x=''):
    global ok
    print(('OK   ' if c else 'FALLA') + ' ' + n + (' · ' + str(x) if x != '' else '')); ok = ok and bool(c)
HOY = date.today().isoformat()
VERDE_R = '#00c853'
LABORES = ['Corte de fruto', 'Recolección con búfalo', 'Corte y recolección', 'Alce de fruto en sendero']
VIEJOS = ('cosechados', 'maduros', 'verdes', 'sobremaduros', 'fruto_suelto', 'a', 'p', 'b', 'cond', 'inflorescencias')

# ---- 1. La App arma los GeoJSON de tres jornadas, como al sincronizar ----
ARMAR = """(hoy)=>{const t=h=>new Date(hoy+'T'+h+':00-05:00').toISOString();
  const reg=(jid,ev,lab,pid,lote,lin,num,x,h,lat)=>completarPol({id:jid+'-'+pid,palma_id:pid,jornada_id:jid,evaluador:ev,labor:lab,racimos:x.r,
    fuente:x.f||'boton',pasadas:x.pas||Array.from({length:x.r},()=>({c:'R',f:x.f||'boton',t:t(h)})),lote,linea:lin,numero:num,lat,lng:-78.70,creado:t(h),fecha:hoy+' '+h,modificado:t(h),
    transitabilidad:x.tr||'Transitable',observaciones:x.obs||'',fotos:[],sync:'pendiente',gps_acc:4,dist_gps:2.5});
  const jor=(id,u,ev,lab,ini,fin,transito,lotes,ev2={})=>({id,labor:lab,evaluador:ev,usuario:u,inicio:t(ini),fin:t(fin),km:1.5,paradas:[],estado:'finalizada',viaje:0,descargues:ev2.D||[],alces:ev2.A||[],
    visita:{palmas_visitadas:60,ha_recorridas:0.5,por_lote:lotes.map(l=>({lote:l,palmas_visitadas:30,ha:0.25}))},transito,secuencias:[],tiempos:null,seleccion:lotes.map(l=>({lote:l}))});
  const pas=[{c:'R',f:'boton',t:t('07:10')},{c:'R',f:'nfc',t:t('07:10')},{c:'R',f:'boton',t:t('07:11')}];
  const G='GOMEZ PEREZ ANDRES',Lz='LOPEZ DIAZ CARLOS',Rz='RUIZ MORA JUAN';
  const J1=jor('J1','op1',G,'corte','07:00','08:05',[{lote:'IT01',entrada:'Transitable',t_entrada:t('07:05'),salida:'Poco transitable',t_salida:t('08:00'),cierre:'boton'}],['IT01']);
  const R1=[reg('J1',G,'corte','P101','IT01',3,1,{r:3,pas,obs:'Racimo pesado'},'07:10',1.5000),
    reg('J1',G,'corte','P102','IT01',3,2,{r:1,f:'nfc'},'07:12',1.5002),
    reg('J1',G,'corte','P103','IT01',3,3,{r:2,f:'voz'},'07:14',1.5004),
    reg('J1',G,'corte','P104','IT01',3,4,{r:2,f:'formulario'},'07:16',1.5006)];
  const dsc=(n,r,lote,h,lat)=>({id:'d'+n,n,racimos:r,t:t(h),hora:h,lat,lng:-78.7005,acc:3,lote,fuente:'nfc'});
  const J2=jor('J2','op2',Lz,'recoleccion','08:20','09:30',[{lote:'IT05',entrada:'Poco transitable',t_entrada:t('08:30'),salida:'Transitable',t_salida:t('08:50'),cierre:'boton'},
    {lote:'IT01',entrada:'Transitable',t_entrada:t('08:55'),salida:'',t_salida:''}],['IT05','IT01'],{D:[dsc(1,4,'IT05','08:45',1.5110),dsc(2,3,'IT01','09:10',1.5010)]});
  const R2=[reg('J2',Lz,'recoleccion','P201','IT05',1,1,{r:3,tr:'Poco transitable'},'08:31',1.5100),
    reg('J2',Lz,'recoleccion','P202','IT05',1,2,{r:1,tr:'Poco transitable'},'08:33',1.5102),
    reg('J2',Lz,'recoleccion','P203','IT05',1,3,{r:2,tr:'Poco transitable'},'08:35',1.5104),
    reg('J2',Lz,'recoleccion','P102','IT01',3,2,{r:1},'09:00',1.5002)];
  const alc=(n,r,lote,h,lat)=>({id:'a'+n,n,racimos:r,lat,lng:-78.7006,acc:3,lote,t_ini:t(h),t_fin:t(h),hora:h,fuente:'boton'});
  const J3=jor('J3','op3',Rz,'alce','10:00','10:40',[{lote:'IT05',entrada:'No transitable',t_entrada:t('10:05'),salida:'No transitable',t_salida:t('10:35'),cierre:'boton'}],['IT05'],
    {A:[alc(1,5,'IT05','10:10',1.5112),alc(2,2,'IT01','10:30',1.5012)]});
  const ahora=new Date().toISOString();
  return {g1:geoJornada(J1,R1,[],ahora,null),g2:geoJornada(J2,R2,[],ahora,null),g3:geoJornada(J3,[],[],ahora,null),csv:csvRegs(R1).split('\\r\\n')[0]};}"""
errores = []
EST = {}
def gh(route):
    u = route.request.url
    if '/contents/jornadas?' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps([{'type': 'dir', 'name': HOY, 'sha': 'dia1'}]))
    if u.endswith('/git/trees/dia1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps({'tree': [
        {'path': 'J1.geojson', 'type': 'blob', 'sha': 'g1'}, {'path': 'J2.geojson', 'type': 'blob', 'sha': 'g2'}, {'path': 'J3.geojson', 'type': 'blob', 'sha': 'g3'}]}))
    if u.endswith('/git/blobs/g1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g1']))
    if u.endswith('/git/blobs/g2'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g2']))
    if u.endswith('/git/blobs/g3'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g3']))
    route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 1400, 'height': 950}, accept_downloads=True, timezone_id='America/Bogota', locale='es-CO')
    ctx.route('https://api.github.com/**', gh)
    app = ctx.new_page(); app.on('pageerror', lambda e: errores.append('app: ' + str(e)[:200]))
    app.goto(BASE + '/index.html'); app.wait_for_function("typeof geoJornada==='function'&&typeof completarPol==='function'&&typeof S!=='undefined'", timeout=30000); time.sleep(1.5)
    r = app.evaluate(ARMAR, HOY)
    g1, g2, g3 = r['g1'], r['g2'], r['g3']
    f101 = next(f for f in g1['features'] if f['properties'].get('palma_id') == 'P101')['properties']
    check('Sincronización: el punto lleva R (racimos), labor, fuente y pasadas (sin C/M/V/S/F, a, p, b, cond, inflorescencias)',
          f101['racimos'] == 3 and f101['labor'] == 'corte' and f101['nivel1'] == '3R' and f101['n1_codigo'] == 'R' and f101['fuente'] == 'boton'
          and len(f101['pasadas']) == 3 and f101['n_pasadas'] == 3 and f101['tipo'] == 'diagnostico' and not any(k in f101 for k in VIEJOS),
          {k: f101.get(k) for k in ('racimos', 'labor', 'nivel1', 'n1_codigo', 'fuente', 'n_pasadas') + VIEJOS if k in f101})
    check('Sincronización: la jornada lleva la labor y la transitabilidad de cada lote',
          g1['jornada']['labor'] == 'corte' and g1['jornada']['labor_nombre'] == 'Corte de fruto' and g1['jornada']['transito'][0]['salida'] == 'Poco transitable' and len(g2['jornada']['transito']) == 2, g1['jornada'].get('transito'))
    tip2 = [f['properties']['tipo'] for f in g2['features']]
    check('Recolección: 2 viajes (D) con 7 R descargados y sus puntos «descargue»',
          g2['jornada']['labor'] == 'recoleccion' and g2['jornada']['viajes'] == 2 and g2['jornada']['racimos_descargados'] == 7 and g2['jornada']['racimos_viaje_abierto'] == 0
          and tip2.count('descargue') == 2 and tip2.count('diagnostico') == 4, (g2['jornada'].get('viajes'), tip2))
    tip3 = [f['properties']['tipo'] for f in g3['features']]
    check('Alce: 2 acopios con 7 R alzados, sin registros de palma',
          g3['jornada']['labor'] == 'alce' and g3['jornada']['acopios_alzados'] == 2 and g3['jornada']['racimos_alzados'] == 7 and tip3.count('alce') == 2 and 'diagnostico' not in tip3, tip3)
    cab_app = r['csv'].lstrip('\ufeff').split(';')
    check('CSV de la App: columnas labor, racimos, transitabilidad y fuente (sin conteos antiguos)',
          all(c in cab_app for c in ['labor', 'racimos', 'transitabilidad', 'fuente', 'n_pasadas']) and not any(c in cab_app for c in VIEJOS), r['csv'][:200])
    # Importar en otro celular (historial): recupera los campos
    imp = app.evaluate("""async(g)=>{await importarJornadaGeo(g,null);const x=await dbGet('registros','J1-P101'),j=await dbGet('jornadas','J1');
      return {r:x.racimos,lab:x.labor,f:x.fuente,pas:(x.pasadas||[]).length,n1:x.n1,cod:x.n1_codigo,tr:(j.transito||[]).length,jl:j.labor};}""", g1)
    check('Importar la jornada (historial) recupera R, labor, fuente, pasadas y transitabilidad',
          imp == {'r': 3, 'lab': 'corte', 'f': 'boton', 'pas': 3, 'n1': '3R', 'cod': 'R', 'tr': 1, 'jl': 'corte'}, imp)
    # Registro sin el conteo (solo con el resumen «2R»): el visor lo lee del resumen
    f104 = next(f for f in g1['features'] if f['properties'].get('palma_id') == 'P104')['properties']
    for k in ('racimos', 'pasadas', 'n_pasadas'): f104.pop(k, None)
    EST['g1'], EST['g2'], EST['g3'] = g1, g2, g3

    # ---- 2. Visor ----
    vz = ctx.new_page(); vz.on('pageerror', lambda e: errores.append('visor: ' + str(e)[:200] + ' ' + (e.stack or '')[:300]))
    vz.goto(BASE + '/visor.html'); vz.wait_for_function("typeof alternarGerencia==='function'&&typeof cargar==='function'", timeout=30000); time.sleep(1)
    vz.evaluate("""async(hoy)=>{document.querySelector('#login').hidden=true;document.querySelector('#app').hidden=false;mapa.invalidateSize();window.chunkLote=async()=>[];
      SES={u:'admin1',nombre:'Admin',rol:'admin',token:'tok',repo:{owner:'didpalmares',repo:'CosechaData',rama:'main'}};ACCESO={usuarios:[]};aplicarPermisosGer();
      LOTES={type:'FeatureCollection',features:['IT01','IT05'].map((l,k)=>({type:'Feature',properties:{_lote:l},geometry:{type:'Polygon',coordinates:[[[-78.701,1.499+k*0.01],[-78.699,1.499+k*0.01],[-78.699,1.508+k*0.01],[-78.701,1.508+k*0.01],[-78.701,1.499+k*0.01]]]}}))};
      IND_LOTES={IT01:{n:500},IT05:{n:400}};opcionesLote();
      document.querySelector('#fDesde').value=hoy;document.querySelector('#fHasta').value=hoy;await cargar();}""", HOY)
    vz.wait_for_function("JOR.length===3", timeout=15000); time.sleep(.5)
    check('Visor: lee las 3 jornadas sincronizadas con su labor', vz.evaluate("JOR.map(j=>j.id+':'+j.labor).sort().join()") == 'J1:corte,J2:recoleccion,J3:alce')
    check('Visor: lee los descargues y los acopios de cada jornada',
          vz.evaluate("JOR.map(j=>j.id+':'+j.descargues.length+'D'+j.alces.length+'A').sort().join()") == 'J1:0D0A,J2:2D0A,J3:0D2A')
    # Leyenda
    ley = vz.inner_text('#leyenda')
    check('Leyenda: R (palma con racimos), D (descargue) y acopio alzado', 'R: Palma con racimos' in ley and 'D: Descargue del viaje' in ley and 'Acopio alzado (Alce)' in ley, ley[:200])
    check('Leyenda: sin enfermedades ni códigos anteriores', 'Pudrición' not in ley and 'Enfermedad' not in ley and 'Racimo cosechado' not in ley)
    # Colores del mapa: último registro de cada palma
    col = vz.evaluate("(()=>{const o={};capaDiag.eachLayer(l=>{o[l.options.palma_id]=[l.options.codigo,l.options.fillColor];});return o;})()")
    check('Mapa: una palma por marcador (7), todas con R en verde', col == {k: ['R', VERDE_R] for k in ['P101', 'P102', 'P103', 'P104', 'P201', 'P202', 'P203']}, col)
    ev = vz.evaluate("(()=>{const a=[];capaPar.eachLayer(l=>{if(l.options&&l.options.fillColor)a.push(l.options.fillColor);});return a.sort();})()")
    check('Mapa: 2 descargues (azul) y 2 acopios alzados (naranja)', ev == sorted(['#1e88e5', '#1e88e5', '#ff6d00', '#ff6d00']), ev)

    def ficha(pid):
        try:
            vz.evaluate(f"popupDiag(DIAGF.find(d=>d.palma_id==='{pid}'))"); time.sleep(.4)
            return vz.inner_text('.leaflet-popup-content')
        except Exception as e:
            return 'ERROR: ' + str(e).splitlines()[0]
    pop = ficha('P101')
    check('Ficha: resumen 3R, racimos y labor', '3R' in pop and 'R: Racimos: 3' in pop and 'Labor: Corte de fruto' in pop, pop[:300])
    check('Ficha: operario, fecha y hora, transitabilidad, fuente y observación',
          'Operario: GOMEZ PEREZ ANDRES' in pop and f'Fecha y hora: {HOY} 07:10' in pop and 'Transitabilidad: Transitable' in pop and 'Fuente: Botón, Tarjeta NFC' in pop and 'Observación: Racimo pesado' in pop, pop[:400])
    check('Ficha: sin campos de enfermedad (cirugía, estado)', 'Cirugía' not in pop and 'Enfermedad' not in pop and 'Estado' not in pop)
    pop = ficha('P201')
    check('Ficha de Recolección: labor y fuente', 'Labor: Recolección con búfalo' in pop and 'R: Racimos: 3' in pop and 'Fuente: Botón' in pop, pop[:300])
    pop = ficha('P104')
    check('Ficha de un registro sin el conteo (solo resumen «2R»): se lee del resumen', '2R' in pop and 'R: Racimos: 2' in pop, pop[:200])
    vz.evaluate("mapa.closePopup()")
    # Panel: resumen y pestañas
    vz.click('nav.tabs [data-tab=resumen]'); time.sleep(.3)
    kp = re.sub(r'\s+', ' ', vz.inner_text('#kpisPol')).upper()
    check('Resumen del visor: R corte 8 · R recolección 7 · R corte y recolección 0 · 2 viajes · 3,5 R por viaje · 7 R alzados (2 acopios)',
          kp == '8 R · CORTE DE FRUTO 7 R · RECOLECCIÓN CON BÚFALO 0 R · CORTE Y RECOLECCIÓN 2 VIAJES DESCARGADOS (D) 3,5 R POR VIAJE 7 R ALZADOS (2 ACOPIOS)', kp)
    rk = vz.inner_text('#panel')
    check('Resumen del visor: 7 palmas registradas y 15 racimos (R) en palma', re.search(r'7\s+Palmas registradas', rk, re.I) is not None and re.search(r'15\s+Racimos \(R\) en palma', rk, re.I) is not None,
          re.sub(r'\s+', ' ', rk)[:300])
    br = vz.evaluate("Object.fromEntries([...document.querySelectorAll('#panel .barra[data-bar]')].map(b=>[b.dataset.bar,b.querySelector('.n').innerText]))")
    check('Cosecha por labor: barras corte 8, recolección 7, corte y recolección 0, alce 7', br == {'corte': '8', 'recoleccion': '7', 'corte_recoleccion': '0', 'alce': '7'}, br)
    try:
        vz.click('nav.tabs [data-tab=diag]'); time.sleep(.3)
        T = vz.inner_text('#panel')
    except Exception as e:
        T = 'ERROR: ' + str(e).splitlines()[0]
    check('Pestaña REGISTROS: 8 registros con código, transitabilidad y fuente', '8 registro(s)' in T and 'Tarjeta NFC' in T and 'Formulario' in T, T[:160])
    vz.click('nav.tabs [data-tab=lotes]'); time.sleep(.3)
    th = [c.strip() for c in vz.evaluate("[...document.querySelectorAll('#tLot thead th')].map(t=>t.innerText)")]
    check('Pestaña LOTES: columnas de R por labor, viajes y alzados (sin C/M/V/S/F)',
          all(h in th for h in ['Palmas registradas', 'R en palma', 'R corte', 'R recolección', 'R corte y recol.', 'Viajes (D)', 'R descargados', 'R alzados'])
          and not any(h in th for h in ['C', 'M', 'V', 'S', 'F (palmas)', 'PC']), th)
    lot = vz.evaluate("""(()=>{const th=[...document.querySelectorAll('#tLot thead th')].map(t=>t.innerText.trim());
      return Object.fromEntries([...document.querySelectorAll('#tLot tbody tr')].map(tr=>{const c=[...tr.cells].map(x=>x.innerText.trim());
        return [c[0],['Palmas registradas','R en palma','R corte','R recolección','R corte y recol.','Viajes (D)','R descargados','R alzados'].map(h=>c[th.indexOf(h)]).join(' ')];}));})()""")
    check('Pestaña LOTES: IT01 4 palmas, 9 R (8 corte, 1 recolección), 1 viaje, 3 descargados, 2 alzados; IT05 3 palmas, 6 R recolección, 1 viaje, 4 descargados, 5 alzados',
          lot.get('IT01') == '4 9 8 1 0 1 3 2' and lot.get('IT05') == '3 6 0 6 0 1 4 5', lot)
    # Filtro por labor (interfaz)
    lbl = vz.evaluate("document.querySelector('#filtros .ms[data-k=cod]').parentNode.querySelector('label').innerText")
    vz.click('#filtros .ms[data-k=cod] .ms-bt'); time.sleep(.2)
    ops = vz.evaluate("[...document.querySelectorAll('#msL .ms-it span')].map(s=>s.innerText)")
    check('Filtro Labor: Corte, Recolección, Corte y recolección y Alce', lbl.strip().upper() == 'LABOR' and ops == LABORES, (lbl, ops))
    vz.click('#msL .solo[data-i="1"]'); time.sleep(.4)
    fb = vz.evaluate("({j:JORF.map(j=>j.id).join(),n:DIAGF.length,m:(()=>{const a=[];capaDiag.eachLayer(l=>a.push(l.options.palma_id));return a.sort().join();})(),bt:document.querySelector('#filtros .ms[data-k=cod] .ms-bt').innerText})")
    check('Filtro Labor = Recolección: jornada J2, 4 registros (P201, P202, P203 y P102) y el botón lo dice',
          fb == {'j': 'J2', 'n': 4, 'm': 'P102,P201,P202,P203', 'bt': 'Recolección con búfalo'}, fb)
    vz.evaluate("msSolo('cod','alce');aplicarFiltros(false)"); time.sleep(.2)
    fa = vz.evaluate("(()=>{const e=totalesEventos(JORF);return {j:JORF.map(j=>j.id).join(),n:DIAGF.length,a:e.acopios,ra:e.r_alzados,v:e.viajes}})()")
    check('Filtro Labor = Alce: solo J3, sin registros de palma, 2 acopios con 7 R', fa == {'j': 'J3', 'n': 0, 'a': 2, 'ra': 7, 'v': 0}, fa)
    vz.evaluate("msSolo('cod',null);aplicarFiltros(false)"); time.sleep(.2)
    check('Sin filtros de enfermedad en el visor', vz.evaluate("!document.querySelector('#filtros [data-k=n1]')&&!document.querySelector('#filtros [data-k=est]')&&Object.keys(FIL).join()") == 'prog,op,lote,cod')
    # Detalle de jornada: transitabilidad
    vz.evaluate("abrirDetalle(JOR.find(j=>j.id==='J2'))"); time.sleep(.4)
    det = vz.inner_text('#detalle')
    check('Detalle de la jornada: transitabilidad por lote y lote abierto', 'TRANSITABILIDAD POR LOTE' in det.upper() and 'Sin salida (lote abierto)' in det and 'Registros: 4' in det, det[-300:])
    vz.evaluate("cerrarDetalle()")

    # ---- 3. Gerencia · 🌴 Cosecha ----
    vz.click('#btGer'); time.sleep(.5)
    T = vz.inner_text('#gerPanel')
    check('Gerencia: secciones Resumen, Cosecha y Mapa de avance (sin Enfermedades)', '🌴 Cosecha' in T and 'Mapa de avance de la cosecha' in T and 'Enfermedades' not in T and 'censo' not in T.lower(), re.sub(r'\s+', ' ', T)[:200])
    check('Gerencia: filtro Labor en la barra (sin enfermedad ni estado)', vz.evaluate("!!document.querySelector('#gerFil .ms[data-k=cod]')&&!document.querySelector('#gerFil .ms[data-k=n1]')&&!document.querySelector('#gerFil .ms[data-k=est]')"))
    glbl = vz.evaluate("document.querySelector('#gerFil .ms[data-k=cod]').parentNode.firstChild.textContent.trim()")
    check('Gerencia: el filtro de labor se llama «Labor» (como en el visor)', glbl == 'Labor', glbl)
    check('Gerencia · Resumen: palmas registradas y racimos (R) en palma', 'Palmas registradas' in T and 'Racimos (R) en palma' in T and 'Inflorescencias' not in T and 'Diagnósticos' not in T)
    vz.click('[data-tsub=pol]'); time.sleep(1)
    K = [re.sub(r'\s+', ' ', x) for x in vz.evaluate("[...document.querySelectorAll('#polKpis .ger-kpi')].map(k=>k.innerText)")]
    check('KPIs: 7 palmas con R, R por labor 8/7/0, 2 viajes, 7 R descargados, 3,5 R por viaje, 7 R alzados en 2 acopios',
          K == ['7 Palmas con R', '8 R · Corte de fruto', '7 R · Recolección con búfalo', '0 R · Corte y recolección', '2 Viajes descargados (D)', '7 R descargados',
                '3,5 R por viaje', '7 R alzados · 2 acopios (Alce)'], K)
    th = vz.evaluate("[...document.querySelectorAll('#polLotes thead th')].map(t=>t.innerText.trim())")
    filas = vz.evaluate("[...document.querySelectorAll('#polLotes tbody tr')].map(t=>[...t.cells].map(c=>c.innerText.trim()))")
    check('Por lote: columnas de R por labor, viajes, descargados, alzados y pendiente de alce', 'Pendiente de alce' in th and 'Viajes (D)' in th and 'R alzados' in th, th)
    check('Por lote: IT01 4 palmas, R 8/1/0, 1 viaje, 3 descargados, 2 alzados, 1 pendiente de alce, entrada Transitable, salida Poco transitable (1 sin salida)',
          bool(filas) and filas[0] == ['IT01', '—', '4', '8', '1', '0', '1', '3', '2', '1', 'Transitable', 'Poco transitable 1 sin salida'], filas[0] if filas else filas)
    check('Por lote: IT05 3 palmas, R 0/6/0, 1 viaje, 4 descargados, 5 alzados, nada pendiente, entrada Poco transitable, salida Transitable',
          len(filas) == 2 and filas[1] == ['IT05', '—', '3', '0', '6', '0', '1', '4', '5', '0', 'Poco transitable', 'Transitable'], filas[1:])
    bar = vz.evaluate("[...document.querySelectorAll('#polBarLote rect')].map(r=>r.dataset.lc)")
    check('Gráfico por lote: R por labor y R alzados apilados', sorted(bar) == sorted(['IT01|corte|8', 'IT01|recoleccion|1', 'IT01|r_alzados|2', 'IT05|recoleccion|6', 'IT05|r_alzados|5']), bar)
    sem = vz.evaluate("[...document.querySelectorAll('#polSemana rect')].map(r=>r.dataset.sc.split('|').slice(1).join(''))")
    check('Gráfico por semana: corte 8, recolección 7, alzados 7', sorted(sem) == ['corte8', 'r_alzados7', 'recoleccion7'], sem)
    oth = vz.evaluate("[...document.querySelectorAll('#polOps thead th')].map(t=>t.innerText.trim())")
    check('Rendimiento por operario: columnas Operario, Labores, Días, Racimos (R), R/día y Viajes (D)', oth[:6] == ['Operario', 'Labores', 'Días', 'Racimos (R)', 'R/día', 'Viajes (D)'], oth)
    ops = vz.evaluate("[...document.querySelectorAll('#polOps tbody tr')].map(t=>[...t.cells].slice(0,7).map(c=>c.innerText.trim()))")
    check('Rendimiento por operario: labores, racimos (en palma y alzados), R/día, viajes y palmas con R',
          ops == [['GOMEZ PEREZ ANDRES', 'Corte', '1', '8', '8,0', '0', '4'], ['LOPEZ DIAZ CARLOS', 'Recolección', '1', '7', '7,0', '2', '4'], ['RUIZ MORA JUAN', 'Alce', '1', '7', '7,0', '0', '0']], ops)
    rv = vz.evaluate("({n:GER.rvN,m:(()=>{const a=[];GER.rv.eachLayer(l=>{if(l.options&&l.options.codigo)a.push(l.options.codigo+l.options.fillColor);});return a.sort();})(),e:document.querySelector('#rvEstado').innerText})")
    check('Mapa de acopios: 2 descargues (azul) y 2 acopios alzados (naranja)', rv['n'] == 4 and rv['m'] == sorted(['D#1e88e5', 'D#1e88e5', 'A#ff6d00', 'A#ff6d00'])
          and '2 descargues (7 R)' in rv['e'] and '2 acopios alzados (7 R)' in rv['e'], rv)
    with vz.expect_download() as dl: vz.click('#xPolEv')
    cab = open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    cols = cab[0].split(';')
    check('CSV de descargues y acopios: 4 filas (2 descargue, 2 acopio_alzado) con labor, lote y racimos',
          cols == ['tipo', 'fecha', 'hora', 'operario', 'labor', 'lote', 'n', 'racimos', 'lat', 'lng', 'fuente'] and len(cab) == 5
          and sum(l.startswith('descargue;') for l in cab) == 2 and sum(l.startswith('acopio_alzado;') for l in cab) == 2, cab[:3])
    try:
        with vz.expect_download(timeout=5000) as dl: vz.click('#xPolReg')
        cab = open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    except Exception as e:
        cab = ['ERROR: ' + str(e).splitlines()[0]]
    cols = cab[0].split(';')
    check('CSV de registros: labor, racimos, resumen, transitabilidad y fuente (sin conteos antiguos), 8 filas',
          all(c in cols for c in ['labor', 'racimos', 'resumen', 'codigo', 'transitabilidad', 'fuente']) and not any(c in cols for c in VIEJOS) and len(cab) == 9, cols)
    if len(cab) > 1:
        fila = dict(zip(cols, next((l for l in cab[1:] if 'P101' in l), '').split(';')))
        check('CSV de registros: fila de P101', fila.get('racimos') == '3' and fila.get('resumen') == '3R' and fila.get('codigo') == 'R'
              and fila.get('labor') == 'Corte de fruto' and fila.get('fuente') == 'Botón, Tarjeta NFC', fila)
    # Filtro de labor desde Gerencia
    vz.evaluate("msSolo('cod','recoleccion');aplicarFiltros(false)"); time.sleep(.5)
    K = [re.sub(r'\s+', ' ', x) for x in vz.evaluate("[...document.querySelectorAll('#polKpis .ger-kpi')].map(k=>k.innerText)")]
    check('Gerencia respeta el filtro Labor (Recolección: 4 palmas, 7 R, 2 viajes, sin alce)', K[:3] == ['4 Palmas con R', '0 R · Corte de fruto', '7 R · Recolección con búfalo']
          and K[4] == '2 Viajes descargados (D)' and K[7].startswith('0 R alzados'), K)
    vz.evaluate("msSolo('cod',null);aplicarFiltros(false)"); time.sleep(.3)
    # Mapa de avance
    vz.click('[data-tsub=avance]'); time.sleep(1.2)
    check('Mapa de avance de la cosecha (título)', 'AVANCE DE LA COSECHA' in vz.inner_text('#avLeyenda').upper())
    # ---- 4. Coordinación y supervisión: transitabilidad ----
    vz.click('#btCoord'); time.sleep(.3)
    tabs = [b.inner_text() for b in vz.query_selector_all('#gerPanel [data-gt]')]
    check('Coordinación: pestaña TRANSITABILIDAD', 'TRANSITABILIDAD' in tabs and 'CALIDAD' in tabs and 'AUDITORÍA' in tabs, tabs)
    vz.click('[data-gt=transito]'); time.sleep(.4)
    T = vz.inner_text('#gerPanel')
    tr = vz.evaluate("[...document.querySelectorAll('#trTabla tbody tr')].map(t=>[...t.cells].map(c=>c.innerText.trim()))")
    check('Transitabilidad por lote: 4 entradas (lote, operario, entrada + hora, salida + hora, duración)',
          len(tr) == 4 and tr[0][1:] == ['IT01', 'GOMEZ PEREZ ANDRES', 'Transitable 07:05', 'Poco transitable 08:00', '0:55'] and tr[1][1:] == ['IT05', 'LOPEZ DIAZ CARLOS', 'Poco transitable 08:30', 'Transitable 08:50', '0:20']
          and tr[3][1:] == ['IT05', 'RUIZ MORA JUAN', 'No transitable 10:05', 'No transitable 10:35', '0:30'], tr)
    check('Transitabilidad: marca el lote abierto (sin salida)', len(tr) > 2 and tr[2][1] == 'IT01' and 'Sin salida' in tr[2][4] and tr[2][5] == '—' and '1 lote(s) quedaron abiertos' in T, tr[2] if len(tr) > 2 else T[:200])
    # Calidad y auditoría con el registro de cosecha
    vz.click('[data-gt=calidad]'); time.sleep(.4); T = vz.inner_text('#gerPanel')
    check('Calidad: registros (sin «Sin foto» ni diagnósticos)', 'Registros de cosecha' in T and 'Sin foto' not in T and 'iagnóstico' not in T, re.sub(r'\s+', ' ', T)[:200])
    vz.click('[data-gt=auditoria]'); time.sleep(.4); T = vz.inner_text('#gerPanel')
    check('Auditoría: textos de la cosecha', 'registros de cada operario' in T and 'censador' not in T.lower())
    vz.click('#gerX')
    check('Sin errores de JavaScript', not errores, errores[:4])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
