# 43 · El panel del cliente

> `app/index.html` (acceso) y `app/panel/index.html` (panel), contra la API de verdad.
> Validado con el panel de AIRBUS: nueve centros, 120 días.

## Una página, no una por cliente

`app/airbus/index.html` era una página de AIRBUS: sus dieciséis paneles estaban escritos para
AIRBUS y leían un JSON fabricado a mano. La de ahora no sabe quién es AIRBUS.

**AIRBUS es un perfil, no una página.** El navegador pide `/api/yo` y `/api/panel`, y dibuja lo que
venga. Cada panel declara dos cosas:

```js
{ id:"centros", sesion:"resumen", bloque implícito: P.servicio, ... }
```

y se dibuja sólo si **el bloque llegó** y **el perfil tiene esa sesión**. Un cliente con otras
sesiones ve otros paneles sin que nadie toque una línea de la página. Un cliente nuevo no necesita
página nueva: necesita una fila en `perfiles.json` y un perfil en DynamoDB.

Esto no es una comodidad de programación. El recorte lo hace `autorizacion.recorta` **en el
servidor**: lo que no debe ver este perfil no sale de AWS. La página no oculta nada, porque no
recibe nada que ocultar. Y no hay ningún parámetro con el que pedir el panel de otro perfil: el
perfil sale de la fila de sesión, nunca de la petición.

## Lo que ve AIRBUS, y de dónde sale

Sesiones concedidas: `resumen`, `venta_consumo`, `disponibilidad`, `surtido`.

| Panel | Sesión | De dónde sale |
|---|---|---|
| Visitas por día | resumen | `servicio.visitas_por_dia` |
| Visitas por centro | resumen | `servicio.por_centro` |
| Patrón semanal | resumen | calculado en el navegador sobre `visitas_por_dia` |
| Duración de la visita | resumen | `servicio.duracion_min` |
| Recaudación por mes | venta_consumo | `dinero.periodos` |
| Efectivo sin telemetría | venta_consumo | `dinero.periodos[].pct_ciego` |
| Reposición del periodo | venta_consumo | `servicio.carga` |
| Merma por motivo | servicio | `servicio.merma` |
| Caducidad por artículo | servicio | `servicio.merma.caducidad_por_articulo` |
| Disponibilidad y averías | disponibilidad | `sat` |
| Máquinas reincidentes | disponibilidad | `sat.reincidentes` |

Lo que **no** llega al navegador de un cliente, aunque esté en el panel interno: `coste_servicio`
(lo que nos cuesta a nosotros atenderle) e `inventario.existencias` (nuestro stock). No es pudor:
es que no es dato suyo. Lo quita `recorta` antes de responder, y hay una prueba que lo vigila.

El `surtido` está concedido y no sale ningún panel: ese bloque todavía no lo calcula la Lambda de
agregados. Es correcto que no aparezca nada —mejor eso que un panel vacío que parece un cero.

## El fallo que apareció al enchufarlo

Al construir el panel con datos reales salió **0 € de recaudación y 0 unidades cargadas** para
AIRBUS. Las demás cifras eran buenas, que es lo que lo hacía peligroso: un panel con la mitad de
los números bien no parece roto, parece un mes flojo.

La causa: **sólo tres de los ocho informes traen columna `centro`** —`visita_cabecera`,
`stock_maquina` y `sat_averias`—. Los otros cinco traen `matricula` y nada más. Y el ámbito de un
perfil de cliente se declara por nombre de centro (`"clientes": ["AIRBUS"]`), así que
`en_ambito` miraba un campo que en esas filas no existe, no encajaban en ningún ámbito, y se caían
enteras.

Por qué no lo cazó la prueba: **la prueba se inventaba la columna**. Los datos de
`test_agregados.py` llevaban `"centro": "AIRBUS GETAFE"` en las filas de recaudación y de
reposición, donde el informe de verdad no lo lleva. La prueba verificaba un modelo de datos que no
era el nuestro. Ahora las filas de la prueba llevan exactamente las columnas que trae VenCloud, y
el que las lea verá cuáles son.

El arreglo es `MapaCentros`: mientras lee, aprende de qué centro es cada máquina a partir de los
informes que sí lo dicen, y las filas que no lo dicen se resuelven por su matrícula. No cuesta ni
una descarga más, porque sale de lo que ya se estaba leyendo. Las fuentes se reordenaron para que
los tres informes con `centro` vayan primero; como todas las reglas son cuentas y sumas, el orden
no cambia ningún resultado, y hay una prueba que lo demuestra.

El mapa **no se guarda entre ejecuciones**, a propósito: una máquina se cambia de centro, y un mapa
viejo le atribuiría la recaudación al cliente equivocado. Vale lo que diga la ventana que se está
agregando.

Las jornadas son la excepción que no tiene arreglo: son de una ruta y un vehículo, no de un centro,
y el informe no trae matrícula. No se pueden atribuir a un cliente. Tampoco hace falta: ese bloque
no llega a un perfil de cliente.

## Decisiones de dibujo

Las de siempre, y una nueva:

- **Un solo eje.** La recaudación lleva efectivo y banco apilados porque son la misma unidad. Nunca
  dos escalas en el mismo gráfico.
- **Los meses sin cerrar van con trama**, no sólo con color: se ven igual impresos en blanco y
  negro y para quien no distingue los tonos. Y debajo dice cuáles y por qué (falta el cobro por
  tarjeta, que se escribe al mes siguiente).
- **Cada gráfico lleva su tabla detrás**, plegada. Es la única forma de leer una cifra exacta y la
  única que funciona con un lector de pantalla. El verde de «Caducidad por artículo» tiene 2,74:1
  de contraste sobre el papel claro —por debajo de 3:1—, y por eso lleva obligatoriamente la cifra
  escrita en cada barra y su tabla.
- **El nombre largo se recorta en el gráfico y entero en la tabla.** Un texto de SVG no se corta
  solo: «AIRBUS PUERTO REAL» se metía por debajo de su barra.
- **En el móvil el eje va en miles** (`483 k€`), nunca el dato: ése va entero en la etiqueta.
- **Paleta de tres**, validada en claro y en oscuro con el validador, no a ojo.

## Qué se guarda dónde

| Qué | Dónde | Por qué |
|---|---|---|
| Modo claro/oscuro | `localStorage` | es de este aparato: en la pantalla del almacén se quiere oscuro y en el portátil claro |
| Orden de los paneles | servidor, `/api/orden` | viaja con la persona, no con el navegador |
| Sesión | cookie `HttpOnly` + fila con caducidad | se puede cerrar en el acto; un token firmado no |

## Lo que sigue sin existir

- El bloque `surtido`, que AIRBUS tiene concedido.
- Venta por máquina y por artículo para el cliente: hoy el panel da **servicio**, no venta. La
  venta está en `visita_ventas`, que se extrae pero todavía no se agrega.
- La consola de administración (`app/consola/`) sigue siendo el prototipo: no valida contraseñas
  contra Cognito.
- El asistente y las alarmas, que tienen API y pruebas pero no pantalla.
