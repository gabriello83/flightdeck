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
    cuadrados: ['rutas', 'averias', 'devoluciones', 'almacenes', 'furgonetas', 'pdvs', 'ventas', 'reposiciones', 'telemetria', 'tarifas', 'revision', 'utilizo'],
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
            devoluciones: { mes: iso(AYER).slice(0, 7), hasta: iso(AYER), total: 518, mes_anterior: 569, sin_cerrar: 76, especiales: 92,
                            por_canal: [['En el sitio', 244], ['Transferencia', 181]] },
            tarifas: { pct: 81.3, color: 'amarillo', coinciden: 13, controlados: 16, sin_tarifa: 2, sin_dato_productos: 1, desde: '2026-04-14' },
            revision: { sin_planograma: 301, creados_ayer: 4, sin_tarifa: 1894, precio_distinto: 1541 },
            utilizo: { dia: iso(AYER), usuarios: 37, acciones: 4210, horas: 160 },
            almacenes: { valor: 502429.74, periodo: '2026-09', por_almacen: [{ almacen: 'A', delegacion: '', valor: 1 }] } }
  },
  // Los almacenes por dentro (docs/54), con la forma que escribe infra/almacenes.py.
  '/api/almacenes': {
    generado: new Date().toISOString(), umbral_pct: 15, periodo_cierre: '2026-09', maestro: true, fotos: true,
    avisos: [], total: { productos: 3, bajo_minimo: 1, sin_codigo_unidad: 1, sin_foto: 2, sin_pack: 1, almacenes: 2 },
    almacenes: [
      { almacen: 'Sevilla CECO L0K071', delegacion: 'Andalucia - Sevilla',
        resumen: { productos: 2, bajo_minimo: 1, sin_compra: 0, sin_foto: 1, sin_codigo_unidad: 1, sin_pack: 1 },
        productos: [
          { cod: '5322', nombre: 'AGUA FONT VELLA PET 50CL', existencias: 80, de: 'movimiento', fecha: iso(AYER),
            compra: { fecha: iso(AYER), cantidad: 600, proveedor: 'FONT VELLA', documento: 'Albarán de compra: 77' },
            pct: 13.3, bajo: true, categoria: 'Agua', unid_pack: 24, unid_caja: 24,
            ean_unidad: ['8410000000016'], otros_codigos: [{ codigo: '8410000000023', cantidad: 24 }], foto: true },
          { cod: '5961', nombre: 'AZUCAR 1KG', existencias: 100, de: 'movimiento', fecha: iso(AYER),
            compra: { fecha: iso(AYER), cantidad: 200, proveedor: 'AZUCARERA', documento: '' },
            pct: 50, bajo: false, categoria: '', unid_pack: null, unid_caja: 10,
            ean_unidad: [], otros_codigos: [{ codigo: '8410000000030', cantidad: 10 }], foto: false }] },
      { almacen: 'Madrid - Leganes CECO L0H036', delegacion: 'Madrid - Leganes',
        resumen: { productos: 1, bajo_minimo: 0, sin_compra: 1, sin_foto: 1, sin_codigo_unidad: 0, sin_pack: 0 },
        productos: [
          { cod: '119162', nombre: 'CAFE GARIBALDI ESPRESSO BAR 1000GR', existencias: 60, de: 'cierre', fecha: '2026-10-05',
            categoria: 'Café', unid_pack: 6, unid_caja: 6, ean_unidad: ['8000000000001'], otros_codigos: [], foto: false }] }]
  },
  // Las incidencias (docs/56), con la forma que escribe infra/incidencias.py.
  '/api/incidencias': (() => {
    const d = (n, h = '09:00') => `${iso(new Date(AYER.getTime() - n * 86400000))} ${h}`;
    return {
      generado: new Date().toISOString(), perfil: 'interno', estado_al_dia: true, sin_estado: null,
      fuente: 'M13 · EXT_SAT_INCIDENCIAS', ultimo_dia: iso(AYER), desde: '2026-01-26', horas_sla: 24,
      umbrales: { verde: 95, amarillo: 75 },
      marcas: { tecnica: 1, reposicion: 4, caducado: 8, higiene: 16, bloqueante: 32, especial: 64 },
      zonas: { 'Levante - Valencia': 'Levante', 'Madrid - Leganes': 'Centro', 'Levante - Murcia': 'Levante' },
      centros: [['500073', 'INDUSTRIA DEL CURTIDO', '32072', 'CURTIDO SA'], ['1001', 'AIRBUS GETAFE', 'C7', 'AIRBUS'],
                ['2002', 'CONSUM MURCIA', '10002', 'SERUNION']],
      delegaciones: ['Levante - Valencia', 'Madrid - Leganes', 'Levante - Murcia'],
      operaciones: [['T08', 'CAFÉ - Distribuidor fuera de servicio', 'AVERIAS TECNICAS'],
                    ['D01', 'DEVOLUCION - Transferencia Bancaria', 'Devolución dinero'],
                    ['S010', 'Reponer distribuidor automatico', 'Solicitudes cliente'],
                    ['T31', 'CAFÉ - Grupo café averiado', 'AVERIAS TECNICAS']],
      tecnicos: ['Javier', 'Miguel'],
      incidencias: [
        { n: 'A-7', a: d(35), x: d(35, '19:00'), h: 10, m: 'A1', c: 1, d: 1, o: 3, t: 1, f: 1 },
        { n: 'A-6', a: d(6), m: 'C1', c: 2, d: 2, o: 0, t: 1, f: 33, tx: 'fuera de servicio', u: 'Hall', p: 'C09' },
        { n: 'A-1', a: d(5), x: d(5, '14:00'), h: 5, m: 'M1', c: 0, d: 0, o: 0, t: 0, f: 33 },
        { n: 'A-2', a: d(4), x: d(3, '15:00'), h: 30, m: 'M1', c: 0, d: 0, o: 3, t: 0, f: 1 },
        { n: 'A-3', a: d(2), m: 'M1', c: 0, d: 0, o: 3, t: 0, f: 1, tx: 'no sale café · vuelve a fallar', u: 'Comedor', p: 'C01502' },
        { n: 'A-4', a: d(1), x: d(1, '11:00'), h: 2, m: 'A1', c: 1, d: 1, o: 3, t: 1, f: 1 },
        { n: 'E-5', a: d(0), m: 'C1', c: 2, d: 2, o: 2, t: 1, f: 68, tx: 'máquina vacía', u: 'Hall', p: 'C09' }]
    };
  })(),
  // Las furgonetas (docs/58), con la forma que escribe infra/operativo.py.
  '/api/furgonetas': (() => {
    const d = n => iso(new Date(AYER.getTime() - n * 86400000));
    return {
      generado: new Date().toISOString(), perfil: 'interno', ultimo_dia: d(0), desde: d(7),
      dias: [7, 6, 5, 4, 3, 2, 1, 0].map(d),
      umbrales_km: { min: 10, max: 400 },
      flota: [['1234ABC', 'CRAFTER - Ana', 'Madrid - Leganes'],
              ['5678DEF', 'JUMPER <Luis>', 'Andalucía - Málaga'],
              ['9999ZZZ', 'CADDY', 'Madrid - Leganes']],
      visitas: { '1234ABC': [d(7), d(0)], '5678DEF': [d(3)], '9999ZZZ': [] },
      km: { [d(0)]: { '1234ABC': [95, 1, ''], '5678DEF': [450, 2, ''], '9999ZZZ': [null, 1, 'sin anotar'] },
            [d(1)]: { '1234ABC': [5, 1, ''] } }
    };
  })(),
  // Utilizo (docs/60), con la forma que escribe infra/utilizo.py.
  '/api/utilizo': (() => {
    const d1 = iso(AYER), d2 = iso(new Date(AYER.getTime() - 86400000));
    // Un dia de hace mas de dos meses: llega sin su detalle, solo las cifras.
    const viejo = iso(new Date(AYER.getTime() - 100 * 86400000));
    const dia = (dia, acciones, horas, cuentas, por_hora, entidades) => ({ dia, acciones, horas, primera: '08:05:00', ultima: '17:40:10', cuentas, por_hora, entidades });
    return {
      generado: iso(new Date()), dias: [d1, d2, viejo], detalle_desde: iso(new Date(AYER.getTime() - 61 * 86400000)),
      personas: [
        { nombre: 'M. García', cuentas: ['M.GARCIA', 'M2.GARCIA'], dias: [
          dia(d1, 120, 6, ['M.GARCIA', 'M2.GARCIA'], { 8: 50, 9: 40, 17: 30 }, [['MaquinaCanal', 'U', 100], ['Maquina', 'I', 20]]),
          dia(d2, 30, 2, ['M.GARCIA'], { 10: 30 }, [['MaquinaCanal', 'U', 30]])] },
        { nombre: 'J. Marcos', cuentas: ['J.MARCOS', 'J2.MARCOS'], dias: [dia(d2, 15, 1, ['J2.MARCOS'], { 12: 15 }, [['Pdv', 'U', 15]])] },
        { nombre: 'A.PEREZ <X>', cuentas: ['A.PEREZ <X>'], dias: [dia(d1, 300, 8, ['A.PEREZ <X>'], { 9: 300 }, [['Pdv', 'D', 300]]),
          { dia: viejo, acciones: 40, horas: 3, primera: '09:00:00', ultima: '12:00:00', cuentas: ['A.PEREZ <X>'] }] }]
    };
  })(),
  // La revision de clientes (docs/59), con la forma que escribe infra/revision.py.
  '/api/revision': (() => {
    const sitio = (mat, d, cl, cli, ce, cen) => ({ matricula: mat, delegacion: d, cod_cliente: cl, cliente: cli,
      num_centro: ce, centro: cen, cod_pdv: 'P' + mat, ubicacion: 'Planta 1' });
    const v = (p, f = iso(AYER)) => ({ venta: { precio: p, fecha: f, fuente: 'telemetria' } });
    return {
      generado: new Date().toISOString(), creados_desde: iso(new Date(AYER.getTime() - 86400000)),
      zonas: { 'Andalucía - Sevilla': 'Sur', 'Madrid - Leganes': 'Centro' },
      sin_usuario: 'Quién lo creó todavía no se descarga de VenCloud: falta el informe con el usuario del planograma.',
      actividad: { grupos: [
        { nombre: 'M. García', cuentas: ['M.GARCIA', 'M2.GARCIA'], dias: [
          { dia: iso(AYER), acciones: 120, horas: 6, primera: '08:05:00', ultima: '17:40:10', cuentas: ['M.GARCIA', 'M2.GARCIA'],
            por_hora: { 8: 50, 9: 40, 17: 30 }, entidades: [['MaquinaCanal', 'U', 100], ['Maquina', 'I', 20]] }] },
        { nombre: 'J. Marcos', cuentas: ['J.MARCOS', 'J2.MARCOS'], dias: [] }] },
      sin_planograma: [
        { ...sitio('24SE0001', 'Andalucía - Sevilla', '10', 'AIRBUS <OPS>', '500092', 'AIRBUS GETAFE'), marcada: true, canales: 0 },
        { ...sitio('24SE0002', 'Madrid - Leganes', '20', 'CONSUM', '600', 'CONSUM MURCIA'), marcada: false, canales: 0 }],
      creados: [
        { ...sitio('24SE0003', 'Andalucía - Sevilla', '10', 'AIRBUS <OPS>', '500092', 'AIRBUS GETAFE'), dia: iso(AYER), detectado: iso(new Date()), canales: 24 },
        { ...sitio('24SE0004', 'Madrid - Leganes', '20', 'CONSUM', '600', 'CONSUM MURCIA'), dia: iso(new Date(AYER.getTime() - 86400000)), detectado: iso(AYER), canales: 30 }],
      sin_tarifa: [
        { ...sitio('24SE0005', 'Andalucía - Sevilla', '10', 'AIRBUS <OPS>', '500092', 'AIRBUS GETAFE'), subvencion: false,
          productos_total: 12, sin_tarifa: 2, nivel: 'estandar', niveles: { estandar: 9, pdv: 1 },
          estandar: [{ tarifa: 'AIRBUS OPERATIONS SLU', asignada: 'cliente', productos: 9 }],
          productos: [{ cod_articulo: '100', articulo: 'AGUA <0,5>', ultima_carga: iso(AYER), medios: { ef: v(0.9) } },
                      { cod_articulo: '101', articulo: 'KIT KAT', ultima_carga: iso(AYER), medios: {} }] },
        { ...sitio('24SE0006', 'Madrid - Leganes', '20', 'CONSUM', '600', 'CONSUM MURCIA'), subvencion: false,
          productos_total: 5, sin_tarifa: 5, nivel: null, niveles: {}, estandar: [],
          productos: [{ cod_articulo: '102', articulo: 'COCA-COLA', ultima_carga: iso(AYER), medios: { ef: v(1.6) } }] }],
      precio_distinto: [
        { ...sitio('24SE0007', 'Madrid - Leganes', '20', 'CONSUM', '600', 'CONSUM MURCIA'), subvencion: false,
          productos_total: 10, distintos: 2, comprobados: 8, max_diferencia: 0.15, nivel: 'centro', niveles: { centro: 10 }, estandar: [],
          productos: [
            { cod_articulo: '200', articulo: 'BOCADILLO', nivel: 'centro', tarifa: '', asignada: '', cambio_tarifa: '', diferencia: 0.15,
              medios: { ef: { tarifa: 2.2, ...v(2.35), ok: false }, tc: { tarifa: 2.2, ...v(2.2), ok: true } } },
            { cod_articulo: '201', articulo: 'ZUMO', nivel: 'centro', tarifa: '', asignada: '', cambio_tarifa: '', diferencia: -0.05,
              medios: { ef: { tarifa: 1.3, ...v(1.25), ok: false } } }] }]
    };
  })(),
  // Las devoluciones (docs/57), con la forma que escribe infra/devoluciones.py.
  '/api/devoluciones': (() => {
    const d = (n, h = '09:00') => `${iso(new Date(AYER.getTime() - n * 86400000))} ${h}`;
    return {
      generado: new Date().toISOString(), perfil: 'interno', ultimo_dia: iso(AYER),
      fuente: 'M13 · EXT_SAT_INCIDENCIAS', desde: iso(new Date(AYER.getFullYear(), AYER.getMonth() - 12, 1)),
      zonas: { 'Madrid - Leganes': 'Centro', 'Levante - Murcia': 'Levante' },
      centros: [['1001', 'AIRBUS GETAFE', 'C7', 'AIRBUS'], ['2002', 'CONSUM <MURCIA>', '10002', 'SERUNION']],
      delegaciones: ['Madrid - Leganes', 'Levante - Murcia'],
      canales: ['En el sitio', 'Transferencia', 'Tarjeta de crédito', 'Tarjeta de empleado', 'Otra'],
      origenes: ['Atención al cliente', 'Solicitud especial'],
      tecnicos: ['Javier', 'Miguel'],
      devoluciones: [
        { n: 'A-90', a: d(70), x: d(70, '10:00'), h: 1, m: 'M1', c: 0, d: 0, k: 0, t: 0 },
        { n: 'A-91', a: d(40), x: d(39, '09:00'), h: 24, m: 'M1', c: 0, d: 0, k: 1, t: 0 },
        { n: 'A-92', a: d(0, '08:00'), x: d(0, '10:00'), h: 2, m: 'M1', c: 0, d: 0, k: 0, t: 0 },
        { n: 'A-93', a: d(0, '11:00'), m: 'M1', c: 0, d: 0, k: 1, t: 1 },
        { n: 'A-94', a: d(0, '12:00'), x: d(0, '16:00'), h: 4, m: 'C1', c: 1, d: 1, k: 2, t: 1 },
        { n: 'E-97', a: d(0, '13:00'), x: d(0, '14:00'), h: 1, m: 'C1', c: 1, d: 1, k: 0, t: 1, e: 1 },
        { n: 'A-95', a: d(400), m: 'C1', c: 1, d: 1, k: 3, t: 1 },
        // De hoy: la foto ya la trae, pero las cifras llegan hasta ayer.
        { n: 'A-96', a: d(-1), m: 'M1', c: 0, d: 0, k: 1, t: 0 }]
    };
  })(),
  '/api/estado-carga': { ultima_carga: new Date().toISOString(), dias_pedidos: [iso(AYER)], descargas_ok: 75, descargas_fallidas: 0, bytes: 12345678, filas_por_informe: { visita_cabecera: 1000 }, errores: [], retraso_dias: 0 },
  '/api/admin/usuarios': { usuarios: [{ _id: 'eva@airbus.com', nombre: 'Eva', perfil_id: 'cli-airbus', estado: 'activo' }] },
  '/api/admin/perfiles': {
    perfiles: [{ _id: 'cli-airbus', nombre: 'AIRBUS', tipo: 'cliente', ambito: { centros: ['500092'] }, sesiones: ['resumen', 'cuadro'], permisos: {}, panel: { existe: true, calculado: new Date().toISOString() } }],
    catalogo_sesiones: { resumen: { nombre: 'Resumen', minimo: 'operaciones' }, cuadro: { nombre: 'Cuadro de mando', minimo: 'cliente' } },
    otras_pantallas: ['resumen', 'cuadro'],
    catalogo_cuadro: { indicadores: { nombre: 'Indicadores', flujos: ['ventas', 'visitas', 'incidencias'] },
                       articulos: { nombre: 'Mix de artículos', flujos: ['ventas'] },
                       listado_visitas: { nombre: 'Listado de visitas', flujos: ['visitas'] } },
    techo: { cliente: ['ver'] }, niveles: { cliente: 0, operaciones: 1, admin: 3 }, implicitos: { cliente: ['ver'] }
  },
  '/api/admin/config': { asistente_global: true, limite_preguntas_dia: 40, umbral_rentabilidad_mes: 350 },
  '/api/admin/telefonos': { telefonos: [] },
  '/api/admin/cola': { cola: [] },
  // Los ficheros de telemetria de la consola y su cruce (docs/53), con la forma
  // que escriben lambda_api.py y operativo.detalle_telemetria.
  '/api/admin/telemetria': {
    ficheros: { nayax: { _id: 'nayax', tipo: 'nayax', nombre: 'MachineStatus.xlsx', subido: new Date().toISOString(),
                         por: 'g@serunion.es', resumen: { filas: 2301, con_matricula: 2252, exportado: iso(HOY) } } },
    tipos: { nayax: 'Nayax', prodelfi: 'Prodelfi', nebula: 'Nebula (Coges)', grupos: 'Grupos de Prodelfi' }
  },
  '/api/telemetria': {
    generado: new Date().toISOString(), perfil: 'interno', ultimo_dia: iso(AYER),
    dias: {
      [iso(new Date(HOY.getTime() - 3 * 86400000))]: { venta: ['20SE0003'], dex: ['20SE0003'] },
      [iso(AYER)]: { venta: ['20SE0001', '20SE0002', '18CE4507'], dex: ['20SE0001'] }
    },
    ficheros: { ficheros: { nayax: { nombre: 'MachineStatus.xlsx', subido: new Date().toISOString(), resumen: { exportado: iso(HOY) } },
                            prodelfi: { nombre: 'Maquinas 1.xlsx', subido: new Date().toISOString(), resumen: {} } },
                faltan: ['nebula', 'grupos'] },
    maquinas: [
      { matricula: '20SE0001', sistema: 'nayax', tambien: [], delegacion: 'Cataluña', cliente: 'FUNDACIO PUIGVERT', num_centro: 100, centro: 'HOSPITAL', cod_pdv: 'P1', ubicacion: 'Hall', vencloud: true, nayax: { id: '20SE0001', ultima: `${iso(HOY)}T10:00:00` } },
      { matricula: '20SE0002', sistema: 'nayax', tambien: [], delegacion: 'Cataluña', cliente: 'FUNDACIO PUIGVERT', num_centro: 100, centro: 'HOSPITAL', cod_pdv: 'P2', ubicacion: 'Planta 1', vencloud: true, nayax: { id: '20SE0002', ultima: `${iso(HOY)}T09:00:00` } },
      { matricula: '20SE0003', sistema: 'nayax', tambien: [], delegacion: 'Cataluña', cliente: 'FUNDACIO PUIGVERT', num_centro: 100, centro: 'HOSPITAL', cod_pdv: 'P3', ubicacion: 'Urgencias', vencloud: false, nayax: { id: '20SE0003', ultima: '2026-10-01T09:00:00' } },
      { matricula: '18CE4507', sistema: 'prodelfi', tambien: ['nayax'], delegacion: 'Madrid', cliente: 'RTVE', num_centro: 200, centro: 'TORRESPAÑA', cod_pdv: 'P4', ubicacion: 'Planta 2', vencloud: true, prodelfi: { codigo: 4, grupo: 138, descripcion: 'CE4507 Torrespaña', como: 'tipo y número CE4507' }, nayax: { id: '18CE4507', ultima: '2026-10-01T09:00:00' } },
      { matricula: '24SE0777', sistema: 'solo_vencloud', tambien: [], vencloud: true, delegacion: 'Andalucía', cliente: 'AIRBUS', num_centro: 300, centro: 'SAN PABLO SUR', cod_pdv: 'P5', ubicacion: 'Comedor' }
    ],
    fuera: [{ sistema: 'nayax', id: '99XX9999', nombre: 'FANTASMA', detalle: 'Serunion / Sur', ultima: `${iso(HOY)}T10:00:00`, motivo: 'La matrícula 99XX9999 no está instalada en VenCloud.' }]
  }
};

