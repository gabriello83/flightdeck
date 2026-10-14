/* Las tres pantallas, abiertas de verdad en un navegador.
 *
 *   node app/comun/prueba_pantallas.js
 *
 * POR QUE EXISTE. El selector de tiempo se monta con JavaScript en tres
 * pantallas de miles de lineas. Un parentesis mal puesto no lo ve ninguna
 * prueba de Python: la pagina se abre en blanco y no se descubre hasta que
 * alguien entra. Esto abre las tres con Chromium, les sirve una API falsa con
 * la misma forma que la de verdad, pulsa los rangos y comprueba que las cifras
 * cambian y que la consola del navegador no escupe ni un error.
 *
 * La API falsa la sirve este mismo fichero: no hace falta AWS ni red.
 */
'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');

const RAIZ = path.join(__dirname, '..');
const HOY = new Date();
const iso = d => d.toISOString().slice(0, 10);
const mesDe = d => iso(d).slice(0, 7);
const MES_HOY = mesDe(HOY);
const AYER = new Date(HOY.getTime() - 86400000);

let fallos = 0;
function comprueba(que, obtenido, esperado) {
  const ok = JSON.stringify(obtenido) === JSON.stringify(esperado);
  console.log(`  ${ok ? 'ok   ' : 'FALLO'} ${que}${ok ? '' : `: ${JSON.stringify(obtenido)} != ${JSON.stringify(esperado)}`}`);
  if (!ok) fallos++;
}
function comprueba_que(que, condicion, detalle) {
  console.log(`  ${condicion ? 'ok   ' : 'FALLO'} ${que}${condicion ? '' : `: ${detalle || ''}`}`);
  if (!condicion) fallos++;
}

// ---------------------------------------------------------------- la API falsa
// Una fila de la serie con la misma forma que escribe infra/serie.py.
function filaSerie(fecha, visitas, importe, minutos) {
  const bordes = BORDES.minutos;
  const h = new Array(bordes.length + 1).fill(0);
  for (const m of minutos) {
    let i = 0;
    for (const b of bordes) { if (m < b) break; i++; }
    h[i]++;
  }
  return {
    f: fecha,
    servicio: {
      visitas, partes: visitas + 1, maquinas_dia: visitas, centros_dia: 1,
      min: { n: minutos.length, suma: minutos.reduce((a, b) => a + b, 0), h, max: Math.max(...minutos, 0) },
      carga: { valor: importe * 2, unidades: visitas * 30, vendibles: visitas * 10 },
      merma: { caducidad: { lineas: 1, unidades: 2, euros: 3.5 }, rotura: { lineas: 0, unidades: 0, euros: 0 }, retirada: { lineas: 0, unidades: 0, euros: 0 } }
    },
    dinero: { periodos: { '2025-02': { registros: 3, efectivo: importe, banco: 1, ciego: 2, imposibles: 0 } } },
    sat: { tareas: 2, averias_tecnicas: 1, preventivos: 0, fallos_tecnicos: 1, cierres: { n: 1, suma: 5, h: new Array(BORDES.horas_cierre.length + 1).fill(0), max: 5 } },
    jornadas: { jornadas: 1, km_total: 80, km: { n: 1, suma: 80, h: new Array(BORDES.km.length + 1).fill(0), max: 80 }, temperatura: { n: 1, suma: 9, h: new Array(BORDES.temperatura.length + 1).fill(0), max: 9 }, temperatura_fuera: 1, gps: 1 },
    venta: { unidades: visitas * 4, importe, maquinas_dia: visitas, fuente: 'visita_ventas' }
  };
}

const BORDES = {
  minutos: [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 30, 45, 60, 90, 120, 180, 240, 360],
  horas_cierre: [0, 1, 2, 4, 8, 12, 24, 48, 72, 120, 168, 336, 720],
  km: [0, 10, 25, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500],
  temperatura: [-10, -2, 0, 2, 4, 6, 8, 10, 12, 15, 20, 25, 30]
};

// Dos meses: el de hoy y marzo de 2025, que es lo que hace falta para ver que
// un rango viejo baja su mes y uno nuevo no vuelve a pedir nada.
const MES_PASADO = mesDe(new Date(HOY.getFullYear(), HOY.getMonth() - 1, 15));
const SERIE = {
  '2025-03': [filaSerie('2025-03-10', 4, 100, [5, 7, 60, 9]), filaSerie('2025-03-11', 6, 200, [6, 6, 8])],
  [MES_PASADO]: [filaSerie(`${MES_PASADO}-05`, 7, 70, [5, 7, 30])],
  [MES_HOY]: [filaSerie(iso(AYER), 2, 50, [5, 7])]
};
const pedidos = [];

// El dia partido por centro (serie/centros-<mes>), con la forma de PorCentro:
// los bloques de la fila del dia menos jornadas y cierres. 500092 se lleva
// todo menos una visita, que es de 500100; y CONSUM, que solo ve el interno.
const FICHAS = {
  '500092': { nombre: 'AIRBUS SAN PABLO SUR', num: '500092', cliente: 'AIRBUS', cod_cliente: 'C7', delegacion: 'SEVILLA' },
  '500100': { nombre: 'AIRBUS GETAFE', num: '500100', cliente: 'AIRBUS', cod_cliente: 'C7', delegacion: 'MADRID' },
  '600': { nombre: 'CONSUM MURCIA', num: '600', cliente: 'CONSUM', cod_cliente: 'C9', delegacion: 'MADRID' }
};
function centrosDe(fila) {
  return {
    f: fila.f,
    centros: {
      '500092': { servicio: { visitas: fila.servicio.visitas - 1, min: fila.servicio.min },
                  venta: { importe: fila.venta.importe } },
      '500100': { servicio: { visitas: 1 }, sat: { tareas: 1 } },
      '600': { servicio: { visitas: 40 } }
    }
  };
}

