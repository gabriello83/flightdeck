/* ===================================================================
   La bienvenida del informe general operativo (Gabriele, 20-oct-2026).

   Al entrar, el logo de Serunion Vending se deshace en teselas, las teselas
   forman una esfera que gira sobre si misma y la esfera se rompe: sus trozos
   vuelan hasta los cuadrados de la pagina y se convierten en ellos.

   - Sale una vez, al entrar: la pantalla de acceso deja la marca en
     sessionStorage y aqui se borra nada mas leerla. Volver al informe desde
     otra seccion no la repite. `?bienvenida` en la direccion la fuerza.
   - Se salta con un clic, una tecla o el boton «Saltar».
   - Con «reducir movimiento» en el sistema no sale.
   - Mientras llegan los datos, la esfera sigue girando: hace de «Cargando».
     Si no llegan, o falla la API, se apaga sin romperse y la pagina dice lo
     que tenga que decir.
   - Todo es de esta pagina: lienzo 2D y el logo en data:, sin bibliotecas
     ni ningun otro dominio (CLAUDE.md).
   =================================================================== */
(function(){
  "use strict";
  const CLAVE = "digivend.bienvenida";
  let toca = /[?&]bienvenida(=|&|$)/.test(location.search);
  try{
    if(sessionStorage.getItem(CLAVE) === "1"){ toca = true; sessionStorage.removeItem(CLAVE); }
  }catch(e){}
  if(!toca) return;
  if(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const raiz = document.documentElement;
  const lienzoPrueba = document.createElement("canvas");
  if(!lienzoPrueba.getContext || !lienzoPrueba.getContext("2d")) return;

  const LOGO = "data:image/png;base64,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";

  /* ------------------------------------------------------------- el tiempo
     En segundos desde que arranca. La rotura espera a que esten los cuadrados;
     si a los NUNCA no estan, la esfera se apaga sin romperse. */
  const T = {
    logo: 0.55,        // el logo aparece
    pixel: 0.85,       // el logo se vuelve teselas
    morf: 0.95,        // las teselas viajan a la esfera (escalonadas de izquierda a derecha)
    ola: 0.35,         // lo que tarda la ola de izquierda a derecha
    viaje: 0.8,        // lo que tarda cada tesela en llegar a la esfera
    rotura: 2.15,      // lo antes que se rompe
    grieta: 0.42,      // de la primera a la ultima tesela que se suelta
    vuelo: 0.82,       // lo que tarda cada trozo en llegar a su cuadrado
    encaje: 0.16,      // el destello al encajar
    revela: 0.35,      // el cuadrado de verdad aparece debajo
    nunca: 9,
  };

  /* --------------------------------------------------------- lo de la pagina */
  const estilo = document.createElement("style");
  estilo.textContent =
    "html.bienvenida #cuadros .cuadro:not(.bv-listo){opacity:0}" +
    ".bv-capa{position:fixed;inset:0;z-index:2147483000;cursor:pointer;touch-action:none}" +
    ".bv-fondo{position:absolute;inset:0;background:var(--fondo,#f4f4f2)}" +
    ".bv-capa canvas{position:absolute;inset:0;width:100%;height:100%;display:block}" +
    ".bv-saltar{position:absolute;right:16px;bottom:16px;font:inherit;font-size:13px;cursor:pointer;" +
    "color:var(--tinta-2,#52514e);background:transparent;border:1px solid var(--borde-fuerte,#cdccc5);" +
    "border-radius:999px;padding:5px 13px;opacity:.85}" +
    ".bv-saltar:hover{opacity:1}" +
    ".bv-saltar:focus-visible{outline:2px solid var(--s1,#2a78d6);outline-offset:2px}";
  document.head.appendChild(estilo);
  raiz.classList.add("bienvenida");

  const capa = document.createElement("div");
  capa.className = "bv-capa";
  const fondo = document.createElement("div");
  fondo.className = "bv-fondo";
  const lienzo = document.createElement("canvas");
  lienzo.setAttribute("aria-hidden", "true");
  const saltar = document.createElement("button");
  saltar.type = "button";
  saltar.className = "bv-saltar";
  saltar.textContent = "Saltar";
  saltar.setAttribute("aria-label", "Saltar la animación de entrada");
  capa.append(fondo, lienzo, saltar);
  (document.body || raiz).appendChild(capa);
  const ctx = lienzo.getContext("2d");

  /* ----------------------------------------------------------- el tema */
  function oscuro(){
    const t = raiz.getAttribute("data-theme");
    if(t) return t === "dark";
    let g = null;
    try{ g = localStorage.getItem("digivend.tema"); }catch(e){}
    if(g) return g === "dark";
    return !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
  }
  const OSC = oscuro();
  // El azul de la marca, #105b82, y su esfera: sombra, cuerpo, luz y brillo.
  const C = OSC ? {
    logo:[255,255,255], sombra:[6,40,62], luz:[70,160,220], brillo:[235,246,255],
    dentro:[3,18,28], halo:"rgba(57,135,229,", suelo:"rgba(0,0,0,", halo_a:0.20, suelo_a:0.45,
  } : {
    logo:[16,91,130], sombra:[8,52,78], luz:[52,140,196], brillo:[240,248,255],
    dentro:[5,30,46], halo:"rgba(16,91,130,", suelo:"rgba(16,40,60,", halo_a:0.10, suelo_a:0.16,
  };
  const mezcla = (a, b, t) => [a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t];
  const rgb = (c, a) => a == null || a >= 1
    ? `rgb(${c[0]|0},${c[1]|0},${c[2]|0})`
    : `rgba(${c[0]|0},${c[1]|0},${c[2]|0},${a.toFixed(3)})`;

  /* ----------------------------------------------------------- las curvas */
  const lim = (x, a, b) => x < a ? a : x > b ? b : x;
  const suave = (a, b, x) => { const t = lim((x-a)/(b-a), 0, 1); return t*t*(3-2*t); };
  const entraSale = t => t < .5 ? 4*t*t*t : 1 - Math.pow(-2*t+2, 3)/2;
  const sale = t => 1 - Math.pow(1-t, 3);
  // Azar con semilla: la animacion es siempre la misma.
  let semilla = 20261020;
  const azar = () => { semilla = (semilla*1664525 + 1013904223) >>> 0; return semilla/4294967296; };

  /* ----------------------------------------------------------- las medidas */
  let VW = 0, VH = 0, DPR = 1, CX = 0, CY = 0, R = 0, D = 0, LW = 0, LH = 0;
  function mide(){
    VW = window.innerWidth; VH = window.innerHeight;
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    lienzo.width = Math.round(VW*DPR); lienzo.height = Math.round(VH*DPR);
    CX = VW/2; CY = VH*0.46;
    R = lim(Math.min(VW, VH)*0.21, 70, 170);
    D = R*5;
    LW = Math.min(520, VW - 48); LH = LW*129/640;
  }
  mide();

  /* -------------------------------------------- la esfera, hecha de teselas
     Bandas de latitud con tantas teselas como quepan en cada una: una bola de
     espejos. Cada tesela guarda sus cuatro esquinas en la esfera unidad. */
  const BANDAS = VW < 560 ? 17 : 22;
  const teselas = [];
  for(let i=0; i<BANDAS; i++){
    const lat = -Math.PI/2 + (i+0.5)*Math.PI/BANDAS;
    const n = Math.max(3, Math.round(2*BANDAS*Math.cos(lat)));
    const hl = Math.PI/BANDAS*0.43, hw = Math.PI/n*0.86;
    for(let j=0; j<n; j++){
      const lon = (j + (i%2)*0.5)/n*2*Math.PI;
      const p = (la, lo) => [Math.cos(la)*Math.sin(lo), -Math.sin(la), Math.cos(la)*Math.cos(lo)];
      teselas.push({
        lat, lon,
        esq:[p(lat-hl, lon-hw), p(lat-hl, lon+hw), p(lat+hl, lon+hw), p(lat+hl, lon-hw)],
        n:p(lat, lon),
        azar:azar(),
      });
    }
  }
  const N = teselas.length;

  /* El giro: arranca suave y acelera hasta una velocidad que ya no cambia
     mientras se espera a los datos. Inclinada, para que se vea el polo. */
  const INCL = 0.38, ci = Math.cos(INCL), si = Math.sin(INCL);
  function giro(t){
    const u = Math.max(0, t - T.morf + 0.4), u1 = 1.8, w0 = 0.5, a = 0.65;
    return u <= u1 ? w0*u + a*u*u : w0*u1 + a*u1*u1 + (w0 + 2*a*u1)*(u - u1);
  }
  function rota(v, cg, sg){
    const x = v[0]*cg + v[2]*sg, z0 = -v[0]*sg + v[2]*cg;
    return [x, v[1]*ci - z0*si, v[1]*si + z0*ci];
  }
  const LUZ = (() => { const l = [-0.45, -0.62, 0.64], m = Math.hypot(...l); return l.map(x => x/m); })();
  const MEDIO = (() => { const h = [LUZ[0], LUZ[1], LUZ[2]+1], m = Math.hypot(...h); return h.map(x => x/m); })();
  function tono(n){
    const lam = Math.max(0, n[0]*LUZ[0] + n[1]*LUZ[1] + n[2]*LUZ[2]);
    const esp = Math.pow(Math.max(0, n[0]*MEDIO[0] + n[1]*MEDIO[1] + n[2]*MEDIO[2]), 30);
    const borde = Math.pow(1 - Math.max(0, n[2]), 3);
    let c = mezcla(C.sombra, C.luz, 0.12 + 0.88*lam);
    c = mezcla(c, C.luz, borde*0.35);
    return mezcla(c, C.brillo, esp*0.9);
  }
  // Del mundo (pixeles, z hacia quien mira) a la pantalla, con perspectiva.
  function proyecta(p){
    const f = D/(D - p[2]);
    return [CX + (p[0]-CX)*f, CY + (p[1]-CY)*f, p[2]];
  }

  /* -------------------------------------------- el logo, como mapa de teselas */
  const img = new Image();
  let logoListo = false, logoColor = null;
  img.onload = () => {
    const w = Math.round(LW), h = Math.round(LH);
    // El logo en su color (azul en claro, blanco en oscuro), a la resolucion de la pantalla.
    logoColor = document.createElement("canvas");
    logoColor.width = Math.round(w*DPR); logoColor.height = Math.round(h*DPR);
    const lc = logoColor.getContext("2d");
    lc.drawImage(img, 0, 0, logoColor.width, logoColor.height);
    lc.globalCompositeOperation = "source-in";
    lc.fillStyle = rgb(C.logo);
    lc.fillRect(0, 0, logoColor.width, logoColor.height);

    // Donde hay tinta, a la medida de la pagina, para repartir las teselas.
    const m = document.createElement("canvas");
    m.width = w; m.height = h;
    const mc = m.getContext("2d");
    mc.drawImage(img, 0, 0, w, h);
    let datos;
    try{ datos = mc.getImageData(0, 0, w, h).data; }catch(e){ datos = null; }
    const tinta = (x, y) => datos ? datos[(y*w + x)*4 + 3] > 110 : true;
    let llenos = 0;
    if(datos) for(let k=3; k<datos.length; k+=4) if(datos[k] > 110) llenos++;
    else llenos = w*h*0.4;
    // El paso de la rejilla que da tantas celdas con tinta como teselas tiene la esfera.
    let g = Math.sqrt(llenos/N), celdas = [];
    for(let intento=0; intento<6; intento++){
      celdas = [];
      for(let y=g/2; y<h; y+=g) for(let x=g/2; x<w; x+=g)
        if(tinta(Math.min(w-1, x|0), Math.min(h-1, y|0))) celdas.push([x, y]);
      const r = celdas.length/N;
      if(r > 0.92 && r < 1.12) break;
      g *= Math.sqrt(r);
    }
    if(!celdas.length) celdas = [[w/2, h/2]];
    // Izquierda a derecha en el logo y en la esfera: los caminos no se cruzan tanto.
    celdas.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cg = Math.cos(giro(T.morf + T.viaje)), sg = Math.sin(giro(T.morf + T.viaje));
    const orden = teselas.map((s, i) => [rota(s.n, cg, sg), i])
      .sort((a, b) => a[0][0] - b[0][0] || a[0][1] - b[0][1]);
    const ox = CX - w/2, oy = CY - h/2;
    orden.forEach(([, i], k) => {
      const c = celdas[Math.min(celdas.length-1, Math.floor(k*celdas.length/N))];
      const s = teselas[i];
      s.lx = ox + c[0]; s.ly = oy + c[1]; s.lg = g*0.46;
      s.xn = c[0]/w;
    });
    logoListo = true;
  };
  img.src = LOGO;

  /* ------------------------------------------------------- los cuadrados */
  function cuadrados(){
    const cont = document.getElementById("cuadros");
    if(!cont || cont.hidden) return [];
    return [...cont.querySelectorAll(".cuadro")];
  }
  // La pagina ya ha dicho que no hay informe (error, sin dias): no hay nada que formar.
  function sinCuadrados(){
    const cargando = document.getElementById("cargando");
    const barra = document.getElementById("barra");
    const aviso = document.getElementById("aviso");
    if(cargando && !cargando.hidden && cargando.textContent.trim() !== "Cargando…") return true;
    if(cargando && cargando.hidden && barra && barra.hidden && aviso && !aviso.hidden) return true;
    const cont = document.getElementById("cuadros");
    return !!(cont && !cont.hidden && !cont.querySelector(".cuadro"));
  }
  const colorDe = el => {
    const m = getComputedStyle(el).backgroundColor.match(/[\d.]+/g) || [255, 255, 255];
    return [+m[0], +m[1], +m[2]];
  };

  /* La rotura: cada cuadrado visible pide una rejilla de celdas, y cada celda
     se la lleva una tesela. Las que sobran se van como polvo. */
  let rotura = null;
  function rompe(t, els){
    const vis = [];
    els.forEach(el => {
      const r = el.getBoundingClientRect();
      if(r.bottom > 0 && r.top < VH && r.right > 0 && r.left < VW && r.width > 4 && r.height > 4)
        vis.push({el, r, color:colorDe(el), radio:parseFloat(getComputedStyle(el).borderTopLeftRadius) || 0,
          fin:0, listo:false});
      else el.classList.add("bv-listo");
    });
    if(!vis.length) return apaga(t);
    const reparto = Math.max(1, Math.floor(N*0.9/vis.length));
    const celdas = [];
    vis.forEach((c, k) => {
      const cols = Math.max(1, Math.round(Math.sqrt(reparto*c.r.width/c.r.height)));
      const filas = Math.max(1, Math.floor(reparto/cols));
      const cw = c.r.width/cols, ch = c.r.height/filas;
      for(let f=0; f<filas; f++) for(let q=0; q<cols; q++)
        celdas.push({k, x:c.r.left + q*cw, y:c.r.top + f*ch, w:cw, h:ch});
    });
    // Se sueltan antes las de delante; las de detras, al quedar al aire, despues.
    const ahora = teselas.map(s => s.vista || {z:0, cx:CX, cy:CY});
    const porZ = teselas.map((s, i) => i)
      .sort((a, b) => (ahora[b].z + teselas[b].azar*R*0.6) - (ahora[a].z + teselas[a].azar*R*0.6));
    const llevan = porZ.slice(0, celdas.length), polvo = porZ.slice(celdas.length);
    // Por angulo alrededor de la esfera, en las dos: cada trozo va al lado que le cae.
    const ang = (x, y) => Math.atan2(y - CY, x - CX);
    const tesAng = llevan.slice().sort((a, b) => ang(ahora[a].cx, ahora[a].cy) - ang(ahora[b].cx, ahora[b].cy));
    const celAng = celdas.slice().sort((a, b) => ang(a.x + a.w/2, a.y + a.h/2) - ang(b.x + b.w/2, b.y + b.h/2));
    const rango = new Map(porZ.map((i, k) => [i, k]));
    tesAng.forEach((i, k) => {
      const s = teselas[i], c = celAng[k];
      s.destino = c;
      s.suelta = t + T.grieta*rango.get(i)/N;
      const fin = s.suelta + T.vuelo;
      if(fin > vis[c.k].fin) vis[c.k].fin = fin;
    });
    polvo.forEach(i => {
      const s = teselas[i];
      s.destino = null;
      s.suelta = t + T.grieta*rango.get(i)/N;
    });
    teselas.forEach(s => { s.giros = (s.azar < .5 ? -1 : 1)*(1 + Math.floor(s.azar*3)); s.vueltas = 1 + (s.azar*7|0)%2; });
    rotura = {t, vis};
  }

  /* El final sin cuadrados: la esfera se encoge y se va. */
  let salida = null;
  function apaga(t){ salida = t; }

  /* ----------------------------------------------------------- el dibujo */
  const inicio = performance.now();
  let rafId = 0, acabado = false;

  function cuadro(ahora){
    if(acabado) return;
    const t = (ahora - inicio)/1000;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    ctx.clearRect(0, 0, VW, VH);

    // ¿Toca romper?
    if(!rotura && salida == null && logoListo && t >= T.rotura){
      const els = cuadrados();
      if(els.length) rompe(t, els);
      else if(sinCuadrados() || t >= T.nunca) apaga(t);
    }

    // El fondo se va con la rotura: debajo ya esta la pagina.
    const tf = rotura ? rotura.t : salida;
    fondo.style.opacity = tf == null ? "1" : String(1 - sale(lim((t - tf)/0.55, 0, 1)));

    if(!logoListo){ rafId = requestAnimationFrame(cuadro); return; }

    const encoge = salida == null ? 1 : 1 - entraSale(lim((t - salida)/0.45, 0, 1));
    if(salida != null && t - salida > 0.5) return acaba();

    // Halo y sombra en el suelo, con la esfera.
    const hayEsfera = suave(T.morf, T.morf + 0.9, t)
      * (rotura ? 1 - suave(rotura.t, rotura.t + T.grieta + 0.3, t) : 1) * encoge;
    if(hayEsfera > 0.01){
      const halo = ctx.createRadialGradient(CX, CY, R*0.2, CX, CY, R*2.3);
      halo.addColorStop(0, C.halo + (C.halo_a*hayEsfera).toFixed(3) + ")");
      halo.addColorStop(1, C.halo + "0)");
      ctx.fillStyle = halo;
      ctx.fillRect(CX - R*2.4, CY - R*2.4, R*4.8, R*4.8);
      const sy = CY + R*1.32, sx = R*0.95*encoge;
      ctx.save();
      ctx.translate(CX, sy); ctx.scale(1, 0.17);
      const suelo = ctx.createRadialGradient(0, 0, 0, 0, 0, sx);
      suelo.addColorStop(0, C.suelo + (C.suelo_a*hayEsfera).toFixed(3) + ")");
      suelo.addColorStop(1, C.suelo + "0)");
      ctx.fillStyle = suelo;
      ctx.beginPath(); ctx.arc(0, 0, sx, 0, Math.PI*2); ctx.fill();
      ctx.restore();
    }

    // El nucleo: con la esfera cerrada, las juntas entre teselas se ven oscuras,
    // como en una bola de espejos. Se quita en cuanto empieza la rotura.
    const nucleo = suave(T.morf + T.ola + T.viaje - 0.25, T.morf + T.ola + T.viaje, t)
      * (rotura ? 1 - suave(rotura.t, rotura.t + 0.12, t) : 1) * encoge;
    if(nucleo > 0.01){
      ctx.globalAlpha = nucleo;
      ctx.fillStyle = rgb(C.dentro);
      ctx.beginPath(); ctx.arc(CX, CY, R*encoge*0.985*D/Math.sqrt(D*D - R*R*encoge*encoge), 0, Math.PI*2); ctx.fill();
      ctx.globalAlpha = 1;
    }

    // El logo, entero, con un brillo que lo cruza; luego se deshace.
    const aLogo = sale(lim(t/T.logo, 0, 1)) * (1 - suave(T.pixel, T.pixel + 0.2, t));
    if(aLogo > 0.005) pintaLogo(t, aLogo);

    // Las teselas.
    const aTes = suave(T.pixel, T.pixel + 0.2, t);
    if(aTes > 0.005) pintaTeselas(t, aTes, encoge);

    // Los cuadrados que ya han encajado.
    let pendientes = 0;
    if(rotura) rotura.vis.forEach(c => { if(pintaCuadrado(t, c)) pendientes++; });

    if(rotura && !pendientes && teselas.every(s => t > s.suelta + T.vuelo)) return acaba();
    rafId = requestAnimationFrame(cuadro);
  }

  function pintaLogo(t, a){
    const e = sale(lim(t/T.logo, 0, 1));
    const esc = 0.94 + 0.06*e;
    const w = LW*esc, h = LH*esc;
    const x = CX - w/2, y = CY - h/2;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.drawImage(logoColor, x, y, w, h);
    // El brillo: una franja de luz que pasa por las letras, solo sobre la tinta.
    const b = lim((t - 0.2)/0.6, 0, 1);
    if(b > 0 && b < 1){
      const capaB = pintaLogo.capa || (pintaLogo.capa = document.createElement("canvas"));
      capaB.width = logoColor.width; capaB.height = logoColor.height;
      const bc = capaB.getContext("2d");
      bc.drawImage(logoColor, 0, 0);
      bc.globalCompositeOperation = "source-atop";
      const W = capaB.width, H = capaB.height, cx = -0.3*W + b*1.6*W;
      const gr = bc.createLinearGradient(cx - W*0.12, 0, cx + W*0.12, H*0.6);
      gr.addColorStop(0, "rgba(255,255,255,0)");
      gr.addColorStop(0.5, OSC ? "rgba(140,200,255,.85)" : "rgba(255,255,255,.75)");
      gr.addColorStop(1, "rgba(255,255,255,0)");
      bc.fillStyle = gr; bc.fillRect(0, 0, W, H);
      ctx.drawImage(capaB, x, y, w, h);
    }
    ctx.restore();
  }

  function pintaTeselas(t, aTes, encoge){
    const th = giro(t), cg = Math.cos(th), sg = Math.sin(th);
    const RR = R*encoge;
    const lista = [];
    for(const s of teselas){
      if(rotura && t >= s.suelta){
        // Suelta: se queda con donde estaba y desde ahi vuela.
        if(!s.vuelo) s.vuelo = arranque(s);
        lista.push({z:1e6 + s.vuelo.orden, s, vuela:true});
        continue;
      }
      // En el logo o en la esfera, o entre los dos.
      const e = entraSale(lim((t - T.morf - T.ola*s.xn)/T.viaje, 0, 1));
      const salto = Math.sin(Math.PI*e)*R*0.35;
      const esq = new Array(4);
      for(let k=0; k<4; k++){
        const v = rota(s.esq[k], cg, sg);
        const ex = CX + v[0]*RR, ey = CY + v[1]*RR, ez = v[2]*RR;
        const fx = s.lx + (k === 1 || k === 2 ? s.lg : -s.lg);
        const fy = s.ly + (k < 2 ? s.lg : -s.lg);
        esq[k] = proyecta([fx + (ex - fx)*e, fy + (ey - fy)*e, ez*e + salto]);
      }
      const nr = rota(s.n, cg, sg);
      const nz = 1 + (nr[2] - 1)*e;
      const color = mezcla(C.logo, nz >= 0 ? tono(nr) : mezcla(C.dentro, C.sombra, 0.5 + 0.5*nr[2] + 0.3), suave(0, 0.7, e));
      const z = (esq[0][2] + esq[1][2] + esq[2][2] + esq[3][2])/4;
      const cx = (esq[0][0] + esq[1][0] + esq[2][0] + esq[3][0])/4;
      const cy = (esq[0][1] + esq[1][1] + esq[2][1] + esq[3][1])/4;
      s.vista = {esq, z, cx, cy, color, nz};
      lista.push({z, s});
    }
    lista.sort((a, b) => a.z - b.z);
    for(const it of lista){
      if(it.vuela){ pintaVuelo(t, it.s); continue; }
      const v = it.s.vista;
      ctx.globalAlpha = aTes;
      ctx.fillStyle = rgb(v.color);
      ctx.beginPath();
      ctx.moveTo(v.esq[0][0], v.esq[0][1]);
      ctx.lineTo(v.esq[1][0], v.esq[1][1]);
      ctx.lineTo(v.esq[2][0], v.esq[2][1]);
      ctx.lineTo(v.esq[3][0], v.esq[3][1]);
      ctx.closePath();
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  let ordenVuelo = 0;
  function arranque(s){
    const v = s.vista;
    const area = Math.abs((v.esq[0][0]-v.esq[2][0])*(v.esq[1][1]-v.esq[3][1]) - (v.esq[1][0]-v.esq[3][0])*(v.esq[0][1]-v.esq[2][1]))/2;
    const lado = Math.max(2, Math.sqrt(area));
    const ang0 = Math.atan2(v.esq[1][1] - v.esq[0][1], v.esq[1][0] - v.esq[0][0]);
    // Hacia fuera de la esfera primero; luego, a su sitio.
    let dx = v.cx - CX, dy = v.cy - CY;
    const m = Math.hypot(dx, dy) || 1; dx /= m; dy /= m;
    const empuje = R*(0.55 + 0.6*s.azar);
    const d = s.destino;
    const p1 = d ? [d.x + d.w/2, d.y + d.h/2] : [v.cx + dx*R*(1.6 + s.azar), v.cy + dy*R*(1.6 + s.azar)];
    const c = [v.cx + dx*empuje + (p1[0] - v.cx)*0.2, v.cy + dy*empuje + (p1[1] - v.cy)*0.2 - R*0.25];
    return {p0:[v.cx, v.cy], c, p1, lado, ang0, color:v.nz >= 0 ? v.color : tono([0, 0, 1]), orden:ordenVuelo++};
  }

  function pintaVuelo(t, s){
    const f = s.vuelo, d = s.destino;
    const u = lim((t - s.suelta)/T.vuelo, 0, 1);
    if(d && rotura.vis[d.k].listo) return;            // ya lo pinta su cuadrado
    const e = entraSale(u);
    const a = 1 - e;
    const x = a*a*f.p0[0] + 2*a*e*f.c[0] + e*e*f.p1[0];
    const y = a*a*f.p0[1] + 2*a*e*f.c[1] + e*e*f.p1[1];
    if(!d){
      // Polvo: se va hacia fuera y se apaga.
      const al = 1 - sale(u);
      if(al < 0.01) return;
      ctx.save();
      ctx.globalAlpha = al;
      ctx.translate(x, y); ctx.rotate(f.ang0 + s.giros*Math.PI*u);
      const l = f.lado*(1 - 0.7*u);
      ctx.fillStyle = rgb(f.color);
      ctx.fillRect(-l/2, -l/2, l, l);
      ctx.restore();
      return;
    }
    const card = rotura.vis[d.k];
    const hueco = 2.5*(1 - suave(0.75, 1, u)) - 0.6*suave(0.9, 1, u);
    const w = f.lado + (d.w - hueco - f.lado)*e, h = f.lado + (d.h - hueco - f.lado)*e;
    const ang = (f.ang0 + s.giros*Math.PI*0.5)*(1 - e);
    const voltea = Math.cos(s.vueltas*Math.PI*(1 - e));
    ctx.save();
    ctx.translate(x, y); ctx.rotate(ang); ctx.scale(voltea, 1);
    ctx.fillStyle = rgb(mezcla(f.color, card.color, suave(0.15, 0.85, u)));
    ctx.fillRect(-w/2, -h/2, w, h);
    ctx.restore();
  }

  /* Un cuadrado con todas sus teselas: se pinta entero, con un destello, y el
     de verdad aparece debajo mientras el pintado se desvanece. Devuelve si
     aun queda algo que pintar de el. */
  function pintaCuadrado(t, c){
    if(t < c.fin) return true;
    const u = t - c.fin;
    if(!c.listo){ c.listo = true; }
    if(u >= T.encaje && !c.el.classList.contains("bv-listo")) c.el.classList.add("bv-listo");
    const al = u < T.encaje ? 1 : 1 - suave(0, 1, (u - T.encaje)/T.revela);
    if(al <= 0.002) return false;
    const r = c.r, esc = 1 + 0.025*Math.sin(Math.PI*lim(u/T.encaje, 0, 1));
    ctx.save();
    ctx.globalAlpha = al;
    ctx.translate(r.left + r.width/2, r.top + r.height/2); ctx.scale(esc, esc);
    redondo(-r.width/2, -r.height/2, r.width, r.height, c.radio);
    ctx.fillStyle = rgb(c.color);
    ctx.fill();
    if(u < T.encaje){
      ctx.globalAlpha = al*0.32*(1 - u/T.encaje);
      ctx.fillStyle = "#fff";
      ctx.fill();
    }
    ctx.restore();
    return true;
  }
  function redondo(x, y, w, h, r){
    r = Math.min(r, w/2, h/2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  /* ----------------------------------------------------------- el final */
  function acaba(){
    if(acabado) return;
    acabado = true;
    cancelAnimationFrame(rafId);
    removeEventListener("keydown", tecla, true);
    removeEventListener("resize", acaba);
    removeEventListener("scroll", acaba);
    raiz.classList.remove("bienvenida");
    cuadrados().forEach(el => el.classList.remove("bv-listo"));
    capa.style.transition = "opacity .2s ease-out";
    capa.style.opacity = "0";
    capa.style.pointerEvents = "none";
    setTimeout(() => { capa.remove(); estilo.remove(); }, 260);
  }
  function tecla(e){
    if(e.key === "Tab") return;
    e.preventDefault(); e.stopPropagation();
    acaba();
  }
  capa.addEventListener("pointerdown", e => { e.preventDefault(); acaba(); });
  saltar.addEventListener("click", acaba);
  addEventListener("keydown", tecla, true);
  addEventListener("resize", acaba);
  addEventListener("scroll", acaba);

  rafId = requestAnimationFrame(cuadro);
})();
