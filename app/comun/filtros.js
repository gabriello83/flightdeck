/* ===================================================================
   Los filtros con seleccion multiple y buscador (David, 22-oct-2026, docs/72).

   «En todos los filtros pondria que fuera multiseleccion y que permita
   buscar: comenzar a escribir y que encuentre todo lo que contenga lo que
   escribo». Un boton con lo elegido; al pulsarlo, un buscador y la lista con
   casillas. El buscador encuentra lo que CONTIENE lo escrito, sin mirar
   mayusculas ni acentos: «leg» da «Madrid - Leganes».

   Nada vacio es «todos»: sin marcar ninguno no se filtra. Se usa asi:

     const f = Filtros.multi(contenedor, {
       etiqueta: "Cliente", todos: "Todos",
       opciones: [{v: "AIRBUS", t: "AIRBUS"}, ...],   // t es lo que se lee
       elegidos: ["AIRBUS"],
       alCambiar: lista => {...}});
     f.opciones(nuevas)   // otras opciones (encadenados); lo elegido que ya no
                          // esta se quita, y si cambia se avisa con alCambiar
     f.valor()            // lo elegido, en el orden de las opciones
     f.pon(lista)         // marca esos, sin avisar

   Lo pinta con los colores de la pagina (--tarjeta, --borde-fuerte, --tinta,
   --tinta-2, --s1, --fondo), asi que vale en claro y en oscuro.
   =================================================================== */