const API = {
  '/api/yo': {
    correo: 'eva@airbus.com', nombre: 'Eva', tipo: 'cliente', perfil: 'AIRBUS',
    perfil_id: 'cli-airbus',
    sesiones: ['resumen', 'servicio', 'disponibilidad', 'cuadro'],
    catalogo_sesiones: { resumen: 'Resumen', servicio: 'Servicio recibido', disponibilidad: 'Disponibilidad', cuadro: 'Cuadro de mando' },
    permisos: { ver: true, reordenar: true, exportar: true, asistente: false },
    asistente: { habilitado: false, motivo: '' }, umbral: 350
  },
  '/api/orden': { orden: [] },
  '/api/panel': {
    generado: new Date().toISOString(),
    periodo: { desde: '2026-06-08', hasta: iso(AYER), dias: 120 },
    perfil: 'cli-airbus',
    servicio: {
      visitas: 999, partes_totales: 1500, maquinas: 563, centros: 10,
      duracion_min: { n: 999, mediana: 6.8, media: 20.2, p90: 40, max: 387 },
      visitas_por_dia: [{ f: '2026-09-01', v: 10 }],
      por_centro: [{ centro: 'AIRBUS SAN PABLO SUR', visitas: 500, maquinas: 300, min_medio: 7, tareas_sat: 20 }],
      carga: { valor: 50000, unidades_total: 100000, unidades_vendibles: 30000 },
      merma: {
        caducidad: { lineas: 50, unidades: 100, euros: 500 },
        rotura: { lineas: 1, unidades: 1, euros: 2 },
        retirada: { lineas: 2, unidades: 2, euros: 4 },
        caducidad_por_articulo: [{ articulo: 'CAFE', lineas: 10, unidades: 10, euros: 230, eur_unidad: 23 }]
      }
    },
    dinero: { periodos: [{ periodo: '2026-08', registros: 100, efectivo: 1000, banco: 2000, total: 3000, efectivo_sin_telemetria: 100, pct_ciego: 10, provisional: false }] },
    sat: { tareas: 300, tareas_con_ficticia: 400, averias_tecnicas: 100, fallos_tecnicos: 150, preventivos: 10, horas_cierre: { n: 90, mediana: 20, media: 40, p90: 100, max: 500 }, reincidentes: [{ m: '24SE1983', c: 'AIRBUS', n: 7 }] },
    sesiones: ['resumen', 'servicio', 'disponibilidad', 'cuadro']
  },
  '/api/serie': {
    perfil: 'cli-airbus', primer_dia: '2025-01-01', bordes: BORDES,
    rangos: { hoy: 'Hoy', ayer: 'Ayer', mes: 'Este mes', mes_pasado: 'Mes pasado' },
    meses: [
      { mes: '2025-03', dias: 2, visitas: 10, importe: 300, tareas: 4, carga: 600 },
      { mes: MES_PASADO, dias: 1, visitas: 7, importe: 70, tareas: 2, carga: 140 },
      { mes: MES_HOY, dias: 1, visitas: 2, importe: 50, tareas: 2, carga: 100 }
    ]
  },
  // El informe general operativo (docs/51), con la forma que escribe
  // infra/operativo.py ya recortada por la API: un dia con todo y uno sin plan.
  '/api/operativo': {
    generado: new Date().toISOString(), ultimo_dia: iso(AYER), umbrales: { verde: 95, amarillo: 75 },
    cuadrados: ['rutas', 'averias', 'almacenes', 'furgonetas', 'pdvs', 'ventas', 'reposiciones', 'telemetria', 'tarifas'],
    dias: {
      [iso(AYER)]: {
        rutas: { previstas: 400, hechas: 350, pct: 87.5, color: 'amarillo', visitas: 1100, fuera_de_plan: 12 },
        averias: { cerradas: 43, a_tiempo: 30, pct: 69.8, color: 'rojo', horas: 24, sin_tarea: 2 },
        furgonetas: { activas: 40, visitas: 1100, visitas_sin_vehiculo: 110 },
        ventas: { importe: 49859.02, unidades: 54119, maquinas: 1893, fuente: 'telemetria', imposibles: 0 },
        reposiciones: { unidades: 52168, por_clase: [{ clase: 'Snack', unidades: 30340 }, { clase: 'Bebida fría', unidades: 19448 }], consumibles: 88124, valor: 27616 },
        telemetria: { auditables: 2253, con_dex: 2200, pct: 97.6, color: 'verde' }
      },
      '2026-10-01': {
        rutas: { sin_dato: 'Falta el plan de visitas.', visitas: 900 },
        averias: { sin_dato: 'Ese día no se cerró ninguna avería.', cerradas: 0, sin_tarea: 0 },
        furgonetas: { activas: 30, visitas: 900, visitas_sin_vehiculo: 0 },
        ventas: { sin_dato: 'Ese día no llegó venta.' },
        reposiciones: { unidades: 0, por_clase: [], consumibles: 0, valor: 0 },
        telemetria: { auditables: 2253, con_dex: 900, pct: 39.9, color: 'rojo' }
      }
    },
    foto: { pdvs: { activos: 3195, maquinas: 3165 },
            tarifas: { pct: 81.3, color: 'amarillo', coinciden: 13, controlados: 16, sin_tarifa: 2, sin_dato_productos: 1, desde: '2026-04-14' },
            almacenes: { valor: 502429.74, periodo: '2026-09', por_almacen: [{ almacen: 'A', delegacion: '', valor: 1 }] } }
  },
  '/api/estado-carga': { ultima_carga: new Date().toISOString(), dias_pedidos: [iso(AYER)], descargas_ok: 75, descargas_fallidas: 0, bytes: 12345678, filas_por_informe: { visita_cabecera: 1000 }, errores: [], retraso_dias: 0 },
  '/api/admin/usuarios': { usuarios: [{ _id: 'eva@airbus.com', nombre: 'Eva', perfil_id: 'cli-airbus', estado: 'activo' }] },
  '/api/admin/perfiles': {
    perfiles: [{ _id: 'cli-airbus', nombre: 'AIRBUS', tipo: 'cliente', ambito: { centros: ['500092'] }, sesiones: ['resumen'], permisos: {}, panel: { existe: true, calculado: new Date().toISOString() } }],
    catalogo_sesiones: { resumen: { nombre: 'Resumen', minimo: 'operaciones' }, cuadro: { nombre: 'Cuadro de mando', minimo: 'cliente' } },
    catalogo_cuadro: { indicadores: { nombre: 'Indicadores', flujos: ['ventas', 'visitas', 'incidencias'] },
                       articulos: { nombre: 'Mix de artículos', flujos: ['ventas'] },
                       listado_visitas: { nombre: 'Listado de visitas', flujos: ['visitas'] } },
    techo: { cliente: ['ver'] }, niveles: { cliente: 0, operaciones: 1, admin: 3 }, implicitos: { cliente: ['ver'] }
  },
  '/api/admin/config': { asistente_global: true, limite_preguntas_dia: 40, umbral_rentabilidad_mes: 350 },
  '/api/admin/telefonos': { telefonos: [] },
  '/api/admin/cola': { cola: [] }
};

