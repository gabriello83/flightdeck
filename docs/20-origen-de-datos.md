# De dónde lee la cabina

## Lo que cambia

Hasta ahora la página llevaba los datos dentro: 660 KB de JSON incrustados en el HTML. Cada vez
que cambiaba un dato había que republicar la página entera, y la página sólo sabía de septiembre
porque septiembre estaba escrito en ella.

Ahora los pide. Una constante decide a dónde:

```js
const ORIGEN = (window.FLIGHTDECK_ORIGEN || "datos/");
const FICHEROS = { nucleo: "nucleo.json", servicio: "servicio.json" };
```

El día que el pipeline esté vivo, esa línea pasa a ser la del bucket y **no cambia nada más**.
La página no sabe de dónde vienen los datos.

## Por qué el destino final no es un artifact

Un artifact publicado sólo puede pedir ficheros que viajen con él: cualquier petición a otro
dominio está bloqueada por la política de seguridad de la plataforma. Sirve como prototipo y como
sitio donde enseñar el producto, pero no puede leer de S3.

La cabina de producción es **un sitio estático en S3 con CloudFront**, en vuestra cuenta:

- misma cuenta que los datos, así que leer el bucket es trivial
- CloudFront delante, que es donde se enchufa **Cognito** para el acceso de verdad
- y el reparto por alcance deja de ser cosa del navegador: el servidor entrega sólo lo que a cada
  usuario le corresponde

## El contrato de los ficheros

Esto es lo que el proceso nocturno tiene que dejar escrito en `cabina/`. Mientras no exista, los
mismos ficheros viajan con la página.

### `nucleo.json`

| clave | qué lleva |
|---|---|
| `gen` | totales del periodo: importe, transacciones, máquinas, centros, delegaciones, efectivo, importe sin artículo |
| `dele` | lista de delegaciones; el resto de tablas la referencian por índice |
| `cen` | una fila por centro: nombre, delegación, número, máquinas, importe, efectivo, transacciones, ventana horaria, importe de fin de semana, importe sin artículo y la curva de 24 horas |
| `maq` | una fila por máquina: matrícula, centro, delegación, importe, efectivo, transacciones, días activos, días sin vender, primera y última hora, importe sin artículo, artículos distintos y días hasta juntar 100 € |
| `dia` | serie diaria del periodo con el reparto por medio de pago |
| `diacen` | serie diaria por centro |
| `art` | diccionario de artículos: código, nombre, clase y precio de compra |
| `pro` | los 80 artículos con más venta a escala nacional |
| `procen` | los 25 con más venta de cada centro |
| `fechas` | las fechas del periodo |

### `servicio.json`

| clave | qué lleva |
|---|---|
| `vis` | visitas por máquina, con la última y el reparto por mes |
| `vlist` | las 400 visitas más recientes |
| `ave` | incidencias, una por fila, con estado y tiempo de cierre |
| `pre` | mantenimientos preventivos |
| `rango` | fechas cubiertas por cada bloque |
| `centros` | centros con datos de servicio |

**Las listas son arrays de arrays, no de objetos.** Ocupan la mitad y la página los lee por
posición. Si el proceso nocturno los genera, tiene que respetar el orden de las columnas.

## Estados de la página

Mientras carga se ve una pantalla con el nombre y una barra. Si falla, esa misma pantalla dice
que no se han podido cargar los datos **y enseña la URL que falló**, para que se vea si es un
fichero que no está, un permiso o un bucket mal escrito. Nunca se queda en blanco.

## Lo que falta para producción

1. El pipeline que escriba estos dos ficheros cada noche en `cabina/`.
2. El sitio estático en S3 con CloudFront.
3. Cognito, y que el servidor filtre por alcance en vez de hacerlo el navegador.

El punto 1 depende de la Lambda, que a su vez sigue esperando a que veamos qué devuelve la API.
