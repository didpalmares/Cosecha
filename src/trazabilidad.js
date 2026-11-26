/* =====================================================================
   TRAZABILIDAD · Fase 1 (todo funciona sin señal; se une al sincronizar)
   · Conteo doble: en «Corte y recolección» cada R cuenta 1 racimo de corte y 1 de recolección.
   · Ficha NFC del acopio: al confirmar el descargue (D), el recolector graba en una ficha NFC el acopio (lote, racimos, recolector,
     hora) y la deja sobre el montón. El alcero la toca: su celular sabe, sin señal, de quién y cuántos son los racimos que alza.
     La grabación está protegida: si se acerca una tarjeta R o D por error, no se graba encima (APK 1.0.5 o superior).
   · Copia al supervisor por QR: el operario muestra su jornada en uno o varios QR; el supervisor la escanea con la cámara.
     Es una copia informativa (solo lectura): la data oficial sube del celular de cada operario.
   · Tablero del supervisor: resumen del día con racimos de corte y de recolección por operario, cuadre por lote y acopios sin alzar.
   ===================================================================== */
document.head.insertAdjacentHTML('beforeend',`<style>
.ficha-aco{text-align:center}
.ficha-aco svg{width:120px;height:120px}
.ficha-aco-t{display:block;font-family:var(--t);font-size:30px;font-weight:700;letter-spacing:1px;color:var(--acento);margin:6px 0}
.ficha-aco .btn.grande{margin-top:14px;font-size:20px;min-height:58px}
.qr-comp{text-align:center}
.qr-caja{background:#fff;border-radius:16px;padding:10px;margin:0 auto;width:min(86vw,380px)}
.qr-caja svg{display:block;width:100%;height:auto}
.qr-parte{display:block;font-family:var(--t);font-size:22px;margin:8px 0;color:var(--acento)}
.qr-rec video{width:100%;max-height:52vh;border-radius:14px;background:#000;object-fit:cover}
.rac-lab svg{display:block;margin:0 auto 2px}
.tab-sup td.n,.tab-sup th.n{text-align:right}
.tab-sup tr.tot td{font-weight:700;border-top:2px solid var(--borde)}
.tab-sup .dif{color:#ffb4ab}
.tab-sup{white-space:normal}
.tab-sup td small{display:block;font-size:12px;opacity:.75;margin-top:2px;white-space:normal}
.tab-sup td.n,.tab-sup th.n{width:52px}
.tab-fechas{display:flex;flex-wrap:wrap;gap:6px}
.tab-fechas .btn{min-height:36px;padding:4px 12px}
.btn-comp{font-size:19px;min-height:56px}
</style>`);

/* ---------- Conteo de racimos por labor ---------- */
/* {corte, recoleccion, alzados, lotes:{lote:{c,r,a}}}. regs: registros de la jornada (por defecto, los del celular). */
function racimosDeJornada(j,regs){
  const o={corte:0,recoleccion:0,alzados:0,lotes:{}};if(!j)return o;
  const L=l=>o.lotes[l||'—']||(o.lotes[l||'—']={c:0,r:0,a:0});
  const lab=laborInfo(j.labor),id=lab?lab.id:'corte';
  if(lab&&lab.sendero){for(const a of j.alces||[]){const n=Number(a.racimos)||0;o.alzados+=n;L(a.lote).a+=n;}return o;}
  for(const r of regs||S.registros){if(r.jornada_id!==j.id)continue;const n=Number(r.racimos)||0;if(!n)continue;
    if(id==='corte'||id==='corte_recoleccion'){o.corte+=n;L(r.lote).c+=n;}
    if(id==='recoleccion'||id==='corte_recoleccion'){o.recoleccion+=n;L(r.lote).r+=n;}}
  return o;}
