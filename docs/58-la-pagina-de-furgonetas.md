# 58 · La página de furgonetas

> Gabriele, 16-oct-2026, al revisar el informe general: el cuadrado de Furgonetas era el único que
> no llevaba a ningún sitio («Sin sección todavía»). «Arréglalos los 3 y sube.»

Es lo que abre el cuadrado de **Furgonetas** del informe general (docs/51), en el día del cuadrado
(`/furgonetas/?dia=AAAA-MM-DD`).

## La cifra

Una furgoneta activa es un vehículo **distinto** con alguna visita real ese día en los partes de
VenCloud (`reglas.es_visita_real`: sin los partes automáticos de SYSTEM). No se suman de un día a
otro. VenCloud rellena con «xxxx-xxx» o «xxxxxxx» el vehículo que no se informó
(`operativo.vehiculo_real`): esas visitas están hechas, pero no se sabe en qué furgoneta, y no
cuentan. Se enseñan aparte, para que se vea cuánto se queda fuera.

## La página, /furgonetas/

Filtros de día, delegación y búsqueda, y CSV de lo que se ve.

- **Cuatro cifras:** furgonetas activas, visitas, visitas por furgoneta (de las que tienen
  vehículo) y visitas sin vehículo, con su porcentaje.
- **Furgonetas.** Una fila por vehículo: delegación, rutas, reponedores, visitas, puntos de venta
  distintos, minutos de visita, la hora de inicio de la primera y de la última visita, y cuántos de
  los últimos 30 días salió. La de más visitas va primero.
- **Visitas sin vehículo.** Por delegación y reponedor: sus rutas, visitas, puntos de venta y lo
  que traía el campo vehículo.
- **Por delegación.** Furgonetas, visitas, visitas por furgoneta y sin vehículo. Una furgoneta
  que visitó en dos delegaciones cuenta en las dos; el total de arriba es el de distintas, como el
  cuadrado.
- **Día a día.** Las furgonetas activas de los últimos 30 días hasta el elegido, con la
  delegación del filtro si la hay. Los fines de semana y los festivos salen muchas menos.

## El fichero

`cabina/<perfil>/furgonetas.json.gz`, que escriben los agregados cada noche con
`Operativo.detalle_furgonetas`, con el ámbito del perfil aplicado al escribir. Acumula como el
informe: los días de esta noche sobre los que ya había, hasta 62 (`DIAS_GUARDADOS`). Se sirve por
`/api/furgonetas`, con la misma regla que el cuadrado: perfil de operaciones o más que vea el
cuadrado de Furgonetas (`autorizacion.CUADRADOS`). No hay parámetro con el que pedir otro perfil.

Pruebas: `infra/test_operativo.py` (las cuentas y que cuadren con el cuadrado),
`infra/test_agregados.py` (un fichero por perfil, con su ámbito), `infra/api/test_api.py` (quién
lo ve) y `app/comun/prueba_pantallas.js` (la página, en claro, oscuro y móvil, sin peticiones
fuera del dominio).
