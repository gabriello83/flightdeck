# 65 · Las delegaciones se eligen en cada usuario, no en el perfil

Lo pidió Gabriele el 19 de octubre de 2026: «una vez creado el perfil, quiero que a nivel de usuario
pueda elegir las delegaciones que el usuario puede ver. No lo quiero a nivel de perfil.»

## En la consola

- **Perfiles → Nuevo perfil / Editar** ya no tiene «Ámbito · delegaciones». Quedan clientes y centros,
  que son el ámbito de un cliente. Al personal de Serunion se le deja el ámbito vacío.
- **Usuarios → Nuevo usuario / Editar**, con un perfil del personal (operaciones, dirección,
  administrador), sale **«Delegaciones que ve»**: la misma lista de selección múltiple que tenía el
  perfil, con cuántos centros coge cada una. Vacío = todas.
- Con un perfil de cliente no sale: la delegación es organización interna de Serunion y un cliente no
  la ve (ve_delegaciones). La API tampoco se la guarda aunque se la manden.
- La lista de usuarios tiene la columna **Delegaciones**, y dice «sin panel hasta la noche» mientras
  el panel de esas delegaciones no se haya escrito.

## Cómo sigue aplicándose al escribir

El ámbito se sigue aplicando en la Lambda de agregados, no en la API:

- Por cada usuario del personal con delegaciones se calcula un panel con esas delegaciones y ninguna
  otra, en `cabina/<perfil>~<huella>/`. La huella son los doce primeros caracteres del SHA-1 de las
  delegaciones ordenadas. Dos usuarios del mismo perfil con las mismas delegaciones comparten panel.
- La API elige de qué carpeta lee con el perfil y el usuario de la sesión (`comun.cabina_y_ambito`).
  Ningún parámetro de la petición entra en la cuenta.
- La cuenta de la carpeta está escrita dos veces, en `infra/api/comun.py` y en
  `infra/lambda_agregados.py`, porque van en zips distintos. `test_api.py` y `test_cuadro.py` fijan
  el mismo valor: si se separan, falla la prueba.
- **Recién marcadas, hasta la pasada de agregados siguiente, el usuario no tiene panel.** La API le
  contesta que todavía no hay datos y no le da el de su perfil en su lugar.

| usuario | perfil | lee |
|---|---|---|
| con delegaciones | del personal | `<perfil>~<huella>`: sólo esas delegaciones |
| sin delegaciones | del personal, sin ámbito | `interno`: todo el parque |
| sin delegaciones | del personal, con ámbito | el de su perfil |
| cualquiera | de cliente | el de su perfil |

- Las delegaciones del usuario **sustituyen** a las que el perfil tuviera de antes. Los clientes y
  centros del perfil, si los tiene, se quedan.
- Un usuario con delegaciones no ve Utilizo: es de toda la empresa (SIN_AMBITO).
- El asistente recibe sus delegaciones en el ámbito.
- Un perfil del personal sin ámbito ya no sale en el resumen como «sin ámbito, no se calcula»: no es
  un error. Sus usuarios sin delegaciones leen el panel del interno.

## Los perfiles que ya tenían delegaciones

`ser-operaciones` tenía Madrid · Hospital La Paz y Madrid · Leganés. Para que nadie pierda lo que ve:

- Mientras no se vuelva a guardar el perfil, sus usuarios sin delegaciones siguen leyendo su panel.
- Al editar uno de esos usuarios, sus delegaciones salen ya marcadas con las del perfil.
- Al guardar el perfil, las delegaciones pasan a cada usuario suyo que no tenga ninguna, y el perfil se
  queda sin ellas.

## Despliegue

`api.zip` y `alarmas.zip` (llevan `comun.py` y `autorizacion.py`), `agregados.zip` y la página
`consola/` con `Cache-Control: no-cache`, más la invalidación. Sin cambios en las pilas: la Lambda de
agregados ya tenía `dynamodb:Scan` sobre la tabla, por los perfiles.