function htmlRacimosLabor(j){
  const r=racimosDeJornada(j),lab=laborInfo(j&&j.labor)||{};
  const cel=(pic,n,t)=>`<div class="stat rac-lab">${svgPic(pic,34)}<b>${num(n)}</b><span>${t}</span></div>`;
  const h=lab.sendero?cel('alce',r.alzados,'Racimos alzados'):(lab.id!=='recoleccion'?cel('corte',r.corte,'Racimos de corte'):'')+(lab.id!=='corte'?cel('recoleccion',r.recoleccion,'Racimos de recolección'):'');
  return `<div class="stats" style="margin-bottom:10px">${h}</div>`;}

/* ---------- Ficha NFC del acopio ---------- */
/* Texto grabado: ACO|id|lote|racimos|usuario|hora|AAMMDD (cabe de sobra en una NTAG213). */
const FICHA={activa:false,d:null,ctrl:null,avisoApk:false};
const idAcopio=d=>String(d.aco||d.id||'').replace(/-/g,'').slice(0,12);
function textoFicha(d,j){return ['ACO',idAcopio(d),String(d.lote||'').replace(/\|/g,''),d.racimos,String(j.usuario||(SES&&SES.u)||'').replace(/\|/g,'').slice(0,16),d.hora||'',fechaLocal(d.t).slice(2).replace(/-/g,'')].join('|');}
function parseFicha(t){const p=String(t??'').trim().split('|');if(p[0]!=='ACO'||p.length<7||!p[1])return null;
  return {id:p[1],lote:p[2],racimos:Number(p[3])||0,usuario:p[4],hora:p[5],fecha:p[6]};}
/* La ficha se puede grabar con la APK 1.0.5 o superior (grabación protegida) o con Web NFC (Chrome en Android). */
function fichaPosible(){
  if(nfcNativoDisponible()){try{return typeof NAT_N().capacidades==='function';}catch(e){return false;}}
  return 'NDEFReader' in window;}
/* Graba la próxima tarjeta que se acerque, sin grabar encima de una tarjeta R o D (error «ES_CODIGO:R»). */
async function grabarFichaNfc(texto){
  if(nfcNativoDisponible()){if(NFC.estado!=='listo')await iniciarNfc(false);return await NAT_N().grabar({texto,proteger:true});}
  const ctrl=new AbortController();FICHA.ctrl=ctrl;const rd=new NDEFReader();
  const leido=await new Promise((res,rej)=>{
    ctrl.signal.addEventListener('abort',()=>rej(new Error('Cancelada.')));
    rd.onreading=ev=>{let tx='';for(const rec of ev.message.records){try{if(rec.recordType==='text')tx=new TextDecoder(rec.encoding||'utf-8').decode(rec.data);}catch(e){}if(tx)break;}res({tx,id:ev.serialNumber||''});};
    rd.scan({signal:ctrl.signal}).catch(rej);});
  const c=codigoNfc(leido.tx);if(c)throw new Error('ES_CODIGO:'+c);
  await rd.write({records:[{recordType:'text',lang:'es',data:texto}]},{overwrite:true,signal:ctrl.signal});
  return {ok:true,id:leido.id};}
function cancelarFicha(){if(!FICHA.activa)return;FICHA.activa=false;FICHA.d=null;
  try{if(nfcNativoDisponible()&&typeof NAT_N().cancelarGrabacion==='function')NAT_N().cancelarGrabacion();}catch(e){}
  try{FICHA.ctrl&&FICHA.ctrl.abort();}catch(e){}}