(function(){
  "use strict";
  // Con miles de centros, la lista ensena estos y pide afinar el buscador.
  const MAX_LISTA = 300;
  const llano = s => String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  const num = n => new Intl.NumberFormat("es-ES").format(n);
  let serie = 0;

  const estilo = document.createElement("style");
  estilo.textContent = `
.fm{position:relative;display:inline-flex;align-items:center;gap:8px;font-size:13px;color:var(--tinta-2)}
.fm > button.fm-b{font:inherit;font-size:14px;color:var(--tinta);background:var(--tarjeta);
  border:1px solid var(--borde-fuerte);border-radius:8px;padding:5px 10px;cursor:pointer;
  display:inline-flex;align-items:center;gap:6px;max-width:260px}
.fm > button.fm-b:hover{border-color:var(--tinta-3)}
.fm > button.fm-b.con{border-color:var(--s1);box-shadow:inset 0 0 0 1px var(--s1)}
.fm > button.fm-b:focus-visible{outline:2px solid var(--s1);outline-offset:1px}
.fm-b .fm-t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fm-b svg{width:12px;height:12px;flex:none;stroke:currentColor;fill:none;stroke-width:2}
.fm-p{position:absolute;z-index:30;top:calc(100% + 6px);left:0;width:320px;max-width:calc(100vw - 32px);
  background:var(--tarjeta);border:1px solid var(--borde-fuerte);border-radius:12px;
  box-shadow:0 10px 30px rgba(0,0,0,.18);padding:10px;color:var(--tinta)}
.fm-p input[type=search]{width:100%;font:inherit;font-size:14px;color:var(--tinta);background:var(--fondo);
  border:1px solid var(--borde-fuerte);border-radius:8px;padding:6px 9px}
.fm-p input[type=search]:focus-visible{outline:2px solid var(--s1);outline-offset:0}
.fm-acc{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0 6px;font-size:12.5px}
.fm-acc button{font:inherit;font-size:12.5px;border:1px solid var(--borde-fuerte);background:var(--tarjeta);
  color:var(--tinta);border-radius:999px;padding:2px 10px;cursor:pointer}
.fm-acc button:focus-visible{outline:2px solid var(--s1);outline-offset:1px}
.fm-acc span{color:var(--tinta-2);margin-left:auto;align-self:center}
.fm-l{max-height:290px;overflow:auto;margin:0 -4px;padding:0 4px}
.fm-l label{display:flex;gap:8px;align-items:flex-start;padding:5px 6px;border-radius:7px;cursor:pointer;
  font-size:13.5px;line-height:1.3;color:var(--tinta)}
.fm-l label:hover{background:var(--fondo)}
.fm-l input{margin:2px 0 0;accent-color:var(--s1);flex:none}
.fm-l small{display:block;color:var(--tinta-2);font-size:12px}
.fm-l mark{background:none;color:inherit;font-weight:700}
.fm-l .fm-nada{color:var(--tinta-2);font-size:13px;padding:6px}
@media (max-width:560px){ .fm-p{position:fixed;left:16px;right:16px;top:auto;width:auto;max-width:none} }`;
  (document.head || document.documentElement).appendChild(estilo);

  // Lo encontrado, en negrita: el trozo del texto que casa con lo escrito.
  function resalta(texto, q){
    if(!q) return esc(texto);
    const i = llano(texto).indexOf(q);
    // normalize puede cambiar la longitud con letras raras: sin resaltar, mejor.
    if(i < 0 || llano(texto).length !== String(texto).length) return esc(texto);
    return esc(texto.slice(0, i)) + "<mark>" + esc(texto.slice(i, i + q.length)) + "</mark>" + esc(texto.slice(i + q.length));
  }

  function multi(cont, o){
    const id = "fm" + (++serie);
    let opciones = [], elegidos = new Set(o.elegidos || []), q = "";
    const todos = o.todos || "Todos";
    cont.classList.add("fm");
    cont.innerHTML = `<span>${esc(o.etiqueta)}</span>`
      + `<button type="button" class="fm-b" aria-haspopup="dialog" aria-expanded="false" aria-controls="${id}">`
      + `<span class="fm-t"></span><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 4.5l3.5 3.5 3.5-3.5"/></svg></button>`
      + `<div class="fm-p" id="${id}" role="dialog" aria-label="${esc(o.etiqueta)}" hidden>`
      + `<input type="search" placeholder="Buscar ${esc(String(o.etiqueta).toLowerCase())}…" aria-label="Buscar ${esc(String(o.etiqueta).toLowerCase())}" autocomplete="off">`
      + `<div class="fm-acc"><button type="button" data-a="todos">Marcar los que salen</button>`
      + `<button type="button" data-a="nada">Quitar todos</button><span></span></div>`
      + `<div class="fm-l"></div></div>`;
    const boton = cont.querySelector(".fm-b"), panel = cont.querySelector(".fm-p");
    const buscador = panel.querySelector("input"), lista = panel.querySelector(".fm-l");
    const cuenta = panel.querySelector(".fm-acc span");

    const visibles = () => q ? opciones.filter(x => x._q.includes(q)) : opciones;
    function pintaBoton(){
      const v = valor();
      boton.querySelector(".fm-t").textContent = !v.length ? todos
        : v.length === 1 ? (opciones.find(x => x.v === v[0]) || {t: v[0]}).t
        : `${num(v.length)} elegidos`;
      boton.classList.toggle("con", v.length > 0);
      boton.setAttribute("aria-label", `${o.etiqueta}: ${v.length ? num(v.length) + " elegidos" : todos}. Cambiar.`);
    }
    function pintaLista(){
      const vis = visibles();
      const ver = vis.slice(0, MAX_LISTA);
      lista.innerHTML = ver.length ? ver.map(x =>
        `<label><input type="checkbox" value="${esc(x.v)}"${elegidos.has(x.v) ? " checked" : ""}>`
        + `<span>${resalta(x.t, q)}${x.sub ? `<small>${resalta(x.sub, q)}</small>` : ""}</span></label>`).join("")
        + (vis.length > ver.length ? `<div class="fm-nada">y ${num(vis.length - ver.length)} más: escribe para afinar</div>` : "")
        : `<div class="fm-nada">Nada contiene «${esc(buscador.value)}».</div>`;
      cuenta.textContent = elegidos.size ? `${num(elegidos.size)} de ${num(opciones.length)}` : `${num(vis.length)} de ${num(opciones.length)}`;
    }
    function avisa(){ pintaBoton(); if(o.alCambiar) o.alCambiar(valor()); }
    function abre(){
      panel.hidden = false; boton.setAttribute("aria-expanded", "true");
      buscador.value = ""; q = ""; pintaLista(); buscador.focus();
    }
    function cierra(volver){
      if(panel.hidden) return;
      panel.hidden = true; boton.setAttribute("aria-expanded", "false");
      if(volver) boton.focus();
    }
    boton.addEventListener("click", () => panel.hidden ? abre() : cierra(true));
    buscador.addEventListener("input", () => { q = llano(buscador.value.trim()); pintaLista(); });
    // Enter con una sola que casa la marca: escribir y pulsar Enter basta.
    buscador.addEventListener("keydown", e => {
      if(e.key !== "Enter") return;
      e.preventDefault();
      const vis = visibles();
      if(vis.length === 1){ elegidos.has(vis[0].v) ? elegidos.delete(vis[0].v) : elegidos.add(vis[0].v); pintaLista(); avisa(); }
    });
    lista.addEventListener("change", e => {
      const c = e.target;
      if(!c || c.type !== "checkbox") return;
      c.checked ? elegidos.add(c.value) : elegidos.delete(c.value);
      pintaLista(); avisa();
    });
    panel.querySelector(".fm-acc").addEventListener("click", e => {
      const b = e.target.closest("button"); if(!b) return;
      if(b.dataset.a === "todos") visibles().forEach(x => elegidos.add(x.v));
      else elegidos.clear();
      pintaLista(); avisa();
    });
    document.addEventListener("click", e => { if(!cont.contains(e.target)) cierra(false); });
    cont.addEventListener("keydown", e => { if(e.key === "Escape" && !panel.hidden){ e.stopPropagation(); cierra(true); } });

    function valor(){ return opciones.filter(x => elegidos.has(x.v)).map(x => x.v); }
    function ponOpciones(nuevas){
      opciones = (nuevas || []).map(x => typeof x === "string" ? {v: x, t: x} : x)
        .map(x => Object.assign({}, x, {_q: llano(x.t + " " + (x.sub || ""))}));
      const hay = new Set(opciones.map(x => x.v));
      const antes = elegidos.size;
      elegidos = new Set([...elegidos].filter(v => hay.has(v)));
      if(!panel.hidden) pintaLista();
      if(elegidos.size !== antes) avisa(); else pintaBoton();
    }
    ponOpciones(o.opciones);
    return {
      valor, opciones: ponOpciones,
      pon(lista){ elegidos = new Set((lista || []).filter(v => opciones.some(x => x.v === v))); pintaBoton(); if(!panel.hidden) pintaLista(); },
      cuantas: () => opciones.length,
    };
  }

  window.Filtros = {multi, llano};
})();
