# 69 · Las secciones por áreas

El 21 de octubre de 2026 Gabriele pidió que las secciones empiecen como la portada de Rutas
(docs/67):

> Los mismos cuadrantes tienen que estar en Incidencias, Devoluciones, Almacenes, Furgonetas,
> Puntos de venta activos, Ventas, Reposiciones, Telemetría, Tarifas.

Eligió «cuadrantes por área»: un cuadrado por área, con su nombre en el centro y su porcentaje en
el color del semáforo, y nada más. El detalle está dentro del área.

## Las áreas

Son las cinco de los Power BI de Gabriele, por el principio del nombre de la delegación:
MADRID → Centro, ANDALUCIA → Sur, CATALUNA → Cataluña, LEVANTE → Levante, NORTE → Norte. Lo que no
cae en ninguna es «Otra zona» y no lleva cuadrado. Es la misma regla que `zona_de` en
`infra/operativo.py`; `infra/test_operativo.py` comprueba que la lista de la web y la de la Lambda
no se separen.

El semáforo es el de siempre: por encima de 95 en el color del texto, de 75 a 95 en amarillo, por
debajo de 75 en rojo. Sin dato, el cuadrado dice «Sin dato»; nunca un cero.

`app/comun/areas.js` lleva la regla, el semáforo, el estilo (claro y oscuro) y la portada; cada
página lo carga de su propio dominio.

## Tarifas

- **Portada**: la cifra total y un cuadrado por área. El % es el de siempre de Tarifas, sumando
  las delegaciones del área: productos con la tarifa de VenCloud que coincide, sobre los
  controlados.
- **Dentro del área**: los cuadrados de sus delegaciones, como antes, y dentro de cada delegación
  su tabla. La miga dice «Todas las áreas › Área › Delegación».
- Las delegaciones de «Otra zona» que tienen productos controlados siguen saliendo, como cuadrados
  de delegación, debajo de las áreas.
- Un perfil con una sola área ve sus delegaciones directamente, como antes.

## Almacenes

- **Portada**: un cuadrado por área. El % es la parte de los productos con compra que no están bajo
  mínimo.
- **Dentro del área**: la página de siempre, con los almacenes de esa área. `?area=Sur` abre un área;
  `?area=todas` abre todos.
- **El área de un almacén**: la de su delegación en la tabla de almacenes de VenCloud, que se baja
  cada noche con el informe **M3 · EXT_MAESTRO_ALMACENES** (informe 199, docs/17). Antes la
  delegación salía solo del maestro de rutas, donde faltan muchos almacenes (Cornellà, Bilbao,
  Málaga, Zaragoza…); un almacén que no esté en M3 la sigue tomando de ahí. Los nombres se repiten
  («Caducidades» hay uno por delegación) y el stock llega por nombre: un nombre con varias
  delegaciones no lleva ninguna. Lo que queda sin área («Caducidades», «Principal» de CENTRAL) no
  sale en ningún cuadrado y la portada ofrece «Ver todos los almacenes».
  (22-oct-2026: el 21 se probó a sacar el área de la ciudad del nombre; Gabriele pidió la tabla.)

## Puntos de venta activos, Ventas y Reposiciones

Hasta el 22-oct-2026 sus cuadrados llevaban al panel antiguo. Gabriele pidió para ellos los mismos
cuadrados por área «con la cifra de cada una». Ahora tienen una página, `/cifras/`, con
`?que=pdvs`, `?que=ventas` o `?que=reposiciones` (más `&dia=` y `&area=`).

- **Portada**: el total arriba y un cuadrado por área con su cifra en el color del texto. Aquí no
  hay porcentaje y por tanto no hay semáforo. Ventas en euros, reposiciones en unidades y puntos
  de venta en número de puntos activos.
- **Dentro del área**: un cuadrado por delegación, con su cifra y debajo el detalle: unidades y
  máquinas en ventas, las clases de producto en reposiciones, las máquinas instaladas en puntos
  de venta.
- **Ventas y reposiciones** son de un día: se elige en el selector, y el cuadrado del informe
  general abre la página en su día. **Puntos de venta** es la foto de la noche.
- **Los datos** son los del informe general (`/api/operativo`), ya recortados por el servidor a lo
  que ve el usuario, con su reparto por delegación (docs/66). No hay fichero ni Lambda nuevos.
- **Lo que no tiene delegación** está en el total pero en ningún área, y la página dice cuánto es
  (el 20-oct, 2.509 € de 56.264 € de ventas). Las delegaciones de «Otra zona» (CENTRAL) salen como
  cuadrado de delegación debajo de las áreas.
- «Ver en el panel» sigue llevando al panel de siempre.

## Las demás secciones

Rutas (docs/67), Devoluciones, Furgonetas, Telemetría e Incidencias ya tienen sus áreas, cada una
en su propio cambio.

## Cómo se prueba

`app/comun/prueba_pantallas.js` comprueba en Tarifas los cuadrados de área con su % y su color, que
pulsar uno enseña sus delegaciones y la miga; en Almacenes, la portada, el filtro por área y
`?area=todas`. En `/cifras/`, las áreas con su cifra, entrar en una, la miga, el día sin
venta con su motivo y la nota de lo que no tiene delegación.
