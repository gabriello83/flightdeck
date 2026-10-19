/* ===================================================================
   Preferidos · digivend.es  (docs/62)

   La estrella de cada tabla y gráfico de las páginas de los cuadrados. Se
   pulsa y se pone amarilla, como los favoritos del navegador; la página
   /preferidos/ junta todas las que el usuario marcó, en el orden y el tamaño
   que él elija. Lo guarda el servidor (/api/preferidos), no el navegador: así
   las encuentra igual desde otro ordenador.

   Cada página dice qué es cada cosa con atributos, y llama a monta() cuando
   ya tiene sus datos:

     data-estrella="maquinas"   pon aquí la estrella de la tabla «maquinas»
     data-estrella="*"          la de la tabla que se ve ahora (pestañas):
                                la dice opciones.actual()
     data-tabla="maquinas"      la caja de esa tabla, para la vista suelta

     Preferidos.monta("rutas", {
       actual: () => "vehiculos",         // con pestañas, cuál se ve
       abre: t => { ... },                // en la vista suelta, enseña t
       ocultar: ["#kpis"],                // en la vista suelta, lo que sobra
     });

   La VISTA SUELTA es la página con ?solo=<tabla>: sin cabecera, sin pie, sin
   las otras tablas; sólo sus filtros y esa tabla. Es lo que /preferidos/
   mete en cada recuadro, así cada tabla se dibuja con el código de su propia
   página y no con una copia que se quedaría vieja.

   Las estrellas se vuelven a poner solas cuando la página repinta una parte
   (un MutationObserver): las páginas no tienen que acordarse.
   =================================================================== */
(function(){
  "use strict";
  const SOLO = new URLSearchParams(location.search).get("solo");
  const SVG = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">'
    + '<path d="M12 2.8l2.83 5.74 6.33.92-4.58 4.46 1.08 6.3L12 17.25l-5.66 2.97 1.08-6.3L2.84 9.46l6.33-.92z"/></svg>';
  let CUADRADO = null, OPC = {}, LISTA = null, NOMBRES = {}, guardando = Promise.resolve();

  /* El estilo de la estrella y de la vista suelta, en la propia página: un
     solo origen, nada de fuera. */
  const css = document.createElement("style");
  css.textContent = `
    .estrella{all:unset;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;
      width:28px;height:28px;border-radius:7px;cursor:pointer;flex-shrink:0;vertical-align:-6px;margin:-4px 0 -4px 6px;
      color:var(--tinta-3,#8a8a85)}
    .estrella svg{fill:none;stroke:currentColor;stroke-width:1.7;stroke-linejoin:round}
    .estrella:hover{background:var(--fondo,#f4f4f2);color:var(--tinta-2,#55554f)}
    .estrella:focus-visible{outline:2px solid var(--s1,#2a78d6);outline-offset:1px}
    .estrella[aria-pressed="true"]{color:#e3a008}
    .estrella[aria-pressed="true"] svg{fill:#f5b800;stroke:#e3a008}
    html.solo header,html.solo footer,html.solo .estrella,html.solo #aviso:empty{display:none!important}
    html.solo body{background:var(--tarjeta,#fff)}
    html.solo .env{max-width:none!important;padding:4px 12px 12px!important}
    html.solo .barra{margin-top:4px}
    html.solo section.caja:first-of-type,html.solo .dos>section.caja{margin-top:8px}
  `;
  document.head.appendChild(css);
  if(SOLO) document.documentElement.classList.add("solo");

  const tablaDe = el => el.dataset.estrella === "*" ? (OPC.actual ? OPC.actual() : null) : el.dataset.estrella;
  const marcada = t => !!(LISTA && LISTA.some(x => x.c === CUADRADO && x.t === t));
  const nombre = t => ((NOMBRES[CUADRADO] || {}).tablas || {})[t] || t;

  function pinta(){
    if(SOLO || !LISTA) return;
    document.querySelectorAll("[data-estrella]").forEach(el=>{
      const t = tablaDe(el);
      /* Junto al título, como la de los favoritos junto a la dirección. Si la
         página reescribe el título, el observador la vuelve a poner. */
      const dentro = el.querySelector("h2, b") || el;
      let b = el.querySelector(".estrella");
      if(b && b.parentNode !== dentro){ b.remove(); b = null; }
      if(!t || !((NOMBRES[CUADRADO] || {}).tablas || {})[t]){ if(b) b.remove(); return; }
      if(!b){
        b = document.createElement("button");
        b.type = "button"; b.className = "estrella"; b.innerHTML = SVG;
        b.addEventListener("click", e=>{ e.preventDefault(); e.stopPropagation(); cambia(tablaDe(el)); });
        dentro.appendChild(b);
      }
      const si = marcada(t);
      if(b.getAttribute("aria-pressed") !== String(si)) b.setAttribute("aria-pressed", String(si));
      const txt = (si ? "Quitar de preferidos: " : "Añadir a preferidos: ") + nombre(t);
      if(b.title !== txt){ b.title = txt; b.setAttribute("aria-label", txt); }
    });
  }

  function cambia(t){
    if(!t) return;
    LISTA = marcada(t) ? LISTA.filter(x => !(x.c === CUADRADO && x.t === t))
                       : LISTA.concat([{c: CUADRADO, t, ancho: "media", alto: "medio"}]);
    pinta();
    guarda(LISTA);
  }

  /* Uno detrás de otro: dos estrellas seguidas no se pisan en el servidor. */
  function guarda(lista){
    guardando = guardando.then(async ()=>{
      try{
        const r = await fetch("/api/preferidos", {method:"PUT", credentials:"same-origin",
          headers:{"content-type":"application/json"}, body: JSON.stringify({preferidos: lista})});
        if(!r.ok) throw new Error();
      }catch(e){
        avisa("No se ha podido guardar el preferido. Vuelve a pulsar la estrella.");
      }
    });
    return guardando;
  }
  function avisa(t){
    const a = document.getElementById("aviso");
    if(a){ a.textContent = t; a.hidden = false; }
  }

  async function lee(){
    try{
      const r = await fetch("/api/preferidos", {credentials:"same-origin"});
      if(!r.ok) return null;
      return await r.json();
    }catch(e){ return null; }
  }

  async function monta(cuadrado, opciones){
    CUADRADO = cuadrado; OPC = opciones || {};
    if(SOLO){
      /* Lo que sobra en la vista suelta: las demás tablas y lo que diga la página. */
      const st = document.createElement("style");
      st.textContent = [`[data-tabla]:not([data-tabla="${CSS.escape(SOLO)}"])`, ...(OPC.ocultar || [])]
        .map(s => `html.solo ${s}{display:none!important}`).join("\n");
      document.head.appendChild(st);
      if(OPC.abre) OPC.abre(SOLO);
      return;
    }
    const d = await lee();
    if(!d) return;
    LISTA = d.preferidos || []; NOMBRES = d.nombres || {};
    pinta();
    let espera = null;
    new MutationObserver(()=>{ clearTimeout(espera); espera = setTimeout(pinta, 30); })
      .observe(document.body, {childList:true, subtree:true});
  }

  window.Preferidos = {monta, repinta: pinta, solo: SOLO, guarda, lee};
})();