const svgFicha=()=>`<svg viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="34" r="22" fill="#1b5e20" stroke="#a5d6a7" stroke-width="3"/><path d="M24 28a11 11 0 010 12M29 24a17 17 0 010 20M34 20a23 23 0 010 28" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/><g transform="translate(36 2) scale(.42)">${PIC_P.racimo}</g></svg>`;
/* Tras confirmar el descargue: pide la ficha. «SIN FICHA» o 90 s sin ficha = el acopio queda solo con su punto GPS. */
async function ofrecerFicha(d){
  const j=S.jornada;if(!j||!d)return;
  if(!fichaPosible()){if(nfcNativoDisponible()&&!FICHA.avisoApk){FICHA.avisoApk=true;toast('Actualice la APK de Cosecha para usar la ficha del acopio.',5000);}return;}
  cancelarFicha();FICHA.activa=true;FICHA.d=d;const hasta=Date.now()+90000;
  abrirHoja('Ficha del acopio',`<div class="ficha-aco">${svgFicha()}
    <b class="ficha-aco-t">ACERQUE LA FICHA</b>
    <p>Viaje ${d.n} · <b>${num(d.racimos)} racimos</b>${d.lote?` · lote <b>${esc(d.lote)}</b>`:''}</p>
    <div id="fichaMsj" class="aviso">📶 Acerque la ficha del acopio al celular y déjela quieta un segundo. Después déjela sobre el montón.</div>
    <button type="button" class="btn ancho grande" id="fichaNo">SIN FICHA</button></div>`,{alCerrar:cancelarFicha});
  $('#fichaNo').onclick=()=>cerrarHoja();
  const msj=(h,ok)=>{const m=$('#fichaMsj');if(m&&FICHA.d===d){m.innerHTML=h;m.className=ok?'candado':'aviso';}};
  setTimeout(()=>{if(FICHA.activa&&FICHA.d===d&&HAY_VOZ())hablar('Acerque la ficha del acopio',true);},2200);
  const txt=textoFicha(d,j);
  while(FICHA.activa&&FICHA.d===d&&Date.now()<hasta){
    try{const r=await grabarFichaNfc(txt);
      if(!FICHA.activa||FICHA.d!==d)return;
      FICHA.activa=false;FICHA.d=null;
      d.aco=idAcopio(d);d.ficha={uid:(r&&r.id)||'',t:new Date(ahoraReal()).toISOString()};
      if(r&&r.id){const m=uidsNfc();if(m[r.id]){delete m[r.id];try{localStorage.setItem('cos_nfc_uid',JSON.stringify(m));}catch(e){}}}
      j.sync='pendiente';await dbPut('jornadas',j);await marcarJornadaPendiente(j.id);
      if($('#fichaMsj'))cerrarHoja();
      avisoPol(`Ficha grabada: ${vozRacimos(d.racimos)}. Déjela sobre el acopio.`);dibujarEventosCosecha();return;}
    catch(e){if(!FICHA.activa||FICHA.d!==d)return;const m=String(e&&e.message||e);
      if(/^ES_CODIGO:/.test(m)){const c=m.slice(10);msj(`⚠️ Esa es la tarjeta <b>${esc(c)}</b>. Acerque la <b>FICHA</b> del acopio.`);
        avisoPol(`Esa es la tarjeta ${c==='R'?'erre':'de'}. Acerque la ficha del acopio.`,true);await esperar(600);continue;}
      if(/Cancelada|Reemplazada/.test(m))return;
      msj('⚠️ '+esc(m)+' Intente de nuevo.');await esperar(900);}}
  if(FICHA.activa&&FICHA.d===d){cancelarFicha();msj('⏱ Tiempo agotado: el acopio queda sin ficha (se ubicará por GPS).');}
}

/* Alcero: al tocar una ficha, los R siguientes van a ese acopio (mientras esté a 40 m o menos) y se cuentan contra la ficha. */
const FICHA_ALCE={pend:null,actual:null};
async function leerFichaAcopio(fa,ev){
  const j=S.jornada;
  if(!j){avisoPol('Inicie una jornada para registrar.',true);return;}
  const lab=laborInfo(j.labor);
  if(!lab||!lab.sendero){avisoPol(`Ficha del acopio: ${vozRacimos(fa.racimos)}${fa.lote?', lote '+paraVoz(fa.lote):''}. La registra el alcero.`);return;}
  const ya=(j.alces||[]).find(a=>a.ficha&&a.ficha.id===fa.id);
  if(ya){FICHA_ALCE.actual=ya.id;FICHA_ALCE.pend=null;avisoPol(`Acopio ${ya.n} otra vez: ${ya.racimos} de ${ya.esperados} racimos alzados.`);return;}
  FICHA_ALCE.pend={...fa,uid:(ev&&ev.id)||'',t:new Date(ahoraReal()).toISOString()};FICHA_ALCE.actual=null;
  avisoPol(`Acopio con ficha: ${vozRacimos(fa.racimos)}${fa.lote?' del lote '+paraVoz(fa.lote):''}. Marque erre por cada racimo que alce.`);}
