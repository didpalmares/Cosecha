"""Visor · cosecha de punta a punta: la App arma el GeoJSON de la jornada (el mismo que sincroniza) con C, M, V, S, F,
fuente, pasadas y transitabilidad; el visor lo lee de GitHub (simulado) y muestra colores y leyenda, ficha de la palma,
filtro por código, indicadores de Gerencia (🌴 Cosecha), tabla por lote y transitabilidad por lote. Datos ficticios.

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
COLORES = {'C': '#00c853', 'M': '#ffab00', 'V': '#1e88e5', 'S': '#6d4c41', 'F': '#e53935'}
NOMBRES = {'C': 'Racimo cosechado', 'M': 'Racimo maduro dejado sin cortar', 'V': 'Racimo verde cortado', 'S': 'Racimo sobremaduro / podrido', 'F': 'Fruto suelto sin recoger'}

# ---- 1. La App arma los GeoJSON de dos jornadas, como al sincronizar ----
ARMAR = """(hoy)=>{const t=h=>new Date(hoy+'T'+h+':00-05:00').toISOString();
  const reg=(jid,ev,pid,lote,lin,num,x,h,lat)=>completarPol({id:jid+'-'+pid,palma_id:pid,jornada_id:jid,evaluador:ev,labor:'cosecha',cosechados:x.c||0,maduros:x.m||0,verdes:x.v||0,sobremaduros:x.s||0,fruto_suelto:x.fs||0,
    fuente:x.f||'boton',pasadas:x.pas||[{c:x.fs?'F':x.v?'V':'C',f:x.f||'boton',t:t(h)}],lote,linea:lin,numero:num,lat,lng:-78.70,creado:t(h),fecha:hoy+' '+h,modificado:t(h),
    transitabilidad:x.tr||'Transitable',observaciones:x.obs||'',fotos:[],sync:'pendiente',gps_acc:4,dist_gps:2.5});
  const jor=(id,u,ev,ini,fin,transito,lotes)=>({id,labor:'cosecha',evaluador:ev,usuario:u,inicio:t(ini),fin:t(fin),km:1.5,paradas:[],estado:'finalizada',
    visita:{palmas_visitadas:60,ha_recorridas:0.5,por_lote:lotes.map(l=>({lote:l,palmas_visitadas:30,ha:0.25}))},transito,secuencias:[],tiempos:null,seleccion:lotes.map(l=>({lote:l}))});
  const pas=[{c:'C',f:'boton',t:t('07:10')},{c:'C',f:'nfc',t:t('07:10')},{c:'M',f:'boton',t:t('07:11')},{c:'S',f:'boton',t:t('07:11')}];
  const J1=jor('J1','op1','GOMEZ PEREZ ANDRES','07:00','08:05',[{lote:'IT01',entrada:'Transitable',t_entrada:t('07:05'),salida:'Poco transitable',t_salida:t('08:00'),cierre:'boton'}],['IT01']);
  const R1=[reg('J1','GOMEZ PEREZ ANDRES','P101','IT01',3,1,{c:2,m:1,s:1,pas,obs:'Racimo pesado'},'07:10',1.5000),
    reg('J1','GOMEZ PEREZ ANDRES','P102','IT01',3,2,{c:1,f:'nfc'},'07:12',1.5002),
    reg('J1','GOMEZ PEREZ ANDRES','P103','IT01',3,3,{fs:1,f:'voz'},'07:14',1.5004),
    reg('J1','GOMEZ PEREZ ANDRES','P104','IT01',3,4,{s:2,f:'formulario'},'07:16',1.5006)];
  const J2=jor('J2','op2','LOPEZ DIAZ CARLOS','08:20','09:30',[{lote:'IT05',entrada:'Poco transitable',t_entrada:t('08:30'),salida:'Transitable',t_salida:t('08:50'),cierre:'boton'},
    {lote:'IT01',entrada:'Transitable',t_entrada:t('08:55'),salida:'',t_salida:''}],['IT05','IT01']);
  const R2=[reg('J2','LOPEZ DIAZ CARLOS','P201','IT05',1,1,{m:3,tr:'Poco transitable'},'08:31',1.5100),
    reg('J2','LOPEZ DIAZ CARLOS','P202','IT05',1,2,{v:1,tr:'Poco transitable'},'08:33',1.5102),
    reg('J2','LOPEZ DIAZ CARLOS','P203','IT05',1,3,{c:1,tr:'Poco transitable'},'08:35',1.5104),
    reg('J2','LOPEZ DIAZ CARLOS','P204','IT05',1,4,{c:1,m:2,tr:'Poco transitable'},'08:37',1.5106),
    reg('J2','LOPEZ DIAZ CARLOS','P102','IT01',3,2,{s:1},'09:00',1.5002)];
  const ahora=new Date().toISOString();
  return {g1:geoJornada(J1,R1,[],ahora,null),g2:geoJornada(J2,R2,[],ahora,null),plano:planos(R1[0]),csv:csvRegs(R1).split('\\r\\n')[0]};}"""
errores = []
EST = {}
def gh(route):
    u = route.request.url
    if '/contents/jornadas?' in u: return route.fulfill(status=200, content_type='application/json', body=json.dumps([{'type': 'dir', 'name': HOY, 'sha': 'dia1'}]))
    if u.endswith('/git/trees/dia1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps({'tree': [
        {'path': 'J1.geojson', 'type': 'blob', 'sha': 'g1'}, {'path': 'J2.geojson', 'type': 'blob', 'sha': 'g2'}]}))
    if u.endswith('/git/blobs/g1'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g1']))
    if u.endswith('/git/blobs/g2'): return route.fulfill(status=200, content_type='application/json', body=json.dumps(EST['g2']))
    route.fulfill(status=404, content_type='application/json', body='{"message":"Not Found"}')

with sync_playwright() as p:
    nav = p.chromium.launch(**CANAL, headless=True)
    ctx = nav.new_context(service_workers='block', viewport={'width': 1400, 'height': 950}, accept_downloads=True, timezone_id='America/Bogota', locale='es-CO')
    ctx.route('https://api.github.com/**', gh)
    app = ctx.new_page(); app.on('pageerror', lambda e: errores.append('app: ' + str(e)[:200]))
    app.goto(BASE + '/index.html'); app.wait_for_function("typeof geoJornada==='function'&&typeof completarPol==='function'&&typeof S!=='undefined'", timeout=30000); time.sleep(1.5)
    r = app.evaluate(ARMAR, HOY)
    g1, g2 = r['g1'], r['g2']
    f101 = next(f for f in g1['features'] if f['properties'].get('palma_id') == 'P101')['properties']
    check('Sincronización: el punto lleva C, M, V, S, F, racimos, fuente, labor y pasadas (sin a, p, b, cond, inflorescencias)',
          (f101['cosechados'], f101['maduros'], f101['verdes'], f101['sobremaduros'], f101['fruto_suelto']) == (2, 1, 0, 1, 0) and f101['racimos'] == 3 and f101['fuente'] == 'boton'
          and f101['labor'] == 'cosecha' and len(f101['pasadas']) == 4 and f101['n_pasadas'] == 4 and f101['nivel1'] == '2C + 1M + 1S' and f101['n1_codigo'] == 'M'
          and not any(k in f101 for k in ('a', 'p', 'b', 'cond', 'inflorescencias')),
          {k: f101.get(k) for k in ('cosechados', 'maduros', 'verdes', 'sobremaduros', 'fruto_suelto', 'racimos', 'fuente', 'nivel1', 'n1_codigo', 'a', 'cond', 'inflorescencias')})
    check('Sincronización: la jornada lleva la transitabilidad de cada lote y la labor',
          g1['jornada']['labor'] == 'cosecha' and g1['jornada']['transito'][0]['salida'] == 'Poco transitable' and len(g2['jornada']['transito']) == 2, g1['jornada'].get('transito'))
    cab_app = r['csv'].lstrip('\ufeff').split(';')
    check('CSV de la App: columnas cosechados, maduros, verdes, sobremaduros, fruto_suelto, racimos, transitabilidad y fuente',
          all(c in cab_app for c in ['cosechados', 'maduros', 'verdes', 'sobremaduros', 'fruto_suelto', 'racimos', 'transitabilidad', 'fuente'])
          and not any(c in cab_app for c in ['a', 'p', 'b', 'cond', 'inflorescencias']), r['csv'][:200])
    # Importar en otro celular (historial): recupera los campos
    imp = app.evaluate("""async(g)=>{await importarJornadaGeo(g,null);const x=await dbGet('registros','J1-P101'),y=await dbGet('registros','J1-P103'),j=await dbGet('jornadas','J1');
      return {c:x.cosechados,m:x.maduros,v:x.verdes,s:x.sobremaduros,f:x.fuente,pas:(x.pasadas||[]).length,n1:x.n1,fs:y.fruto_suelto,n1y:y.n1,tr:(j.transito||[]).length};}""", g1)
    check('Importar la jornada (historial) recupera C, M, V, S, F, fuente, pasadas y transitabilidad',
          imp == {'c': 2, 'm': 1, 'v': 0, 's': 1, 'f': 'boton', 'pas': 4, 'n1': '2C + 1M + 1S', 'fs': 1, 'n1y': 'F', 'tr': 1}, imp)
    # Registro sin los conteos (solo con el resumen «1C + 2M»): el visor lo lee del resumen
    f204 = next(f for f in g2['features'] if f['properties'].get('palma_id') == 'P204')['properties']
    for k in ('cosechados', 'maduros', 'verdes', 'sobremaduros', 'fruto_suelto', 'racimos', 'pasadas', 'n_pasadas'): f204.pop(k, None)
    EST['g1'], EST['g2'] = g1, g2

    # ---- 2. Visor ----
    vz = ctx.new_page(); vz.on('pageerror', lambda e: errores.append('visor: ' + str(e)[:200] + ' ' + (e.stack or '')[:300]))
    vz.goto(BASE + '/visor.html'); vz.wait_for_function("typeof alternarGerencia==='function'&&typeof cargar==='function'", timeout=30000); time.sleep(1)
    vz.evaluate("""async(hoy)=>{document.querySelector('#login').hidden=true;document.querySelector('#app').hidden=false;mapa.invalidateSize();window.chunkLote=async()=>[];
      SES={u:'admin1',nombre:'Admin',rol:'admin',token:'tok',repo:{owner:'didpalmares',repo:'CosechaData',rama:'main'}};ACCESO={usuarios:[]};aplicarPermisosGer();
      LOTES={type:'FeatureCollection',features:['IT01','IT05'].map((l,k)=>({type:'Feature',properties:{_lote:l},geometry:{type:'Polygon',coordinates:[[[-78.701,1.499+k*0.01],[-78.699,1.499+k*0.01],[-78.699,1.508+k*0.01],[-78.701,1.508+k*0.01],[-78.701,1.499+k*0.01]]]}}))};
      IND_LOTES={IT01:{n:500},IT05:{n:400}};opcionesLote();
      document.querySelector('#fDesde').value=hoy;document.querySelector('#fHasta').value=hoy;await cargar();}""", HOY)
    vz.wait_for_function("JOR.length===2", timeout=15000); time.sleep(.5)
    check('Visor: lee las 2 jornadas sincronizadas', vz.evaluate("JOR.map(j=>j.id).sort().join()") == 'J1,J2')
    # Leyenda
    ley = vz.inner_text('#leyenda')
    check('Leyenda: los 5 códigos con su nombre completo', all(f'{c}: {n}' in ley for c, n in NOMBRES.items()), ley[:200])
    check('Leyenda: sin enfermedades', 'Pudrición' not in ley and 'Enfermedad' not in ley)
    # Colores del mapa: último registro de cada palma
    col = vz.evaluate("(()=>{const o={};capaDiag.eachLayer(l=>{o[l.options.palma_id]=[l.options.codigo,l.options.fillColor];});return o;})()")
    esperado = {'P101': 'M', 'P102': 'S', 'P103': 'F', 'P104': 'S', 'P201': 'M', 'P202': 'V', 'P203': 'C', 'P204': 'M'}
    check('Mapa: una palma por marcador, color del código principal del último registro (V, M, S, F, C)', col == {k: [c, COLORES[c]] for k, c in esperado.items()}, col)
    # Ficha de la palma
    vz.evaluate("popupDiag(DIAGF.find(d=>d.palma_id==='P101'))"); time.sleep(.4)
    pop = vz.inner_text('.leaflet-popup-content')
    check('Ficha: resumen 2C + 1M + 1S', '2C + 1M + 1S' in pop, pop[:120])
    check('Ficha: cada conteo con su nombre completo', 'C: Racimo cosechado: 2' in pop and 'M: Racimo maduro dejado sin cortar: 1' in pop and 'V: Racimo verde cortado: 0' in pop
          and 'S: Racimo sobremaduro / podrido: 1' in pop and 'F: Fruto suelto sin recoger: No' in pop, pop)
    check('Ficha: operario, fecha y hora, transitabilidad, fuente y observación',
          'Operario: GOMEZ PEREZ ANDRES' in pop and f'Fecha y hora: {HOY} 07:10' in pop and 'Transitabilidad: Transitable' in pop and 'Fuente: Botón, Tarjeta NFC' in pop and 'Observación: Racimo pesado' in pop, pop)
    check('Ficha: sin campos de enfermedad (cirugía, estado)', 'Cirugía' not in pop and 'Enfermedad' not in pop and 'Estado' not in pop)
    vz.evaluate("popupDiag(DIAGF.find(d=>d.palma_id==='P103'))"); time.sleep(.3)
    pop = vz.inner_text('.leaflet-popup-content')
    check('Ficha F: resumen «F», fruto suelto Sí y fuente Voz', 'F: Fruto suelto sin recoger: Sí' in pop and 'Fuente: Voz' in pop and 'C: Racimo cosechado: 0' in pop, pop[:300])
    vz.evaluate("popupDiag(DIAGF.find(d=>d.palma_id==='P204'))"); time.sleep(.3)
    pop = vz.inner_text('.leaflet-popup-content')
    check('Ficha de un registro sin conteos (solo resumen): se lee del resumen', '1C + 2M' in pop and 'M: Racimo maduro dejado sin cortar: 2' in pop, pop[:200])
    vz.evaluate("mapa.closePopup()")
    # Panel: resumen y pestañas
    vz.click('nav.tabs [data-tab=resumen]'); time.sleep(.3)
    kp = vz.inner_text('#kpisPol')
    check('Resumen del visor: C 5 · M 6 · V 1 · S 4 · F 1 palma · % verdes 10,0 % · % maduros 37,5 %', re.sub(r'\s+', ' ', kp).upper() == '5 C: RACIMO COSECHADO 6 M: RACIMO MADURO DEJADO SIN CORTAR 1 V: RACIMO VERDE CORTADO 4 S: RACIMO SOBREMADURO / PODRIDO 1 F: FRUTO SUELTO SIN RECOGER (PALMAS) 10,0 % % VERDES CORTADOS (V ÷ C+V+S) 37,5 % % MADUROS DEJADOS (M ÷ C+V+S+M)', re.sub(r'\s+', ' ', kp))
    rk = vz.inner_text('#panel')
    check('Resumen del visor: racimos cortados (C+V+S) = 10', re.search(r'10\s+Racimos cortados \(C\+V\+S\)', rk, re.I) is not None, re.sub(r'\s+', ' ', rk)[:300])
    vz.click('nav.tabs [data-tab=diag]'); time.sleep(.3)
    T = vz.inner_text('#panel')
    check('Pestaña REGISTROS: 9 registros con código, transitabilidad y fuente', '9 registro(s)' in T and 'Tarjeta NFC' in T and 'Formulario' in T, T[:160])
    vz.click('nav.tabs [data-tab=lotes]'); time.sleep(.3)
    th = [c.strip() for c in vz.evaluate("[...document.querySelectorAll('#tLot thead th')].map(t=>t.innerText)")]
    check('Pestaña LOTES: columnas C, M, V, S, % verdes y F (palmas), sin PC', all(h in th for h in ['Palmas registradas', 'C', 'M', 'V', 'S', '% verdes', 'F (palmas)']) and 'PC' not in th, th)
    # Filtro por código (interfaz)
    vz.click('#filtros .ms[data-k=cod] .ms-bt'); time.sleep(.2)
    ops = vz.evaluate("[...document.querySelectorAll('#msL .ms-it span')].map(s=>s.innerText)")
    check('Filtro Código: C, M, V, S, F con su nombre', ops == [f'{c}: {n}' for c, n in NOMBRES.items()], ops)
    vz.click('#msL .solo[data-i="3"]'); time.sleep(.4)
    fb = vz.evaluate("({n:DIAGF.length,m:(()=>{const a=[];capaDiag.eachLayer(l=>a.push(l.options.palma_id));return a.sort().join();})(),bt:document.querySelector('#filtros .ms[data-k=cod] .ms-bt').innerText})")
    check('Filtro Código = S: 3 registros (P101, P104 y P102) y el botón dice S', fb == {'n': 3, 'm': 'P101,P102,P104', 'bt': 'S'}, fb)
    vz.evaluate("msSolo('cod','F');aplicarFiltros(false)"); time.sleep(.2)
    check('Filtro Código = F: solo la palma con fruto suelto', vz.evaluate("DIAGF.map(d=>d.palma_id).join()") == 'P103')
    vz.evaluate("msSolo('cod',null);aplicarFiltros(false)"); time.sleep(.2)
    check('Sin filtros de enfermedad en el visor', vz.evaluate("!document.querySelector('#filtros [data-k=n1]')&&!document.querySelector('#filtros [data-k=est]')&&Object.keys(FIL).join()") == 'prog,op,lote,cod')
    # Detalle de jornada: transitabilidad
    vz.evaluate("abrirDetalle(JOR.find(j=>j.id==='J2'))"); time.sleep(.4)
    det = vz.inner_text('#detalle')
    check('Detalle de la jornada: transitabilidad por lote y lote abierto', 'TRANSITABILIDAD POR LOTE' in det.upper() and 'Sin salida (lote abierto)' in det and 'Registros: 5' in det, det[-300:])
    vz.evaluate("cerrarDetalle()")

    # ---- 3. Gerencia · 🌴 Cosecha ----
    vz.click('#btGer'); time.sleep(.5)
    T = vz.inner_text('#gerPanel')
    check('Gerencia: secciones Resumen, Cosecha y Mapa de avance (sin Enfermedades)', '🌴 Cosecha' in T and 'Mapa de avance de la cosecha' in T and 'Enfermedades' not in T and 'censo' not in T.lower(), re.sub(r'\s+', ' ', T)[:200])
    check('Gerencia: filtro Código en la barra (sin enfermedad ni estado)', vz.evaluate("!!document.querySelector('#gerFil .ms[data-k=cod]')&&!document.querySelector('#gerFil .ms[data-k=n1]')&&!document.querySelector('#gerFil .ms[data-k=est]')"))
    check('Gerencia · Resumen: palmas registradas y racimos cortados', 'Palmas registradas' in T and 'Racimos cortados (C + V + S)' in T and 'Inflorescencias' not in T and 'Diagnósticos' not in T)
    vz.click('[data-tsub=pol]'); time.sleep(1)
    K = [re.sub(r'\s+', ' ', x) for x in vz.evaluate("[...document.querySelectorAll('#polKpis .ger-kpi')].map(k=>k.innerText)")]
    check('KPIs: 8 palmas, C 5, M 6, V 1, S 4, F 1 palma, 10 racimos cortados, % verdes 10,0 %, % maduros 37,5 %', K == ['8 Palmas registradas', '5 Total C: Racimo cosechado', '6 Total M: Racimo maduro dejado sin cortar',
          '1 Total V: Racimo verde cortado', '4 Total S: Racimo sobremaduro / podrido', '1 Palmas F: Fruto suelto sin recoger', '10 Racimos cortados (C + V + S)',
          '10,0 % % Verdes cortados = V ÷ (C + V + S)', '37,5 % % Maduros dejados = M ÷ (C + V + S + M)'], K)
    filas = vz.evaluate("[...document.querySelectorAll('#polLotes tbody tr')].map(t=>[...t.cells].map(c=>c.innerText.trim()))")
    check('Por lote: IT01 4 palmas, C 3, M 1, V 0, S 4, F 1, 7 racimos, 0,0 % verdes, entrada Transitable, salida Poco transitable (1 sin salida)',
          filas[0] == ['IT01', '—', '4', '3', '1', '0', '4', '1', '7', '0,0 %', 'Transitable', 'Poco transitable 1 sin salida'], filas[0] if filas else filas)
    check('Por lote: IT05 4 palmas, C 2, M 5, V 1, S 0, F 0, 3 racimos, 33,3 % verdes, entrada Poco transitable, salida Transitable',
          len(filas) == 2 and filas[1] == ['IT05', '—', '4', '2', '5', '1', '0', '0', '3', '33,3 %', 'Poco transitable', 'Transitable'], filas[1:] )
    bar = vz.evaluate("[...document.querySelectorAll('#polBarLote rect')].map(r=>r.dataset.lc)")
    check('Gráfico por lote: barras C/M/V/S apiladas', sorted(bar) == sorted(['IT01|C|3', 'IT01|M|1', 'IT01|S|4', 'IT05|C|2', 'IT05|M|5', 'IT05|V|1']), bar)
    sem = vz.evaluate("[...document.querySelectorAll('#polSemana rect')].map(r=>r.dataset.sc.split('|').slice(1).join(''))")
    check('Gráfico por semana: C 5, M 6, V 1, S 4 apiladas', sorted(sem) == ['C5', 'M6', 'S4', 'V1'], sem)
    oth = vz.evaluate("[...document.querySelectorAll('#polOps thead th')].map(t=>t.innerText.trim())")
    check('Rendimiento por operario: columnas de racimos cosechados, racimos/día y % verdes', all(h in oth for h in ['Racimos cosechados (C)', 'Racimos/día', '% verdes']), oth)
    ops = vz.evaluate("[...document.querySelectorAll('#polOps tbody tr')].map(t=>[...t.cells].slice(0,6).map(c=>c.innerText.trim()))")
    check('Rendimiento por operario: palmas registradas, racimos cosechados, racimos/día y % verdes', ops == [['LOPEZ DIAZ CARLOS', '1', '5', '2', '2,0', '25,0 %'], ['GOMEZ PEREZ ANDRES', '1', '4', '3', '3,0', '0,0 %']], ops)
    rv = vz.evaluate("({n:GER.rvN,m:(()=>{const a=[];GER.rv.eachLayer(l=>{if(l.options&&l.options.codigo)a.push(l.options.codigo+l.options.fillColor);});return a.sort();})(),e:document.querySelector('#rvEstado').innerText})")
    check('Mapa de palmas con novedad (V, M, S o F; sin la palma solo C)', rv['n'] == 7 and rv['m'] == sorted([c + COLORES[c] for c in ['F', 'M', 'M', 'M', 'S', 'S', 'V']])
          and '1 V' in rv['e'] and '3 M' in rv['e'] and '2 S' in rv['e'] and '1 F' in rv['e'], rv)
    with vz.expect_download() as dl: vz.click('#xPolReg')
    ruta = dl.value.path(); cab = open(ruta, encoding='utf-8-sig').read().splitlines()
    cols = cab[0].split(';')
    check('CSV de registros: cosechados, maduros, verdes, sobremaduros, fruto_suelto, racimos, transitabilidad y fuente',
          all(c in cols for c in ['cosechados', 'maduros', 'verdes', 'sobremaduros', 'fruto_suelto', 'racimos', 'transitabilidad', 'fuente'])
          and not any(c in cols for c in ['a', 'p', 'b', 'cond', 'inflorescencias']) and len(cab) == 10, cols)
    fila = dict(zip(cols, next(l for l in cab[1:] if 'P101' in l).split(';')))
    check('CSV de registros: fila de P101', (fila['cosechados'], fila['maduros'], fila['verdes'], fila['sobremaduros'], fila['fruto_suelto'], fila['racimos']) == ('2', '1', '0', '1', '0', '3')
          and fila['resumen'] == '2C + 1M + 1S' and fila['codigo'] == 'M' and fila['fuente'] == 'Botón, Tarjeta NFC', fila)
    # Filtro de código desde Gerencia
    vz.evaluate("msSolo('cod','V');aplicarFiltros(false)"); time.sleep(.5)
    K = [re.sub(r'\s+', ' ', x) for x in vz.evaluate("[...document.querySelectorAll('#polKpis .ger-kpi')].map(k=>k.innerText)")]
    check('Gerencia respeta el filtro Código (V: 1 palma, 1 racimo verde, 100 % verdes)', K[0] == '1 Palmas registradas' and K[1].startswith('0 ') and K[3].startswith('1 ')
          and K[6].startswith('1 ') and K[7].startswith('100,0 %'), K)
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
    check('Transitabilidad por lote: 3 entradas (lote, operario, entrada + hora, salida + hora, duración)',
          len(tr) == 3 and tr[0][1:] == ['IT01', 'GOMEZ PEREZ ANDRES', 'Transitable 07:05', 'Poco transitable 08:00', '0:55'] and tr[1][1:] == ['IT05', 'LOPEZ DIAZ CARLOS', 'Poco transitable 08:30', 'Transitable 08:50', '0:20'], tr)
    check('Transitabilidad: marca el lote abierto (sin salida)', tr[2][1] == 'IT01' and 'Sin salida' in tr[2][4] and tr[2][5] == '—' and '1 lote(s) quedaron abiertos' in T, tr[2] if len(tr) > 2 else T[:200])
    # Calidad y auditoría con el registro de cosecha
    vz.click('[data-gt=calidad]'); time.sleep(.4); T = vz.inner_text('#gerPanel')
    check('Calidad: registros (sin «Sin foto» ni diagnósticos)', 'Registros de cosecha' in T and 'Sin foto' not in T and 'iagnóstico' not in T, re.sub(r'\s+', ' ', T)[:200])
    vz.click('[data-gt=auditoria]'); time.sleep(.4); T = vz.inner_text('#gerPanel')
    check('Auditoría: textos de la cosecha', 'registros de cada operario' in T and 'censador' not in T.lower())
    vz.click('#gerX')
    check('Sin errores de JavaScript', not errores, errores[:4])
    nav.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLAS'); sys.exit(0 if ok else 1)
