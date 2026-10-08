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
  '/api/estado-carga': { ultima_carga: new Date().toISOString(), dias_pedidos: [iso(AYER)], descargas_ok: 75, descargas_fallidas: 0, bytes: 12345678, filas_por_informe: { visita_cabecera: 1000 }, errores: [], retraso_dias: 0 },
  '/api/admin/usuarios': { usuarios: [{ _id: 'eva@airbus.com', nombre: 'Eva', perfil_id: 'cli-airbus', estado: 'activo' }] },
  '/api/admin/perfiles': {
    perfiles: [{ _id: 'cli-airbus', nombre: 'AIRBUS', tipo: 'cliente', ambito: { centros: ['500092'] }, sesiones: ['resumen'], permisos: {}, panel: { existe: true, calculado: new Date().toISOString() } }],
    catalogo_sesiones: { resumen: { nombre: 'Resumen', minimo: 'cliente' } },
    techo: { cliente: ['ver'] }, niveles: { cliente: 0, admin: 3 }, implicitos: { cliente: ['ver'] }
  },
  '/api/admin/config': { asistente_global: true, limite_preguntas_dia: 40, umbral_rentabilidad_mes: 350 },
  '/api/admin/telefonos': { telefonos: [] },
  '/api/admin/cola': { cola: [] }
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
    incidencias: dias.map(d => [`${mes}-${String(d).padStart(2, '0')}`, '', 0, `A-${d}`, 'AVERIAS TECNICAS', 'TECNICO - No enfría', 'Finalizado']),
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
    maquinas_con_venta: 2, fuente: 'visita_ventas', bytes: 1000
  })),
  ventas: { fuente: 'visita_ventas', dias_telemetria: 0, dias_visita: 3, maquinas_censo: 2, maquinas_censo_con_venta: 2, _nota: 'parcial' },
  preventivos: null, _preventivos: 'no hay fuente'
};

const TIPOS = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8' };

const servidor = http.createServer((pet, res) => {
  const u = new URL(pet.url, 'http://x');
  const json = o => { res.writeHead(200, { 'content-type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(o)); };
  if (u.pathname.startsWith('/api/')) {
    pedidos.push(u.pathname + (u.search || ''));
    if (u.pathname === '/api/serie') {
      const mes = u.searchParams.get('mes');
      const interno = API['/api/yo'].tipo !== 'cliente';
      const suyos = k => interno || k !== '600';
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
      if (!mes) return json(INDICE_CUADRO);
      if (!CUADRO[mes]) { res.writeHead(400); return res.end('{"error":"mes"}'); }
      return json(CUADRO[mes]);
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
    await pagina.goto(base + ruta, { waitUntil: 'networkidle' });
    return { pagina, errores };
  }

  // ------------------------------------------------------- el panel de cliente
  console.log('\nEl panel de cliente');
  {
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
    comprueba_que('el cliente tiene filtro de centro', await pagina.isVisible('#filtroLugar select[data-dim="centro"]'));
    comprueba('pero no de delegacion, que es interna',
      await pagina.$$eval('#filtroLugar select[data-dim="delegacion"]', x => x.length), 0);
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

    // El ambito del perfil sugiere lo que hay en los datos mientras se escribe.
    await pagina.click('#pestanas button[data-s="perfiles"]');
    await pagina.click('[data-ed="cli-airbus"]');
    comprueba_que('el centro ya puesto se lee por su nombre',
      (await pagina.textContent('#rCentros')).includes('500092 AIRBUS SAN PABLO SUR'), await pagina.textContent('#rCentros'));
    await pagina.click('#fClientes');
    await pagina.keyboard.type('c');
    comprueba('una letra y salen los clientes que la llevan, el que empieza por ella primero (AIRBUS por su codigo C7)',
      await pagina.$$eval('#fClientesLista li span:first-child', x => x.map(l => l.textContent)), ['CONSUM', 'AIRBUS']);
    await pagina.keyboard.press('Backspace');
    await pagina.keyboard.type('air');
    comprueba('y filtra mientras se escribe',
      await pagina.$$eval('#fClientesLista li span:first-child', x => x.map(l => l.textContent)), ['AIRBUS']);
    await pagina.keyboard.press('Enter');
    comprueba('Intro lo pone sin guardar el perfil', [await pagina.inputValue('#fClientes'), await pagina.isVisible('#dlg')],
      ['AIRBUS, ', true]);
    comprueba_que('y dice con cuantos centros encaja', (await pagina.textContent('#rClientes')).includes('AIRBUS: 2 centros'));
    await pagina.click('#fCentros');
    await pagina.keyboard.press('End');
    await pagina.keyboard.type(', geta');
    await pagina.click('#fCentrosLista li:has-text("AIRBUS GETAFE")');
    comprueba('el centro se busca por nombre y se guarda su numero', await pagina.inputValue('#fCentros'), '500092, 500100, ');
    await pagina.click('#fDelegaciones');
    await pagina.keyboard.type('zz');
    comprueba_que('lo que no esta en los datos se dice', await pagina.isVisible('#fDelegacionesLista li.nada')
      && (await pagina.getAttribute('#rDelegaciones', 'class')).includes('mal'));
    await pagina.keyboard.press('Escape');
    comprueba('Escape cierra la lista y no el dialogo',
      [await pagina.isVisible('#fDelegacionesLista'), await pagina.isVisible('#dlg')], [false, true]);
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
    comprueba_que('y las fechas del filtro son las de ese mes',
      (await pagina.inputValue('#dateFrom')).startsWith(MES_HOY));
    // Los datos llegan hasta ayer: el resto del mes no son dias a cero, son
    // dias que no han llegado, y ni el filtro ni el grafico deben pintarlos.
    if (iso(AYER).startsWith(MES_HOY)) {
      comprueba('el hasta se queda en ayer, no en el fin de mes', await pagina.inputValue('#dateTo'), iso(AYER));
      const ultimaEtiqueta = await pagina.evaluate(() => [...document.querySelectorAll('#trendChart text')].map(t => t.textContent).filter(t => /^\d\d\/\d\d$/.test(t)).pop());
      comprueba('y el grafico acaba en ayer', ultimaEtiqueta, `${iso(AYER).slice(8, 10)}/${iso(AYER).slice(5, 7)}`);
    }

    await pagina.fill('.periodo-intervalo input[type=date]', '2025-03-01');
    await pagina.fill('.periodo-intervalo input[type=date] ~ label + input', '2025-03-31');
    await pagina.click('.periodo-aplicar');
    await pagina.waitForFunction(() => document.querySelector('#dateFrom').value === '2025-03-01');
    comprueba_que('elegir marzo de 2025 baja su mes', pedidos.includes('/api/cuadro?mes=2025-03'));
    comprueba('y mueve las fechas del filtro cruzado',
      [await pagina.inputValue('#dateFrom'), await pagina.inputValue('#dateTo')],
      ['2025-03-01', '2025-03-31']);
    comprueba_que('el cliente con un solo cliente no ve filtro de lugar en el cuadro',
      !(await pagina.isVisible('#filtroLugar select')));
    const tabla = await pagina.textContent('#visitLogTable');
    comprueba_que('la tabla de visitas ensena las de marzo de 2025', tabla.includes('2025'), tabla.slice(0, 120));
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
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

  await navegador.close();
  servidor.close();
  console.log();
  if (fallos) { console.log(`${fallos} PRUEBAS FALLIDAS`); process.exit(1); }
  console.log('Las tres pantallas estan bien.');
})().catch(e => { console.error(e); process.exit(1); });