/* Lo usa registrarAlce: devuelve el acopio de la ficha (nuevo o el actual) o null para agrupar como siempre. */
function fichaParaAlce(A,g,lote,t,ti,fuente){
  const P=FICHA_ALCE.pend;
  if(P){FICHA_ALCE.pend=null;
    const a={id:uid(),n:A.length+1,racimos:0,lat:+g.lat.toFixed(7),lng:+g.lng.toFixed(7),acc:Math.round(g.acc*10)/10,lote:P.lote||lote||'',t_ini:ti,t_fin:ti,hora:hhmm(t),fuente:fuente||'boton',
      ficha:{id:P.id,lote:P.lote,racimos:P.racimos,usuario:P.usuario,hora:P.hora,fecha:P.fecha,uid:P.uid,t:P.t},esperados:P.racimos};
    A.push(a);FICHA_ALCE.actual=a.id;return a;}
  if(FICHA_ALCE.actual){const a=A.find(x=>x.id===FICHA_ALCE.actual);
    if(a&&dist(a.lat,a.lng,g.lat,g.lng)<=40)return a;FICHA_ALCE.actual=null;}
  return null;}
function avisoAlce(a){
  if(!a.esperados)return `Acopio ${a.n}: ${a.racimos===1?'un racimo alzado':paraVoz(a.racimos)+' racimos alzados'}.`;
  if(a.racimos<a.esperados)return `Acopio ${a.n}: ${a.racimos} de ${a.esperados}.`;
  if(a.racimos===a.esperados)return `Acopio ${a.n} completo: ${a.racimos} de ${a.esperados} racimos.`;
  return `Atención: ${a.racimos} racimos alzados, la ficha dice ${a.esperados}.`;}

/* ---------- Copia de la jornada por QR ---------- */
const b64De=u8=>{let s='';for(let i=0;i<u8.length;i+=0x8000)s+=String.fromCharCode.apply(null,u8.subarray(i,i+0x8000));return btoa(s);};
const u8De=b=>Uint8Array.from(atob(b),c=>c.charCodeAt(0));
async function comprimirTxt(txt){
  if(typeof CompressionStream!=='function')return 'J'+b64De(new TextEncoder().encode(txt));
  const st=new Blob([txt]).stream().pipeThrough(new CompressionStream('deflate-raw'));
  return 'Z'+b64De(new Uint8Array(await new Response(st).arrayBuffer()));}
async function descomprimirTxt(s){
  if(s[0]==='J')return new TextDecoder().decode(u8De(s.slice(1)));
  const st=new Blob([u8De(s.slice(1))]).stream().pipeThrough(new DecompressionStream('deflate-raw'));
  return await new Response(st).text();}
const r6=x=>Math.round(Number(x)*1e6)/1e6;
function copiaJornada(j){
  const rac=racimosDeJornada(j),lab=laborInfo(j.labor);
  return {v:1,id:j.id,u:j.usuario||(SES&&SES.u)||'',nom:j.evaluador||(SES&&SES.nombre)||'',lab:lab?lab.id:'corte',zona:j.zona||'',
    f:fechaLocal(j.inicio),ini:hhmm(j.inicio),fin:j.fin?hhmm(j.fin):'',km:+(j.km||0).toFixed(2),
    rc:rac.corte,rr:rac.recoleccion,ra:rac.alzados,lotes:rac.lotes,vab:j.viaje||0,
    aco:(j.descargues||[]).map(d=>[d.n,d.lote||'',d.racimos,r6(d.lat),r6(d.lng),d.hora||'',d.ficha?idAcopio(d):'',d.aco||idAcopio(d)]),
    alz:(j.alces||[]).map(a=>[a.n,a.lote||'',a.racimos,r6(a.lat),r6(a.lng),a.hora||'',a.ficha?a.ficha.id:'',a.esperados||0])};}