// Tarifas (docs/52), con la forma que escribe infra/tarifas.py: dos
// delegaciones, y en Cadiz un centro con un precio distinto y uno sin tarifa.
const CENTRO_TARIFAS = {
  num_centro: '114001', centro: 'HOSPITAL DE JEREZ', cliente: 'SERUNION, SA', cod_cliente: '10002',
  delegacion: 'Andalucía - Cádiz',
  filas: [
    { matricula: '22SE1877', cod_pdv: 'S00741', ubicacion: 'Planta 2', cod_articulo: '9354', articulo: 'COCA COLA LATA 33CL',
      ultima_carga: '2026-10-10', nivel: 'estandar', asignada: 'cliente', origen: 'tarifa', tarifa: 'ESTANDAR 2024', cambio_tarifa: '2026-01-02', desde: '2026-04-14',
      medios: { ef: { tarifa: 1.2, venta: { precio: 1.3, fecha: '2026-10-13', fuente: 'telemetria' }, ok: false },
                tc: { tarifa: 1.2, venta: { precio: 1.2, fecha: '2026-10-13', fuente: 'telemetria' }, ok: true } },
      estado: 'no_coincide' },
    { matricula: '22SE1877', cod_pdv: 'S00741', ubicacion: 'Planta 2', cod_articulo: '102411', articulo: 'ÑAMING ENSALADA <MIXTA> & CO',
      ultima_carga: '2026-10-01', nivel: null, origen: null, tarifa: '', cambio_tarifa: '', desde: '2026-04-14',
      medios: { ef: { venta: { precio: 2.3, fecha: '2026-10-12', fuente: 'audit' } } }, estado: 'sin_tarifa' },
    { matricula: '22SE1878', cod_pdv: 'S00742', ubicacion: '', cod_articulo: '5322', articulo: 'AGUA 50CL',
      ultima_carga: '2026-09-20', nivel: 'centro', origen: 'productos', tarifa: '', cambio_tarifa: '2026-10-05', desde: '2026-10-05',
      medios: { ef: { tarifa: 0.9 } }, estado: 'sin_dato' },
    { matricula: '22SE1878', cod_pdv: 'S00742', ubicacion: '', cod_articulo: '9355', articulo: 'FANTA',
      ultima_carga: '2026-09-20', nivel: 'estandar', asignada: 'cliente', origen: 'tarifa', tarifa: 'ESTANDAR 2024', cambio_tarifa: '2026-01-02', desde: '2026-04-14',
      medios: { ef: { tarifa: 1.2, venta: { precio: 1.2, fecha: '2026-10-11', fuente: 'telemetria' }, ok: true } }, estado: 'coincide' }
  ]
};
const RESUMEN_TARIFAS = {
  generado: new Date().toISOString(), desde: '2026-04-14', dias: 183,
  total: { coincide: 13, no_coincide: 3, sin_tarifa: 2, sin_dato: 1, controlados: 16, pct: 81.3 },
  provisional: 'El orden entre niveles es provisional.',
  delegaciones: [
    { delegacion: 'Andalucía - Cádiz', coincide: 1, no_coincide: 1, sin_tarifa: 1, sin_dato: 1, controlados: 2, pct: 50, color: 'rojo',
      centros: [{ num_centro: '114001', centro: 'HOSPITAL DE JEREZ', cliente: 'SERUNION, SA', cod_cliente: '10002', maquinas: 2,
        nivel: 'estandar', niveles: { estandar: 2, centro: 1 }, tarifas: [{ tarifa: 'ESTANDAR 2024 (asignada al cliente)', maquinas: 2 }],
        coincide: 1, no_coincide: 1, sin_tarifa: 1, sin_dato: 1, controlados: 2, pct: 50, color: 'rojo' }] },
    { delegacion: 'Madrid - Leganés', coincide: 12, no_coincide: 2, sin_tarifa: 1, sin_dato: 0, controlados: 14, pct: 85.7, color: 'amarillo',
      centros: [{ num_centro: '500', centro: 'CENTRO 500', cliente: 'CLIENTE', cod_cliente: '1', maquinas: 5,
        nivel: 'pdv', niveles: { pdv: 15 }, tarifas: [], coincide: 12, no_coincide: 2, sin_tarifa: 1, sin_dato: 0, controlados: 14, pct: 85.7, color: 'amarillo' }] }
  ]
};

// El cuadro: el indice y un fichero por mes, con la forma que escribe cuadro.py.
function mesCuadro(mes, dias) {
  return {
    mes,
    centros: ['AIRBUS SAN PABLO SUR'],
    maquinas: [['24SE1983', 0, 'Comedor', 'P1', 1], ['24SE1984', 0, 'Hangar', 'P2', 1]],
    articulos: ['AGUA', 'CAFE'],
    _columnas: ['dia', 'maquina', 'articulo', 'unidades', 'importe'],
    ventas: dias.flatMap(d => [[d, 0, 0, 3, 1.8], [d, 1, 1, 2, 1.4]]),
    visitas: dias.map(d => [`${mes}-${String(d).padStart(2, '0')} 08:15`, 0]),
    // Una averia por dia y un preventivo: viajan juntos y la pagina los aparta.
    incidencias: [...dias.map(d => [`${mes}-${String(d).padStart(2, '0')}`, '', 0, `A-${d}`, 'AVERIAS TECNICAS', 'TECNICO - No enfría', 'Finalizado']),
      [`${mes}-${String(dias[0]).padStart(2, '0')}`, '', 1, 'E-11887', 'Solicitudes internas', 'Preventivo Electrodomésticos Airbus (Interno)', 'Finalizado']],
    fuente: 'visita_ventas', maquinas_con_venta: 2
  };
}
const CUADRO = { '2025-03': mesCuadro('2025-03', [10, 11]), [MES_HOY]: mesCuadro(MES_HOY, [1]) };
const INDICE_CUADRO = {
  generado: new Date().toISOString(), perfil: 'cli-airbus', nombre: 'AIRBUS',
  periodo: { desde: '2026-06-08', hasta: iso(AYER), dias: 120 },
  primer_dia: '2025-01-01',
  centros: ['AIRBUS SAN PABLO SUR'],
  censo: [['24SE1983', 0, 'Comedor', 'P1'], ['24SE1984', 0, 'Hangar', 'P2']],
  meses: Object.keys(CUADRO).sort().map(m => ({
    mes: m, filas: CUADRO[m].ventas.length, unidades: 10, importe: 3.2 * CUADRO[m].ventas.length / 2,
    visitas: CUADRO[m].visitas.length, incidencias: CUADRO[m].incidencias.length,
    // El mes de hoy ya con telemetria; los viejos, con la venta parcial del parte.
    maquinas_con_venta: 2, fuente: m === MES_HOY ? 'telemetria' : 'visita_ventas', bytes: 1000
  })),
  ventas: { fuente: 'visita_ventas', dias_telemetria: 0, dias_visita: 3, maquinas_censo: 2, maquinas_censo_con_venta: 2, _nota: 'parcial' },
  preventivos: { fuente: 'sat_averias' }, _preventivos: 'las tareas de SAT con operacion de preventivo'
};