// Rutas (docs/55), con la forma que escribe operativo.detalle_rutas: dos
// delegaciones ayer, y hace tres dias un festivo nacional con el plan entero.
const HACE3 = iso(new Date(HOY.getTime() - 3 * 86400000));
API['/api/rutas'] = {
  generado: new Date().toISOString(), perfil: 'interno', ultimo_dia: iso(AYER),
  umbrales: { verde: 95, amarillo: 75, festivo_bajo: 0.5 },
  festivos: { nacional: [HACE3], delegaciones: { 'Andalucía - Málaga': { ciudad: 'Málaga', comunidad: 'Andalucía', autonomico: [iso(AYER)], local: [] } }, nota: '' },
  dias: {
    [HACE3]: {
      visitas_deleg: { 'Madrid - Leganes': 3, 'Andalucía - Málaga': 40 },
      total: { previstas: 300, hechas: 20, pct: 6.7, color: 'rojo', fuera: 1, visitas: 43 },
      delegaciones: [
        { delegacion: 'Madrid - Leganes', previstas: 260, hechas: 2, fuera: 1, visitas: 3, pct: 0.8, color: 'rojo' },
        { delegacion: 'Andalucía - Málaga', previstas: 40, hechas: 18, fuera: 0, visitas: 40, pct: 45, color: 'rojo' }],
      rutas: [], no_visitados: [], fuera: []
    },
    [iso(AYER)]: {
      visitas_deleg: { 'Madrid - Leganes': 6, 'Andalucía - Málaga': 3 },
      total: { previstas: 8, hechas: 6, pct: 75, color: 'amarillo', fuera: 2, visitas: 9, vacio: 2 },
      delegaciones: [
        { delegacion: 'Madrid - Leganes', previstas: 6, hechas: 4, fuera: 2, vacio: 2, visitas: 6, pct: 66.7, color: 'rojo' },
        { delegacion: 'Andalucía - Málaga', previstas: 2, hechas: 2, fuera: 0, vacio: 0, visitas: 3, pct: 100, color: 'verde' }],
      rutas: [
        { delegacion: 'Andalucía - Málaga', ruta: 'Málaga 1', previstas: 2, hechas: 2, fuera: 0, vacio: 0, pct: 100, color: 'verde' },
        { delegacion: 'Madrid - Leganes', ruta: 'Ruta Getafe <Airbus>', previstas: 4, hechas: 2, fuera: 2, vacio: 2, pct: 50, color: 'rojo' },
        { delegacion: 'Madrid - Leganes', ruta: 'Ruta Leganés', previstas: 2, hechas: 2, fuera: 0, vacio: 0, pct: 100, color: 'verde' }],
      visitas: [
        ['PENDIENTE', 'P7', '19FP1530', 'Madrid - Leganes', 'Ruta Getafe <Airbus>', '1001', 'AIRBUS GETAFE', 'Planta 8', '', '', null],
        ['PENDIENTE', 'P8', '24CE4842', 'Madrid - Leganes', 'Ruta Getafe <Airbus>', '1002', 'AIRBUS ILLESCAS', '', '', '', null],
        ['HECHA', 'P1', '10CE5680', 'Andalucía - Málaga', 'Málaga 1', '2001', 'HOSPITAL MÁLAGA', 'Hall', '08:05', 'Luis Gil', 0],
        ['HECHA', 'P2', '10CE5681', 'Andalucía - Málaga', 'Málaga 1', '2001', 'HOSPITAL MÁLAGA', '', '08:20', 'Luis Gil', 0],
        ['HECHA', 'P3', '11AA0001', 'Madrid - Leganes', 'Ruta Getafe <Airbus>', '1001', 'AIRBUS GETAFE', '', '09:10', 'Ana Pérez', 1],
        ['HECHA', 'P4', '11AA0002', 'Madrid - Leganes', 'Ruta Getafe <Airbus>', '1001', 'AIRBUS GETAFE', '', '09:30', 'Ana Pérez', 0],
        ['HECHA', 'P5', '11AA0003', 'Madrid - Leganes', 'Ruta Leganés', '1004', 'HOSPITAL SEVERO OCHOA', '', '10:00', 'Rosa Gil', 0],
        ['HECHA', 'P6', '11AA0004', 'Madrid - Leganes', 'Ruta Leganés', '1004', 'HOSPITAL SEVERO OCHOA', '', '10:15', 'Rosa Gil', 0],
        ['FUERA DE RUTA', 'P9', '12BB0001', 'Madrid - Leganes', 'Ruta Getafe <Airbus>', '1001', 'AIRBUS GETAFE', '', '11:00', 'Ana Pérez', 1],
        ['FUERA DE RUTA', 'P10', '12BB0002', 'Madrid - Leganes', 'Ruta Getafe <Airbus>', '1003', 'CONSUM ALCORCÓN', '', '12:00', 'Ana Pérez', 0]]
    }
  },
  control_festivos: [
    { fecha: HACE3, delegacion: 'Andalucía - Málaga', festivo: 'nacional', estado: 'festivo_con_visitas', visitas: 40,
      normal: 39, previstas: 40, normal_previstas: 40, plan_sin_descontar: true },
    { fecha: HACE3, delegacion: 'Madrid - Leganes', festivo: 'nacional', estado: 'bien', visitas: 3,
      normal: 300, previstas: 260, normal_previstas: 300, plan_sin_descontar: true }]
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
    { matricula: '22SE1878', cod_pdv: 'S00742', ubicacion: '', subvencion: true, cod_articulo: '5322', articulo: 'AGUA 50CL',
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
  subvencion: 'Los puntos de venta con subvención en vigor van marcados.',
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

// Los preferidos del usuario de la prueba (docs/62), y los nombres que manda la API.
let PREFS = [];
const NOMBRES_TABLAS = {
  rutas: { nombre: 'Rutas', tablas: { rutas: 'Visitas por ruta', estado: 'Estado de las visitas',
    maquinas: 'Máquinas no visitadas', delegaciones: 'Por delegación', festivos: 'Festivos por delegación' } },
  averias: { nombre: 'Incidencias', tablas: { zonas: 'Total de incidencias por zona',
    tecnicas: 'Los 10 centros con más averías técnicas', abiertas: 'Lista de incidencias y su ficha' } },
  furgonetas: { nombre: 'Furgonetas', tablas: { vehiculos: 'Furgonetas activas', dias: 'Furgonetas con visitas, día a día' } },
  revision: { nombre: 'Revisión clientes', tablas: { planograma: 'Sin planograma', tarifa: 'Sin tarifa',
    precio: 'Precio distinto', creados: 'Planogramas creados', usuarios: 'García y Marcos' } },
  almacenes: { nombre: 'Almacenes', tablas: { productos: 'Productos de los almacenes' } }
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
    if (u.pathname === '/api/almacenes/foto') {
      // Un PNG de un pixel: lo que importa es que la pagina la pide aqui.
      res.writeHead(200, { 'content-type': 'image/png' });
      return res.end(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64'));
    }
    if (u.pathname === '/api/tarifas') {
      const c = u.searchParams.get('centro');
      if (c === null) return json(RESUMEN_TARIFAS);
      if (c !== CENTRO_TARIFAS.num_centro) { res.writeHead(400); return res.end('{"error":"Ese centro no está en las tarifas de este perfil."}'); }
      return json(CENTRO_TARIFAS);
    }
    if (u.pathname === '/api/preferidos') {
      // Como la API: los guarda y los devuelve, con los nombres de cada tabla.
      if (pet.method === 'PUT') {
        let b = '';
        pet.on('data', c => { b += c; });
        return pet.on('end', () => { PREFS = JSON.parse(b).preferidos; json({ preferidos: PREFS }); });
      }
      return json({ preferidos: PREFS, nombres: NOMBRES_TABLAS });
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

    // Los paneles que el administrador le quito a su perfil (docs/63).
    const todos = async () => {
      const x = await abre('/panel/');
      await x.pagina.waitForSelector('#rejilla .panel');
      const ids = await x.pagina.$$eval('#rejilla .panel', p => p.map(e => e.dataset.id));
      await x.pagina.close();
      return ids;
    };
    const conTodos = await todos();
    API['/api/yo'] = { ...API['/api/yo'], paneles_ocultos: ['centros', 'sat'] };
    const sinDos = await todos();
    comprueba_que('con paneles quitados no se dibujan',
      conTodos.includes('centros') && conTodos.includes('sat') && !sinDos.includes('centros') && !sinDos.includes('sat'),
      JSON.stringify(sinDos));
    comprueba('y los demas siguen', sinDos, conTodos.filter(i => i !== 'centros' && i !== 'sat'));
    delete API['/api/yo'].paneles_ocultos;
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
    await pagina.uncheck('#cajaSesiones input[value="cuadro"]');
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
    comprueba('los cuadrados en su orden, con Preferidos el primero',
      await pagina.$$eval('#cuadros .cuadro', x => x.map(c => c.dataset.id)),
      ['preferidos', 'rutas', 'averias', 'devoluciones', 'almacenes', 'furgonetas', 'pdvs', 'ventas', 'reposiciones', 'telemetria', 'tarifas', 'revision', 'utilizo']);
    comprueba('revision clientes: las maquinas sin planograma, sin semaforo, y lleva a su pagina',
      [(await pagina.textContent('.cuadro[data-id="revision"] .vl')).trim(),
       await pagina.$eval('.cuadro[data-id="revision"]', c => ['verde', 'amarillo', 'rojo'].some(k => c.classList.contains(k))),
       await pagina.getAttribute('.cuadro[data-id="revision"]', 'href')], ['301', false, '/revision/']);
    comprueba_que('y al lado los creados ayer, sin tarifa y precio distinto',
      (await pagina.textContent('.cuadro[data-id="revision"] .sub')).includes('4 creados ayer'));
    comprueba('utilizo: los usuarios del ultimo dia, y lleva a su pagina',
      [(await pagina.textContent('.cuadro[data-id="utilizo"] .vl')).trim(),
       await pagina.getAttribute('.cuadro[data-id="utilizo"]', 'href')], ['37', '/utilizo/']);
    comprueba('devoluciones: el total del mes, sin semaforo, y lleva a su pagina',
      [(await pagina.textContent('.cuadro[data-id="devoluciones"] .vl')).trim(),
       await pagina.$eval('.cuadro[data-id="devoluciones"]', c => ['verde', 'amarillo', 'rojo'].some(k => c.classList.contains(k))),
       await pagina.getAttribute('.cuadro[data-id="devoluciones"]', 'href')], ['518', false, '/devoluciones/']);
    comprueba_que('y lo compara con el mes anterior, y dice cuantas son especiales',
      (await pagina.textContent('.cuadro[data-id="devoluciones"] .sub')).includes('569 el mes anterior')
      && (await pagina.textContent('.cuadro[data-id="devoluciones"] .sub')).includes('92 de solicitudes especiales'));
    comprueba('tarifas al 81,3 % en amarillo y lleva a su pagina',
      [await pagina.$eval('.cuadro[data-id="tarifas"]', c => c.classList.contains('amarillo')),
       await pagina.getAttribute('.cuadro[data-id="tarifas"]', 'href')], [true, '/tarifas/']);
    comprueba_que('y dice cuantos productos cobran su tarifa',
      (await pagina.textContent('.cuadro[data-id="tarifas"]')).includes('13 de 16 productos'));
    comprueba('el semaforo: rutas al 87,5 % en amarillo, averias en rojo, telemetria en verde',
      await pagina.$$eval('#cuadros .cuadro', x => x.filter(c => ['rutas', 'averias', 'telemetria'].includes(c.dataset.id))
        .map(c => ['verde', 'amarillo', 'rojo'].find(k => c.classList.contains(k)))),
      ['amarillo', 'rojo', 'verde']);
    comprueba('rutas lleva a su pagina, con el dia',
      await pagina.getAttribute('.cuadro[data-id="rutas"]', 'href'), `/rutas/?dia=${iso(AYER)}`);
    comprueba('almacenes lleva a su pagina',
      await pagina.getAttribute('.cuadro[data-id="almacenes"]', 'href'), '/almacenes/');
    comprueba('furgonetas lleva a su pagina, con el dia',
      await pagina.getAttribute('.cuadro[data-id="furgonetas"]', 'href'), `/furgonetas/?dia=${iso(AYER)}`);
    comprueba('incidencias lleva a su pagina, con el dia',
      await pagina.getAttribute('.cuadro[data-id="averias"]', 'href'), `/incidencias/?dia=${iso(AYER)}`);
    comprueba('los que tienen pagina propia dicen Ver detalle',
      await pagina.$$eval('#cuadros .cuadro', x => x.filter(c => ['rutas', 'furgonetas', 'averias'].includes(c.dataset.id))
        .map(c => c.textContent.includes('Ver detalle'))), [true, true, true]);
    await pagina.selectOption('#dia', '2026-10-01');
    comprueba_que('un dia sin plan dice el motivo, no un cero',
      (await pagina.textContent('.cuadro[data-id="rutas"]')).includes('Falta el plan de visitas'));
    comprueba('y ese cuadrado no lleva color de semaforo',
      await pagina.$eval('.cuadro[data-id="rutas"]', c => c.classList.contains('sin')), true);
    await pagina.selectOption('#dia', iso(AYER));
    comprueba('el cuadrado de averias se llama Incidencias',
      await pagina.textContent('.cuadro[data-id="averias"] .et'), 'Incidencias');
    await Promise.all([pagina.waitForURL('**/incidencias/**'), pagina.click('.cuadro[data-id="averias"]')]);
    await pagina.waitForSelector('#kpis .kpi');
    comprueba_que('y al pulsarlo abre su pagina', pagina.url().includes('/incidencias/'), pagina.url());
    comprueba('en el dia del cuadrado, por la fecha de cierre', await pagina.inputValue('#periodo'), 'dia');
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

  console.log('\nLa telemetria cruzada con los ficheros (docs/53)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'admin', perfil: 'Serunion', perfil_id: 'interno',
      sesiones: ['resumen', 'instalaciones'], catalogo_sesiones: { resumen: 'Resumen', instalaciones: 'Instalaciones y altas' } };
    const op = API['/api/operativo'];
    const antes = JSON.stringify(op);
    // El dato sigue siendo el de VenCloud; los ficheros solo anaden las diferencias.
    op.dias[iso(AYER)].telemetria = { auditables: 2254, con_dex: 975, pct: 43.3, color: 'rojo',
      diferencias: { en_sistemas: 2504, sin_marca: 300, solo_vencloud: 20, fuera: 218 } };
    op.foto.telemetria = { ficheros: { nayax: { nombre: 'MachineStatus.xlsx' } }, faltan: [] };
    const { pagina, errores, fuera } = await abre('/operativo/');
    await pagina.waitForSelector('.cuadro[data-id="telemetria"]');
    comprueba('el cuadrado sigue con el DEX de VenCloud, en rojo',
      [(await pagina.textContent('.cuadro[data-id="telemetria"] .vl')).trim(),
       await pagina.$eval('.cuadro[data-id="telemetria"]', c => c.classList.contains('rojo'))], ['43,3 %', true]);
    const sub = await pagina.textContent('.cuadro[data-id="telemetria"] .sub');
    comprueba_que('y debajo las diferencias con los ficheros',
      sub.includes('975 de 2254') && sub.includes('538 diferencias con Nayax, Prodelfi y Nebula'));
    comprueba('lleva a la pagina de telemetria, con el dia',
      await pagina.getAttribute('.cuadro[data-id="telemetria"]', 'href'), `/telemetria/?dia=${iso(AYER)}`);
    comprueba_que('y dice Ver detalle, no Ver seccion: es su pagina',
      (await pagina.textContent('.cuadro[data-id="telemetria"]')).includes('Ver detalle'));
    await Promise.all([pagina.waitForURL('**/telemetria/**'), pagina.click('.cuadro[data-id="telemetria"]')]);
    await pagina.waitForSelector('#tabla table');
    comprueba('pestañas: Nayax, Prodelfi, solo en VenCloud y las que no estan en VenCloud',
      await pagina.$$eval('#pestanas button', x => x.map(b => b.dataset.p)), ['nayax', 'prodelfi', 'solo_vencloud', 'fuera']);
    comprueba('Nayax: las que tienen alguna diferencia ayer',
      await pagina.$$eval('#tabla tbody tr td:first-child', x => x.map(t => t.textContent.trim())), ['20SE0002', '20SE0003']);
    comprueba_que('con el ultimo dia que si mando', (await pagina.textContent('#tabla tbody tr:nth-child(2)')).match(/\d+ \w+/));
    comprueba_que('y dice que fichero falta', (await pagina.textContent('#ficheros')).includes('Falta Nebula (Coges), Grupos de Prodelfi'));
    await pagina.selectOption('#filtro', 'sin_marca');
    comprueba('sin telemetria en VenCloud: la que Nayax tiene y VenCloud no marca',
      await pagina.$$eval('#tabla tbody tr td:first-child', x => x.map(t => t.textContent.trim())), ['20SE0003']);
    await pagina.selectOption('#filtro', 'todas');
    comprueba('todas: las tres', await pagina.locator('#tabla tbody tr').count(), 3);
    await pagina.fill('#busca', 'urgencias');
    comprueba('el buscador', await pagina.locator('#tabla tbody tr').count(), 1);
    await pagina.fill('#busca', '');
    await pagina.click('#pestanas button[data-p="fuera"]');
    comprueba_que('las de Nayax que no estan en VenCloud, con el motivo',
      (await pagina.textContent('#tabla')).includes('no está instalada en VenCloud'));
    const [descarga] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bCsv')]);
    comprueba('el CSV de la pestaña', descarga.suggestedFilename(), `telemetria_fuera_${iso(AYER)}.csv`);
    await pagina.setViewportSize({ width: 380, height: 800 });
    await pagina.click('#pestanas button[data-p="nayax"]');
    comprueba('en movil no se sale de la pantalla',
      await pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await pagina.emulateMedia({ colorScheme: 'dark' });
    comprueba_que('en oscuro el fondo es oscuro',
      (await pagina.evaluate(() => getComputedStyle(document.body).backgroundColor)) === 'rgb(18, 18, 17)');
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();

    const c = await abre('/consola/');
    await c.pagina.waitForSelector('#pestanas button[data-s="telemetria"]');
    await c.pagina.click('#pestanas button[data-s="telemetria"]');
    await c.pagina.waitForSelector('#bTele');
    comprueba_que('la consola dice que fichero hay y cuales faltan',
      (await c.pagina.textContent('#vista')).includes('MachineStatus.xlsx')
      && (await c.pagina.textContent('#vista')).includes('Falta: Prodelfi, Nebula (Coges), Grupos de Prodelfi'));
    comprueba('ni una peticion fuera del dominio', c.fuera, []);
    comprueba('sin un solo error en la consola del navegador', c.errores, []);
    await c.pagina.close();
    Object.assign(op, JSON.parse(antes));
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nLos almacenes por dentro');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'direccion', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre('/almacenes/');
    await pagina.waitForSelector('#filas tr[data-cod]');
    comprueba('todos los almacenes: los tres productos, el bajo minimo primero',
      await pagina.$$eval('#filas tr[data-cod]', x => x.map(t => t.dataset.cod)), ['5322', '5961', '119162']);
    comprueba('el bajo minimo va marcado',
      await pagina.$$eval('#filas tr.bajo', x => x.map(t => t.dataset.cod)), ['5322']);
    comprueba_que('con su porcentaje de la ultima compra',
      (await pagina.textContent('tr[data-cod="5322"]')).includes('13 %'));
    comprueba('la foto se pide a la API del mismo dominio',
      await pagina.getAttribute('tr[data-cod="5322"] img.foto', 'src'), '/api/almacenes/foto?art=5322');
    comprueba_que('el azucar sin codigo de la unidad, y lo dice',
      (await pagina.textContent('tr[data-cod="5961"]')).includes('Sin código de unidad'));
    comprueba_que('las unidades por pack, y los packs que hay',
      (await pagina.textContent('tr[data-cod="5322"]')).includes('3 packs de 24'));
    comprueba_que('el cafe sin compra lo dice, sin porcentaje inventado',
      (await pagina.textContent('tr[data-cod="119162"]')).includes('Sin compra en la ventana'));
    await pagina.click('#resumen button[data-f="sin_codigo"]');
    comprueba('el filtro de sin codigo de la unidad',
      await pagina.$$eval('#filas tr[data-cod]', x => x.map(t => t.dataset.cod)), ['5961']);
    await pagina.click('#resumen button[data-f="bajo"]');
    comprueba('el de bajo minimo',
      await pagina.$$eval('#filas tr[data-cod]', x => x.map(t => t.dataset.cod)), ['5322']);
    await pagina.click('#resumen button[data-f="todos"]');
    await pagina.selectOption('#almacen', 'Madrid - Leganes CECO L0H036');
    comprueba('un almacen solo ensena lo suyo',
      await pagina.$$eval('#filas tr[data-cod]', x => x.map(t => t.dataset.cod)), ['119162']);
    await pagina.selectOption('#almacen', '');
    await pagina.fill('#buscar', '8410000000016');
    comprueba('se busca por EAN',
      await pagina.$$eval('#filas tr[data-cod]', x => x.map(t => t.dataset.cod)), ['5322']);
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();

    // Sin el maestro de articulos no se ensena a nadie «sin codigo»: se dice que falta.
    const antes = API['/api/almacenes'];
    API['/api/almacenes'] = { ...antes, maestro: false, fotos: false,
      avisos: ['Falta el maestro de artículos de VenCloud (M8 · EXT_MAESTRO_ARTICULOS): sin él no hay unidades por pack ni códigos de barras.'],
      almacenes: antes.almacenes.map(a => ({ ...a, productos: a.productos.map(p => {
        const q = { ...p, foto: false }; ['unid_pack', 'unid_caja', 'ean_unidad', 'otros_codigos', 'categoria'].forEach(k => delete q[k]); return q; }) })) };
    const b = await abre('/almacenes/');
    await b.pagina.waitForSelector('#filas tr[data-cod]');
    comprueba_que('sin maestro lo dice arriba', (await b.pagina.textContent('#avisos')).includes('M8 · EXT_MAESTRO_ARTICULOS'));
    comprueba('y no hay filtro de sin codigo',
      await b.pagina.$$eval('#resumen button', x => x.map(t => t.dataset.f)), ['todos', 'bajo']);
    comprueba_que('ni nadie sale sin codigo', !(await b.pagina.textContent('#filas')).includes('Sin código de unidad'));
    comprueba('sin un solo error en la consola del navegador', b.errores, []);
    await b.pagina.close();
    API['/api/almacenes'] = antes;
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nRutas: delegaciones, rutas, puntos de venta y festivos (docs/55)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre(`/rutas/?dia=${iso(AYER)}`);
    await pagina.waitForSelector('#tDeleg table');
    comprueba('arranca en el dia que trae la direccion', await pagina.inputValue('#dia'), iso(AYER));
    comprueba('los seis indicadores del Power BI, en su orden',
      await pagina.$$eval('#kpis .kpi .et', x => x.map(e => e.textContent.trim())),
      ['Visitas pendientes', 'Cumplimiento de ruta', 'Visitas en ruta', 'Visitas efectuadas',
       'Visitas no planificadas', 'Pasaje vacío']);
    comprueba('las cifras: 2 pendientes, 75 % en amarillo, 8, 6, 2 y 2',
      [await pagina.$$eval('#kpis .kpi .vl', x => x.map(e => e.textContent.trim())),
       await pagina.$eval('#kpis .kpi:nth-child(2)', k => k.classList.contains('amarillo'))],
      [['2', '75 %', '8', '6', '2', '2'], true]);
    comprueba('las dos delegaciones', await pagina.$$eval('#tDeleg tbody tr', x => x.map(t => t.dataset.d)),
      ['Madrid - Leganes', 'Andalucía - Málaga']);
    comprueba('las tres rutas, con el nombre escapado', await pagina.locator('#tRutas tbody tr').count(), 3);
    comprueba_que('sin colar HTML del nombre', (await pagina.textContent('#tRutas')).includes('Ruta Getafe <Airbus>'));
    comprueba('la matriz: Getafe 2 hechas, 2 pendientes, 2 fuera, 6 en total',
      await pagina.$$eval('#tRutas tbody tr', x => {
        const t = x.find(r => r.textContent.includes('Getafe'));
        return [...t.querySelectorAll('td.n')].slice(0, 4).map(c => c.textContent.trim()); }),
      ['2', '2', '2', '6']);
    comprueba('el donut con los tres estados', await pagina.locator('#dona svg circle').count(), 3);
    comprueba('maquinas no visitadas: las dos de Getafe', await pagina.locator('#tPdv tbody tr').count(), 2);
    comprueba_que('con matricula y ubicacion', (await pagina.textContent('#tPdv')).includes('19FP1530')
      && (await pagina.textContent('#tPdv')).includes('Planta 8'));
    await pagina.click('#tRutas tbody tr[data-r$="Ruta Leganés"]');
    comprueba('al pulsar una ruta, todo se filtra a ella',
      [await pagina.inputValue('#deleg'), await pagina.locator('#tRutas tbody tr').count(),
       (await pagina.textContent('#kpis .kpi:nth-child(2) .vl')).trim(),
       (await pagina.textContent('#tPdv')).includes('Ninguna')],
      ['Madrid - Leganes', 1, '100 %', true]);
    await pagina.selectOption('#ruta', '');
    await pagina.click('#tDeleg tbody tr[data-d="Andalucía - Málaga"]');
    comprueba('al pulsar una delegacion, se filtra todo',
      [await pagina.inputValue('#deleg'), await pagina.locator('#tRutas tbody tr').count(),
       (await pagina.textContent('#tPdv')).includes('Ninguna')], ['Andalucía - Málaga', 1, true]);
    await pagina.click('#tDeleg tbody tr[data-d="Andalucía - Málaga"]');
    comprueba('y al volver a pulsarla, todas', await pagina.inputValue('#deleg'), '');
    await pagina.click('#pestanas button[data-p="vacio"]');
    comprueba('pasaje vacio: las dos, resaltadas', await pagina.locator('#tPdv tbody tr.vacio').count(), 2);
    await pagina.click('#pestanas button[data-p="fuera"]');
    comprueba_que('fuera de plan, con el reponedor', (await pagina.textContent('#tPdv')).includes('Ana Pérez'));
    await pagina.fill('#busca', 'consum');
    comprueba('el buscador', await pagina.locator('#tPdv tbody tr').count(), 1);
    const [descarga] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bCsv')]);
    comprueba('el CSV', descarga.suggestedFilename(), `rutas_fuera_${iso(AYER)}.csv`);
    comprueba_que('el control de festivos marca el festivo con visitas de dia normal',
      (await pagina.textContent('#tFest')).includes('Visitas de día normal')
      && (await pagina.textContent('#tFest')).includes('sin descontar'));
    comprueba_que('el autonomico de la delegacion sale en su fila', (await pagina.textContent('#tDeleg')).includes('festivo autonómico'));
    await pagina.selectOption('#dia', HACE3);
    comprueba_que('un festivo lo dice arriba', !(await pagina.$eval('#festivoDia', n => n.hidden))
      && (await pagina.textContent('#festivoDia')).includes('festivo nacional'));
    await pagina.fill('#busca', '');
    await pagina.click('#pestanas button[data-p="hechas"]');
    comprueba_que('y de un dia calculado antes, sin hechas en la lista, lo dice',
      (await pagina.textContent('#tPdv')).includes('antes de que la lista'));
    comprueba('sin pasaje vacio en ese dia, sin dato y no un cero',
      (await pagina.textContent('#kpis .kpi:nth-child(6) .vl')).trim(), 'Sin dato');
    await pagina.setViewportSize({ width: 380, height: 800 });
    comprueba('en movil no se sale de la pantalla',
      await pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await pagina.emulateMedia({ colorScheme: 'dark' });
    comprueba_que('en oscuro el fondo es oscuro',
      (await pagina.evaluate(() => getComputedStyle(document.body).backgroundColor)) === 'rgb(18, 18, 17)');
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nLas incidencias, como el Power BI (docs/56)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre('/incidencias/');
    await pagina.waitForSelector('#kpis .kpi');
    comprueba('arranca en los ultimos 3 meses: el ano no esta entero', await pagina.inputValue('#periodo'), 'tres');
    const kpi = async i => pagina.$eval(`#kpis .kpi:nth-child(${i}) .vl`, e => e.textContent);
    comprueba('siete incidencias, sin el preventivo que la noche ya quito', await kpi(1), '7');
    comprueba('tasa de resolucion: 4 de 7', await kpi(2), '57,1 %');
    comprueba('SLA: 3 de las 4 cerradas en menos de 24 h', await kpi(4), '75 %');
    comprueba('y en amarillo, como el cuadrado', await pagina.$eval('#kpis .kpi:nth-child(4)', e => e.className), 'kpi amarillo');
    comprueba('el centro con mas averias tecnicas va primero',
      await pagina.$eval('#gTecnicas .fb .nom', e => e.textContent), 'INDUSTRIA DEL CURTIDO');
    comprueba('y sin el grafico de devoluciones', await pagina.locator('#gDevol').count(), 0);
    await pagina.click('#gZonas .fb[data-d="Levante - Murcia"]');
    comprueba('pulsar una delegacion filtra por ella', [await pagina.inputValue('#deleg'), await kpi(1)], ['Levante - Murcia', '2']);
    await pagina.click('#bLimpiar');
    await pagina.selectOption('#estado', 'abierta');
    comprueba('solo las abiertas: la tasa no aplica', [await kpi(1), await kpi(2)], ['3', '—']);
    await pagina.selectOption('#estado', '');
    await pagina.click('.hojas button[data-h="abiertas"]');
    await pagina.waitForSelector('#tarjetas .kpi');
    comprueba('las seis tarjetas', await pagina.$$eval('#tarjetas .kpi .vl', x => x.map(e => e.textContent)),
      ['2', '1', '0', '0', '1', '1']);
    comprueba('la que lleva mas dias, sin vender y de Serunion va primero',
      await pagina.$$eval('#tLista tr.elige .mat', x => x.filter((_, i) => i % 2 === 0).map(e => e.textContent)), ['A-6', 'A-3']);
    comprueba_que('la maquina critica va marcada', (await pagina.textContent('#tLista')).includes('crítica'));
    await pagina.click('#tLista tr.elige:nth-child(2)');
    comprueba_que('la ficha ensena sus notas', (await pagina.textContent('#ficha')).includes('vuelve a fallar'));
    await pagina.click('#tarjetas button[data-t="criticas"]');
    comprueba('maquinas criticas: las tres averias de M1',
      await pagina.$$eval('#tLista tr.elige .mat', x => x.filter((_, i) => i % 2 === 0).map(e => e.textContent)).then(l => l.sort()),
      ['A-1', 'A-2', 'A-3']);
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();

    // Desde el cuadrado del informe general llega con ?dia=: las tecnicas
    // cerradas ese dia, lo mismo que cuenta el cuadrado.
    {
      const dia = n => iso(new Date(AYER.getTime() - n * 86400000));
      const c = await abre(`/incidencias/?dia=${dia(1)}`);
      await c.pagina.waitForSelector('#kpis .kpi');
      const k = async i => c.pagina.$eval(`#kpis .kpi:nth-child(${i}) .vl`, e => e.textContent);
      comprueba('con ?dia= abre en ese dia, por cierre', [await c.pagina.inputValue('#periodo'), await c.pagina.inputValue('#dia')], ['dia', dia(1)]);
      comprueba('una tecnica cerrada ese dia, en 2 h: SLA 100 %', [await k(1), await k(4)], ['1', '100 %']);
      comprueba_que('y dice que es lo que cuenta el cuadrado', (await c.pagina.textContent('#rango')).includes('cuadrado del informe general'));
      await c.pagina.fill('#dia', dia(3));
      await c.pagina.dispatchEvent('#dia', 'change');
      comprueba('otro dia: la de 30 h, fuera de SLA', [await k(1), await k(4)], ['1', '0 %']);
      comprueba('sin un solo error en la consola del navegador', c.errores, []);
      await c.pagina.close();
    }

    // Sin M13 no se ensena un estado que no se sabe: se dice por que.
    const antes = API['/api/incidencias'];
    API['/api/incidencias'] = { ...antes, estado_al_dia: false, fuente: 'D7 · EXT_SAT_AVERIAS y D8 · EXT_SAT_EVENTOS',
      sin_estado: 'Falta el informe M13 · EXT_SAT_INCIDENCIAS de VenCloud (docs/17).',
      incidencias: antes.incidencias.map(r => { const q = { ...r }; ['x', 'h', 'tx', 'u', 'p'].forEach(k => delete q[k]); return q; }) };
    const b = await abre('/incidencias/?ver=abiertas');
    await b.pagina.waitForSelector('#tarjetas .kpi');
    comprueba_que('sin M13 lo dice arriba', (await b.pagina.textContent('#notaEstado')).includes('M13'));
    comprueba('las abiertas sin dato, las criticas si', await b.pagina.$$eval('#tarjetas .kpi .vl', x => x.map(e => e.textContent)),
      ['—', '—', '—', '—', '—', '1']);
    await b.pagina.click('.hojas button[data-h="panel"]');
    comprueba('el total si, la tasa no', [await b.pagina.$eval('#kpis .kpi:nth-child(1) .vl', e => e.textContent),
      await b.pagina.$eval('#kpis .kpi:nth-child(2) .vl', e => e.textContent)], ['7', '—']);
    comprueba('sin un solo error en la consola del navegador', b.errores, []);
    await b.pagina.close();
    API['/api/incidencias'] = antes;
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nLas furgonetas (docs/58)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre(`/furgonetas/?dia=${iso(AYER)}`);
    await pagina.waitForSelector('#kpis .kpi');
    comprueba('arranca en el dia que llega', await pagina.inputValue('#dia'), iso(AYER));
    const kpi = async i => pagina.$eval(`#kpis .kpi:nth-child(${i}) .vl`, e => e.textContent);
    const mats = () => pagina.$$eval('#tabla tbody tr .mat', x => x.map(e => e.textContent));
    comprueba('activas, con visitas, sin visitas y km en rojo', [await kpi(1), await kpi(2), await kpi(3), await kpi(4)],
      ['3', '1', '2', '2']);
    comprueba('toda la flota, la que lleva mas dias sin visitar primero', await mats(), ['9999ZZZ', '5678DEF', '1234ABC']);
    comprueba('desde cuantos dias no visita',
      await pagina.$$eval('#tabla tbody tr td:nth-child(5)', x => x.map(e => e.textContent)),
      ['Más de 7 días', '3 días', 'Visitó']);
    comprueba_que('el nombre del vehiculo se escapa', (await pagina.textContent('#tabla')).includes('JUMPER <Luis>'));
    comprueba('los km de los ultimos 7 dias, el elegido el ultimo',
      await pagina.$$eval('#tabla tbody tr:last-child td.km', x => x.map(e => e.textContent)),
      ['s/d', 's/d', 's/d', 's/d', 's/d', '5', '95']);
    comprueba('en rojo menos de 10, mas de 400 y la jornada sin km; 95 no',
      await pagina.$$eval('#tabla tbody tr', x => x.map(f => f.querySelector('td.km.hoy span').className)),
      ['falta', 'fuera', '']);
    comprueba('y el 5 de antes de ayer tambien',
      await pagina.$eval('#tabla tbody tr:last-child td.km:nth-last-child(2) span', e => e.className), 'fuera');
    await pagina.selectOption('#ver', 'sin');
    comprueba('solo las que no visitaron ese dia', await mats(), ['9999ZZZ', '5678DEF']);
    await pagina.selectOption('#ver', '');
    await pagina.selectOption('#deleg', 'Andalucía - Málaga');
    comprueba('la delegacion filtra la lista y las cifras', [await mats(), await kpi(1), await kpi(4)], [['5678DEF'], '1', '1']);
    await pagina.selectOption('#deleg', '');
    await pagina.selectOption('#dia', iso(new Date(AYER.getTime() - 3 * 86400000)));
    comprueba('otro dia: la ultima visita es la de ese dia o antes',
      await pagina.$$eval('#tabla tbody tr td:nth-child(5)', x => x.map(e => e.textContent)),
      ['Más de 4 días', '4 días', 'Visitó']);
    comprueba('el dia a dia, de la flota, hasta el dia elegido', await pagina.$$eval('#dias .fb', x => x.length), 5);
    await pagina.selectOption('#dia', iso(AYER));
    await pagina.setViewportSize({ width: 380, height: 800 });
    comprueba('en movil no se sale de la pantalla',
      await pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await pagina.emulateMedia({ colorScheme: 'dark' });
    comprueba_que('en oscuro el fondo es oscuro',
      (await pagina.evaluate(() => getComputedStyle(document.body).backgroundColor)) === 'rgb(18, 18, 17)');
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nLa revision de clientes (docs/59)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre('/revision/');
    await pagina.waitForSelector('.kpi');
    const kpis = async () => pagina.$$eval('.kpi[data-t] .vl', x => x.map(e => e.textContent));
    // El cambio de tabla va por el hash: hay que esperar a que se pinte.
    const tabla = async t => { await pagina.click(`.kpi[data-t="${t}"]`);
      await pagina.waitForSelector(`.kpi[data-t="${t}"][aria-pressed="true"]`); };
    const maquina = async sel => { await pagina.click(sel); await pagina.waitForSelector('#volver'); };
    const volver = async () => { await pagina.click('#volver'); await pagina.waitForSelector('#volverArea'); };
    // Primero un cuadrado por area; pulsando, sus maquinas por delegacion.
    const area = async a => { await pagina.click(`.area[data-a="${a}"]`); await pagina.waitForSelector('#volverArea'); };
    const areas = async () => { await pagina.click('#volverArea'); await pagina.waitForSelector('.area'); };
    const textos = async sel => pagina.$$eval(sel, x => x.map(e => e.textContent.replace(/\s+/g, ' ').trim()));
    const filasMaq = '#tabla tbody tr:not(.grupo)';
    comprueba('las cuentas: sin planograma, sin tarifa, precio distinto, creados el ultimo dia y acciones de Garcia y Marcos',
      (await kpis()).slice(0, 5), ['2', '2', '1', '1', '120']);
    comprueba('arranca en las sin planograma, un cuadrado por area con sus maquinas',
      [await textos('.area .et'), await textos('.area .vl')], [['Centro', 'Sur'], ['1', '1']]);
    await area('Sur');
    comprueba('pulsando el area, sus maquinas', await textos(`${filasMaq} td:first-child`), ['24SE0001']);
    comprueba('por delegacion, con su cabecera', await textos('#tabla tr.grupo'), ['Andalucía - Sevilla · 1 máquina']);
    comprueba_que('el cliente va escapado', (await pagina.innerHTML('#tabla')).includes('AIRBUS &lt;OPS&gt;'));
    await areas();
    await pagina.selectOption('#fDeleg', 'Madrid - Leganes');
    await pagina.waitForSelector('#tabla tr.grupo');
    comprueba('la delegacion filtra las cuatro, no la actividad', await kpis(), ['1', '1', '1', '1', '120']);
    comprueba('y con una delegacion elegida va directo a su lista', await textos(`${filasMaq} td:first-child`), ['24SE0002']);
    comprueba('y el cliente solo ofrece los de esa delegacion',
      await pagina.$$eval('#fCliente option', x => x.map(o => o.value)), ['', '20']);
    await pagina.click('#bLimpiar');
    await pagina.waitForFunction(() => document.querySelector('#fDeleg').value === '');
    await tabla('tarifa');
    comprueba_que('sin tarifa: por area, con los productos', (await textos('.area .nt')).includes('máquinas en 1 delegación · 2 productos sin tarifa'),
      await textos('.area .nt'));
    const [d1] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('el Excel de la tabla', /^revision_sin_tarifa_todas_\d{4}-\d\d-\d\d\.xlsx$/.test(d1.suggestedFilename()), d1.suggestedFilename());
    const t1 = fs.readFileSync(await d1.path()).toString('utf8');
    comprueba_que('con las maquinas y sus productos', t1.includes('name="Máquinas"') && t1.includes('name="Productos sin tarifa"') && t1.includes('COCA-COLA'));
    await area('Centro');
    comprueba_que('la que no tiene ninguna tarifa lo dice', (await pagina.textContent('#tabla')).includes('Ninguna tarifa'));
    const [d1b] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('el Excel del area, con el area en el nombre', /^revision_sin_tarifa_Centro_/.test(d1b.suggestedFilename()), d1b.suggestedFilename());
    await areas();
    await area('Sur');
    comprueba_que('la tarifa estandar va señalada, con su tabla y a quien esta asignada',
      (await pagina.locator(filasMaq).first().textContent()).includes('AIRBUS OPERATIONS SLU · asignada al cliente')
      && await pagina.locator(`${filasMaq} .etq.estandar`).count() === 1);
    await maquina('#tabla .mat[data-m="24SE0005"]');
    comprueba('pulsando la matricula, sus productos sin tarifa',
      await pagina.$$eval('#vista tbody tr', x => x.length), 2);
    comprueba_que('con lo que cobra hoy', (await pagina.textContent('#vista tbody')).includes('0,90'));
    const [d2] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('y su Excel, con la matricula en el nombre', /^revision_sin_tarifa_24SE0005_/.test(d2.suggestedFilename()), d2.suggestedFilename());
    await volver();
    await tabla('precio');
    await area('Centro');
    comprueba('precio distinto: cuantos productos y la diferencia maxima',
      await textos(`${filasMaq} td.n`), ['2de 8 comprobados', '+0,15 €']);
    await maquina('#tabla .mat');
    comprueba('pulsando, los productos con su diferencia, la mayor primero',
      await textos('#vista tbody tr td.n'), ['+0,15 €', '-0,05 €']);
    const [d3] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    const t3 = fs.readFileSync(await d3.path()).toString('utf8');
    comprueba_que('el Excel lleva solo los medios que no cuadran', t3.includes('<v>2.35</v>') && !t3.includes('Tarjeta crédito</t>'));
    await volver();
    await tabla('creados');
    comprueba('los creados, del ultimo dia', await pagina.$$eval('#tabla tbody tr td:first-child', x => x.map(e => e.textContent)), ['24SE0003']);
    comprueba_que('y dice que el usuario aun no llega', (await pagina.textContent('#tabla')).includes('falta el informe con el usuario'));
    await pagina.selectOption('#fDia', iso(new Date(AYER.getTime() - 86400000)));
    await pagina.waitForFunction(() => location.hash.includes('dia='));
    comprueba('el dia anterior', await pagina.$$eval('#tabla tbody tr td:first-child', x => x.map(e => e.textContent)), ['24SE0004']);
    await tabla('usuarios');
    comprueba('Garcia y Marcos, con sus dos cuentas', await textos('.persona h3'), ['M. García', 'J. Marcos']);
    comprueba('las acciones, las horas y de que hora a que hora', await textos('.persona:first-child .cifras b'),
      ['120', '6', '08:05 – 17:40']);
    comprueba('que toco, con la accion en castellano', await textos('.persona:first-child tbody td'),
      ['MaquinaCanal', 'Cambio', '100', 'Maquina', 'Alta', '20']);
    comprueba_que('el que no hizo nada lo dice', (await pagina.textContent('.persona:nth-child(2)')).includes('Ninguna acción'));
    comprueba('sin los filtros de delegacion', await pagina.$eval('#barra', e => e.hidden), true);
    const [d4] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('y su Excel', /^revision_garcia_marcos_/.test(d4.suggestedFilename()), d4.suggestedFilename());
    await pagina.setViewportSize({ width: 380, height: 800 });
    comprueba('en movil no se sale de la pantalla',
      await pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await pagina.emulateMedia({ colorScheme: 'dark' });
    comprueba_que('en oscuro el fondo es oscuro',
      (await pagina.evaluate(() => getComputedStyle(document.body).backgroundColor)) === 'rgb(18, 18, 17)');
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nUtilizo (docs/60)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'admin', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre('/utilizo/');
    await pagina.waitForSelector('#tabla tbody tr');
    const textos = async sel => pagina.$$eval(sel, x => x.map(e => e.textContent.replace(/\s+/g, ' ').trim()));
    const viejoMes = API['/api/utilizo'].dias[2].slice(0, 7);
    comprueba('el ultimo dia: usuarios, acciones y horas', await textos('.kpi .vl'), ['2', '420', '14']);
    comprueba('todos los usuarios, el que mas primero', await textos('#tabla tbody tr td:first-child .mat'), ['A.PEREZ <X>', 'M. García']);
    comprueba_que('el nombre va escapado', (await pagina.innerHTML('#tabla')).includes('A.PEREZ &lt;X&gt;'));
    comprueba_que('Garcia, con sus dos cuentas juntas', (await pagina.textContent('#tabla')).includes('M.GARCIA + M2.GARCIA'));
    await pagina.fill('#fBusca', 'garcia');
    await pagina.waitForFunction(() => document.querySelectorAll('#tabla tbody tr').length === 1);
    comprueba('buscar, sin tildes', await textos('#tabla tbody tr td:first-child .mat'), ['M. García']);
    const [d1] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('el Excel del dia', /^utilizo_\d{4}-\d\d-\d\d\.xlsx$/.test(d1.suggestedFilename()), d1.suggestedFilename());
    const t1 = fs.readFileSync(await d1.path()).toString('utf8');
    comprueba_que('con el dia, que toco y la historia', t1.includes('name="Día"') && t1.includes('name="Qué tocó"') && t1.includes('name="Día a día"'));
    await pagina.click('#tabla .mat');
    await pagina.waitForSelector('#miga:not([hidden])');
    comprueba('pulsando, su detalle: veinticuatro horas', await pagina.locator('.horas span').count(), 24);
    comprueba('y su historia mes a mes: los dos dias suman 150',
      (await textos('#mesames tbody tr td:nth-child(2)')).reduce((a, t) => a + Number(t.replace(/\./g, '')), 0), 150);
    await pagina.selectOption('#fDia', iso(new Date(AYER.getTime() - 86400000)));
    await pagina.waitForFunction(() => document.querySelector('.persona-cab b') && document.querySelector('.persona-cab b').textContent === '30');
    comprueba_que('el otro dia, con una sola cuenta', (await pagina.textContent('#vista')).includes('Sólo trabajó con M.GARCIA'));
    const [d2] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('y su Excel', /^utilizo_M_Garcia_/.test(d2.suggestedFilename()), d2.suggestedFilename());
    await pagina.click('#volver');
    await pagina.waitForSelector('#miga[hidden]', { state: 'attached' });
    await pagina.fill('#fBusca', '');
    await pagina.waitForFunction(() => !location.hash.includes('q='));
    await pagina.selectOption('#fPer', 'mes');
    await pagina.waitForSelector('#lMes:not([hidden])');
    await pagina.selectOption('#fMes', viejoMes);
    await pagina.waitForFunction(m => location.hash.includes('mes=' + m), viejoMes);
    comprueba('un mes de hace tiempo: el usuario con sus cifras', await textos('#tabla tbody tr td:first-child .mat'), ['A.PEREZ <X>']);
    comprueba_que('y dice que no hay detalle', (await pagina.textContent('#tabla tbody')).includes('sin detalle'));
    const [d3] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bExcel')]);
    comprueba_que('el Excel del mes', d3.suggestedFilename() === `utilizo_${viejoMes}.xlsx`, d3.suggestedFilename());
    await pagina.click('#tabla .mat');
    await pagina.waitForSelector('#miga:not([hidden])');
    comprueba_que('su mes, sin detalle, lo dice', (await pagina.textContent('#vista')).includes('dos últimos meses'));
    await pagina.click('#volver');
    await pagina.waitForSelector('#miga[hidden]', { state: 'attached' });
    await pagina.setViewportSize({ width: 380, height: 800 });
    comprueba('en movil no se sale de la pantalla',
      await pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await pagina.emulateMedia({ colorScheme: 'dark' });
    comprueba_que('en oscuro el fondo es oscuro',
      (await pagina.evaluate(() => getComputedStyle(document.body).backgroundColor)) === 'rgb(18, 18, 17)');
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  console.log('\nLas devoluciones (docs/57)');
  {
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno' };
    const { pagina, errores, fuera } = await abre('/devoluciones/');
    await pagina.waitForSelector('#kpis .kpi');
    comprueba('arranca en el mes corriente, como el cuadrado', await pagina.inputValue('#periodo'), 'mes');
    const kpi = async i => (await pagina.$eval(`#kpis .kpi:nth-child(${i}) .vl`, e => e.textContent)).trim();
    comprueba('las cuatro de ayer, una sin cerrar', [await kpi(1), await kpi(2)], ['4', '1']);
    comprueba('la mediana hasta cerrar: 1, 2 y 4 horas, 2', await kpi(3), '2 h');
    comprueba('por origen: tres de atencion al cliente y una especial',
      await pagina.$$eval('#gOrigen .fb', x => x.map(e => [e.dataset.o, e.querySelector('.v').textContent.split(' ')[0]])),
      [['Atención al cliente', '3'], ['Solicitud especial', '1']]);
    await pagina.click('#gOrigen .fb[data-o="Solicitud especial"]');
    comprueba('pulsar el origen filtra por el', [await pagina.inputValue('#origen'), await kpi(1)], ['Solicitud especial', '1']);
    await pagina.click('#bLimpiar');
    comprueba_que('sin cerrar hoy cuenta tambien la vieja', (await pagina.textContent('#kpis .kpi:nth-child(2)')).includes('3 en total hoy'));
    comprueba('un mes por columna, trece', await pagina.locator('#gMeses .golpe').count(), 13);
    comprueba('la leyenda con los canales que hay', await pagina.$$eval('#leyenda span', x => x.map(e => e.textContent)),
      ['En el sitio', 'Transferencia', 'Tarjeta de crédito']);
    await pagina.hover('#gMeses .golpe[data-i="12"]');
    comprueba_que('pasar por encima dice el reparto del mes', !(await pagina.$eval('#punta', e => e.hidden))
      && (await pagina.textContent('#punta')).includes('Transferencia'));
    comprueba_que('y el mes llega hasta ayer, como las cifras: tres, sin la de hoy',
      (await pagina.textContent('#punta')).endsWith('Total4'), await pagina.textContent('#punta'));
    await pagina.click('#bVista');
    comprueba('y la misma cifra en tabla', await pagina.locator('#tMeses tbody tr').count(), 13);
    await pagina.click('#bVista');
    comprueba('por canal', await pagina.$$eval('#gCanal .fb .nom', x => x.map(e => e.textContent)),
      ['En el sitio', 'Transferencia', 'Tarjeta de crédito']);
    comprueba_que('el nombre del centro va escapado', (await pagina.innerHTML('#tCentros')).includes('CONSUM &lt;MURCIA&gt;'));
    await pagina.click('#gCanal .fb[data-k="Transferencia"]');
    comprueba('pulsar un canal filtra por el', [await pagina.inputValue('#canal'), await kpi(1)], ['Transferencia', '1']);
    await pagina.click('#bLimpiar');
    await pagina.click('#tCentros tr[data-c="1001"]');
    comprueba('pulsar un centro filtra por el', [await pagina.inputValue('#centro'), await kpi(1)], ['1001', '2']);
    await pagina.click('#bLimpiar');
    await pagina.click('.hojas button[data-h="pendientes"]');
    comprueba('sin cerrar: las tres, tambien la de hoy, la mas vieja primero',
      await pagina.$$eval('#tLista tbody .mat', x => x.filter((_, i) => i % 2 === 0).map(e => e.textContent)), ['A-95', 'A-93', 'A-96']);
    const [descarga] = await Promise.all([pagina.waitForEvent('download'), pagina.click('#bCsv')]);
    comprueba('el CSV', descarga.suggestedFilename(), `devoluciones_sin_cerrar_${iso(AYER)}.csv`);
    await pagina.click('.hojas button[data-h="panel"]');
    await pagina.setViewportSize({ width: 380, height: 800 });
    await pagina.waitForTimeout(250);
    comprueba('en movil no se sale de la pantalla',
      await pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    await pagina.emulateMedia({ colorScheme: 'dark' });
    comprueba_que('en oscuro el fondo es oscuro',
      (await pagina.evaluate(() => getComputedStyle(document.body).backgroundColor)) === 'rgb(18, 18, 17)');
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();

    // Sin M13 no se cuenta nada: se dice por que.
    const antes = API['/api/devoluciones'];
    API['/api/devoluciones'] = { generado: antes.generado, perfil: 'interno', ultimo_dia: iso(AYER),
      sin_dato: 'Falta el informe M13 · EXT_SAT_INCIDENCIAS de VenCloud (docs/17).', devoluciones: [] };
    const b = await abre('/devoluciones/');
    await b.pagina.waitForSelector('#aviso:not([hidden])');
    comprueba_que('sin M13 lo dice', (await b.pagina.textContent('#aviso')).includes('M13'));
    comprueba('sin un solo error en la consola del navegador', b.errores, []);
    await b.pagina.close();
    API['/api/devoluciones'] = antes;
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  // ------------------------------------ cuadrados y tablas por usuario
  console.log('\nCuadrados y tablas por usuario (docs/61)');
  {
    const FOTOS = process.env.FOTOS_USUARIOS;
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'admin', perfil: 'Serunion', perfil_id: 'interno' };
    const antesU = API['/api/admin/usuarios'], antesP = API['/api/admin/perfiles'];
    API['/api/admin/usuarios'] = { usuarios: [...antesU.usuarios,
      { _id: 'olga@serunion.es', nombre: 'Olga', perfil_id: 'ope-sur', estado: 'activo',
        cuadrados_ocultos: ['devoluciones'], tablas_ocultas: { rutas: ['festivos'] } }] };
    API['/api/admin/perfiles'] = { ...antesP,
      perfiles: [...antesP.perfiles, { _id: 'ope-sur', nombre: 'Operaciones Sur', tipo: 'operaciones',
        ambito: { delegaciones: ['SEVILLA'] }, sesiones: ['resumen'], permisos: {},
        cuadrados: ['rutas', 'averias', 'devoluciones', 'furgonetas', 'ventas'] }],
      catalogo_cuadrados: {
        rutas: { nombre: 'Rutas', tablas: { rutas: 'Visitas por ruta', estado: 'Estado de las visitas',
          maquinas: 'Máquinas no visitadas', delegaciones: 'Por delegación', festivos: 'Festivos por delegación' } },
        averias: { nombre: 'Incidencias', tablas: { zonas: 'Total de incidencias por zona',
          tecnicas: 'Los 10 centros con más averías técnicas', abiertas: 'Lista de incidencias y su ficha' } },
        devoluciones: { nombre: 'Devoluciones', tablas: { meses: 'Devoluciones por mes y canal', pendientes: 'Devoluciones sin cerrar' } },
        furgonetas: { nombre: 'Furgonetas', tablas: { vehiculos: 'Furgonetas activas', dias: 'Furgonetas con visitas, día a día' } },
        ventas: { nombre: 'Ventas', tablas: {} } } };
    const { pagina, errores, fuera } = await abre('/consola/');
    await pagina.waitForSelector('[data-ed="olga@serunion.es"]');
    comprueba_que('la lista de usuarios dice lo que se le ha quitado',
      (await pagina.textContent('body')).includes('4 de 5 cuadrados · 1 tabla quitada'));
    comprueba_que('y a quien no se le quita nada, que no tiene cuadrados (cliente)',
      (await pagina.textContent('tr:has-text("eva@airbus.com")')).includes('—'));
    await pagina.click('[data-ed="olga@serunion.es"]');
    comprueba_que('al editarla salen los cuadrados de su perfil', await pagina.isVisible('#campoCuadrados'));
    comprueba('con lo quitado sin marcar, y las tablas del quitado apagadas',
      await pagina.$$eval('#cajaCuadrados fieldset', fs => fs.map(f => [f.dataset.c,
        f.querySelector('input[data-cuadrado]').checked,
        [...f.querySelectorAll('input[data-tabla]')].filter(i => !i.checked || i.disabled).map(i => i.value)])),
      [['rutas', true, ['festivos']], ['averias', true, []], ['devoluciones', false, ['meses', 'pendientes']],
       ['furgonetas', true, []], ['ventas', true, []]]);
    comprueba_que('un cuadrado de una sola tabla lo dice',
      (await pagina.textContent('#cajaCuadrados fieldset[data-c="ventas"]')).includes('Una sola tabla'));
    await pagina.uncheck('#cajaCuadrados fieldset[data-c="furgonetas"] input[data-cuadrado]');
    comprueba('quitar el cuadrado apaga sus tablas',
      await pagina.$$eval('#cajaCuadrados fieldset[data-c="furgonetas"] input[data-tabla]', x => x.map(i => i.disabled)),
      [true, true]);
    await pagina.check('#cajaCuadrados fieldset[data-c="devoluciones"] input[data-cuadrado]');
    await pagina.uncheck('#cajaCuadrados fieldset[data-c="averias"] input[value="abiertas"]');
    if (FOTOS) {
      await pagina.screenshot({ path: path.join(FOTOS, 'consola-claro.png'), fullPage: false });
      await pagina.emulateMedia({ colorScheme: 'dark' });
      await pagina.screenshot({ path: path.join(FOTOS, 'consola-oscuro.png'), fullPage: false });
      await pagina.emulateMedia({ colorScheme: 'light' });
    }
    await pagina.setViewportSize({ width: 380, height: 800 });
    await pagina.waitForTimeout(200);
    comprueba('en movil el dialogo no se sale de la pantalla',
      await pagina.evaluate(() => document.querySelector('#dlg').scrollWidth <= window.innerWidth), true);
    if (FOTOS) await pagina.screenshot({ path: path.join(FOTOS, 'consola-movil.png'), fullPage: false });
    await pagina.setViewportSize({ width: 1280, height: 800 });
    const envio = new Promise(r => pagina.on('request', q => {
      if (q.method() === 'POST' && q.url().endsWith('/api/admin/usuarios')) r(JSON.parse(q.postData()));
    }));
    await pagina.click('#bGuardar');
    const cuerpo = await envio;
    comprueba('se guarda lo que se le quita', [cuerpo.cuadrados_ocultos, cuerpo.tablas_ocultas],
      [['furgonetas'], { rutas: ['festivos'], averias: ['abiertas'] }]);
    await pagina.waitForSelector('[data-ed="olga@serunion.es"]');
    await pagina.click('[data-ed="olga@serunion.es"]');
    await pagina.selectOption('#fPerfil', 'cli-airbus');
    comprueba_que('un perfil de cliente no tiene cuadrados que quitar', !(await pagina.isVisible('#campoCuadrados')));
    comprueba('ni una peticion fuera del dominio', fuera, []);
    comprueba('sin un solo error en la consola del navegador', errores, []);
    await pagina.close();
    API['/api/admin/usuarios'] = antesU;

    // Al crear un perfil, el cuadro de mando de los clientes se enciende o se
    // apaga (docs/63), y el personal se elige cuadrado a cuadrado, con sus
    // tablas, sin sesiones que agrupen varios (docs/64).
    API['/api/admin/perfiles'] = { ...antesP, niveles: { cliente: 0, operaciones: 1, direccion: 2, admin: 3 },
      catalogo_sesiones: {
        resumen: { nombre: 'Resumen', minimo: 'operaciones', bloques: ['servicio', 'dinero'],
          paneles: { visitas_dia: 'Visitas por día', semana: 'Patrón semanal' } },
        avisos: { nombre: 'Avisos y acciones', minimo: 'operaciones', bloques: ['alarmas'], paneles: {} },
        instalaciones: { nombre: 'Instalaciones y altas', minimo: 'operaciones', bloques: ['instalaciones'], paneles: {} },
        cuadro: { nombre: 'Cuadro de mando', minimo: 'cliente', bloques: [], paneles: {} } },
      otras_pantallas: ['resumen', 'avisos', 'cuadro'],
      catalogo_cuadrados: {
        rutas: { nombre: 'Rutas', bloque: 'servicio', paneles: {},
          tablas: { rutas: 'Visitas por ruta', estado: 'Estado de las visitas', maquinas: 'Máquinas no visitadas' } },
        almacenes: { nombre: 'Almacenes', bloque: 'inventario', solo_direccion: true, paneles: {}, tablas: { productos: 'Productos' } },
        ventas: { nombre: 'Ventas', bloque: 'dinero', tablas: {},
          paneles: { recaudacion: 'Recaudación por mes', ciego: 'Efectivo sin telemetría' } },
        telemetria: { nombre: 'Telemetría', bloque: 'instalaciones', paneles: {}, tablas: { maquinas: 'Máquinas' } },
        revision: { nombre: 'Revisión clientes', bloque: 'instalaciones', paneles: {},
          tablas: { planograma: 'Sin planograma', tarifa: 'Sin tarifa', precio: 'Precio distinto' } },
        utilizo: { nombre: 'Utilizo', bloque: 'instalaciones', solo_direccion: true, sin_ambito: true, paneles: {},
          tablas: { uso: 'Uso de VenCloud' } } } };
    {
      const c = await abre('/consola/');
      await c.pagina.waitForSelector('#pestanas button[data-s="perfiles"]');
      await c.pagina.click('#pestanas button[data-s="perfiles"]');
      comprueba_que('la lista dice si el cliente tiene el cuadro',
        (await c.pagina.textContent('tr:has-text("cli-airbus")')).includes('Cuadro de mando'));
      await c.pagina.click('#bNuevoPerfil');
      comprueba('un cliente nuevo trae el cuadro encendido, con sus partes, y sin cuadrados',
        [await c.pagina.isVisible('#fCuadroOn'), await c.pagina.isChecked('#fCuadroOn'),
         await c.pagina.isVisible('#campoCuadro'), await c.pagina.isVisible('#campoSesiones')],
        [true, true, true, false]);
      await c.pagina.uncheck('#fCuadroOn');
      comprueba_que('apagado, no hay partes que elegir', !(await c.pagina.isVisible('#campoCuadro')));
      if (FOTOS) await c.pagina.screenshot({ path: path.join(FOTOS, 'perfil-cliente-sin-cuadro.png'), fullPage: false });
      await c.pagina.fill('#fPid', 'cli-prueba');
      await c.pagina.fill('#fNombreP', 'Prueba');
      let envio = new Promise(r => c.pagina.on('request', q => {
        if (q.method() === 'POST' && q.url().endsWith('/api/admin/perfiles')) r(JSON.parse(q.postData()));
      }));
      await c.pagina.click('#bGuardar');
      const cli = await envio;
      comprueba('se guarda sin la sesion del cuadro y sin cuadrados', [cli.sesiones, 'cuadrados' in cli], [[], false]);

      await c.pagina.waitForSelector('#bNuevoPerfil');
      await c.pagina.click('#bNuevoPerfil');
      await c.pagina.selectOption('#fTipo', 'operaciones');
      comprueba_que('el personal no tiene el interruptor del cliente', !(await c.pagina.isVisible('#fCuadroOn')));
      comprueba('cada cuadrado por separado, en el orden del informe',
        await c.pagina.$$eval('#cajaSesiones input[data-cuadrado]', x => x.map(i => i.value)),
        ['rutas', 'almacenes', 'ventas', 'telemetria', 'revision', 'utilizo']);
      comprueba('y aparte, lo que no es un cuadrado',
        await c.pagina.$$eval('#cajaSesiones input[data-sesion]', x => x.map(i => i.value)),
        ['resumen', 'avisos', 'cuadro']);
      comprueba_que('ninguna casilla agrupa cuadrados',
        !(await c.pagina.textContent('#cajaSesiones')).includes('Instalaciones y altas'));
      comprueba('almacenes y utilizo son de direccion: apagados en operaciones',
        await c.pagina.$$eval('#cajaSesiones input[data-cuadrado]:disabled', x => x.map(i => i.value)), ['almacenes', 'utilizo']);
      comprueba('sin marcar, sus tablas apagadas',
        await c.pagina.$$eval('fieldset[data-c="revision"] input[data-tabla]', x => x.every(i => i.disabled)), true);
      await c.pagina.check('#cajaSesiones input[data-cuadrado][value="revision"]');
      comprueba('marcado, sus tablas, todas puestas',
        await c.pagina.$$eval('fieldset[data-c="revision"] input[data-tabla]', x => x.map(i => [i.value, i.checked, i.disabled])),
        [['planograma', true, false], ['tarifa', true, false], ['precio', true, false]]);
      await c.pagina.uncheck('fieldset[data-c="revision"] input[value="precio"]');
      await c.pagina.check('#cajaSesiones input[data-cuadrado][value="ventas"]');
      comprueba('ventas lleva al panel: dentro, sus paneles',
        await c.pagina.$$eval('fieldset[data-c="ventas"] input[data-panel]', x => x.map(i => i.value)), ['recaudacion', 'ciego']);
      await c.pagina.uncheck('fieldset[data-c="ventas"] input[value="ciego"]');
      await c.pagina.selectOption('#fTipo', 'direccion');
      comprueba('cambiar de tipo no pierde lo marcado',
        [await c.pagina.isChecked('#cajaSesiones input[data-cuadrado][value="revision"]'),
         await c.pagina.isChecked('fieldset[data-c="revision"] input[value="precio"]'),
         await c.pagina.isEnabled('#cajaSesiones input[data-cuadrado][value="utilizo"]')], [true, false, true]);
      await c.pagina.check('#cajaSesiones input[data-cuadrado][value="utilizo"]');
      await c.pagina.check('#cajaSesiones input[data-sesion][value="avisos"]');
      if (FOTOS) {
        await c.pagina.evaluate(() => document.querySelector('#campoSesiones').scrollIntoView());
        await c.pagina.screenshot({ path: path.join(FOTOS, 'perfil-cuadrados-claro.png'), fullPage: false });
        await c.pagina.emulateMedia({ colorScheme: 'dark' });
        await c.pagina.screenshot({ path: path.join(FOTOS, 'perfil-cuadrados-oscuro.png'), fullPage: false });
        await c.pagina.emulateMedia({ colorScheme: 'light' });
      }
      await c.pagina.setViewportSize({ width: 380, height: 800 });
      await c.pagina.waitForTimeout(200);
      comprueba('en movil el dialogo no se sale de la pantalla',
        await c.pagina.evaluate(() => document.querySelector('#dlg').scrollWidth <= window.innerWidth), true);
      if (FOTOS) {
        await c.pagina.evaluate(() => document.querySelector('#campoSesiones').scrollIntoView());
        await c.pagina.screenshot({ path: path.join(FOTOS, 'perfil-cuadrados-movil.png'), fullPage: false });
      }
      await c.pagina.setViewportSize({ width: 1280, height: 800 });
      await c.pagina.fill('#fPid', 'dir-prueba');
      await c.pagina.fill('#fNombreP', 'Prueba');
      envio = new Promise(r => c.pagina.on('request', q => {
        if (q.method() === 'POST' && q.url().endsWith('/api/admin/perfiles')) r(JSON.parse(q.postData()));
      }));
      await c.pagina.click('#bGuardar');
      const cuerpo = await envio;
      comprueba('se guardan los cuadrados, sus tablas y paneles quitados, y las otras pantallas',
        [cuerpo.cuadrados, cuerpo.tablas_ocultas, cuerpo.paneles_ocultos, cuerpo.sesiones],
        [['ventas', 'revision', 'utilizo'], { revision: ['precio'] }, ['ciego'], ['avisos']]);
      comprueba('ni una peticion fuera del dominio', c.fuera, []);
      comprueba('sin un solo error en la consola del navegador', c.errores, []);
      await c.pagina.close();
    }
    API['/api/admin/perfiles'] = antesP;

    // Las paginas, con lo que el administrador le quito a este usuario.
    const conQuitadas = async (ruta, tablas, espera) => {
      API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno',
                         tablas_ocultas: tablas };
      const x = await abre(ruta);
      await x.pagina.waitForSelector(espera);
      return x;
    };
    let x = await conQuitadas('/rutas/', { rutas: ['maquinas', 'estado'] }, '#todo:not([hidden])');
    comprueba('rutas: sin las maquinas ni la dona, con lo demas',
      await x.pagina.$$eval('[data-tabla]', s => s.map(e => [e.dataset.tabla, !e.hidden])),
      [['rutas', true], ['estado', false], ['maquinas', false], ['delegaciones', true], ['festivos', true]]);
    comprueba_que('la de rutas ocupa la fila entera',
      await x.pagina.evaluate(() => getComputedStyle(document.querySelector('.dos')).gridTemplateColumns.split(' ').length === 1));
    if (FOTOS) await x.pagina.screenshot({ path: path.join(FOTOS, 'rutas-sin-maquinas.png'), fullPage: true });
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();
    x = await conQuitadas('/incidencias/', { averias: ['abiertas'] }, '#todo:not([hidden])');
    comprueba('incidencias: sin la lista no hay hojas, y queda el panel',
      [await x.pagina.isVisible('.hojas'), await x.pagina.isVisible('#hPanel'), await x.pagina.isVisible('#hAbiertas')],
      [false, true, false]);
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();
    x = await conQuitadas('/incidencias/?ver=abiertas', { averias: ['abiertas'] }, '#todo:not([hidden])');
    comprueba('ni pidiendola en la direccion', await x.pagina.isVisible('#hAbiertas'), false);
    await x.pagina.close();
    x = await conQuitadas('/furgonetas/', { furgonetas: ['vehiculos'] }, '#todo:not([hidden])');
    comprueba('furgonetas: sin la lista quedan las cifras y el dia a dia, sin CSV',
      [await x.pagina.isVisible('#cajaTabla'), await x.pagina.isVisible('#bCsv'),
       await x.pagina.isVisible('#kpis .kpi'), await x.pagina.isVisible('[data-tabla="dias"]')], [false, false, true, true]);
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();
    x = await conQuitadas('/revision/', { revision: ['planograma', 'precio'] }, '#vista .kpi');
    comprueba('revision: sin las quitadas, y arranca en la primera que ve',
      await x.pagina.$$eval('#vista .kpi', b => b.map(e => [e.dataset.t, e.getAttribute('aria-pressed')])).then(l => l.slice(0, 2)),
      [['tarifa', 'true'], ['creados', 'false']]);
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();
    x = await conQuitadas('/revision/#t=planograma', { revision: ['planograma', 'tarifa', 'precio', 'creados', 'usuarios'] }, '#vista .vacio');
    comprueba_que('sin ninguna, lo dice', (await x.pagina.textContent('#vista')).includes('ninguna tabla'));
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();
    delete API['/api/yo'].tablas_ocultas;
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  // ------------------------------------------------------------ preferidos
  console.log('\nPreferidos (docs/62): la estrella y su pagina');
  {
    const FOTOS = process.env.FOTOS_USUARIOS;
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'operaciones', perfil: 'Serunion', perfil_id: 'interno' };
    PREFS = [];
    let x = await abre('/rutas/');
    await x.pagina.waitForSelector('[data-estrella="maquinas"] .estrella');
    comprueba('rutas: una estrella junto al titulo de cada tabla, apagadas',
      await x.pagina.$$eval('.estrella', b => b.map(e => [e.closest('[data-estrella]').dataset.estrella, e.getAttribute('aria-pressed')])),
      [['rutas', 'false'], ['estado', 'false'], ['maquinas', 'false'], ['delegaciones', 'false'], ['festivos', 'false']]);
    const guardado = () => x.pagina.waitForRequest(q => q.method() === 'PUT' && q.url().endsWith('/api/preferidos'));
    let put = guardado();
    await x.pagina.click('[data-estrella="maquinas"] .estrella');
    comprueba('al pulsarla se pone amarilla y se guarda',
      [await x.pagina.getAttribute('[data-estrella="maquinas"] .estrella', 'aria-pressed'), JSON.parse((await put).postData()).preferidos],
      ['true', [{ c: 'rutas', t: 'maquinas', ancho: 'media', alto: 'medio' }]]);
    comprueba_que('amarilla de verdad',
      (await x.pagina.$eval('[data-estrella="maquinas"] .estrella svg', s => getComputedStyle(s).fill)) === 'rgb(245, 184, 0)');
    await x.pagina.click('#pestanas button[data-p]:nth-child(2)');
    await x.pagina.waitForTimeout(100);
    comprueba_que('y sigue al repintar la tabla', (await x.pagina.$$('[data-estrella="maquinas"] .estrella[aria-pressed="true"]')).length === 1);
    if (FOTOS) await x.pagina.screenshot({ path: path.join(FOTOS, 'estrella-rutas.png'), clip: { x: 0, y: 0, width: 1280, height: 700 } });
    comprueba('ni una peticion fuera del dominio', x.fuera, []);
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();

    x = await abre('/furgonetas/');
    await x.pagina.waitForSelector('#cajaTabla .estrella');
    put = guardado();
    await x.pagina.click('#cajaTabla .estrella');
    await put;
    comprueba('furgonetas: la estrella de la lista', PREFS.map(p => p.t), ['maquinas', 'vehiculos']);
    await x.pagina.selectOption('#ver', 'sin');
    await x.pagina.waitForTimeout(100);
    comprueba('y sigue encendida al filtrar',
      await x.pagina.getAttribute('#cajaTabla .estrella', 'aria-pressed'), 'true');
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();

    x = await abre('/almacenes/');
    await x.pagina.waitForSelector('.marca .estrella');
    comprueba_que('una pagina de una sola tabla la lleva junto a su titulo',
      (await x.pagina.$$('.marca b .estrella')).length === 1);
    await x.pagina.close();

    PREFS = [{ c: 'rutas', t: 'maquinas', ancho: 'media', alto: 'medio' },
             { c: 'furgonetas', t: 'dias', ancho: 'media', alto: 'todo' },
             { c: 'revision', t: 'tarifa', ancho: 'entera', alto: 'bajo' }];
    x = await abre('/preferidos/');
    await x.pagina.waitForSelector('.pref iframe');
    comprueba('preferidos: un recuadro por tabla, en su orden y su ancho',
      await x.pagina.$$eval('.pref', p => p.map(e => [e.dataset.k, e.classList.contains('entera')])),
      [['rutas|maquinas', false], ['furgonetas|dias', false], ['revision|tarifa', true]]);
    const marco = k => x.pagina.frameLocator(`.pref[data-k="${k}"] iframe`);
    await marco('rutas|maquinas').locator('#tPdv table').waitFor();
    const fr = x.pagina.frames().find(f => f.url().includes('/rutas/?solo=maquinas'));
    comprueba('dentro, la pagina de rutas con solo esa tabla, sin cabecera ni estrellas',
      await fr.evaluate(() => [...document.querySelectorAll('[data-tabla]')].filter(e => e.offsetParent).map(e => e.dataset.tabla)
        .concat([document.querySelector('header').offsetParent === null, document.querySelectorAll('.estrella').length])),
      ['maquinas', true, 0]);
    await marco('furgonetas|dias').locator('#dias .barras').waitFor();
    const ff = x.pagina.frames().find(f => f.url().includes('/furgonetas/?solo=dias'));
    comprueba('furgonetas: solo el dia a dia',
      await ff.evaluate(() => [!!document.querySelector('#cajaTabla').offsetParent, !!document.querySelector('[data-tabla="dias"]').offsetParent]),
      [false, true]);
    await marco('revision|tarifa').locator('#tabla h2').waitFor();
    const fv = x.pagina.frames().find(f => f.url().includes('/revision/'));
    comprueba('revision: abre en sin tarifa, sin los botones de las otras',
      await fv.evaluate(() => [location.hash.includes('t=tarifa'), !!document.querySelector('#vista > .kpis').offsetParent]), [true, false]);
    await x.pagina.waitForTimeout(400);
    const altos = await x.pagina.$$eval('.pref iframe', f => f.map(e => e.getBoundingClientRect().height));
    comprueba_que('alto medio 540, bajo 340, entero lo que mida', altos[0] === 540 && altos[2] === 340 && altos[1] > 160, JSON.stringify(altos));
    if (FOTOS) {
      await x.pagina.screenshot({ path: path.join(FOTOS, 'preferidos-claro.png'), fullPage: true });
      await x.pagina.click('#bTema');
      await x.pagina.waitForTimeout(300);
      await x.pagina.screenshot({ path: path.join(FOTOS, 'preferidos-oscuro.png'), fullPage: true });
      await x.pagina.click('#bTema');
    }
    let put2 = x.pagina.waitForRequest(q => q.method() === 'PUT' && q.url().endsWith('/api/preferidos'));
    await x.pagina.click('.pref[data-k="furgonetas|dias"] [data-m="-1"]');
    comprueba('mover antes cambia el orden y se guarda',
      [await x.pagina.$$eval('.pref', p => p.map(e => e.dataset.k)), JSON.parse((await put2).postData()).preferidos.map(p => p.t)],
      [['furgonetas|dias', 'rutas|maquinas', 'revision|tarifa'], ['dias', 'maquinas', 'tarifa']]);
    put2 = x.pagina.waitForRequest(q => q.method() === 'PUT' && q.url().endsWith('/api/preferidos'));
    // Los dos recuadros a la vista a la vez: mientras se arrastra no se desplaza.
    await x.pagina.setViewportSize({ width: 1280, height: 2400 });
    await x.pagina.dragAndDrop('.pref[data-k="revision|tarifa"] .asa', '.pref[data-k="furgonetas|dias"]', { targetPosition: { x: 20, y: 20 } });
    comprueba('arrastrar por el asa tambien', JSON.parse((await put2).postData()).preferidos.map(p => p.t), ['tarifa', 'dias', 'maquinas']);
    put2 = x.pagina.waitForRequest(q => q.method() === 'PUT' && q.url().endsWith('/api/preferidos'));
    await x.pagina.selectOption('.pref[data-k="rutas|maquinas"] select[data-q="ancho"]', 'entera');
    comprueba('el ancho se cambia y se guarda',
      [await x.pagina.$eval('.pref[data-k="rutas|maquinas"]', e => e.classList.contains('entera')),
       JSON.parse((await put2).postData()).preferidos.find(p => p.t === 'maquinas').ancho], [true, 'entera']);
    put2 = x.pagina.waitForRequest(q => q.method() === 'PUT' && q.url().endsWith('/api/preferidos'));
    await x.pagina.click('.pref[data-k="revision|tarifa"] .quita');
    comprueba('la estrella del recuadro lo quita', [await x.pagina.$$eval('.pref', p => p.length),
      JSON.parse((await put2).postData()).preferidos.length], [2, 2]);
    await x.pagina.setViewportSize({ width: 380, height: 800 });
    await x.pagina.waitForTimeout(300);
    comprueba('en movil no se sale de la pantalla',
      await x.pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    if (FOTOS) await x.pagina.screenshot({ path: path.join(FOTOS, 'preferidos-movil.png'), fullPage: false });
    comprueba('ni una peticion fuera del dominio', x.fuera, []);
    comprueba('sin un solo error en la consola del navegador', x.errores, []);
    await x.pagina.close();

    PREFS = [];
    x = await abre('/preferidos/');
    await x.pagina.waitForSelector('#vacio');
    comprueba_que('sin ninguno, dice como se marcan', (await x.pagina.textContent('#vacio')).includes('Pulsa la estrella'));
    await x.pagina.close();
    API['/api/yo'] = { ...API['/api/yo'], tipo: 'cliente', perfil: 'AIRBUS', perfil_id: 'cli-airbus' };
  }

  await navegador.close();
  servidor.close();
  console.log();
  if (fallos) { console.log(`${fallos} PRUEBAS FALLIDAS`); process.exit(1); }
  console.log('Las pantallas estan bien.');
})().catch(e => { console.error(e); process.exit(1); });