const QR_PARTE=300;   // caracteres por QR: códigos medianos que otro celular lee fácil en pantalla
async function framesCopia(obj){
  const z=await comprimirTxt(JSON.stringify(obj)),sid=Math.random().toString(36).slice(2,6),n=Math.max(1,Math.ceil(z.length/QR_PARTE));
  return Array.from({length:n},(_,k)=>`CQ1|${sid}|${k+1}|${n}|${z.slice(k*QR_PARTE,(k+1)*QR_PARTE)}`);}
function svgQR(txt){const q=qrcode(0,'M');q.addData(txt,'Byte');q.make();return q.createSvgTag({cellSize:4,margin:4,scalable:true});}
const QRC={t:null};
async function ultimaJornadaPropia(){
  const l=(await dbAll('jornadas')).filter(x=>esLaborCosecha(x.labor)&&(!SES||!x.usuario||x.usuario===SES.u)).sort((a,b)=>String(b.inicio).localeCompare(String(a.inicio)));
  return l[0]||null;}
async function compartirJornada(j){
  clearInterval(QRC.t);
  j=j||S.jornada||await ultimaJornadaPropia();
  if(!j){toast('No hay jornadas en este celular para compartir.');return;}
  const fr=await framesCopia(copiaJornada(j));
  abrirHoja('Compartir con el supervisor',`<div class="qr-comp">
    ${htmlRacimosLabor(j)}
    <div class="qr-caja" id="qrCaja"></div><b class="qr-parte" id="qrParte"></b>
    <div class="aviso">📱 Muestre esta pantalla al supervisor. Él la escanea con su celular. No necesita señal.</div>
    <p class="tenue">${esc(j.evaluador||'')} · ${esc((laborInfo(j.labor)||{}).corto||'')} · ${esc(fechaLocal(j.inicio))} · ${hhmm(j.inicio)}–${j.fin?hhmm(j.fin):'en curso'}</p></div>`,{alCerrar:()=>clearInterval(QRC.t)});
  let k=0;const pinta=()=>{const c=$('#qrCaja');if(!c){clearInterval(QRC.t);return;}c.innerHTML=svgQR(fr[k]);c.dataset.parte=k+1;
    $('#qrParte').textContent=fr.length>1?`Parte ${k+1} de ${fr.length}`:'';k=(k+1)%fr.length;};
  pinta();if(fr.length>1)QRC.t=setInterval(pinta,900);
  if(HAY_VOZ())hablar('Muestre la pantalla al supervisor',true);
  return fr;}

/* ---------- Recibir copias (supervisor) ---------- */
const COPIAS_K='cos_copias';
function copiasSup(){try{return JSON.parse(localStorage.getItem(COPIAS_K)||'{}')||{};}catch(e){return {};}}
function guardarCopia(o){const m=copiasSup();m[o.u+'|'+o.id]={...o,recibida:new Date().toISOString()};
  const lim=fechaLocal(Date.now()-10*864e5);for(const k in m)if(String(m[k].f||'')<lim)delete m[k];   // se guardan 10 días
  try{localStorage.setItem(COPIAS_K,JSON.stringify(m));}catch(e){toast('No se pudo guardar la copia: '+e.message,5000);}}
