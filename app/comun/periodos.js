/* El selector de tiempo, y la suma de la serie diaria. Lo comparten las tres
   pantallas —consola, panel de cliente y cuadro de mando— para que «este mes»
   signifique lo mismo en las tres y para que el dia que se afine un rango se
   afine en un solo sitio.

   De donde sale el dato: /api/serie da el indice de meses, y /api/serie?mes=
   las filas de un mes. Una fila es un dia y se SUMA; las medianas de un rango
   salen del histograma sumado, con los tramos que manda el propio indice (ver
   infra/serie.py, que hace la misma cuenta en Python). La pagina no sabe de
   que perfil son: la API los saca de la sesion, nunca de la peticion.

   No usa ninguna biblioteca y no habla con nadie que no sea este dominio. */

(function (global) {
  "use strict";

  // ------------------------------------------------------------------ fechas
  function iso(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  function dia(texto) { const [a, m, d] = texto.split("-").map(Number); return new Date(a, m - 1, d); }
  function suma(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }

  // Los mismos rangos que `serie.rango()` en Python, con el mismo nombre.
  // Si se toca uno, se toca el otro: el indice de la serie trae la lista de
  // nombres y aqui estan las fechas.
  const RANGOS = {
    ayer:       { nombre: "Ayer",              calcula: h => [iso(suma(h, -1)), iso(suma(h, -1))] },
    semana:     { nombre: "Esta semana",       calcula: h => [iso(suma(h, -((h.getDay() + 6) % 7))), iso(h)] },
    mes:        { nombre: "Este mes",          calcula: h => [iso(new Date(h.getFullYear(), h.getMonth(), 1)), iso(h)] },
    mes_pasado: { nombre: "Mes pasado",        calcula: h => [iso(new Date(h.getFullYear(), h.getMonth() - 1, 1)),
                                                              iso(new Date(h.getFullYear(), h.getMonth(), 0))] },
    "30dias":   { nombre: "Últimos 30 días",   calcula: h => [iso(suma(h, -29)), iso(h)] },
    anio:       { nombre: "Este año",          calcula: h => [iso(new Date(h.getFullYear(), 0, 1)), iso(h)] },
    todo:       { nombre: "Todo el histórico", calcula: (h, primero) => [primero, iso(h)] }
  };

  // El orden en que se ofrecen. Los dos primeros son los que se miran a diario.
  // No hay «hoy»: la carga trae hasta ayer y hoy siempre saldria vacio. Un
  // indice viejo que aun lo nombre no pinta el boton, porque aqui no existe.
  const ORDEN = ["ayer", "semana", "mes", "mes_pasado", "30dias", "anio", "todo"];

  const PRIMER_DIA = "2025-01-01";

  function rango(nombre, hoy, primerDia) {
    const r = RANGOS[nombre];
    if (!r) throw new Error(`No existe el rango «${nombre}»`);
    return r.calcula(hoy || new Date(), primerDia || PRIMER_DIA);
  }

  function meses(desde, hasta) {
    const out = [];
    let d = dia(desde); d.setDate(1);
    const fin = dia(hasta);
    while (d <= fin) {
      out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
      d = new Date(d.getFullYear(), d.getMonth() + 1, 1);
    }
    return out;
  }

  function etiqueta(desde, hasta) {
    const fmt = f => dia(f).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });
    return desde === hasta ? fmt(desde) : `${fmt(desde)} – ${fmt(hasta)}`;
  }

  // -------------------------------------------------------------- histogramas
  // La media y los totales son exactos porque la fila guarda la suma y el n.
  // La mediana y el p90 de un rango se interpolan dentro del tramo donde caen:
  // son aproximados hasta el ancho de ese tramo, y quien los ensena lo dice.
  function sumaHist(a, b) {
    if (!a) return b ? Object.assign({}, b, { h: (b.h || []).slice() }) : null;
    if (!b) return a;
    const h = (a.h || []).slice();
    (b.h || []).forEach((n, i) => { h[i] = (h[i] || 0) + n; });
    const maxes = [a.max, b.max].filter(x => x !== null && x !== undefined);
    return { n: (a.n || 0) + (b.n || 0), suma: (a.suma || 0) + (b.suma || 0), h,
             max: maxes.length ? Math.max.apply(null, maxes) : null };
  }

  function percentil(bordes, h, n, q, maximo) {
    const objetivo = q * n;
    let acumulado = 0;
    for (let i = 0; i < h.length; i++) {
      if (!h[i]) continue;
      if (acumulado + h[i] >= objetivo) {
        const bajo = i > 0 ? bordes[i - 1] : Math.min(bordes[0], 0);
        let alto = i < bordes.length ? bordes[i] : (maximo !== null && maximo !== undefined ? maximo : bordes[bordes.length - 1]);
        if (alto === null || alto <= bajo) return bajo;
        return bajo + (alto - bajo) * ((objetivo - acumulado) / h[i]);
      }
      acumulado += h[i];
    }
    return null;
  }

  function resumenHist(bordes, d) {
    if (!d || !d.n) return { n: 0 };
    return {
      n: d.n,
      media: d.suma / d.n,
      mediana: percentil(bordes, d.h || [], d.n, 0.5, d.max),
      p90: percentil(bordes, d.h || [], d.n, 0.9, d.max),
      max: d.max,
      aprox: true
    };
  }

  // ------------------------------------------------------------------ sumar
  function sumaFilas(filas, bordes) {
    bordes = bordes || {};
    filas = (filas || []).filter(Boolean).slice().sort((a, b) => a.f.localeCompare(b.f));
    const t = {
      dias: filas.length,
      desde: filas.length ? filas[0].f : null,
      hasta: filas.length ? filas[filas.length - 1].f : null,
      servicio: { visitas: 0, partes: 0, coste_servicio: 0,
                  carga: { valor: 0, unidades: 0, vendibles: 0 },
                  merma: {}, maquinas_dia_max: 0, centros_dia_max: 0 },
      dinero: { periodos: {} },
      sat: { tareas: 0, averias_tecnicas: 0, preventivos: 0, fallos_tecnicos: 0 },
      jornadas: { jornadas: 0, km_total: 0, temperatura_fuera: 0, gps: 0 },
      venta: { unidades: 0, importe: 0, maquinas_dia_max: 0, fuentes: [], imposibles: 0 },
      por_dia: []
    };
    let hmin = null, hcierres = null, hkm = null, htemp = null;
    const fuentes = new Set();

    for (const f of filas) {
      const s = f.servicio || {}, o = t.servicio;
      o.visitas += s.visitas || 0;
      o.partes += s.partes || 0;
      o.coste_servicio += s.coste_servicio || 0;
      o.maquinas_dia_max = Math.max(o.maquinas_dia_max, s.maquinas_dia || 0);
      o.centros_dia_max = Math.max(o.centros_dia_max, s.centros_dia || 0);
      for (const k in (s.carga || {})) o.carga[k] = (o.carga[k] || 0) + s.carga[k];
      for (const motivo in (s.merma || {})) {
        const a = o.merma[motivo] || (o.merma[motivo] = { lineas: 0, unidades: 0, euros: 0 });
        a.lineas += s.merma[motivo].lineas || 0;
        a.unidades += s.merma[motivo].unidades || 0;
        a.euros += s.merma[motivo].euros || 0;
      }
      hmin = sumaHist(hmin, s.min);

      const per = ((f.dinero || {}).periodos) || {};
      for (const p in per) {
        const a = t.dinero.periodos[p] ||
          (t.dinero.periodos[p] = { registros: 0, efectivo: 0, banco: 0, ciego: 0, imposibles: 0 });
        for (const k in a) a[k] += per[p][k] || 0;
      }

      const sat = f.sat || {};
      ["tareas", "averias_tecnicas", "preventivos", "fallos_tecnicos"]
        .forEach(k => { t.sat[k] += sat[k] || 0; });
      hcierres = sumaHist(hcierres, sat.cierres);

      const j = f.jornadas || {};
      t.jornadas.jornadas += j.jornadas || 0;
      t.jornadas.km_total += j.km_total || 0;
      t.jornadas.temperatura_fuera += j.temperatura_fuera || 0;
      t.jornadas.gps += j.gps || 0;
      hkm = sumaHist(hkm, j.km);
      htemp = sumaHist(htemp, j.temperatura);

      const v = f.venta || {};
      t.venta.unidades += v.unidades || 0;
      t.venta.importe += v.importe || 0;
      t.venta.maquinas_dia_max = Math.max(t.venta.maquinas_dia_max, v.maquinas_dia || 0);
      t.venta.imposibles += v.imposibles || 0;
      if (v.fuente) fuentes.add(v.fuente);

      t.por_dia.push({ f: f.f, visitas: s.visitas || 0, importe: v.importe || 0,
                       tareas: sat.tareas || 0, carga: (s.carga || {}).valor || 0 });
    }

    t.servicio.duracion_min = resumenHist(bordes.minutos || [], hmin);
    t.sat.horas_cierre = resumenHist(bordes.horas_cierre || [], hcierres);
    t.jornadas.km = resumenHist(bordes.km || [], hkm);
    t.jornadas.temperatura = resumenHist(bordes.temperatura || [], htemp);
    t.venta.fuentes = [...fuentes].sort();
    t.dinero.lista = Object.keys(t.dinero.periodos).sort()
      .map(p => Object.assign({ periodo: p }, t.dinero.periodos[p]));
    return t;
  }

  // ---------------------------------------------- partido por centro (filtro)
  /* El filtro por delegación, cliente y centro. El CENTRO es el átomo: cada día
     tiene sus cifras partidas por centro (serie/centros-<mes>), y la ficha de
     cada centro —nombre, cliente y, sólo para Serunion, delegación— viene en el
     índice. Filtrar por un cliente es sumar sus centros. La misma cuenta que
     `serie.filas_de_centros` en Python: infra/test_serie.py compara las dos. */
  function sumaProfunda(a, b) {
    if (a === null || a === undefined) return JSON.parse(JSON.stringify(b));
    if (b && typeof b === "object") {
      if ("h" in b && "n" in b) return sumaHist(a, b);
      const out = Object.assign({}, a);
      for (const k in b) out[k] = sumaProfunda(a[k], b[k]);
      return out;
    }
    if (typeof a === "number" && typeof b === "number") {
      const r = a + b;
      return Number.isInteger(r) ? r : Math.round(r * 1000) / 1000;
    }
    return b;
  }

  /* Las filas de cada día sumando sólo los centros de `quiere` (un Set; null =
     todos), con la forma de la fila del día: sumaFilas las junta igual. */
  function filasDeCentros(filasCentros, quiere) {
    const out = [];
    const orden = (filasCentros || []).slice().sort((a, b) => a.f.localeCompare(b.f));
    for (const f of orden) {
      let fila = null;
      for (const clave in (f.centros || {})) {
        if (quiere && !quiere.has(clave)) continue;
        fila = sumaProfunda(fila, f.centros[clave]);
      }
      if (fila) { fila.f = f.f; out.push(fila); }
    }
    return out;
  }

  /* Un renglón por centro para un rango. La misma cuenta que serie.suma_centros. */
  function sumaCentros(filasCentros, quiere) {
    const por = {};
    for (const f of filasCentros || []) {
      for (const clave in (f.centros || {})) {
        if (quiere && !quiere.has(clave)) continue;
        const c = f.centros[clave], s = c.servicio || {}, ve = c.venta || {}, sat = c.sat || {};
        const a = por[clave] || (por[clave] = { visitas: 0, min_n: 0, min_suma: 0,
          maquinas_dia_max: 0, carga_valor: 0, merma_euros: 0, venta_importe: 0, tareas: 0, dias: 0 });
        a.dias += 1;
        a.visitas += s.visitas || 0;
        a.min_n += (s.min || {}).n || 0;
        a.min_suma += (s.min || {}).suma || 0;
        a.maquinas_dia_max = Math.max(a.maquinas_dia_max, s.maquinas_dia || 0);
        a.carga_valor += (s.carga || {}).valor || 0;
        for (const m in (s.merma || {})) a.merma_euros += (s.merma[m] || {}).euros || 0;
        a.venta_importe += ve.importe || 0;
        a.tareas += sat.tareas || 0;
      }
    }
    for (const k in por) {
      const a = por[k];
      a.min_medio = a.min_n ? Math.round(10 * a.min_suma / a.min_n) / 10 : null;
    }
    return por;
  }

  /* Qué centros entran con lo elegido. null = sin filtro (todos). */
  function centrosElegidos(fichas, sel) {
    sel = sel || {};
    if (!sel.delegacion && !sel.cliente && !sel.centro) return null;
    const out = new Set();
    for (const k in (fichas || {})) {
      const f = fichas[k] || {};
      if (sel.delegacion && f.delegacion !== sel.delegacion) continue;
      if (sel.cliente && f.cliente !== sel.cliente) continue;
      if (sel.centro && k !== sel.centro) continue;
      out.add(k);
    }
    return out;
  }

  function etiquetaLugar(fichas, sel) {
    sel = sel || {};
    const partes = [];
    if (sel.delegacion) partes.push("Delegación " + sel.delegacion);
    if (sel.cliente) partes.push(sel.cliente);
    if (sel.centro) partes.push(((fichas || {})[sel.centro] || {}).nombre || sel.centro);
    return partes.join(" · ");
  }

  /* Los desplegables en cascada: Delegación → Cliente → Centro. La delegación
     sólo sale si el índice la ofrece (`filtros`): a un cliente la API ni se la
     manda. Con un solo centro no se pinta nada: no habría nada que elegir. */
  function montaFiltroLugar(contenedor, opciones) {
    const o = opciones || {};
    const fichas = o.fichas || {};
    const filtros = o.filtros || ["cliente", "centro"];
    const claves = Object.keys(fichas);
    contenedor.innerHTML = "";
    const sel = { delegacion: "", cliente: "", centro: "" };
    if (claves.length < 2) {
      contenedor.hidden = true;
      return { estado: () => Object.assign({}, sel), quiere: () => null, etiqueta: () => "" };
    }
    contenedor.hidden = false;
    contenedor.classList.add("filtro-lugar");

    const NOMBRES = { delegacion: ["Delegación", "Todas"], cliente: ["Cliente", "Todos"],
                      centro: ["Centro", "Todos"] };
    const cajas = {};
    // Un desplegable con una sola opción no deja elegir nada: un cliente con
    // un solo cliente no ve el de «Cliente», y nadie ve el de una delegación.
    const distintos = dim => new Set(claves.map(k => dim === "centro" ? k : (fichas[k] || {})[dim])
                                           .filter(Boolean)).size;
    for (const dim of ["delegacion", "cliente", "centro"]) {
      if (!filtros.includes(dim) || distintos(dim) < 2) continue;
      const id = "pdL" + dim + Math.random().toString(36).slice(2, 7);
      const l = document.createElement("label");
      l.htmlFor = id; l.textContent = NOMBRES[dim][0];
      const s = document.createElement("select");
      s.id = id; s.dataset.dim = dim;
      s.addEventListener("change", () => {
        sel[dim] = s.value;
        // Lo de abajo se vacía si ya no cuadra con lo de arriba.
        if (dim === "delegacion") { sel.cliente = ""; sel.centro = ""; }
        if (dim === "cliente") sel.centro = "";
        rellena(); avisa();
      });
      contenedor.appendChild(l); contenedor.appendChild(s);
      cajas[dim] = s;
    }
    if (!Object.keys(cajas).length) {
      contenedor.hidden = true;
      return { estado: () => Object.assign({}, sel), quiere: () => null, etiqueta: () => "" };
    }
    const quitar = document.createElement("button");
    quitar.type = "button"; quitar.className = "btn filtro-quitar"; quitar.textContent = "Quitar filtro";
    quitar.addEventListener("click", () => { sel.delegacion = sel.cliente = sel.centro = ""; rellena(); avisa(); });
    contenedor.appendChild(quitar);

    function opcionesDe(dim) {
      const vistos = new Map();
      for (const k of claves) {
        const f = fichas[k] || {};
        if (dim !== "delegacion" && sel.delegacion && f.delegacion !== sel.delegacion) continue;
        if (dim === "centro" && sel.cliente && f.cliente !== sel.cliente) continue;
        if (dim === "delegacion" && f.delegacion) vistos.set(f.delegacion, f.delegacion);
        if (dim === "cliente" && f.cliente) vistos.set(f.cliente, f.cliente);
        if (dim === "centro") vistos.set(k, (f.nombre || k) + (f.num && f.num !== f.nombre ? ` (${f.num})` : ""));
      }
      return [...vistos.entries()].sort((a, b) => a[1].localeCompare(b[1], "es"));
    }

    function rellena() {
      for (const dim in cajas) {
        const s = cajas[dim];
        s.innerHTML = "";
        const todas = document.createElement("option");
        todas.value = ""; todas.textContent = NOMBRES[dim][1];
        s.appendChild(todas);
        for (const [v, t] of opcionesDe(dim)) {
          const op = document.createElement("option");
          op.value = v; op.textContent = t;
          s.appendChild(op);
        }
        s.value = sel[dim];
      }
      quitar.hidden = !(sel.delegacion || sel.cliente || sel.centro);
    }

    function avisa() {
      if (o.alCambiar) o.alCambiar(Object.assign({}, sel),
                                   centrosElegidos(fichas, sel), etiquetaLugar(fichas, sel));
    }

    rellena();
    return {
      estado: () => Object.assign({}, sel),
      quiere: () => centrosElegidos(fichas, sel),
      etiqueta: () => etiquetaLugar(fichas, sel)
    };
  }

  // ------------------------------------------------------- la serie, en caché
  // Un mes se baja UNA vez por visita a la pagina. Cambiar de rango dentro del
  // mismo mes no vuelve a pedir nada, y un intervalo largo solo pide los meses
  // que le falten.
  function Serie(opciones) {
    const o = opciones || {};
    this.getJson = o.getJson || (url => fetch(url, { credentials: "same-origin" }).then(r => {
      if (r.status === 401) { location.href = "/"; throw new Error("Sin sesión"); }
      return r.json();
    }));
    this.ruta = o.ruta || "/api/serie";
    this.indice = null;
    this.cache = new Map();
    this.cacheCentros = new Map();
  }

  Serie.prototype.abre = async function () {
    if (!this.indice) this.indice = await this.getJson(this.ruta);
    return this.indice;
  };

  Serie.prototype.bordes = function () { return (this.indice && this.indice.bordes) || {}; };

  Serie.prototype.primerDia = function () {
    return (this.indice && this.indice.primer_dia) || PRIMER_DIA;
  };

  Serie.prototype.mesesConDato = function () {
    return ((this.indice && this.indice.meses) || []).map(m => m.mes);
  };

  /* Las filas de un intervalo. Solo pide los meses que el indice dice que
     tienen dato: un intervalo que cae en un mes sin cargar no es un error, es
     un rango vacio, y la pagina lo ensena a cero. */
  Serie.prototype.filas = async function (desde, hasta, avisa) {
    await this.abre();
    const quiere = meses(desde, hasta).filter(m => this.mesesConDato().includes(m));
    const faltan = quiere.filter(m => !this.cache.has(m));
    for (let i = 0; i < faltan.length; i++) {
      if (avisa) avisa(i + 1, faltan.length);
      const d = await this.getJson(`${this.ruta}?mes=${encodeURIComponent(faltan[i])}`);
      this.cache.set(faltan[i], d.filas || []);
    }
    const out = [];
    for (const m of quiere) {
      for (const f of this.cache.get(m) || []) {
        if (f.f >= desde && f.f <= hasta) out.push(f);
      }
    }
    return out;
  };

  /* Las fichas de los centros y por qué se puede filtrar. La API ya le quita
     la delegación a quien no es de Serunion. */
  Serie.prototype.fichas = function () { return (this.indice && this.indice.centros) || {}; };
  Serie.prototype.filtros = function () {
    return (this.indice && this.indice.filtros) || ["cliente", "centro"];
  };

  /* Lo mismo que `filas`, pero del día partido por centro. Sólo se baja si
     alguien filtra: quien mira el total no lo necesita. */
  Serie.prototype.filasCentros = async function (desde, hasta, avisa) {
    await this.abre();
    const conCentros = (this.indice && this.indice.meses_centros) || [];
    const quiere = meses(desde, hasta).filter(m => conCentros.includes(m));
    const faltan = quiere.filter(m => !this.cacheCentros.has(m));
    for (let i = 0; i < faltan.length; i++) {
      if (avisa) avisa(i + 1, faltan.length);
      const d = await this.getJson(`${this.ruta}?centros=${encodeURIComponent(faltan[i])}`);
      this.cacheCentros.set(faltan[i], d.filas || []);
    }
    const out = [];
    for (const m of quiere) {
      for (const f of this.cacheCentros.get(m) || []) {
        if (f.f >= desde && f.f <= hasta) out.push(f);
      }
    }
    return out;
  };

  /* Los totales de un rango; con `centros` (un Set), sólo de esos centros.
     Con filtro, `por_centro` trae además un renglón por centro. */
  Serie.prototype.totales = async function (desde, hasta, avisa, centros) {
    if (!centros) return sumaFilas(await this.filas(desde, hasta, avisa), this.bordes());
    const fc = await this.filasCentros(desde, hasta, avisa);
    const t = sumaFilas(filasDeCentros(fc, centros), this.bordes());
    t.filtrado = true;
    t.por_centro = sumaCentros(fc, centros);
    return t;
  };

  // ------------------------------------------------------------- el selector
  /* Pinta los botones de rango y las dos fechas, y llama a `alCambiar` con
     {nombre, desde, hasta} cada vez. No pide nada: quien lo use decide si eso
     es una suma de la serie, un filtro local o las dos cosas.

     `limites` acota lo que se puede elegir —desde el primer dia con historia
     hasta hoy—, para que nadie pida 2019 y se quede mirando un cero sin saber
     si es que no hubo o es que no hay. */
  function montaSelector(contenedor, opciones) {
    const o = opciones || {};
    const hoy = o.hoy || new Date();
    const primerDia = o.primerDia || PRIMER_DIA;
    const nombres = (o.rangos || ORDEN).filter(n => RANGOS[n]);
    const estado = { nombre: o.inicial || "mes", desde: null, hasta: null };

    contenedor.innerHTML = "";
    contenedor.classList.add("selector-periodo");

    const chips = document.createElement("div");
    chips.className = "periodo-chips";
    chips.setAttribute("role", "group");
    chips.setAttribute("aria-label", "Periodo");
    const botones = new Map();
    for (const n of nombres) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn periodo-chip";
      b.dataset.rango = n;
      b.textContent = RANGOS[n].nombre;
      b.addEventListener("click", () => elige(n));
      chips.appendChild(b);
      botones.set(n, b);
    }
    contenedor.appendChild(chips);

    const caja = document.createElement("div");
    caja.className = "periodo-intervalo";
    const idd = "pdDesde" + Math.random().toString(36).slice(2, 7);
    const idh = "pdHasta" + Math.random().toString(36).slice(2, 7);
    caja.innerHTML =
      `<label for="${idd}">Desde</label><input type="date" id="${idd}" min="${primerDia}" max="${iso(hoy)}">` +
      `<label for="${idh}">Hasta</label><input type="date" id="${idh}" min="${primerDia}" max="${iso(hoy)}">` +
      `<button type="button" class="btn periodo-aplicar">Aplicar</button>` +
      `<span class="periodo-sello" aria-live="polite"></span>`;
    contenedor.appendChild(caja);

    const eDesde = caja.querySelector("#" + idd);
    const eHasta = caja.querySelector("#" + idh);
    const sello = caja.querySelector(".periodo-sello");

    function pinta() {
      botones.forEach((b, n) => {
        const activo = n === estado.nombre;
        b.classList.toggle("activo", activo);
        b.setAttribute("aria-pressed", activo ? "true" : "false");
      });
      eDesde.value = estado.desde || "";
      eHasta.value = estado.hasta || "";
      sello.textContent = estado.desde ? etiqueta(estado.desde, estado.hasta) : "";
    }

    function avisa() {
      pinta();
      if (o.alCambiar) o.alCambiar({ nombre: estado.nombre, desde: estado.desde, hasta: estado.hasta });
    }

    function elige(n) {
      const [d, h] = rango(n, hoy, primerDia);
      estado.nombre = n; estado.desde = d; estado.hasta = h;
      avisa();
    }

    function aplica() {
      let d = eDesde.value || estado.desde, h = eHasta.value || estado.hasta;
      if (!d || !h) return;
      if (d > h) { const x = d; d = h; h = x; }   // al reves es un despiste, no un error
      if (d < primerDia) d = primerDia;
      estado.nombre = "intervalo"; estado.desde = d; estado.hasta = h;
      avisa();
    }

    caja.querySelector(".periodo-aplicar").addEventListener("click", aplica);
    [eDesde, eHasta].forEach(e => e.addEventListener("keydown", ev => {
      if (ev.key === "Enter") { ev.preventDefault(); aplica(); }
    }));

    const api = {
      estado: () => Object.assign({}, estado),
      elige,
      pon(desde, hasta) { estado.nombre = "intervalo"; estado.desde = desde; estado.hasta = hasta; avisa(); },
      // Sin avisar: para que la pagina ensene donde esta sin provocar otra carga.
      muestra(desde, hasta, nombre) {
        estado.nombre = nombre || "intervalo"; estado.desde = desde; estado.hasta = hasta; pinta();
      }
    };
    if (o.inicial !== null) elige(estado.nombre);
    return api;
  }

  /* El CSS del selector. Va aqui y no en cada pagina para que las tres se vean
     igual. Los colores salen de cuatro variables --pd-*: cada pagina las
     apunta a las suyas en una linea, y asi el selector hereda su tema —modo
     oscuro incluido— sin que este fichero sepa como se llaman los colores de
     cada pantalla. Los valores de aqui son solo el apano para cuando no se
     apuntan. */
  const ESTILO = `
.selector-periodo{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center;margin:0 0 14px}
.periodo-chips{display:flex;flex-wrap:wrap;gap:6px}
.periodo-chip{font-size:13px;padding:5px 11px}
.periodo-chip.activo{background:var(--pd-acento,#2a78d6);border-color:var(--pd-acento,#2a78d6);color:#fff}
.periodo-intervalo{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px}
.periodo-intervalo label{color:var(--pd-apagado,#52514e);margin-left:4px}
.periodo-intervalo input[type=date]{font:inherit;padding:4px 6px;
  border:1px solid var(--pd-borde,#cdccc5);border-radius:6px;
  background:var(--pd-fondo,#fff);color:inherit}
.periodo-sello{color:var(--pd-apagado,#52514e)}
.filtro-lugar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px;margin:0 0 14px}
.filtro-lugar label{color:var(--pd-apagado,#52514e);margin-left:4px}
.filtro-lugar select{font:inherit;padding:4px 6px;max-width:260px;
  border:1px solid var(--pd-borde,#cdccc5);border-radius:6px;
  background:var(--pd-fondo,#fff);color:inherit}
@media (max-width:700px){.selector-periodo{gap:8px}.periodo-chip{font-size:12px;padding:4px 9px}}
`;

  function ponEstilo(documento) {
    const doc = documento || document;
    if (doc.getElementById("estilo-periodos")) return;
    const s = doc.createElement("style");
    s.id = "estilo-periodos";
    s.textContent = ESTILO;
    doc.head.appendChild(s);
  }

  global.Periodos = {
    RANGOS, ORDEN, PRIMER_DIA, rango, meses, etiqueta, iso,
    sumaFilas, sumaHist, resumenHist, Serie, montaSelector, ponEstilo, ESTILO,
    filasDeCentros, sumaCentros, centrosElegidos, etiquetaLugar, montaFiltroLugar
  };
})(typeof window !== "undefined" ? window : globalThis);
