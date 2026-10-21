/* ===================================================================
   Las areas de las secciones (Gabriele, 21-oct-2026, docs/69).

   Cada seccion empieza como la portada de Rutas: un cuadrado por area, con
   su nombre en el centro y su porcentaje en el color del semaforo (en el
   color del texto si va bien, en amarillo si hay que vigilar, en rojo si
   esta por debajo). Nada mas: el detalle esta dentro del area.

   Las areas son las cinco de los Power BI de Gabriele, por el principio del
   nombre de la delegacion: la misma regla que `zona_de` en
   infra/operativo.py (test_operativo.py comprueba que no se separen). Lo que
   no cae en ninguna es «Otra zona» y no lleva cuadrado.
   =================================================================== */
(function(){
  "use strict";
  const ZONAS = [["MADRID", "Centro"], ["ANDALUCIA", "Sur"], ["CATALUNA", "Cataluña"],
                 ["LEVANTE", "Levante"], ["NORTE", "Norte"]];
  const ORDEN = ["Centro", "Sur", "Cataluña", "Levante", "Norte"];
  const OTRA = "Otra zona";
  const UMBRAL = {verde: 95, amarillo: 75};

  const llano = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
  function zona(delegacion){
    const d = llano(delegacion);
    const x = ZONAS.find(([p]) => d.startsWith(p));
    return x ? x[1] : OTRA;
  }
  function color(p){
    if(p == null) return null;
    return p > UMBRAL.verde ? "verde" : p >= UMBRAL.amarillo ? "amarillo" : "rojo";
  }
  const orden = (a, b) => (ORDEN.indexOf(a) + 1 || 99) - (ORDEN.indexOf(b) + 1 || 99) || a.localeCompare(b, "es");
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const fpct = n => new Intl.NumberFormat("es-ES", {maximumFractionDigits: 1}).format(n) + " %";

  const estilo = document.createElement("style");
  estilo.textContent = `
.ar-areas{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-top:14px}
button.ar-area{all:unset;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;cursor:pointer;background:var(--tarjeta);color:var(--tinta);border:1px solid var(--borde);border-radius:12px;
  padding:18px 14px;min-height:118px;box-shadow:var(--sombra,none);transition:border-color .15s ease,transform .15s ease}
button.ar-area:hover{border-color:var(--tinta-3);transform:translateY(-2px)}
button.ar-area:focus-visible{outline:2px solid var(--s1);outline-offset:1px}
.ar-area .ar-nom{font-size:15px;font-weight:650}
.ar-area .ar-pc{font-size:36px;font-weight:700;letter-spacing:-.02em;font-variant-numeric:tabular-nums;line-height:1.2;margin-top:4px}
.ar-area .ar-pc.amarillo{color:#d49b00} .ar-area .ar-pc.rojo{color:#c62828}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]) .ar-area .ar-pc.amarillo{color:#f2c94c}
  :root:not([data-theme="light"]) .ar-area .ar-pc.rojo{color:#f87171}
}
:root[data-theme="dark"] .ar-area .ar-pc.amarillo{color:#f2c94c}
:root[data-theme="dark"] .ar-area .ar-pc.rojo{color:#f87171}
.ar-area .ar-pc.sin{color:var(--tinta-3);font-size:22px}
.ar-volver{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:14px 0 4px}
.ar-volver h2{font-size:18px;margin:0}
@media (prefers-reduced-motion:reduce){ button.ar-area{transition:none} }`;
  (document.head || document.documentElement).appendChild(estilo);

  /* La portada. `areas` es [{area, pct, titulo}] (pct null = sin dato) y
     `abre(area)` se llama al pulsar una. */
  function portada(cont, areas, abre){
    const lista = areas.filter(a => a.area !== OTRA).sort((a, b) => orden(a.area, b.area));
    cont.innerHTML = `<div class="ar-areas">` + lista.map(a => {
      const c = color(a.pct);
      return `<button class="ar-area" type="button" data-area="${esc(a.area)}"${a.titulo ? ` title="${esc(a.titulo)}"` : ""}`
        + ` aria-label="${esc(a.area)}: ${a.pct == null ? "sin dato" : fpct(a.pct)}">`
        + `<span class="ar-nom">${esc(a.area)}</span>`
        + `<span class="ar-pc ${a.pct == null ? "sin" : c}">${a.pct == null ? "Sin dato" : fpct(a.pct)}</span></button>`;
    }).join("") + `</div>`;
    cont.querySelectorAll("button.ar-area").forEach(b => b.addEventListener("click", () => abre(b.dataset.area)));
    return lista.length;
  }

  /* Las areas distintas de una lista de delegaciones (sin «Otra zona»). */
  function de(delegaciones){
    return [...new Set(delegaciones.map(zona))].filter(a => a !== OTRA).sort(orden);
  }

  window.Areas = {ZONAS, ORDEN, OTRA, zona, color, de, portada,
    pct: (a, b) => b ? Math.round(1000*a/b)/10 : null};
})();