const QRR={stream:null,t:null,partes:{},recibidas:[]};
function pararCamaraQR(){clearTimeout(QRR.t);QRR.t=null;try{QRR.stream&&QRR.stream.getTracks().forEach(t=>t.stop());}catch(e){}QRR.stream=null;}
function estadoQR(h,ok){const e=$('#qrEstado');if(e){e.innerHTML=h;e.className=ok?'candado':'aviso';}}
async function procesarTextoQR(txt){
  const m=/^CQ1\|(\w+)\|(\d+)\|(\d+)\|([\s\S]*)$/.exec(String(txt||''));
  if(!m){estadoQR('⚠️ Ese QR no es una jornada de Cosecha.');return null;}
  const sid=m[1],k=+m[2],n=+m[3];const P=QRR.partes[sid]||(QRR.partes[sid]={n,p:{}});
  if(P.listo)return null;P.p[k]=m[4];const tengo=Object.keys(P.p).length;
  if(tengo<P.n){estadoQR(`📶 Leyendo… parte ${tengo} de ${P.n}. Mantenga la cámara quieta.`);return null;}
  P.listo=true;
  try{const obj=JSON.parse(await descomprimirTxt(Array.from({length:P.n},(_,i)=>P.p[i+1]).join('')));
    if(!obj||obj.v!==1||!obj.id)throw new Error('copia inválida');
    guardarCopia(obj);QRR.recibidas.push(obj);try{pitido(1300,120);navigator.vibrate&&navigator.vibrate(120);}catch(e){}
    if(HAY_VOZ())hablar(`Copia recibida de ${obj.nom}`,true);
    estadoQR(`✅ Copia recibida: <b>${esc(obj.nom)}</b> · ${esc((laborInfo(obj.lab)||{}).corto||obj.lab)} · ${esc(obj.f)}. Apunte al QR del siguiente operario.`,true);
    const l=$('#qrRecibidas');if(l)l.innerHTML=QRR.recibidas.map(o=>`<div class="ficha" style="margin-top:6px">✅ ${esc(o.nom)} · ${esc((laborInfo(o.lab)||{}).corto||o.lab)} · corte ${num(o.rc)} · recolección ${num(o.rr)}${o.ra?` · alzados ${num(o.ra)}`:''}</div>`).join('');
    return obj;}
  catch(e){delete QRR.partes[sid];estadoQR('⚠️ No se pudo leer la copia. Pida al operario que la muestre de nuevo.');return null;}}
async function recibirCopias(){
  if(!puedeAuditar()){toast('Solo supervisores y administradores reciben copias.');return;}
  pararCamaraQR();QRR.partes={};QRR.recibidas=[];
  abrirHoja('Recibir jornadas',`<div class="qr-rec"><video id="qrVid" playsinline muted autoplay></video><canvas id="qrCan" hidden></canvas>
    <div id="qrEstado" class="aviso" style="margin-top:8px">📷 Apunte la cámara al QR del celular del operario.</div><div id="qrRecibidas"></div>
    <button type="button" class="btn prim ancho" id="qrTab" style="margin-top:10px">${IC.grafico} Ver tablero del día</button></div>`,{alCerrar:pararCamaraQR});
  $('#qrTab').onclick=()=>{pararCamaraQR();abrirTablero();};
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){estadoQR('⚠️ Este celular no permite usar la cámara aquí.');return;}
  try{QRR.stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}}});}
  catch(e){estadoQR('⚠️ No se pudo abrir la cámara. Permita el uso de la cámara a Cosecha.');return;}
  const v=$('#qrVid');if(!v){pararCamaraQR();return;}v.srcObject=QRR.stream;try{await v.play();}catch(e){}
  const cv=$('#qrCan'),cx=cv.getContext('2d',{willReadFrequently:true});
  const paso=async()=>{if(!QRR.stream||!$('#qrVid'))return;
    try{const w=v.videoWidth,h=v.videoHeight;if(w&&h&&window.jsQR){const s=Math.min(1,800/Math.max(w,h));cv.width=Math.round(w*s);cv.height=Math.round(h*s);
      cx.drawImage(v,0,0,cv.width,cv.height);const im=cx.getImageData(0,0,cv.width,cv.height);
      const r=jsQR(im.data,im.width,im.height,{inversionAttempts:'dontInvert'});if(r&&r.data)await procesarTextoQR(r.data);}}catch(e){}
    if(QRR.stream)QRR.t=setTimeout(paso,180);};
  paso();}