const TIPOS = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8' };

const servidor = http.createServer((pet, res) => {
  const u = new URL(pet.url, 'http://x');
  const json = o => { res.writeHead(200, { 'content-type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(o)); };
  if (u.pathname.startsWith('/api/')) {
    pedidos.push(u.pathname + (u.search || ''));
    if (u.pathname === '/api/serie') {
      const mes = u.searchParams.get('mes');
      // El ambito es del perfil; la delegacion se le quita solo al cliente.
      const interno = API['/api/yo'].tipo !== 'cliente';
      const suyos = k => API['/api/yo'].perfil_id === 'interno' || k !== '600';
      const cm = u.searchParams.get('centros');
      if (cm !== null) {
        if (!SERIE[cm]) { res.writeHead(400); return res.end('{"error":"mes"}'); }
        return json({ mes: cm, filas: SERIE[cm].map(centrosDe).map(f => ({ f: f.f,
          centros: Object.fromEntries(Object.entries(f.centros).filter(([k]) => suyos(k))) })) });
      }
      if (!mes) {
        // Como la API de verdad: a un cliente, sin delegacion y solo sus centros.
        const centros = {};
        for (const [k, v] of Object.entries(FICHAS)) {
          if (!suyos(k)) continue;
          centros[k] = { ...v };
          if (!interno) delete centros[k].delegacion;
        }
        return json({ ...API['/api/serie'], meses_centros: Object.keys(SERIE), centros,
                      filtros: interno ? ['delegacion', 'cliente', 'centro'] : ['cliente', 'centro'] });
      }
      if (!SERIE[mes]) { res.writeHead(400); return res.end('{"error":"mes"}'); }
      return json({ mes, filas: SERIE[mes] });
    }
    if (u.pathname === '/api/cuadro') {
      const mes = u.searchParams.get('mes');
      // Como la API: sin venta en los flujos del perfil, la venta no sale.
      const conVenta = !API['/api/yo'].cuadro || API['/api/yo'].cuadro.flujos.includes('ventas');
      const sinVenta = o => { const c = { ...o }; ['ventas', 'articulos', '_columnas', 'fuente', 'maquinas_con_venta'].forEach(k => delete c[k]); return c; };
      if (!mes) return json(conVenta ? INDICE_CUADRO : { ...sinVenta(INDICE_CUADRO), meses: INDICE_CUADRO.meses.map(m => ({ mes: m.mes, visitas: m.visitas, incidencias: m.incidencias })) });
      if (!CUADRO[mes]) { res.writeHead(400); return res.end('{"error":"mes"}'); }
      return json(conVenta ? CUADRO[mes] : sinVenta(CUADRO[mes]));
    }
    if (u.pathname === '/api/tarifas') {
      const c = u.searchParams.get('centro');
      if (c === null) return json(RESUMEN_TARIFAS);
      if (c !== CENTRO_TARIFAS.num_centro) { res.writeHead(400); return res.end('{"error":"Ese centro no está en las tarifas de este perfil."}'); }
      return json(CENTRO_TARIFAS);
    }
    if (API[u.pathname]) return json(API[u.pathname]);
    res.writeHead(404); return res.end('{"error":"no existe"}');
  }
  if (u.pathname === '/favicon.ico') { res.writeHead(204); return res.end(); }
  let p = u.pathname === '/' ? '/index.html' : u.pathname;
  if (p.endsWith('/')) p += 'index.html';
  const f = path.join(RAIZ, p);
  if (!f.startsWith(RAIZ) || !fs.existsSync(f)) { res.writeHead(404); return res.end('no'); }
  res.writeHead(200, { 'content-type': TIPOS[path.extname(f)] || 'text/plain' });
  res.end(fs.readFileSync(f));
});

// ---------------------------------------------------------------- las pruebas
(async () => {
  const { chromium } = require(path.join(RAIZ, '..', 'node_modules', 'playwright'));
  await new Promise(r => servidor.listen(0, r));
  const base = `http://127.0.0.1:${servidor.address().port}`;
  // El Chromium de este contenedor puede no ser el que pide la version de
  // Playwright instalada; si esta en /opt/pw-browsers, se usa ese.
  const AQUI_CHROMIUM = '/opt/pw-browsers/chromium';
  const navegador = await chromium.launch(
    fs.existsSync(AQUI_CHROMIUM) ? { executablePath: AQUI_CHROMIUM } : {});

  async function abre(ruta) {
    const pagina = await navegador.newPage();
    const errores = [];
    pagina.on('pageerror', e => errores.push(String(e)));
    pagina.on('console', m => { if (m.type() === 'error') errores.push(m.text()); });
    // Un solo origen (CLAUDE.md): cualquier peticion a otro dominio se apunta.
    const fuera = [];
    pagina.on('request', q => { if (!q.url().startsWith(base) && !q.url().startsWith('data:')) fuera.push(q.url()); });
    await pagina.goto(base + ruta, { waitUntil: 'networkidle' });
    return { pagina, errores, fuera };
  }

  // ------------------------------------------------- un cliente, al cuadro
  console.log('\nUn cliente solo tiene el cuadro');
  {
    const { pagina } = await abre('/panel/');
    await pagina.waitForURL('**/cuadro/');
    comprueba_que('si abre el panel, acaba en el cuadro', pagina.url().endsWith('/cuadro/'), pagina.url());
    await pagina.close();
  }

  // -------------------------------------------- el panel, desde operaciones
  console.log('\nEl panel de operaciones');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones' };
    const { pagina, errores } = await abre('/panel/');
    await pagina.waitForSelector('.periodo-menu');
    // La serie de prueba aun nombra «hoy», como un indice escrito antes de
    // quitarlo: no debe salir en el menu, porque hoy nunca tiene dato.
    comprueba('sin hoy en el menu', await pagina.locator('.periodo-menu option[value="hoy"]').count(), 0);
    comprueba('los periodos van en un menu, no en botones',
      await pagina.locator('.selector-periodo button:not(.periodo-aplicar)').count(), 0);
    comprueba('con la ventana la primera y los rangos detras',
      await pagina.$$eval('.periodo-menu option:not([disabled])', x => x.map(o => o.value)),
      ['ventana', 'ayer', 'semana', 'mes', 'mes_pasado', '30dias', 'anio', 'todo']);
    const visitasVentana = await pagina.textContent('#kpis .kpi .vl');
    comprueba('arranca en la foto de la ventana', visitasVentana.trim(), '999');
    comprueba('y el menu dice que es la ventana', await pagina.inputValue('.periodo-menu'), 'ventana');

    await pagina.selectOption('.periodo-menu', 'mes_pasado');
    await pagina.waitForFunction(() => !document.querySelector('#kpis .kpi .vl').textContent.includes('999'));
    comprueba_que('al elegir «mes pasado» cambian las cifras',
      (await pagina.textContent('#kpis .kpi .vl')).trim() !== '999');
    comprueba_que('y se dice lo que no se puede partir por dias',
      (await pagina.textContent('#notaPeriodo')).includes('reparto por centro'));

    // Marzo de 2025: un mes que hay que bajar.
    comprueba_que('un mes con telemetria no lleva el aviso de venta parcial', !(await pagina.isVisible('#salesNotice')));

    await pagina.fill('.periodo-intervalo input[type=date]', '2025-03-01');
    await pagina.fill('.periodo-intervalo input[type=date] ~ label + input', '2025-03-31');
    await pagina.click('.periodo-aplicar');
    await pagina.waitForFunction(() => document.querySelector('#notaPeriodo').textContent.includes('2 días'));
    comprueba('suma los dos dias de marzo de 2025',
      (await pagina.textContent('#kpis .kpi .vl')).trim(), '10');
    comprueba_que('pidiendo su mes al servidor', pedidos.includes('/api/serie?mes=2025-03'));
    comprueba('y el menu dice que son fechas a medida', await pagina.inputValue('.periodo-menu'), 'intervalo');

    await pagina.selectOption('.periodo-menu', 'ventana');
    await pagina.waitForFunction(() => document.querySelector('#kpis .kpi .vl').textContent.includes('999'));
    comprueba('volver a la ventana desde el menu', (await pagina.textContent('#kpis .kpi .vl')).trim(), '999');

    await pagina.selectOption('.periodo-menu', 'ayer');
    await pagina.waitForTimeout(400);
    const antes = pedidos.length;
    await pagina.selectOption('.periodo-menu', 'mes');
    await pagina.waitForTimeout(400);
    comprueba_que('un mes ya bajado no se vuelve a pedir',
      pedidos.slice(antes).filter(x => x.startsWith('/api/serie?')).length === 0,
      JSON.stringify(pedidos.slice(antes)));

    console.log('  · el filtro de lugar');
    comprueba_que('tiene filtro de centro', await pagina.isVisible('#filtroLugar select[data-dim="centro"]'));
    comprueba('y de delegacion, que es de Serunion',
      await pagina.$$eval('#filtroLugar select[data-dim="delegacion"]', x => x.length), 1);
    comprueba('ni de cliente: solo tiene uno',
      await pagina.$$eval('#filtroLugar select[data-dim="cliente"]', x => x.length), 0);
    comprueba('y solo ve sus centros',
      await pagina.$$eval('#filtroLugar select[data-dim="centro"] option', x => x.map(o => o.value)),
      ['', '500100', '500092']);
    await pagina.selectOption('.periodo-menu', 'mes_pasado');
    await pagina.waitForTimeout(300);
    await pagina.selectOption('#filtroLugar select[data-dim="centro"]', '500100');
    await pagina.waitForFunction(() => document.querySelector('#notaPeriodo').textContent.includes('AIRBUS GETAFE'));
    comprueba('el mes pasado de un solo centro', (await pagina.textContent('#kpis .kpi .vl')).trim(), '1');
    comprueba_que('bajando el mes partido por centro', pedidos.includes(`/api/serie?centros=${MES_PASADO}`));
    await pagina.click('.filtro-quitar');
    await pagina.waitForFunction(() => document.querySelector('#kpis .kpi .vl').textContent.trim() === '7');
    comprueba('quitar el filtro vuelve al total', (await pagina.textContent('#kpis .kpi .vl')).trim(), '7');

    await pagina.selectOption('.periodo-menu', 'ventana');
    await pagina.waitForFunction(() => document.querySelector('#kpis .kpi .vl').textContent.includes('999'));
    comprueba('se puede volver a la ventana',
      (await pagina.textContent('#kpis .kpi .vl')).trim(), '999');
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente' };
  }

  // ------------------------------------------------------------- la consola
  console.log('\nLa consola de administracion');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'admin', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores } = await abre('/consola/');
    await pagina.waitForSelector('#pestanas button');
    await pagina.click('#pestanas button[data-s="historico"]');
    await pagina.waitForSelector('#cifrasPeriodo .kpi');
    comprueba_que('la pestana del historico sale con el mes en curso',
      (await pagina.textContent('#cifrasPeriodo')).includes('1 día'));
    comprueba_que('y la tabla de meses dice lo que hay cargado',
      (await pagina.textContent('body')).includes('2025-03'));
    await pagina.selectOption('.periodo-menu', 'mes_pasado');
    await pagina.waitForTimeout(400);
    await pagina.fill('.periodo-intervalo input[type=date]', '2025-03-01');
    await pagina.fill('.periodo-intervalo input[type=date] ~ label + input', '2025-03-11');
    await pagina.click('.periodo-aplicar');
    await pagina.waitForFunction(() => document.querySelector('#cifrasPeriodo').textContent.includes('2 días'));
    const cifras = await pagina.textContent('#cifrasPeriodo');
    comprueba_que('un intervalo de 2025 suma sus dias', cifras.includes('2 días'), cifras.slice(0, 200));
    comprueba_que('con sus visitas', cifras.includes('10'));
    comprueba_que('el interno si filtra por delegacion',
      await pagina.isVisible('#filtroLugar select[data-dim="delegacion"]'));
    await pagina.selectOption('#filtroLugar select[data-dim="delegacion"]', 'MADRID');
    await pagina.waitForSelector('#cifrasPeriodo table th:has-text("Delegación")');
    comprueba('los clientes de esa delegacion',
      await pagina.$$eval('#filtroLugar select[data-dim="cliente"] option', x => x.map(o => o.value)),
      ['', 'AIRBUS', 'CONSUM']);
    const porCentro = await pagina.textContent('#cifrasPeriodo');
    comprueba_que('una tabla con sus centros', porCentro.includes('CONSUM MURCIA') && porCentro.includes('AIRBUS GETAFE')
      && !porCentro.includes('SAN PABLO'), porCentro.slice(0, 300));
    comprueba_que('y la suma de los dos dias de esos centros', porCentro.includes('82'), porCentro.slice(0, 300));

    // El ambito del perfil se elige de una lista, varios a la vez.
    await pagina.click('#pestanas button[data-s="perfiles"]');
    await pagina.click('[data-ed="cli-airbus"]');
    const fichasDe = id => pagina.$$eval(`#${id} .elegido > span`, x => x.map(s => s.textContent));
    const listaDe = id => pagina.$$eval(`#${id}Lista li[role=option]`, x => x.map(l => [l.querySelector('.txt').textContent, l.getAttribute('aria-selected') === 'true']));
    comprueba('el centro ya puesto sale por su nombre, con su cliente elegido',
      [await fichasDe('mClientes'), await fichasDe('mCentros')], [['AIRBUS'], ['AIRBUS SAN PABLO SUR']]);
    comprueba_que('debajo, el numero que se guarda y cuantos de sus centros lleva',
      (await pagina.textContent('#rCentros')).includes('500092')
      && (await pagina.textContent('#rClientes')).includes('AIRBUS: 1 de sus 2 centros'), await pagina.textContent('#rClientes'));
    console.log('  · un perfil de cliente');
    comprueba('no tiene delegaciones ni sesiones que elegir, y si las partes del cuadro',
      [await pagina.isVisible('#campoDelegaciones'), await pagina.isVisible('#campoSesiones'), await pagina.isVisible('#campoCuadro')],
      [false, false, true]);
    await pagina.click('#fClientes');
    comprueba('al entrar salen todos los clientes, con el suyo marcado',
      await listaDe('fClientes'), [['AIRBUS', true], ['CONSUM', false]]);
    await pagina.keyboard.type('c');
    comprueba('una letra y salen los que la llevan, el que empieza por ella primero (AIRBUS por su codigo C7)',
      (await listaDe('fClientes')).map(x => x[0]), ['CONSUM', 'AIRBUS']);
    await pagina.keyboard.press('Enter');
    comprueba('Intro lo elige sin guardar el perfil, y la lista sigue abierta',
      [await fichasDe('mClientes'), await pagina.isVisible('#dlg'), await pagina.isVisible('#fClientesLista')],
      [['AIRBUS', 'CONSUM'], true, true]);
    await pagina.fill('#fClientes', '');
    await pagina.click('#fCentros');
    comprueba('los centros son los de los clientes elegidos',
      (await listaDe('fCentros')).map(x => x[0]), ['AIRBUS GETAFE', 'AIRBUS SAN PABLO SUR', 'CONSUM MURCIA']);
    await pagina.keyboard.type('geta');
    await pagina.click('#fCentrosLista li:has-text("AIRBUS GETAFE")');
    await pagina.fill('#fCentros', '');
    await pagina.click('#fCentrosLista li:has-text("CONSUM MURCIA")');
    comprueba('se buscan por nombre y se eligen varios', await fichasDe('mCentros'),
      ['AIRBUS SAN PABLO SUR', 'AIRBUS GETAFE', 'CONSUM MURCIA']);
    await pagina.click('#mClientes .elegido:has-text("CONSUM") button');
    comprueba('quitado un cliente, se van sus centros', await fichasDe('mCentros'), ['AIRBUS SAN PABLO SUR', 'AIRBUS GETAFE']);
    await pagina.click('#fCentros');
    comprueba('y ya no salen en la lista', (await listaDe('fCentros')).map(x => x[0]), ['AIRBUS GETAFE', 'AIRBUS SAN PABLO SUR']);
    await pagina.keyboard.press('Escape');
    comprueba('Escape cierra la lista y no el dialogo',
      [await pagina.isVisible('#fCentrosLista'), await pagina.isVisible('#dlg')], [false, true]);
    const guardado = () => new Promise(r => pagina.on('request', q => {
      if (q.method() === 'POST' && q.url().endsWith('/api/admin/perfiles')) r(JSON.parse(q.postData()));
    }));
    let envio = guardado();
    await pagina.click('#bGuardar');
    let cuerpo = await envio;
    comprueba('se guarda: el cliente con centros marcados, solo sus centros; y solo el cuadro',
      [cuerpo.ambito, cuerpo.sesiones],
      [{ clientes: [], centros: ['500092', '500100'], delegaciones: [] }, ['cuadro']]);

    console.log('  · un perfil de operaciones');
    await pagina.waitForSelector('[data-ed="cli-airbus"]');
    await pagina.click('[data-ed="cli-airbus"]');
    await pagina.selectOption('#fTipo', 'operaciones');
    comprueba('tiene delegaciones y sesiones',
      [await pagina.isVisible('#campoDelegaciones'), await pagina.isVisible('#campoSesiones')], [true, true]);
    await pagina.click('#mClientes .elegido button');
    await pagina.click('#fClientes');
    await pagina.click('#fClientesLista li:has-text("CONSUM")');
    await pagina.click('#fDelegaciones');
    await pagina.keyboard.type('zz');
    comprueba_que('lo que no esta en los datos se dice', await pagina.isVisible('#fDelegacionesLista li.nada'));
    await pagina.fill('#fDelegaciones', 'mad');
    await pagina.keyboard.press('Enter');
    comprueba_que('y lo elegido dice con cuantos centros encaja',
      (await pagina.textContent('#rDelegaciones')).includes('MADRID: 2 centros')
      && (await pagina.textContent('#rClientes')).includes('CONSUM: entero, 1 centro'), await pagina.textContent('#rClientes'));
    comprueba_que('sin el cuadro marcado no hay partes que elegir', !(await pagina.isVisible('#campoCuadro')));
    await pagina.check('#cajaSesiones input[value="cuadro"]');
    comprueba('al marcarlo salen todas, puestas',
      await pagina.$$eval('#cajaCuadro input', x => x.map(i => [i.value, i.checked])),
      [['indicadores', true], ['articulos', true], ['listado_visitas', true]]);
    envio = guardado();
    await pagina.click('#bGuardar');
    cuerpo = await envio;
    comprueba('se guarda el cliente entero y la delegacion', [cuerpo.ambito, cuerpo.sesiones],
      [{ clientes: ['CONSUM'], centros: [], delegaciones: ['MADRID'] }, ['resumen', 'cuadro']]);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  // ----------------------------------------------------------- el cuadro
  console.log('\nEl cuadro de mando');
  {
    const { pagina, errores } = await abre('/cuadro/');
    await pagina.waitForSelector('#kpiGrid .kpi-card, #kpiGrid > *');
    comprueba_que('arranca en el ultimo mes con dato, no en la historia entera',
      pedidos.includes(`/api/cuadro?mes=${MES_HOY}`) && !pedidos.includes('/api/cuadro?mes=2025-03'),
      JSON.stringify(pedidos.filter(x => x.startsWith('/api/cuadro'))));
    comprueba_que('y las fechas del periodo son las de ese mes',
      (await pagina.inputValue('.periodo-intervalo input[type=date]')).startsWith(MES_HOY));
    comprueba('el filtro cruzado no repite Desde y Hasta',
      await pagina.locator('.filter-grid input[type=date]').count(), 0);
    // Los datos llegan hasta ayer: el resto del mes no son dias a cero, son
    // dias que no han llegado, y ni el filtro ni el grafico deben pintarlos.
    if (iso(AYER).startsWith(MES_HOY)) {
      comprueba('el hasta se queda en ayer, no en el fin de mes', await pagina.inputValue('.periodo-intervalo input[type=date] ~ label + input'), iso(AYER));
      const ultimaEtiqueta = await pagina.evaluate(() => [...document.querySelectorAll('#trendChart text')].map(t => t.textContent).filter(t => /^\d\d\/\d\d$/.test(t)).pop());
      comprueba('y el grafico acaba en ayer', ultimaEtiqueta, `${iso(AYER).slice(8, 10)}/${iso(AYER).slice(5, 7)}`);
    }

    await pagina.fill('.periodo-intervalo input[type=date]', '2025-03-01');
    await pagina.fill('.periodo-intervalo input[type=date] ~ label + input', '2025-03-31');
    const marzo = pagina.waitForResponse(r => r.url().includes('/api/cuadro?mes=2025-03'));
    await pagina.click('.periodo-aplicar');
    await marzo;
    await pagina.waitForTimeout(400);
    comprueba_que('elegir marzo de 2025 baja su mes', pedidos.includes('/api/cuadro?mes=2025-03'));
    comprueba_que('y marzo de 2025, con la venta del parte, si lo lleva', await pagina.isVisible('#salesNotice'));
    comprueba('y el periodo se queda en marzo',
      [await pagina.inputValue('.periodo-intervalo input[type=date]'),
       await pagina.inputValue('.periodo-intervalo input[type=date] ~ label + input')],
      ['2025-03-01', '2025-03-31']);
    await pagina.click('#resetFilters');
    await pagina.waitForTimeout(300);
    comprueba('limpiar los filtros cruzados no toca el periodo',
      await pagina.inputValue('.periodo-intervalo input[type=date]'), '2025-03-01');
    comprueba_que('el cliente con un solo cliente no ve filtro de lugar en el cuadro',
      !(await pagina.isVisible('#filtroLugar select')));
    const tabla = await pagina.textContent('#visitLogTable');
    comprueba_que('la tabla de visitas ensena las de marzo de 2025', tabla.includes('2025'), tabla.slice(0, 120));
    const preventivos = await pagina.textContent('#preventiveTable');
    comprueba_que('el preventivo de la SAT sale en su tabla', preventivos.includes('E-11887'), preventivos.slice(0, 120));
    const averias = (await pagina.textContent('#operationTable')) + (await pagina.textContent('#issueTable'));
    comprueba_que('y no como averia', averias.includes('No enfría') && !averias.includes('Preventivo'), averias.slice(0, 160));
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
  }

  console.log('\nEl cuadro, con solo algunas partes');
  {
    const visitasEincid = ['visitas_maquina', 'incid_operacion', 'detalle_incid', 'listado_visitas', 'preventivos'];
    API['/api/yo'] = { ...API['/api/yo'], cuadro: { secciones: visitasEincid, flujos: ['visitas', 'incidencias'] } };
    const { pagina, errores } = await abre('/cuadro/');
    await pagina.waitForSelector('#visitLogTable table');
    comprueba('sin indicadores, ni evolucion, ni mix, ni conclusiones',
      [await pagina.isVisible('#kpiGrid'), await pagina.isVisible('#trendChart'),
       await pagina.isVisible('#productTable'), await pagina.isVisible('#insightGrid')], [false, false, false, false]);
    comprueba('con sus visitas e incidencias',
      [await pagina.isVisible('#visitTable'), await pagina.isVisible('#operationTable'),
       await pagina.isVisible('#visitLogTable'), await pagina.isVisible('#issueTable')], [true, true, true, true]);
    comprueba_que('la fila de tres que pierde una reparte el ancho entre dos',
      await pagina.$eval('#visitTable', n => n.closest('.dashboard-grid').classList.contains('recortada')));
    comprueba('sin venta no hay aviso de venta parcial, ni filtro de articulo, ni enlace de fuentes',
      [await pagina.isVisible('#salesNotice'), await pagina.isVisible('#articleField'), await pagina.isVisible('#footerCoverage')],
      [false, false, false]);
    comprueba_que('y no se le pidio nada de venta', !pedidos.some(x => x.includes('ventas')));
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    delete API['/api/yo'].cuadro;
  }

  console.log('\nEl cuadro, visto desde Serunion');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'admin', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores } = await abre('/cuadro/');
    await pagina.waitForSelector('#filtroLugar select[data-dim="delegacion"]');
    comprueba('ofrece delegacion y cliente, el centro ya lo tenia',
      await pagina.$$eval('#filtroLugar select', x => x.map(s => s.dataset.dim)), ['delegacion', 'cliente']);
    await pagina.selectOption('#filtroLugar select[data-dim="delegacion"]', 'SEVILLA');
    await pagina.waitForFunction(() => document.querySelector('#centerFilterText').textContent !== 'Todos los centros');
    comprueba_que('elegir una delegacion marca sus centros en el filtro de centro',
      (await pagina.textContent('#centerFilterText')).includes('SAN PABLO'),
      await pagina.textContent('#centerFilterText'));
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nEl informe general operativo');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'direccion', perfil: 'Serunion', perfil_id: 'interno',
      sesiones: ['resumen', 'venta_consumo', 'disponibilidad', 'instalaciones'],
      catalogo_sesiones: { resumen: 'Resumen', venta_consumo: 'Venta y consumo', disponibilidad: 'Disponibilidad', instalaciones: 'Instalaciones y altas' } };
    const { pagina, errores, fuera } = await abre('/operativo/');
    await pagina.waitForSelector('#cuadros .cuadro');
    comprueba('arranca en ayer', await pagina.inputValue('#dia'), iso(AYER));
    comprueba('los nueve cuadrados, en su orden',
      await pagina.$$eval('#cuadros .cuadro', x => x.map(c => c.dataset.id)),
      ['rutas', 'averias', 'almacenes', 'furgonetas', 'pdvs', 'ventas', 'reposiciones', 'telemetria', 'tarifas']);
    comprueba('tarifas al 81,3 % en amarillo y lleva a su pagina',
      [await pagina.$eval('.cuadro[data-id="tarifas"]', c => c.classList.contains('amarillo')),
       await pagina.getAttribute('.cuadro[data-id="tarifas"]', 'href')], [true, '/tarifas/']);
    comprueba_que('y dice cuantos productos cobran su tarifa',
      (await pagina.textContent('.cuadro[data-id="tarifas"]')).includes('13 de 16 productos'));
    comprueba('el semaforo: rutas al 87,5 % en amarillo, averias en rojo, telemetria en verde',
      await pagina.$$eval('#cuadros .cuadro', x => x.filter(c => ['rutas', 'averias', 'telemetria'].includes(c.dataset.id))
        .map(c => ['verde', 'amarillo', 'rojo'].find(k => c.classList.contains(k)))),
      ['amarillo', 'rojo', 'verde']);
    comprueba('rutas lleva a su seccion del panel',
      await pagina.getAttribute('.cuadro[data-id="rutas"]', 'href'), '/panel/?ver=resumen#visitas_dia');
    comprueba_que('almacenes no tiene seccion todavia, y lo dice',
      (await pagina.evaluate(() => document.querySelector('.cuadro[data-id="almacenes"]').tagName)) === 'DIV'
      && (await pagina.textContent('.cuadro[data-id="almacenes"]')).includes('Sin sección todavía'));
    await pagina.selectOption('#dia', '2026-10-01');
    comprueba_que('un dia sin plan dice el motivo, no un cero',
      (await pagina.textContent('.cuadro[data-id="rutas"]')).includes('Falta el plan de visitas'));
    comprueba('y ese cuadrado no lleva color de semaforo',
      await pagina.$eval('.cuadro[data-id="rutas"]', c => c.classList.contains('sin')), true);
    await pagina.selectOption('#dia', iso(AYER));
    await Promise.all([pagina.waitForURL('**/panel/**'), pagina.click('.cuadro[data-id="averias"]')]);
    await pagina.waitForSelector('#rejilla .panel');
    comprueba('al pulsar averias, el panel abre filtrado en su seccion',
      await pagina.$$eval('#filtros button[aria-pressed="true"]', x => x.map(b => b.dataset.f)), ['disponibilidad']);
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nTarifas: delegaciones, centros, productos y el Excel del centro');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'direccion', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre('/tarifas/');
    await pagina.waitForSelector('#cuadros .cuadro');
    comprueba('un cuadrado por delegacion, con su semaforo',
      await pagina.$$eval('#cuadros .cuadro', x => x.map(c => [c.dataset.deleg, ['verde', 'amarillo', 'rojo'].find(k => c.classList.contains(k))])),
      [['Andalucía - Cádiz', 'rojo'], ['Madrid - Leganés', 'amarillo']]);
    comprueba_que('el total arriba', (await pagina.textContent('.cifra')).includes('81,3'));
    await pagina.click('#cuadros .cuadro[data-deleg="Andalucía - Cádiz"]');
    await pagina.waitForSelector('table .pct');
    comprueba('al pulsar la delegacion, sus centros', await pagina.$$eval('tbody tr td b', x => x.map(b => b.textContent)).then(x => x[0]), 'HOSPITAL DE JEREZ');
    comprueba_que('con el nivel de sus tarifas', (await pagina.textContent('tbody')).includes('Estándar'));
    await pagina.click('table .pct');
    await pagina.waitForSelector('#filas tr');
    comprueba_que('pide el centro al servidor', pedidos.includes('/api/tarifas?centro=114001'));
    comprueba('arranca en las incidencias: precio distinto y sin tarifa',
      await pagina.$$eval('#filas .etq', x => x.map(e => e.className.split(' ')[1])), ['no_coincide', 'sin_tarifa']);
    comprueba_que('el precio cobrado distinto sale marcado', (await pagina.textContent('#filas .precios .mal')).includes('1,30'));
    comprueba_que('el nombre del articulo va escapado', (await pagina.innerHTML('#filas')).includes('&lt;MIXTA&gt;'));
    await pagina.click('.filtros button[data-f="todos"]');
    comprueba('en «Todos», los cuatro', await pagina.locator('#filas tr').count(), 4);
    const [descarga] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('el Excel lleva el centro en el nombre', /^tarifas_114001_HOSPITAL_DE_JEREZ_\d{4}-\d\d-\d\d\.xlsx$/.test(descarga.suggestedFilename()), descarga.suggestedFilename());
    const bytes = fs.readFileSync(await descarga.path());
    const texto = bytes.toString('utf8');
    comprueba('es un zip', bytes.slice(0, 4).toString('hex'), '504b0304');
    comprueba_que('con sus cuatro hojas', ['Resumen', 'Precio distinto', 'Sin tarifa', 'Sin venta electrónica'].every(h => texto.includes(`name="${h}"`)));
    comprueba_que('la incidencia de precio: 1,20 de tarifa y 1,30 cobrado', texto.includes('<v>1.2</v>') && texto.includes('<v>1.3</v>'));
    comprueba_que('el producto sin tarifa, con lo que cobra hoy', texto.includes('<v>2.3</v>'));
    comprueba_que('y el texto escapado dentro del XML', texto.includes('ÑAMING ENSALADA &lt;MIXTA&gt; &amp; CO'));
    await pagina.goBack();
    await pagina.waitForSelector('table .pct');
    comprueba_que('volver atras vuelve a la delegacion', (await pagina.textContent('nav.miga')).includes('Andalucía - Cádiz'));
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  await navegador.close();
  servidor.close();
  console.log();
  if (fallos) { console.log(`${fallos} PRUEBAS FALLIDAS`); process.exit(1); }
  console.log('Las pantallas estan bien.');
})().catch(e => { console.error(e); process.exit(1); });
