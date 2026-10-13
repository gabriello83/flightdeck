# 51 · El informe general operativo

> `infra/operativo.py`, `infra/lambda_agregados.py` (`come_operativo`, `cabina/<perfil>/operativo.json`),
> `infra/api/autorizacion.py` (`CUADRADOS`, `recorta_operativo`), `infra/api/lambda_api.py`
> (`/api/operativo`), `app/operativo/`, y el enlace desde `app/index.html`, `app/panel/` y `app/consola/`.

Lo pidió Gabriele el 13 de octubre de 2026: *«un informe formado por cuadrados de colores
diferentes que pongan un dato principal; pulsando el cuadrado se abre la sección operativa
correspondiente. Los datos siempre filtrados según el perfil del usuario, y empieza con los datos
de ayer»*. Qué se ve al abrir cada cuadrado se decide en un segundo paso; de momento cada uno lleva
a la sección del panel que ya existe.

## Los ocho cuadrados

| cuadrado | dato principal | de dónde sale | color | lleva a |
|---|---|---|---|---|
| Rutas | % de visitas previstas que se hicieron | plan de visitas (D12) contra visitas reales, por punto de venta | semáforo | Resumen · Visitas por día |
| Averías | % de averías cerradas ese día en menos de 24 h | SAT: fallos técnicos (sin serie E ni ficticia), apertura y cierre de sus eventos | semáforo | Disponibilidad · SAT |
| Almacenes | valor del producto en almacén | último cierre mensual de inventario (C9, tipo A) | propio | todavía sin sección |
| Furgonetas | furgonetas con visitas ese día | vehículo de las visitas reales, sin «xxxx-xxx» | propio | todavía sin sección |
| Puntos de venta activos | puntos de venta en estado 1 | censo (M5) de esa noche | propio | Instalaciones · Censo |
| Ventas | venta del día en euros | la misma cuenta que la serie: telemetría, y si no hay, el parte | propio | Venta y consumo · Recaudación |
| Reposiciones | unidades de producto repuestas, por clase de máquina | líneas CM de la reposición; los carriles de café van aparte | propio | Venta y consumo · Carga |
| Telemetría | % de máquinas con telemetría que mandaron su lectura (DEX) | partes de SYSTEM con lectura, sobre las máquinas del censo con telemetría | semáforo | Instalaciones · Incidencias |

Semáforo: **verde por encima del 95 %, amarillo del 75 al 95 %, rojo por debajo del 75 %**. El
mensaje original decía «amarillo >95 % <75 %»; se ha leído como el tramo entre los dos.

### Por qué averías «en menos de 24 horas»

Se pidió proponer un porcentaje. Medido sobre septiembre y octubre de 2026 en todo el parque, el
porcentaje diario de fallos técnicos cerrados en menos de 24 h va del 37 % al 86 % en días
laborables: es el que más se mueve con lo que hace el SAT, y es el que se puede exigir. La
alternativa, disponibilidad (% de máquinas sin un fallo abierto), sale siempre entre el 95 y el
96 %: con los umbrales de arriba estaría siempre en la raya y no diría nada.

Los días sin cierres (festivos, domingos) salen «sin dato», no al 100 %. Un cierre de una tarea
abierta antes de la ventana de 120 días no se puede medir y se cuenta aparte (`sin_tarea`).

## Lo que no se puede calcular todavía

- **Rutas**: hace falta el plan de visitas, `vending.planvisitas`, que no se extrae. El SQL está
  en docs/17, **D12 · EXT_RUTAS_PLAN_VISITAS**. Hasta que exista el informe en VenCloud y su número
  en el manifiesto, el cuadrado dice «Sin dato» con el motivo. No se reconstruye el plan con los
  criterios de ruta (D3): 955 máquinas no tienen día marcado y los criterios «cada n días» no se
  pueden resolver sin el motor de VenCloud.
- **Almacenes, valor de hoy**: VenCloud solo da un cierre al mes. Sumar los movimientos del mes
  encima del cierre anterior no cuadra con el cierre siguiente (agosto + movimientos de septiembre
  daba 861.069 € contra un cierre de 502.430 €), así que se enseña el último cierre con su mes. Para
  el valor del día haría falta un informe de existencias actuales por almacén.

## Por qué es un fichero aparte

El plan de un día pasado no se reconstruye con los maestros de hoy, las furgonetas distintas no se
suman, y puntos de venta, telemetría auditable y almacenes son una foto. Así que la noche escribe
`cabina/<perfil>/operativo.json` con los **últimos siete días** tal cual, encima de los que ya
había (guarda 62). Cada día queda con el plan y el censo de la noche en que se cerró. En un relleno
histórico no se escribe.

El ámbito se aplica al escribir, como todo: un fichero por perfil. Los almacenes son de una
delegación: un perfil acotado por clientes o centros no tiene almacenes y lo dice; uno por
delegaciones ve los de las suyas (la delegación del almacén sale del maestro de rutas).

## Quién ve qué

`/api/operativo` sirve el fichero del perfil de la sesión, recortado con la misma tijera que el
panel: cada cuadrado pide el bloque de su sección (servicio, sat, dinero, instalaciones,
inventario). Almacenes es nuestro stock: solo dirección y administración. Un cliente no tiene
informe operativo (sólo el cuadro, docs/49): 403.

Operaciones y dirección entran ahora directamente en `/operativo/`; el administrador sigue
entrando en la consola, con un botón «Informe general». El panel lleva el mismo botón, y abre ya
filtrado en la sección con `/panel/?ver=<sesión>#<panel>`.

## Lo que salió al calcularlo con el dato real

Viernes 9 de octubre de 2026, perfil interno: averías 83,7 % (36 de 43), 40 furgonetas, 49.859 € de
venta por telemetría, 52.168 unidades de producto repuestas, 3.162 puntos de venta activos.
**Telemetría 43,7 %**: de 2.253 máquinas con telemetría, sólo 985 mandaron lectura ese día, aunque
1.888 sí mandaron venta. Las lecturas DEX llegan mucho menos que las ventas.