/* ---------- Tablero del supervisor ---------- */
/* Acopios del recolector que ninguna copia de alcero cubre: primero por la ficha; si no, por cercanía (30 m) y hora. */
function acopiosSinAlzar(cs){
  const alz=cs.flatMap(c=>(c.alz||[]).map(a=>({lote:a[1],racimos:a[2],lat:a[3],lng:a[4],hora:a[5],ficha:a[6]})));
  const usados=new Set(),out=[];
  for(const c of cs)for(const d of c.aco||[]){const [n,lote,rac,lat,lng,hora,fid,aco]=d;let i=-1;
    i=alz.findIndex((a,ix)=>!usados.has(ix)&&a.ficha&&(a.ficha===fid||a.ficha===aco));
    if(i<0)i=alz.findIndex((a,ix)=>!usados.has(ix)&&!a.ficha&&dist(lat,lng,a.lat,a.lng)<=30&&String(a.hora||'')>=String(hora||''));
    if(i>=0){usados.add(i);continue;}
    out.push({nom:c.nom,n,lote,racimos:rac,lat,lng,hora,ficha:!!fid});}
  return out;}
const minDesde=(f,h)=>{const t=Date.parse(`${f}T${h||'00:00'}:00`);return isNaN(t)?null:Math.round((Date.now()-t)/60000);};
let CAPA_PEND=null;
function verPendientesMapa(p){
  if(CAPA_PEND){mapa.removeLayer(CAPA_PEND);CAPA_PEND=null;}if(!p||!p.length)return;
  CAPA_PEND=L.layerGroup().addTo(mapa);
  for(const a of p)L.marker([a.lat,a.lng],{icon:iconoDescargue({n:a.n,racimos:a.racimos}),zIndexOffset:6000,keyboard:false})
    .bindPopup(`<b>Acopio sin alzar</b><br>${esc(a.nom)} · viaje ${a.n}<br>${a.racimos} racimos · ${esc(a.hora||'')}${a.lote?'<br>Lote '+esc(a.lote):''}`).addTo(CAPA_PEND);
  try{mapa.fitBounds(L.latLngBounds(p.map(a=>[a.lat,a.lng])),{padding:[50,50],maxZoom:18});}catch(e){}}
