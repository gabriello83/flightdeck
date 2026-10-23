# 74 · Los clientes y centros que ve cada usuario

Lo pidió Gabriele el 23 de octubre de 2026: «en el usuario quiero poder decidir los clientes que
pueden ver».

## En la consola

- **Usuarios → Nuevo usuario / Editar** tiene dos casillas nuevas, **«Clientes que ve»** y **«Centros
  que ve»**, de selección múltiple y con buscador, como el ámbito del perfil. Salen con cualquier
  perfil, de cliente o del personal.
- Vacías = ve todo lo de su perfil (y de sus delegaciones), como hasta ahora.
- La lista solo trae lo que su perfil ve, y, si es del personal y tiene delegaciones marcadas, solo lo de
  esas delegaciones. Debajo dice con cuántos centros encaja cada cliente.
- Se guarda con la misma regla que el ámbito del perfil: un cliente al que se le marcan centros no se
  guarda como cliente, solo sus centros, por número. Así se elige por centro lo que en VenCloud cuelga
  de un cliente común: los centros de AIRBUS siguen bajo «SERUNION, SA».
- La lista de usuarios cambia la columna «Delegaciones» por **«Qué ve»**: sus delegaciones y el
  recorte («solo CONSUM», «solo 3 centros»), y «sin panel hasta la noche» mientras no esté escrito.

## Es un recorte, no un permiso

El usuario ve lo que encaja en su perfil **y además** en uno de esos clientes o centros. Nunca le da
nada que su perfil no vea.

| perfil / delegaciones | clientes del usuario | ve |
|---|---|---|
| del personal, Sur | CONSUM | los centros de CONSUM en Sur |
| del personal, sin ámbito | CONSUM | CONSUM en toda España |
| AIRBUS (cliente) | 500088 | solo ese centro de AIRBUS |
| cualquiera | nada | lo de siempre |

## Cómo se aplica: al escribir

- En el usuario se guardan `clientes` y `centros` (`USUARIO#…`). La API los limpia
  (`comun.acota_de`) y los añade al ámbito de la sesión como `acota`.
- La Lambda de agregados escribe un panel para cada combinación en `cabina/<perfil>~<huella>/`, como
  con las delegaciones (docs/65). La huella suma, a las delegaciones, `cliente:<nombre>` y
  `centro:<número>`; sin recorte la cuenta es la de antes y nadie pierde su panel. La cuenta está en
  `infra/api/comun.py` y en `infra/lambda_agregados.py`; `test_api.py` y `test_cuadro.py` fijan el
  mismo valor.
- `en_ambito` mira primero el ámbito de siempre (basta con uno de clientes, centros o delegaciones) y
  luego, si hay `acota`, que encaje además en uno de sus clientes o centros.
- Un perfil de cliente que no se calcula (sin ámbito) no tiene panel por usuario: su ámbito vacío no es
  «todo el parque».
- **Recién marcado, hasta la pasada de agregados siguiente, el usuario no tiene panel.** La API le
  contesta que todavía no hay datos; nunca le da el de su perfil en su lugar.

Lo que sale de ahí, sin tocar cada página: el panel, el informe general, las once secciones y sus
filtros (las fichas salen del fichero de su panel) y el asistente, que además recibe `solo_clientes` y
`solo_centros` en el ámbito.

Lo que no es de ningún cliente se dice, no se reparte:

- **Almacenes**: un almacén es de una delegación. Con recorte no salen, aunque tenga delegaciones.
- **Furgonetas**: solo las que visitaron sus centros, no la flota entera de la delegación.
- **Utilizo**: es de toda la empresa; con recorte no sale.

## Despliegue

`api.zip` y `alarmas.zip` (llevan `comun.py` y `autorizacion.py`), `agregados.zip` y la página
`consola/` con `Cache-Control: no-cache`, más la invalidación. Sin cambios en las pilas. Después, una
pasada de agregados para que los usuarios recortados tengan su panel.
