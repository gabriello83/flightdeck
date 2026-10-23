/* ===================================================================
   El asistente y Vendi, su muñeco (docs/40 y docs/69).

   Una sola pieza para todas las paginas que lo llevan: el panel y el informe
   general operativo. La pagina la monta con

       Asistente.monta({ pagina: "operativo", sugerencias: () => [...] })

   y esto pone el resto: el muñeco flotante, el bocadillo, el cajon del chat y
   la conversacion con /api/pregunta.

   Lo que lo hace seguro no esta aqui: el servidor le pasa al modelo los MISMOS
   datos recortados que esta pagina recibe para esa sesion, y no tiene otra via
   al dato. La pagina solo dice cual es (`pagina`); el perfil lo pone la sesion.

   - Vendi es una maquina de snacks del azul del logo de Serunion Vending
     (#0f5b84), con ojos, guantes y zapatillas, en SVG: ni imagen ni nada que
     pedir fuera del dominio (CLAUDE.md).
   - Saluda con la mano al entrar (despues de la bienvenida, si la hay), al
     pasarle el raton y al abrir el cajon. Con «reducir movimiento», quieto.
   - Las respuestas traen negritas, listas y tablas: se pintan escapando
     antes de dar formato. Cada tabla se baja a Excel (comun/xlsx.js, que se
     carga al pulsar) o a PDF (la ventana de imprimir, solo con la tabla).
   - Una pregunta larga va por pasos (docs/71): el servidor devuelve `sigue`
     y aqui se vuelve a llamar con ese id, ensenando que seccion esta mirando.
   - La conversacion se guarda en sessionStorage: sigue al cambiar de pagina
     en la misma pestana y se pierde al cerrarla. Al salir se borra.
   =================================================================== */