function abrirTablero(fecha){
  const todas=Object.values(copiasSup());const fechas=[...new Set(todas.map(c=>c.f))].sort().reverse();
  fecha=fecha||(fechas.includes(fechaLocal())?fechaLocal():(fechas[0]||fechaLocal()));
  const CS=todas.filter(c=>c.f===fecha).sort((a,b)=>String(a.nom).localeCompare(String(b.nom))||String(a.ini).localeCompare(String(b.ini)));
  const tot={rc:0,rr:0,ra:0,aco:0};const lot={};
  for(const c of CS){tot.rc+=c.rc||0;tot.rr+=c.rr||0;tot.ra+=c.ra||0;tot.aco+=(c.aco||[]).length;
    for(const [l,v] of Object.entries(c.lotes||{})){const x=lot[l]||(lot[l]={c:0,r:0,a:0});x.c+=v.c||0;x.r+=v.r||0;x.a+=v.a||0;}}
  const pend=acopiosSinAlzar(CS),abiertos=CS.filter(c=>c.vab>0),hay=x=>x?num(x):'—';
  const filas=CS.map(c=>`<tr><td><b>${esc(c.nom)}</b><small>${esc((laborInfo(c.lab)||{}).corto||c.lab)} · ${esc(Object.keys(c.lotes||{}).join(', ')||'—')} · ${esc(c.ini)}–${esc(c.fin||'…')}</small></td>
    <td class="n">${hay(c.rc)}</td><td class="n">${hay(c.rr)}</td><td class="n">${hay(c.ra)}</td><td class="n">${hay((c.aco||[]).length)}</td></tr>`).join('');
  const dif=x=>{const t=[];if(x.c&&x.r<x.c)t.push(`${num(x.c-x.r)} sin recolectar`);if(x.r&&x.a<x.r)t.push(`${num(x.r-x.a)} sin alzar`);if(x.r>x.c&&x.c)t.push(`${num(x.r-x.c)} recolectados de más`);return t.join(', ');};
  const filasL=Object.entries(lot).sort((a,b)=>a[0].localeCompare(b[0])).map(([l,x])=>{const d=dif(x);
    return `<tr><td><b>${esc(l)}</b>${d?`<small class="dif">${d}</small>`:'<small>✓ cuadra</small>'}</td><td class="n">${hay(x.c)}</td><td class="n">${hay(x.r)}</td><td class="n">${hay(x.a)}</td></tr>`;}).join('');
  const alertas=[...pend.map(a=>{const m=fecha===fechaLocal()?minDesde(fecha,a.hora):null;
      return `<li>📍 Acopio sin alzar · ${a.lote?'lote <b>'+esc(a.lote)+'</b> · ':''}${num(a.racimos)} racimos · ${esc(a.nom)} (viaje ${a.n}) · desde ${esc(a.hora||'—')}${m!=null&&m>=0?` (hace ${m>=60?Math.floor(m/60)+' h '+(m%60)+' min':m+' min'})`:''}${a.ficha?' · con ficha':''}</li>`;}),
    ...abiertos.map(c=>`<li>🚜 ${esc(c.nom)} tiene ${num(c.vab)} racimos recolectados sin descargar (viaje abierto).</li>`)];
  abrirHoja('Tablero del supervisor',`
    <div class="tab-fechas">${(fechas.length?fechas:[fecha]).slice(0,7).map(f=>`<button type="button" class="btn${f===fecha?' prim':''}" data-tf="${esc(f)}">${esc(f===fechaLocal()?'Hoy':f.slice(5).split('-').reverse().join('/'))}</button>`).join('')}</div>
    <div class="stats" style="margin-top:10px">
      <div class="stat rac-lab">${svgPic('corte',34)}<b>${num(tot.rc)}</b><span>Racimos de corte</span></div>
      <div class="stat rac-lab">${svgPic('recoleccion',34)}<b>${num(tot.rr)}</b><span>Racimos de recolección</span></div>
      <div class="stat rac-lab">${svgPic('alce',34)}<b>${num(tot.ra)}</b><span>Racimos alzados</span></div></div>
    <p class="tenue">${CS.length} copia(s) recibida(s) del ${esc(fecha)} · ${num(tot.aco)} acopio(s). Copia informativa: la data oficial sube del celular de cada operario.</p>
    <h3>Resumen por operario</h3>
    ${CS.length?`<div class="tabla-cont"><table class="tabla tab-sup" id="tsOper"><tr><th>Operario</th><th class="n">Corte</th><th class="n">Recol.</th><th class="n">Alz.</th><th class="n">Acop.</th></tr>${filas}
      <tr class="tot"><td>Total</td><td class="n">${num(tot.rc)}</td><td class="n">${num(tot.rr)}</td><td class="n">${num(tot.ra)}</td><td class="n">${num(tot.aco)}</td></tr></table></div>`
      :'<div class="aviso">Aún no hay copias de este día. Toque «Recibir jornadas» y escanee el QR de cada operario.</div>'}
    <h3>Cuadre por lote</h3>
    ${filasL?`<div class="tabla-cont"><table class="tabla tab-sup" id="tsLotes"><tr><th>Lote</th><th class="n">Cort.</th><th class="n">Recol.</th><th class="n">Alz.</th></tr>${filasL}</table></div>`:'<p class="tenue">Sin datos.</p>'}
    <h3>Alertas</h3>
    ${alertas.length?`<ul id="tsAlertas">${alertas.join('')}</ul>`:'<p class="tenue">✓ Sin alertas.</p>'}
    ${pend.length?`<button type="button" class="btn ancho" id="tsMapa">${IC.mapa} Ver acopios sin alzar en el mapa</button>`:''}
    <button type="button" class="btn prim ancho" id="tsRecibir" style="margin-top:8px">${IC.descarga} Recibir más jornadas</button>`);
  document.querySelectorAll('[data-tf]').forEach(b=>b.onclick=()=>abrirTablero(b.dataset.tf));
  const bm=$('#tsMapa');if(bm)bm.onclick=()=>{cerrarHoja();verPendientesMapa(pend);};
  $('#tsRecibir').onclick=recibirCopias;
  return {CS,tot,lot,pend};}
