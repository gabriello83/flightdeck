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
.fm-cuatro{display:contents}
/* Dentro de la barra de una seccion, sus reglas de label e input no entran aqui. */
.fm .fm-p input[type=search]{min-width:0;max-width:none;width:100%;box-sizing:border-box}
.fm .fm-l input[type=checkbox]{width:auto;min-width:0;padding:0;border:0;background:none;font-size:inherit}
.fm .fm-l label{display:flex;font-size:13.5px;color:var(--tinta);min-width:0}
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

  /* ===================================================================
     Los cuatro de cada seccion: Area, Delegacion, Cliente y Centro, encadenados
     como en el informe general (docs/72, docs/73). El area deja sus
     delegaciones; las delegaciones, sus clientes; los clientes, sus centros.
     Cada uno sale solo si hay mas de una cosa que elegir.

       const F = Filtros.cuatro(contenedor, {
         zonas:   {delegacion: area, ...},              // las que salen
         centros: {numero: {n: nombre, c: cliente, d: delegacion}, ...},
         campos:  ["area", "delegacion", "cliente", "centro"],  // los que se montan
         alCambiar: () => {...}});
       F.sel                 // {areas, delegs, clientes, centros}
       F.pasaDeleg(dl)       // entra por area y delegacion
       F.pasaCentro(n, dl)   // entra por los cuatro (n es el numero de centro)
       F.porCentro()         // hay cliente o centro elegido
       F.pon("delegs", [d])  // elige desde la pagina (pulsar una barra) y avisa
       F.una("delegs")       // la unica elegida, o ""
       F.limpia()

     Lo elegido va en la direccion, repetido (?area=Sur&delegacion=…&cliente=…
     &centro=500088); los demas parametros de la pagina se quedan como estan.
     =================================================================== */
  const CAMPOS = {area: ["areas", "Área", "Todas"], delegacion: ["delegs", "Delegación", "Todas"],
                  cliente: ["clientes", "Cliente", "Todos"], centro: ["centros", "Centro", "Todos"]};
  const ORDEN_CAMPOS = ["area", "delegacion", "cliente", "centro"];

  function cuatro(cont, o){
    const zonas = Object.assign({}, o.zonas || {});
    const fichas = Object.assign({}, o.centros || {});
    // Una delegacion de una ficha que la seccion no traia tambien tiene su area.
    Object.values(fichas).forEach(f => { if(f.d && !(f.d in zonas) && o.zonaDe) zonas[f.d] = o.zonaDe(f.d); });
    const campos = ORDEN_CAMPOS.filter(c => (o.campos || ORDEN_CAMPOS).includes(c));
    const es = (a, b) => a.localeCompare(b, "es");
    const unicos = l => [...new Set(l)];
    const sel = {areas: [], delegs: [], clientes: [], centros: []};
    if(o.url !== false){
      const q = new URLSearchParams(location.search);
      sel.areas = q.getAll("area"); sel.delegs = q.getAll("delegacion");
      sel.clientes = q.getAll("cliente"); sel.centros = q.getAll("centro");
    }
    const delegs = Object.keys(zonas).sort(es);
    const areas = unicos(delegs.map(d => zonas[d]).filter(Boolean)).sort(o.ordenAreas || es);
    const centros = Object.keys(fichas);
    // Las delegaciones que dejan area y delegacion (null: todas).
    function delegsElegidas(){
      if(!sel.areas.length && !sel.delegs.length) return null;
      return delegs.filter(d => (!sel.areas.length || sel.areas.includes(zonas[d]))
                             && (!sel.delegs.length || sel.delegs.includes(d)));
    }
    const dlSet = () => { const dl = delegsElegidas(); return dl && new Set(dl); };
    const opc = {
      area: () => areas,
      delegacion: () => delegs.filter(d => !sel.areas.length || sel.areas.includes(zonas[d])),
      cliente: () => { const dl = dlSet();
        return unicos(centros.filter(c => !dl || dl.has(fichas[c].d)).map(c => fichas[c].c).filter(Boolean)).sort(es); },
      centro: () => { const dl = dlSet();
        return centros.filter(c => (!dl || dl.has(fichas[c].d)) && (!sel.clientes.length || sel.clientes.includes(fichas[c].c)))
          .map(c => ({v: c, t: fichas[c].n || c,
            sub: [fichas[c].n && fichas[c].n !== c ? `nº ${c}` : "", fichas[c].c, fichas[c].d].filter(Boolean).join(" · ")}))
          .sort((a, b) => es(a.t, b.t)); },
    };
    const hay = {area: areas.length, delegacion: delegs.length,
                 cliente: unicos(centros.map(c => fichas[c].c).filter(Boolean)).length, centro: centros.length};
    cont.classList.add("fm-cuatro");
    cont.innerHTML = campos.map(c => `<span data-f="${c}"></span>`).join("");
    const F = {};
    let enCascada = 0;
    function guarda(){
      if(o.url === false) return;
      const q = new URLSearchParams(location.search);
      ["area", "delegacion", "cliente", "centro"].forEach(k => q.delete(k));
      sel.areas.forEach(x => q.append("area", x));
      sel.delegs.forEach(x => q.append("delegacion", x));
      sel.clientes.forEach(x => q.append("cliente", x));
      sel.centros.forEach(x => q.append("centro", x));
      const s = q.toString();
      try{ history.replaceState(null, "", location.pathname + (s ? "?" + s : "") + location.hash); }catch(e){}
    }
    const cascada = i => {
      enCascada++;
      // Mientras se montan, los de debajo todavia no existen: ya nacen con lo de arriba.
      for(let j = i + 1; j < campos.length; j++) if(F[campos[j]]) F[campos[j]].opciones(opc[campos[j]]());
      enCascada--;
      if(!enCascada){ guarda(); if(o.alCambiar) o.alCambiar(sel); }
    };
    // Lo que traiga la direccion y ya no exista se quita sin avisar todavia.
    enCascada++;
    campos.forEach((c, i) => {
      const [k, et, todos] = CAMPOS[c];
      const caja = cont.querySelector(`[data-f="${c}"]`);
      F[c] = multi(caja, {etiqueta: et, todos, opciones: opc[c](), elegidos: sel[k],
        alCambiar: v => { sel[k] = v; cascada(i); }});
      sel[k] = F[c].valor();
      caja.hidden = hay[c] < 2;
    });
    // Un filtro que no se monta no filtra.
    ORDEN_CAMPOS.filter(c => !campos.includes(c)).forEach(c => { sel[CAMPOS[c][0]] = []; });
    enCascada--;
    guarda();

    function pasaDeleg(dl){
      if(sel.areas.length && !sel.areas.includes(zonas[dl] || (o.zonaDe ? o.zonaDe(dl) : ""))) return false;
      return !sel.delegs.length || sel.delegs.includes(dl);
    }
    function pasaCentro(n, dl){
      const f = fichas[n];
      if(!pasaDeleg(dl != null && dl !== "" ? dl : f ? f.d : "")) return false;
      if(sel.centros.length) return sel.centros.includes(String(n));
      if(sel.clientes.length) return !!f && sel.clientes.includes(f.c);
      return true;
    }
    // Elegir desde la pagina: lo de debajo se rehace como si se hubiera marcado a mano.
    function pon(k, lista){
      const c = ORDEN_CAMPOS.find(x => CAMPOS[x][0] === k);
      if(!F[c]) return;
      enCascada++;
      F[c].pon(lista); sel[k] = F[c].valor();
      enCascada--;
      cascada(campos.indexOf(c));
    }
    function limpia(){
      enCascada++;
      campos.forEach(c => { F[c].pon([]); sel[CAMPOS[c][0]] = []; });
      enCascada--;
      cascada(-1);
    }
    return {
      sel, pasaDeleg, pasaCentro, pon, limpia, delegsElegidas,
      porCentro: () => sel.clientes.length > 0 || sel.centros.length > 0,
      alguno: () => campos.some(c => sel[CAMPOS[c][0]].length > 0),
      una: k => sel[k].length === 1 ? sel[k][0] : "",
      ficha: n => fichas[n] || null,
      // Lo elegido en palabras, para un titulo: «Sur · Madrid - Leganes · 2 centros».
      texto(){
        const t = [];
        const de = (l, uno, varios) => l.length === 1 ? uno(l[0]) : l.length ? `${num(l.length)} ${varios}` : "";
        t.push(de(sel.areas, x => x, "áreas"), de(sel.delegs, x => x, "delegaciones"),
               de(sel.clientes, x => x, "clientes"), de(sel.centros, x => (fichas[x] && fichas[x].n) || x, "centros"));
        return t.filter(Boolean).join(" · ");
      },
    };
  }

  /* Las fichas de los centros del perfil (nombre, cliente y delegacion), las
     mismas del informe general: lo que llena las listas de Cliente y Centro.
     Sin ellas (un perfil sin informe general) la seccion se arregla con lo
     suyo. */
  async function fichas(){
    try{
      const r = await fetch("/api/operativo?fichas=1", {credentials: "same-origin"});
      if(!r.ok) return {};
      const d = await r.json();
      return {zonas: d.zonas || {}, centros: d.centros || {}};
    }catch(e){ return {}; }
  }

  /* Un mes del reparto por centro (docs/72), el mismo del informe general:
     {mes, dias: {fecha: {cuadrado: {centro: [...]}}}}, o null si no lo hay.
     Se pide una vez por mes. */
  const MESES = {};
  function mesCentros(mes){
    if(!(mes in MESES))
      MESES[mes] = fetch(`/api/operativo?centros=${encodeURIComponent(mes)}`, {credentials: "same-origin"})
        .then(r => r.ok ? r.json() : null).catch(() => null);
    return MESES[mes];
  }

  window.Filtros = {multi, llano, cuatro, fichas, mesCentros};
})();
