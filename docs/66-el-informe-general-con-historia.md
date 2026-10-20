# 66 · El informe general con calendario, historia, varios días y delegación

> `infra/operativo.py` (`por_delegacion`, `DIAS_HISTORIA`, `cierra`), `infra/lambda_agregados.py`
> (`escribe_operativo`, `previos_averias`, `delegacion_de`), `infra/api/autorizacion.py`
> (`recorta_operativo`), `infra/api/lambda_api.py` (`/api/operativo`) y `app/operativo/`.

Lo pidió Gabriele el 19 de octubre de 2026: *«donde abre el día, que se abra el típico calendario
por mes; pulsando el mes, ver todos los meses, y pulsando los meses, ver los años. Quiero un
histórico: ¿cuál es la mejor manera de calcularlo, de noche o al momento de la petición?
¿Posibilidad de ver varios días también?»*. Y en el mismo rato: *«posibilidad de filtrar por ÁREA y
por Delegación»*.

## De noche, no al pedirlo

La historia se calcula de noche, como todo lo demás. La noche ya lee los informes de VenCloud y
aplica el ámbito de cada usuario al escribir; la página solo elige días y suma. Calcularlo al pedirlo
obligaría a la API a leer el crudo con cada clic (segundos en vez de nada) y a aplicar el ámbito al
leer, que es justo lo que no se hace. Es lo que Gabriele ya pidió para el histórico del cuadro (docs/48):
«la noche lo calcula todo y el portal solo filtra».

## Qué guarda el fichero

`cabina/<perfil>/operativo.json.gz`, comprimido. Antes era `operativo.json` con 62 días; la primera
noche arranca de ese y la API lee el viejo mientras no exista el nuevo.

- **Toda la historia**, hasta `DIAS_HISTORIA` (1.100 días; desde el 1-ene-2025 son unos 660).
- Cada día lleva **`por_delegacion`**: cada cuadrado partido por delegación con cifras que se suman
  (previstas y hechas, cerradas y a tiempo, importe y unidades, auditables y con lectura, las
  matrículas de las furgonetas). La clave vacía es lo que no tiene delegación: cuenta en el total y en
  ninguna delegación.
- Las **furgonetas** del día llevan su lista de matrículas: para varios días se cuentan las distintas.
- **`zonas`**: el área de cada delegación, las cinco del Power BI (`incidencias.zona_de`).
- La foto lleva los **puntos de venta por delegación**.

La delegación sale de la propia fila; si no la trae (líneas de reposición, SAT), del centro de su
máquina en el mapa. La venta por delegación es la del día partido por centro de la serie, sumado por la
delegación de cada centro: la misma regla de venta, no otra.

El ámbito no cambia: el fichero es el del perfil o el del usuario con sus delegaciones (docs/65), así
que solo trae las delegaciones que ese usuario puede ver. La API recorta `por_delegacion` con la misma
tijera que los cuadrados.

## El relleno histórico también lo escribe

Con `{"desde": "2025-01-01", "hasta": "2025-03-31"}` los agregados escriben esos días en el informe
general, sobre lo que ya había. Cada día se cierra en cuanto se ha leído, así que no hay meses de
partes en memoria. Diferencias con la noche:

- **Rutas antes del 13-oct-2026** dice «sin dato»: el plan de visitas (D12) no existe de antes.
- **Telemetría** dice «sin dato»: el relleno no tiene el censo de ese día y no se sabe qué máquinas
  llevaban telemetría entonces.
- **Incidencias**: se leen también los 120 días de SAT anteriores al tramo, como la ventana de la noche,
  para que una avería cerrada el primer día tenga su apertura.
- **No pisa** la telemetría ni las incidencias de un día que ya escribió la noche (la noche tiene el
  censo y el estado de M13), ni la foto.

## La página

- **Un día / Varios días**. El botón de la fecha abre el calendario del mes. Pulsando el título salen
  los meses del año; pulsándolo otra vez, los años. En un día solo se pueden pulsar los días con dato.
  En varios, se pulsa el primero y el último, o un atajo: últimos 7 o 30 días, este mes, mes anterior.
- **Área y Delegación**, solo si el usuario ve más de una delegación. El área deja en la lista sus
  delegaciones.
- **Cómo suma**: lo que se suma se suma; el porcentaje sale del total (no es la media de porcentajes);
  las furgonetas son las distintas; las máquinas con venta no se suman entre días y no salen. Un día
  sin cierres de avería es un cero de verdad y cuenta; un día sin plan no cuenta en rutas.
- **Lo que falta se dice**: si de un rango solo algunos días tienen el dato, el cuadrado dice «solo N de
  M días tienen el dato». Los días de antes de este cambio no tienen reparto por delegación: con el
  filtro, lo dicen.
- **La foto con filtro**: puntos de venta y almacenes se reparten por delegación. Devoluciones,
  tarifas, revisión y utilizo no: con el filtro puesto dicen que no se reparten, en vez de enseñar el
  total como si fuera de la delegación.
- Lo elegido va en la dirección (`?dia=`, `?desde=&hasta=`, `&area=`, `&delegacion=`): el enlace se
  puede guardar o mandar. Los cuadrados con página propia abren en el último día elegido.

## Despliegue

`agregados.zip`, `api.zip` y `alarmas.zip` (llevan `autorizacion.py`), y la página `operativo/` con
`Cache-Control: no-cache`, más la invalidación. Sin cambios en las pilas. Orden: primero la API (lee
el fichero nuevo y el viejo), luego agregados y lanzarlos, y la página al final. Hasta que corran los
agregados la página funciona con el fichero viejo: sin reparto por delegación ni historia.

Para la historia de 2025, los mismos tramos trimestrales del relleno de agregados (docs/48), de más
antiguo a más nuevo.