(function(){
  "use strict";

  const CSS = `
.as-fondo{position:fixed;inset:0;background:rgba(0,0,0,.28);opacity:0;pointer-events:none;transition:opacity .15s;z-index:40}
.as-fondo.vis{opacity:1;pointer-events:auto}
#chat{
  position:fixed;top:0;right:0;bottom:0;width:min(440px,100%);z-index:41;
  background:var(--tarjeta);border-left:1px solid var(--borde);display:flex;flex-direction:column;
  transform:translateX(100%);transition:transform .18s ease-out;box-shadow:-8px 0 28px rgba(0,0,0,.12)
}
#chat.vis{transform:none}
#chat header{display:flex;align-items:center;gap:8px;padding:14px 16px;border-bottom:1px solid var(--borde)}
#chat header b{font-size:15px;flex:1}
#chat header span{font-size:12px;color:var(--tinta-3);white-space:nowrap}
#chat .hilo{flex:1;overflow-y:auto;padding:14px 16px;display:flex;flex-direction:column;gap:12px}
.turno{max-width:92%;font-size:14px;line-height:1.5;overflow-wrap:anywhere}
.turno p{margin:0 0 6px}.turno p:last-child{margin:0}
.turno ul{margin:0 0 6px;padding-left:18px}
.turno .tabla{margin:6px 0 10px;border:1px solid var(--borde);border-radius:10px;overflow:hidden;background:var(--tarjeta)}
.turno .tabla .rueda{overflow-x:auto}
.turno table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
.turno th{background:color-mix(in srgb, var(--s1) 9%, var(--fondo));color:var(--tinta-2);font-weight:600;text-align:left;padding:8px 12px;white-space:nowrap}
.turno td{padding:8px 12px;border-top:1px solid var(--borde);white-space:nowrap}
.turno tbody tr:nth-child(even) td{background:color-mix(in srgb, var(--fondo) 55%, transparent)}
.turno td.n,.turno th.n{text-align:right}
.turno .bajar{display:flex;gap:6px;justify-content:flex-end;padding:6px 8px;border-top:1px solid var(--borde)}
.turno .bajar button{font:inherit;font-size:12px;color:var(--tinta-2);background:transparent;border:1px solid var(--borde-fuerte);border-radius:999px;padding:3px 10px;cursor:pointer}
.turno .bajar button:hover{color:var(--tinta);border-color:var(--tinta-3)}
.turno.espera{color:var(--tinta-3);font-style:italic}
.turno .apuntado{display:block;margin-top:6px;font-size:12px;color:var(--tinta-3)}
.turno.memoria .acciones{display:flex;gap:6px;margin-top:10px}
.turno.memoria .acciones button{font:inherit;font-size:12px;color:var(--tinta-2);background:transparent;border:1px solid var(--borde-fuerte);border-radius:999px;padding:3px 10px;cursor:pointer}
.turno.memoria .acciones button:hover{color:var(--tinta);border-color:var(--tinta-3)}
.turno.yo{align-self:flex-end;background:var(--s1);color:#fff;padding:8px 12px;border-radius:12px 12px 3px 12px;white-space:pre-wrap}
.turno.el{align-self:flex-start;color:var(--tinta)}
.turno.mal{align-self:flex-start;color:var(--critico,var(--rojo,#c62828))}
.turno.el .quien{display:block;font-size:11px;color:var(--tinta-3);text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}
.sugerencias{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 10px}
.sugerencias button{
  font:inherit;font-size:12.5px;color:var(--tinta-2);background:var(--fondo);text-align:left;
  border:1px solid var(--borde);border-radius:999px;padding:5px 11px;cursor:pointer
}
.sugerencias button:hover{border-color:var(--tinta-3);color:var(--tinta)}
#chat form{display:flex;gap:8px;padding:12px 16px;border-top:1px solid var(--borde);align-items:flex-end}
#chat textarea{
  flex:1;font:inherit;font-size:14px;color:var(--tinta);background:var(--fondo);resize:none;
  border:1px solid var(--borde-fuerte);border-radius:9px;padding:8px 10px;min-height:38px;max-height:140px
}
#chat textarea:focus{outline:2px solid var(--s1);outline-offset:1px;border-color:var(--s1)}
#chat form button{
  font:inherit;font-weight:600;font-size:13px;color:#fff;background:var(--s1);
  border:1px solid var(--s1);border-radius:9px;padding:9px 14px;cursor:pointer
}
#chat form button[disabled]{opacity:.55;cursor:progress}
#chat .pieChat{padding:0 16px 12px;font-size:11.5px;color:var(--tinta-3)}
@media (max-width:520px){ #chat{width:100%} }
.muneco{display:block;overflow:visible}
.muneco .mano{transform-origin:92px 70px;transform-box:view-box}
.muneco .todo{transform-origin:60px 140px;transform-box:view-box}
.saluda .mano{animation:as-saluda .42s ease-in-out 6 alternate}
.saluda .todo{animation:as-bote .84s ease-in-out 3}
@keyframes as-saluda{from{transform:rotate(-16deg)}to{transform:rotate(22deg)}}
@keyframes as-bote{0%,100%{transform:none}50%{transform:translateY(-3px) rotate(-2deg)}}
#bVendi{
  position:fixed;right:18px;bottom:18px;z-index:30;width:76px;height:94px;padding:0;
  background:transparent;border:0;cursor:pointer;filter:drop-shadow(0 4px 8px rgba(0,0,0,.18))
}
#bVendi .muneco{width:100%;height:100%}
#bVendi:focus-visible{outline:2px solid var(--s1);outline-offset:4px;border-radius:12px}
#bocadillo{
  position:fixed;right:100px;bottom:70px;z-index:30;max-width:200px;
  background:var(--tarjeta);color:var(--tinta);border:1px solid var(--borde-fuerte);
  border-radius:12px 12px 3px 12px;padding:8px 12px;font-size:13px;line-height:1.4;
  box-shadow:var(--sombra);opacity:0;transform:translateY(6px);transition:opacity .25s,transform .25s;pointer-events:none
}
#bocadillo.vis{opacity:1;transform:none}
#chat header .muneco{width:30px;height:37px;flex:none}
.btn .muneco{display:inline-block;width:15px;height:19px;vertical-align:-4px;margin-right:5px}
@media (max-width:520px){ #bVendi{width:60px;height:74px;right:12px;bottom:12px} #bocadillo{right:80px;bottom:52px} }
@media (prefers-reduced-motion:reduce){ .saluda .mano,.saluda .todo{animation:none} #bocadillo{transition:none} }
`;

  /* El dibujo. Una funcion, porque sale en tres sitios (el boton flotante, el
     boton Preguntar si la pagina lo tiene y la cabecera del cajon) y cada uno
     saluda por su cuenta. */
  function vendi(){
    const t="#0b2f45";
    const snack=(x,y,c)=>`<rect x="${x}" y="${y}" width="9" height="10" rx="2" fill="${c}"/>`;
    return `<svg class="muneco" viewBox="0 0 120 150" aria-hidden="true" focusable="false"><g class="todo">
  <path d="M48 118v15M72 118v15" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
  <path d="M36 140c0-6 6-8 12-8s9 3 9 8z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M63 140c0-5 3-8 9-8s12 2 12 8z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M29 70Q15 80 18 95" fill="none" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
  <circle cx="18" cy="99" r="7.5" fill="#fff" stroke="${t}" stroke-width="2.5"/>
  <rect x="28" y="14" width="64" height="106" rx="12" fill="#0f5b84" stroke="${t}" stroke-width="3"/>
  <rect x="33" y="19" width="54" height="5" rx="2.5" fill="#fff" opacity=".28"/>
  <ellipse cx="48" cy="34" rx="8.5" ry="10.5" fill="#fff" stroke="${t}" stroke-width="2"/>
  <ellipse cx="72" cy="34" rx="8.5" ry="10.5" fill="#fff" stroke="${t}" stroke-width="2"/>
  <circle cx="50" cy="36" r="4.2" fill="${t}"/><circle cx="70" cy="36" r="4.2" fill="${t}"/>
  <circle cx="51.5" cy="34.4" r="1.3" fill="#fff"/><circle cx="71.5" cy="34.4" r="1.3" fill="#fff"/>
  <path d="M50 46Q60 53 70 46" fill="none" stroke="${t}" stroke-width="3" stroke-linecap="round"/>
  <rect x="35" y="55" width="38" height="43" rx="4" fill="#d6ecf8" stroke="${t}" stroke-width="2"/>
  ${snack(38,58,"#f2b632")}${snack(49.5,58,"#2a78d6")}${snack(61,58,"#1baf7a")}
  ${snack(38,72,"#eb6834")}${snack(49.5,72,"#8e5bd0")}${snack(61,72,"#f2b632")}
  ${snack(38,85,"#1baf7a")}${snack(49.5,85,"#eb6834")}${snack(61,85,"#2a78d6")}
  <path d="M37 69.5h34M37 83h34" stroke="${t}" stroke-width="1.4" opacity=".55"/>
  <rect x="77" y="55" width="10" height="19" rx="2" fill="#2b2b2b"/>
  <path d="M80 59h1M84 59h1M80 63h1M84 63h1M80 67h1M84 67h1M80 71h1M84 71h1" stroke="#9fd3ff" stroke-width="2" stroke-linecap="round"/>
  <rect x="79" y="79" width="6" height="10" rx="1.5" fill="#f2c94c" stroke="${t}" stroke-width="1.4"/>
  <rect x="37" y="104" width="46" height="9" rx="3" fill="#2b2b2b"/>
  <g class="mano">
    <path d="M91 70Q106 64 106 47" fill="none" stroke="${t}" stroke-width="5" stroke-linecap="round"/>
    <path d="M99 44c-1-5 1-9 4-9 1-4 4-5 6-3 2-2 5-1 6 2 3 0 4 3 3 6l-2 9c-1 4-5 6-9 6s-8-3-8-7z" fill="#fff" stroke="${t}" stroke-width="2.5" stroke-linejoin="round"/>
  </g>
</g></svg>`;
  }

  function saluda(sitio){
    const m = sitio && sitio.querySelector(".muneco");
    if(!m) return;
    m.classList.remove("saluda"); void m.getBoundingClientRect(); m.classList.add("saluda");
  }

  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  /* Negritas, sobre el texto ya escapado: lo unico que se deja pasar es <b>. */
  const linea = s => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  const esNumero = s => /^[\s−\-+]*[\d.,]+\s*(%|€|h|min|km|uds?\.?)?\s*$/.test(s.replace(/<\/?b>/g, ""));

  /* La respuesta, en parrafos, listas y tablas. Todo lo que llega del modelo
     se escapa antes de darle formato. */
  function formatea(texto){
    const lineas = String(texto).split("\n"), out = [];
    for(let i = 0; i < lineas.length; ){
      const l = lineas[i].trim();
      if(!l){ i++; continue; }
      if(l.startsWith("|")){
        const filas = [];
        while(i < lineas.length && lineas[i].trim().startsWith("|")) filas.push(lineas[i++].trim());
        const celdas = f => f.replace(/^\||\|$/g, "").split("|").map(c => linea(c.trim()));
        const cuerpo = filas.filter(f => !/^\|[\s:|-]+\|?$/.test(f)).map(celdas);
        if(!cuerpo.length) continue;
        const [cab, ...resto] = cuerpo;
        const num = cab.map((_, j) => resto.length > 0 && resto.every(f => !f[j] || esNumero(f[j])));
        out.push('<div class="tabla"><div class="rueda"><table><thead><tr>' +
          cab.map((c, j) => `<th${num[j] ? ' class="n"' : ""}>${c}</th>`).join("") + "</tr></thead><tbody>" +
          resto.map(f => "<tr>" + f.map((c, j) => `<td${num[j] ? ' class="n"' : ""}>${c}</td>`).join("") + "</tr>").join("") +
          '</tbody></table></div><div class="bajar"><button type="button" data-bajar="xlsx">Excel</button>' +
          '<button type="button" data-bajar="pdf">PDF</button></div></div>');
        continue;
      }
      if(/^[-*•]\s+/.test(l)){
        const items = [];
        while(i < lineas.length && /^[-*•]\s+/.test(lineas[i].trim())) items.push(linea(lineas[i++].trim().replace(/^[-*•]\s+/, "")));
        out.push("<ul>" + items.map(x => `<li>${x}</li>`).join("") + "</ul>");
        continue;
      }
      out.push(`<p>${linea(l.replace(/^#+\s*/, ""))}</p>`);
      i++;
    }
    return out.join("");
  }

  /* ---------------------------------------------------- bajar una tabla */
  const sinFormato = s => s.replace(/\s+/g, " ").trim();
  /* «1.234,56 €» -> 1234.56; lo que no es una cifra se queda como texto. */
  function cifra(s){
    const t = sinFormato(s).replace(/[€%]|\b(h|min|km|uds?\.?)\b/g, "").replace(/\s/g, "").replace("−", "-");
    if(!/^[-+]?[\d.]*\d(,\d+)?$/.test(t)) return null;
    const n = Number(t.replace(/\./g, "").replace(",", "."));
    return isFinite(n) ? n : null;
  }
  function deTabla(tabla){
    const cab = [...tabla.querySelectorAll("thead th")].map(th => sinFormato(th.textContent));
    const filas = [...tabla.querySelectorAll("tbody tr")].map(tr => [...tr.children].map(td => sinFormato(td.textContent)));
    return {cab, filas};
  }
  function nombreFichero(ext){
    const d = new Date(), dos = n => String(n).padStart(2, "0");
    return `vendi_${d.getFullYear()}-${dos(d.getMonth()+1)}-${dos(d.getDate())}_${dos(d.getHours())}${dos(d.getMinutes())}.${ext}`;
  }
  let cargandoXlsx = null;
  function xlsxListo(){
    if(window.XLSX) return Promise.resolve();
    if(!cargandoXlsx) cargandoXlsx = new Promise((ok, mal) => {
      const s = document.createElement("script");
      s.src = "/comun/xlsx.js"; s.onload = ok; s.onerror = mal;
      document.head.appendChild(s);
    });
    return cargandoXlsx;
  }
  async function aExcel(tabla, pregunta){
    const {cab, filas} = deTabla(tabla);
    await xlsxListo();
    const euros = cab.map((_, j) => filas.some(f => /€/.test(f[j] || "")));
    const hoja = {
      nombre: "Vendi",
      titulo: [pregunta ? `Vendi · ${pregunta}` : "Vendi", `Generado el ${new Date().toLocaleString("es-ES")}`],
      columnas: cab.map((t, j) => ({titulo: t, ancho: Math.min(40, Math.max(10, t.length + 2,
                 ...filas.map(f => String(f[j] || "").length + 1))), euros: euros[j]})),
      filas: filas.map(f => f.map(c => { const n = cifra(c); return n === null ? c : n; })),
    };
    XLSX.descarga(XLSX.libro([hoja]), nombreFichero("xlsx"));
  }
  /* El PDF es la ventana de imprimir del navegador, con solo la tabla: ahi
     se elige «Guardar como PDF». Sin bibliotecas ni nada de fuera. */
  function aPdf(tabla, pregunta){
    const marco = document.createElement("iframe");
    marco.setAttribute("aria-hidden", "true");
    marco.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
    document.body.appendChild(marco);
    const doc = marco.contentDocument;
    doc.open();
    doc.write(`<!doctype html><html lang="es"><head><meta charset="utf-8"><title>${esc(nombreFichero("pdf"))}</title><style>
body{font:13px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#0b0b0b;margin:24px}
h1{font-size:15px;margin:0 0 2px}p{margin:0 0 14px;color:#52514e;font-size:12px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{background:#eef1f7;text-align:left;padding:8px 12px;font-weight:600;color:#3a3a37}
td{padding:8px 12px;border-top:1px solid #e2e1dc}.n{text-align:right}
tbody tr:nth-child(even) td{background:#f8f8f6}
@page{margin:14mm}</style></head><body>
<h1>${esc(pregunta ? "Vendi · " + pregunta : "Vendi")}</h1><p>Generado el ${esc(new Date().toLocaleString("es-ES"))} · dashboard.digivend.es</p>
${tabla.outerHTML}</body></html>`);
    doc.close();
    setTimeout(()=>{ try{ marco.contentWindow.focus(); marco.contentWindow.print(); }catch(e){}
                     setTimeout(()=>marco.remove(), 60000); }, 50);
  }

  const GUARDA = "digivend.asistente.hilo";
  function leeHilo(){ try{ const x = JSON.parse(sessionStorage.getItem(GUARDA) || "[]"); return Array.isArray(x) ? x.slice(-20) : []; }catch(e){ return []; } }
  function guardaHilo(h){ try{ sessionStorage.setItem(GUARDA, JSON.stringify(h.slice(-20))); }catch(e){} }

  function monta(op){
    op = op || {};
    const pagina = op.pagina || "panel";
    const $ = s => document.querySelector(s);
    /* {de, texto, pregunta?}: lo que se ve en el cajon. Viene de la pagina
       anterior si la hubo; a la API solo le llegan los ultimos 6. */
    const HILO = leeHilo();
    let enVuelo = false;

    const estilo = document.createElement("style");
    estilo.textContent = CSS;
    document.head.appendChild(estilo);

    const sitio = document.createElement("div");
    sitio.innerHTML = `
<div class="as-fondo" id="fondo" hidden></div>
<aside id="chat" role="dialog" aria-modal="true" aria-label="Asistente" hidden>
  <header>
    <span id="vendiChat">${vendi()}</span>
    <b>Asistente</b>
    <span id="chatQuedan"></span>
    <button class="btn" type="button" id="chatMemoria" title="Lo que Vendi recuerda de ti">Memoria</button>
    <button class="btn" type="button" id="chatCerrar" aria-label="Cerrar">Cerrar</button>
  </header>
  <div class="hilo" id="hilo" aria-live="polite"></div>
  <div class="sugerencias" id="sugerencias"></div>
  <form id="chatForm">
    <textarea id="chatTexto" rows="1" placeholder="Pregunta por tus datos…" maxlength="2000"></textarea>
    <button type="submit" id="chatEnviar">Enviar</button>
  </form>
  <p class="pieChat">${esc(op.pie || "Ve lo mismo que tú en la web, nada más. No ejecuta acciones.")}</p>
</aside>
<button id="bVendi" type="button" aria-label="Preguntar al asistente">${vendi()}</button>
<div id="bocadillo" aria-hidden="true">${esc(op.hola || "¡Hola! Pregúntame por los datos de esta página.")}</div>`;
    while(sitio.firstChild) document.body.appendChild(sitio.firstChild);

    const boton = op.boton || null;      /* el «Preguntar» de la cabecera, si la pagina lo tiene */
    if(boton){ boton.innerHTML = vendi() + esc(boton.textContent.trim() || "Preguntar"); boton.hidden = false; }

    function abre(abierto){
      const c = $("#chat"), f = $("#fondo");
      c.hidden = false; f.hidden = false;
      requestAnimationFrame(()=>{ c.classList.toggle("vis", abierto); f.classList.toggle("vis", abierto); });
      $("#bVendi").hidden = abierto;
      if(abierto){ $("#chatTexto").focus(); pintaSugerencias(); saluda($("#vendiChat")); $("#bocadillo").classList.remove("vis"); }
      else (boton || $("#bVendi")).focus();
    }
    function turno(de, texto, clase, preguntaDe){
      const d = document.createElement("div");
      d.className = "turno " + (clase || (de==="yo" ? "yo" : "el"));
      if(de === "yo" || clase) d.textContent = texto;
      else{
        d.innerHTML = `<span class="quien">Asistente</span>` + formatea(texto);
        d.querySelectorAll(".tabla").forEach(caja => {
          const t = caja.querySelector("table");
          caja.querySelector('[data-bajar="xlsx"]').addEventListener("click", ()=>aExcel(t, preguntaDe).catch(()=>{}));
          caja.querySelector('[data-bajar="pdf"]').addEventListener("click", ()=>aPdf(t, preguntaDe));
        });
      }
      $("#hilo").appendChild(d);
      $("#hilo").scrollTop = $("#hilo").scrollHeight;
      return d;
    }
    /* Las sugerencias las da la pagina, porque salen de lo que le ha llegado:
       a un perfil sin recaudacion no se le ofrece preguntar por la recaudacion. */
    function pintaSugerencias(){
      if(HILO.length){ $("#sugerencias").innerHTML = ""; return; }
      let q = [];
      try{ q = (op.sugerencias ? op.sugerencias() : []) || []; }catch(e){}
      $("#sugerencias").innerHTML = q.slice(0,4).map(t => `<button type="button">${esc(t)}</button>`).join("");
      $("#sugerencias").querySelectorAll("button").forEach(b => b.addEventListener("click", ()=>{
        $("#chatTexto").value = b.textContent;
        $("#chatForm").requestSubmit();
      }));
    }
    async function pregunta(texto){
      if(enVuelo || !texto) return;
      enVuelo = true;
      $("#chatEnviar").disabled = true;
      $("#sugerencias").innerHTML = "";
      turno("yo", texto);
      HILO.push({de:"usuario", texto});
      guardaHilo(HILO);
      const esperando = turno("el", "Pensando…", "el espera");
      const llama = cuerpo => fetch("/api/pregunta", {
        method:"POST", credentials:"same-origin",
        headers:{"content-type":"application/json"}, body: JSON.stringify(cuerpo),
      });
      try{
        let r = await llama({pregunta: texto, pagina,
                             historial: HILO.slice(0,-1).map(t => ({de:t.de, texto:t.texto}))});
        let d = {}; try{ d = await r.json(); }catch(e){}
        /* Por pasos: mientras el servidor diga «sigue», se le vuelve a llamar. */
        for(let i = 0; r.ok && d.sigue && i < 12; i++){
          esperando.textContent = d.estado || "Pensando…";
          r = await llama({sigue: d.sigue});
          d = {}; try{ d = await r.json(); }catch(e){}
        }
        esperando.remove();
        if(!r.ok){
          /* El motivo importa: no es lo mismo haber agotado el limite del dia
             que que el asistente este apagado para todo el mundo. */
          turno("el", d.error || (r.status === 503 || r.status === 504
            ? "El asistente ha tardado demasiado. Prueba con una pregunta más concreta."
            : "El asistente no está disponible ahora mismo."), "mal");
          HILO.pop(); guardaHilo(HILO);
          return;
        }
        const t = turno("el", d.respuesta || "", null, texto);
        if(d.memoria_cambiada) t.insertAdjacentHTML("beforeend", `<span class="apuntado">Apuntado en tu memoria · pulsa «Memoria» para verla</span>`);
        HILO.push({de:"asistente", texto: d.respuesta || "", pregunta: texto});
        guardaHilo(HILO);
        if(d.quedan_hoy !== null && d.quedan_hoy !== undefined)
          $("#chatQuedan").textContent = `${d.quedan_hoy} preguntas hoy`;
      }catch(e){
        esperando.remove();
        turno("el", "No hay conexión con el servidor.", "mal");
        HILO.pop(); guardaHilo(HILO);
      }finally{
        enVuelo = false;
        $("#chatEnviar").disabled = false;
        $("#chatTexto").focus();
      }
    }

    /* Su memoria (docs/75): un Markdown por usuario que escribe Vendi cuando
       le dicen «recuerda que…». Aqui solo se ve, se baja o se vacia. */
    async function verMemoria(){
      const caja = turno("el", "Mirando tu memoria…", "el espera");
      const pide = accion => fetch("/api/pregunta", {method:"POST", credentials:"same-origin",
        headers:{"content-type":"application/json"}, body: JSON.stringify({memoria: accion})})
        .then(r => r.ok ? r.json() : Promise.reject(r));
      const pinta = md => {
        caja.className = "turno el memoria";
        caja.innerHTML = `<span class="quien">Lo que recuerdo de ti</span>` + (md
          ? formatea(md) + `<div class="acciones"><button type="button" data-m="bajar">Bajar .md</button><button type="button" data-m="borrar">Olvidarlo todo</button></div>`
          : `<p>Todavía no he apuntado nada. Dime «recuerda que…» y lo apunto aquí.</p>`);
        const b = caja.querySelector('[data-m="bajar"]');
        if(b) b.addEventListener("click", ()=>{
          const a = document.createElement("a");
          a.href = URL.createObjectURL(new Blob([md + "\n"], {type: "text/markdown;charset=utf-8"}));
          a.download = "vendi_memoria.md";
          document.body.appendChild(a); a.click();
          setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); }, 1000);
        });
        const o = caja.querySelector('[data-m="borrar"]');
        /* Dos pulsaciones: borrar no tiene vuelta atras. */
        if(o) o.addEventListener("click", ()=>{
          if(!o.dataset.seguro){ o.dataset.seguro = "1"; o.textContent = "¿Seguro? Pulsa otra vez"; return; }
          pide("borrar").then(x => pinta(x.memoria || "")).catch(()=>{});
        });
      };
      try{ pinta((await pide("ver")).memoria || ""); }
      catch(e){ caja.className = "turno mal"; caja.textContent = "No he podido leer tu memoria ahora."; }
    }
    $("#chatMemoria").addEventListener("click", verMemoria);

    /* La conversacion de la pagina anterior, tal cual se dejo. */
    HILO.forEach(t => t.de === "usuario" ? turno("yo", t.texto) : turno("el", t.texto, null, t.pregunta));
    /* Al salir de la sesion no se queda nada: otro usuario en esta pestana
       no veria lo que se pregunto. */
    const salir = document.querySelector("#bSalir");
    if(salir) salir.addEventListener("click", ()=>{ try{ sessionStorage.removeItem(GUARDA); }catch(e){} }, true);

    if(boton) boton.addEventListener("click", ()=>abre(true));
    $("#bVendi").addEventListener("click", ()=>abre(true));
    $("#bVendi").addEventListener("mouseenter", ()=>saluda($("#bVendi")));
    $("#chatCerrar").addEventListener("click", ()=>abre(false));
    $("#fondo").addEventListener("click", ()=>abre(false));
    addEventListener("keydown", e=>{ if(e.key==="Escape" && $("#chat").classList.contains("vis")) abre(false); });
    $("#chatForm").addEventListener("submit", e=>{
      e.preventDefault();
      const t = $("#chatTexto").value.trim();
      $("#chatTexto").value = ""; $("#chatTexto").style.height = "";
      pregunta(t);
    });
    $("#chatTexto").addEventListener("input", e=>{
      e.target.style.height = "auto";
      e.target.style.height = Math.min(140, e.target.scrollHeight) + "px";
    });
    $("#chatTexto").addEventListener("keydown", e=>{
      /* Enter envia; Mayus+Enter hace parrafo. Es lo que espera quien escribe rapido. */
      if(e.key==="Enter" && !e.shiftKey){ e.preventDefault(); $("#chatForm").requestSubmit(); }
    });

    /* Al entrar, Vendi saluda y dice hola unos segundos. Si la pagina esta con
       su bienvenida animada, espera a que acabe: debajo no lo veria nadie. */
    function hola(){
      setTimeout(()=>{
        saluda($("#bVendi"));
        $("#bocadillo").classList.add("vis");
        setTimeout(()=>$("#bocadillo").classList.remove("vis"), 4500);
      }, 700);
    }
    const raiz = document.documentElement;
    if(raiz.classList.contains("bienvenida")){
      const ob = new MutationObserver(()=>{
        if(!raiz.classList.contains("bienvenida")){ ob.disconnect(); hola(); }
      });
      ob.observe(raiz, {attributes:true, attributeFilter:["class"]});
    }else hola();

    return {abre};
  }

  /* Las secciones (rutas, incidencias…) no montan nada a mano: cargan este
     fichero con data-pagina y Vendi sale solo si la sesion tiene el
     asistente (docs/71). El panel y el informe general lo montan ellos, con
     su boton «Preguntar» y sus sugerencias. */
  const SECCION = {
    rutas: ["las rutas", ["¿Qué delegación cumplió peor las rutas ayer?", "¿Qué máquinas llevan más días sin reponer?"]],
    incidencias: ["las incidencias", ["¿Cuántas averías se cerraron en menos de 24 h esta semana?", "¿Qué área tiene más incidencias abiertas?"]],
    devoluciones: ["las devoluciones", ["¿Cuánto se ha devuelto este mes y por qué motivo?", "¿Qué centros acumulan más devoluciones?"]],
    furgonetas: ["las furgonetas", ["¿Qué furgonetas no tuvieron visitas ayer?", "¿Cuántos km se hicieron ayer por área?"]],
    almacenes: ["los almacenes", ["¿Qué almacenes tienen más artículos bajo mínimo?", "¿Cuándo fue el último pedido de cada almacén?"]],
    telemetria: ["la telemetría", ["¿Cuántas máquinas tienen telemetría por sistema?", "¿Dónde hay más diferencias con VenCloud?"]],
    tarifas: ["las tarifas", ["¿Qué centros cobran precios distintos a su tarifa?", "¿Cuántos productos venden sin tarifa?"]],
    revision: ["la revisión de clientes", ["¿Cuántas máquinas no tienen planograma?", "¿Qué delegación tiene más precios distintos?"]],
    utilizo: ["el uso de VenCloud", ["¿Quién usó más VenCloud este mes?", "¿Quién lleva más días sin entrar?"]],
    preferidos: ["tus preferidos", ["Resúmeme mis preferidos de ayer."]],
  };
  const yo = document.currentScript && document.currentScript.dataset.pagina;
  if(yo){
    const sola = async () => {
      let d = null;
      try{ const r = await fetch("/api/yo", {credentials:"same-origin"}); if(r.ok) d = await r.json(); }catch(e){}
      if(!d || !d.asistente || !d.asistente.habilitado) return;
      const [de, sug] = SECCION[yo] || ["esta página", []];
      monta({pagina: yo, hola: `¡Hola! Pregúntame por ${de} o por cualquier sección que veas.`, sugerencias: () => sug});
    };
    if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", sola); else sola();
  }

  window.Asistente = {monta, vendi, formatea};
})();
