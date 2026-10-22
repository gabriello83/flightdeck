# 70 · El asistente en el informe general, y Vendi

Gabriele, 22-oct-2026: activar el asistente (docs/40), darle una cara —«como el muñeco de M&M's,
pero con una máquina de snacks, y que salude con la mano al entrar», del azul del logo— y ponerlo
también en el informe general operativo.

## Vendi

Una máquina de snacks del azul del logo de Serunion Vending (`#0f5b84`), con ojos, guantes blancos y
zapatillas. Es un dibujo propio, en SVG dentro de la página: ni imagen ni nada que pedir fuera del
dominio. Sale flotando abajo a la derecha, y solo para quien tiene el asistente
(`/api/yo` → `asistente.habilitado`).

- Al entrar saluda con la mano y enseña un bocadillo unos segundos. En el informe general espera a
  que acabe la bienvenida (docs/68), porque debajo no lo vería nadie.
- Vuelve a saludar al pasarle el ratón y en la cabecera del cajón al abrirlo.
- Con «reducir movimiento» se queda quieto.

Todo vive en `app/comun/asistente.js`: el muñeco, el cajón del chat y la conversación con
`/api/pregunta`. Cada página lo monta con `Asistente.monta({pagina, boton, sugerencias})` y pone
solo lo suyo: qué datos son y qué sugerencias tienen sentido con lo que le ha llegado.

## Cada página contesta con sus datos

La regla de docs/40 no cambia: el modelo recibe **exactamente** lo que esa sesión recibe en el
navegador, recortado en el servidor, y ninguna otra vía al dato. Lo nuevo es que la página dice cuál
es:

| desde | `pagina` | lo que recibe el modelo |
|---|---|---|
| `/panel/` | `panel` (o nada) | el panel recortado (`A.recorta`), como hasta ahora |
| `/operativo/` | `operativo` | el informe general recortado (`A.recorta_operativo`): días, cuadrados que ve, foto |

El perfil lo pone la sesión, nunca la petición: `pagina` solo elige *cuál* de los ficheros de su
propia carpeta de `cabina/`. Un cliente no tiene informe general y recibe 403. Lo que el
administrador le quitó a un usuario (docs/61) tampoco llega: el asistente aplica `con_usuario` igual
que la API.

El informe general pesa unos 80 KB sin comprimir, como el panel, así que cuesta lo mismo por
pregunta (unos 0,20 $) y tarda parecido.

Además, el mensaje lleva **`hoy`** (fecha de la península). Sin ella el modelo no sabe qué es
«ayer». El recetario tiene un párrafo nuevo sobre cómo leer el informe general: colores por
umbrales, `por_delegacion`, `zonas`, que `foto` es de la noche y que `sin_dato` no es cero. Cambiar
el recetario invalida la caché una vez.

## Las respuestas, con formato

El modelo contesta con negritas, listas y tablas cortas. Antes salían los asteriscos y las barras
tal cual. Ahora se pintan, escapando primero todo el texto y dejando pasar solo `<b>`, listas y
tablas construidas aquí. Las cifras de las tablas van a la derecha.
