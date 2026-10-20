# 68 · La bienvenida del informe operativo

El 20 de octubre de 2026 Gabriele pidió una animación al entrar:

> Cuando cualquier usuario operativo de Serunion entra en el panel de control quiero que me haga
> esta animación 3D. Sale el logo de Serunion Vending. El logo en 2D se transforma en una esfera
> 3D que empieza a rotar sobre ella misma. La esfera empieza a romperse perdiendo trozos que van
> a formar los cuadrados.

## Lo que se ve

1. **El logo** aparece en el centro, con una franja de luz que cruza las letras (0–0,8 s).
2. **El logo se deshace en teselas**, una rejilla de cuadraditos sobre la tinta del logo, y las
   teselas viajan de izquierda a derecha hasta su sitio en una **esfera de espejos** que ya gira
   (0,85–2,1 s). La esfera tiene luz, brillo, halo y sombra en el suelo; las juntas se ven oscuras.
3. **La esfera se rompe** (desde 2,15 s): primero se sueltan las teselas de delante, luego las de
   dentro. Cada trozo sale hacia fuera, gira, se voltea y vuela a una celda de un cuadrado de la
   página, tomando su color. Las teselas que sobran se van como polvo.
4. **Cada cuadrado encaja** con un destello y el de verdad aparece debajo, con sus cifras.

En total, unos cuatro segundos. En móvil es igual, con la esfera y el logo a la medida de la
pantalla, y los trozos van solo a los cuadrados que se ven sin bajar.

## Cuándo sale

- **Al entrar**: la pantalla de acceso, cuando manda al usuario al informe operativo (operaciones y
  dirección, docs/51), deja una marca en `sessionStorage`; la página la borra nada más leerla.
  Volver al informe desde Rutas o Incidencias no la repite. Los clientes van al cuadro y no la ven;
  el administrador va a la consola.
- **`/operativo/?bienvenida`** la fuerza, para enseñarla.
- **No sale** con «reducir movimiento» activado en el sistema.
- **Se salta** con un clic, cualquier tecla, el botón «Saltar», al hacer scroll o al cambiar el
  tamaño de la ventana.

## Si los datos tardan o no llegan

La esfera hace de «Cargando…»: gira hasta que la página tiene los cuadrados y entonces se rompe.
Si la API falla o no hay ningún día calculado, la esfera se encoge y se va sin romperse y la página
dice lo que tenga que decir. A los nueve segundos sin cuadrados, se va igual.

## Cómo está hecha

`app/comun/bienvenida.js`, cargado al principio de `app/operativo/index.html` para tapar el
«Cargando…» desde el primer instante. Lienzo 2D con la perspectiva hecha a mano: unas 370 (móvil) o
610 (escritorio) teselas, cada una con sus cuatro esquinas sobre la esfera, luz de Lambert y brillo
especular. El logo va dentro del fichero en `data:`, el mismo PNG de la pantalla de acceso,
repintado en el azul de la marca (#105b82) en claro y en blanco en oscuro. Ninguna biblioteca y
ninguna petición a otro dominio.

La prueba de pantallas (`app/comun/prueba_pantallas.js`) comprueba que sale con la marca y no sin
ella, que tapa los cuadrados mientras gira y los deja todos a la vista al acabar, que un clic la
salta, que no se repite y que con «reducir movimiento» no sale.

## Al pulsar un cuadrado

El mismo día Gabriele pidió el paso siguiente:

> Una vez abiertos los cuadrantes, cuando el usuario selecciona el cuadrante, una animación: los
> otros cuadrantes se cierran y el cuadrante seleccionado se hace grande hasta que se ve su página.

Al pulsar un cuadrado, los demás se encogen y se apagan, primero los que tiene más cerca, y la
cabecera y los filtros se van. Las cifras del pulsado se apagan y queda su color. Ese color crece
desde su sitio hasta llenar la pantalla y, mientras crece, se convierte en la página de la sección:
es la misma pieza, sin corte entre las dos (Gabriele lo pidió así tras ver una primera versión que
acababa en el fondo liso).

Lo hace el navegador con una transición entre páginas (View Transitions): `app/comun/transicion.js`
va en el `<head>` del informe y de cada sección; el cuadrado que se va y la página entera que llega
llevan el mismo nombre, y el navegador lleva uno al otro. Solo cuando se llega pulsando un cuadrado:
el informe deja una marca con la hora en `sessionStorage` y la sección la borra al leerla; cualquier
otra navegación sigue como siempre. Chrome y Edge lo hacen, y Safari desde la 18.2. En Firefox el
cuadrado crece hasta la pantalla con una animación propia y se abre la sección.

Solo pasa con el clic normal: con Ctrl, Cmd, Mayúsculas o la rueda, el cuadrado se abre como
siempre en otra pestaña. Con «reducir movimiento» se abre sin animar. Al volver atrás, el informe
está como se dejó, sin restos de la animación. El clic está al final de `app/operativo/index.html` (`abreConAnimacion`).
