# 44 · La mudanza de clientes de VenCloud

> Fin de semana del 4-5 de octubre de 2026. Los centros dejan de colgar de «Serunion» y pasan a
> colgar de su cliente real.

## Qué cambia

La jerarquía de VenCloud es **cliente → centro → PDV → máquina**, y hasta ahora el primer escalón
no se usaba: todos los centros colgaban del cliente «Serunion». El cliente de verdad sólo estaba
escrito **dentro del nombre del centro** — «AIRBUS GETAFE», «CONSUM MURCIA».

Después de la mudanza, `comercial.clientescentros.clienteid` apunta al cliente real.

## Por qué nos importa

Porque el ámbito de un perfil de cliente se declara así:

```json
{ "id": "cli-airbus", "ambito": { "clientes": ["AIRBUS"] } }
```

y hasta hoy eso se resolvía mirando si «AIRBUS» aparecía en el **nombre del centro**. Si la mudanza
viene acompañada de un renombrado —y es lo lógico: un centro que ya cuelga del cliente AIRBUS no
necesita llevar «AIRBUS» delante— ese nombre pasa a ser «GETAFE» y el panel de AIRBUS **se queda
vacío de golpe**, sin ningún error en ningún sitio. Nadie se entera hasta que el cliente llama.

## Lo que ya está hecho

`en_ambito` mira ahora **los dos sitios**: el campo `cliente` cuando viene, y el nombre del centro
como hasta ahora. Las dos cosas valen a la vez, así que no hay que cambiar nada el día exacto de la
mudanza, ni antes ni después: funciona en los tres momentos. Hay pruebas de los tres.

`MapaCentros` aprende `matrícula → (centro, cliente)`, de modo que las filas que no traen ni centro
ni cliente —recaudación, reposiciones, eventos de SAT— se resuelven igual por su matrícula.

Y el resumen de cada ejecución de agregados publica **`clientes_vistos`**. Es el semáforo:

- `["SERUNION"]` → la mudanza no ha entrado todavía, el ámbito va por el nombre del centro.
- varios nombres → ha entrado, y el campo ya manda.

## Lo que hay que hacer en VenCloud

Los informes no traen el cliente porque hasta ahora no servía de nada. **Hay que añadirlo a dos
informes, y conviene en un tercero.** Es editar el SQL del informe en VenCloud; no hay que tocar
nada en AWS, porque la extracción se limita a descargar lo que el informe devuelva.

**Obligatorio · `EXT_VISITA_CABECERA`** — dos columnas y un join:

```sql
  cli.codigo                 as cod_cliente,
  cli.nombre                 as cliente,
```
```sql
left join comercial.clientes cli        on cli.id = cen.clienteid
```

**Obligatorio · `EXT_SAT_AVERIAS`** — lo mismo:

```sql
  cli.codigo    as cod_cliente,
  cli.nombre    as cliente,
```
```sql
left join comercial.clientes cli on cli.id = cen.clienteid
```

**Recomendable · `EXT_RUTAS_PDVS`** — es el maestro de todo el parque, no sólo de lo que se visitó:
con él el mapa cubre también las máquinas que no tuvieron ni una visita en la ventana.

```sql
  cli.codigo    as cod_cliente,
  cli.nombre    as cliente
```
```sql
left join comercial.clientes cli        on cli.id = cen.clienteid
```

El SQL completo de los tres está en `docs/17-sql-extraccion-completa.md`, ya actualizado.

**Se pueden añadir antes de la mudanza.** Hoy devolverán «SERUNION» en todas las filas, que es
inofensivo: el ámbito sigue entrando por el nombre del centro. El lunes empezarán a devolver el
cliente de verdad sin que nadie tenga que hacer nada.

## Qué mirar el lunes

1. El `clientes_vistos` del resumen de agregados. Si sigue diciendo sólo `SERUNION`, la mudanza no
   ha llegado a los informes.
2. Que el panel de AIRBUS siga trayendo visitas. Si se quedara a cero, es que el centro se renombró
   **y** el informe no lleva todavía la columna `cliente`: con añadirla se arregla.
3. `servicio.por_centro`: si aparecen nombres de centro nuevos, la mudanza vino con renombrado.

## Lo que no se puede arreglar desde aquí

Si VenCloud además **recrea** los centros con un `numcentro` nuevo en vez de reasignar los que hay,
el histórico anterior a la mudanza seguirá llevando los nombres viejos. Las cifras no se pierden
—el ámbito las sigue cogiendo por el nombre del centro—, pero `por_centro` enseñará el centro viejo
y el nuevo como dos. Si pasa, se arregla con una tabla de equivalencias en `perfiles.json`; hasta
saber si pasa, no merece la pena escribirla.

---

# Entró el 4 de octubre

`clientes_vistos` pasó de un solo nombre a los clientes de verdad —Consum, Danone, Almirall, AENA,
Banco de España…— y el mapa situó las **3.168 máquinas** del parque. El campo `cliente` ya manda.

Y con él llegó la pregunta que importaba: **AIRBUS no aparecía entre los primeros cincuenta**, que
es hasta donde llegaba la lista. Eso no quiere decir que su panel se haya roto —el ámbito sigue
entrando por el nombre del centro, y los centros se siguen llamando «AIRBUS GETAFE»—, pero sí que
el resumen no servía para responderla.

Ahora el resumen de cada ejecución trae, por perfil:

```json
"perfiles": [
  {"id": "cli-airbus", "filas": 48123, "centros": 9,
   "declara": ["AIRBUS"], "coincide": ["AIRBUS GETAFE", "AIRBUS ILLESCAS", ...]}
]
```

- **`filas`** es lo primero que hay que mirar. Un perfil a cero no es un mes flojo: es un ámbito que
  ha dejado de encajar. Además se escribe un `AVISO` en el registro, que es lo que ve una alarma.
- **`coincide`** distingue las dos formas de quedarse a cero, que piden arreglos distintos: que el
  nombre ya no exista en VenCloud —y haya que cambiarlo en `perfiles.json`—, o que exista y el
  fallo esté en otra parte.

`clientes` deja de ser una lista cortada por la mitad y pasa a ser `{"total": N, "muestra": [...20]}`:
el total es el dato, y veinte nombres bastan para reconocer que son los de verdad.

## Lo que dijo la primera ejecución con el campo puesto

| perfil | filas | centros |
|---|---|---|
| `interno` | 3.383.019 | 430 |
| `cli-airbus` | 965.564 | 10 |

173 clientes distintos en el parque. El panel de AIRBUS no se vació: el ámbito siguió entrando por
el nombre del centro, como estaba previsto.

Pero el mismo resumen dejó ver dos cosas que no se habrían visto de otra forma.

### AIRBUS no es un cliente que se llame AIRBUS

En `coincide` salieron diez nombres, y los diez son **centros**. Ninguno de los 173 clientes lleva
«AIRBUS» en el nombre. Es decir: el perfil está funcionando **sólo por el nombre del centro**, y eso
depende de que nadie los renombre —que es justo lo que acaba de pasar, ver abajo—.

Por eso el resumen trae ahora `clientes_de_verdad`: bajo qué cliente de VenCloud cuelgan de verdad
los centros que el perfil coge. Con ese nombre en `perfiles.json`, el ámbito deja de depender de
cómo se llame un centro.

### La mudanza vino con renombrado

Los centros de AIRBUS pasaron de nueve a diez, y no porque haya uno nuevo:

- `AIRBUS SAN PABLO` se partió en `AIRBUS SAN PABLO NORTE` y `AIRBUS SAN PABLO SUR`.
- Aparecieron `AIRBUS CBC` y `AIRBUS ITC`.
- `AIRBUS ALBACETE` convive con `AIRBUS ALBACETE (PARQUE CIENTIFICO Y TECNOLÓGICO - UNIV. ALBACETE)`.

No se pierde ni un dato —el ámbito los coge todos—, pero en «visitas por centro» el mismo sitio
puede salir dos veces mientras queden días anteriores a la mudanza dentro de la ventana de 120
días. Se arreglará solo a finales de enero, cuando la ventana deje atrás el 4 de octubre. Si antes
de eso molesta, la salida es una tabla de equivalencias en `perfiles.json`.

## El número, que es lo que no se mueve

Gabriele lo dijo en una frase que vale más que todo lo anterior: **cada centro tiene su número y
cada cliente el suyo.** Y en VenCloud, a 4 de octubre, los centros de AIRBUS **siguen colgando del
cliente Serunion** — por eso ninguno de los 173 clientes lleva «AIRBUS» en el nombre.

Eso deja el ámbito de AIRBUS viviendo del nombre del centro, que es justo lo que acaba de moverse.

Así que `en_ambito` admite ahora las cuatro cosas:

| en `perfiles.json` | encaja con |
|---|---|
| `"centros": ["1001"]` | el **número** de centro — no se mueve |
| `"centros": ["AIRBUS GETAFE"]` | el nombre exacto del centro |
| `"clientes": ["C7"]` | el **código** de cliente — no se mueve |
| `"clientes": ["AIRBUS"]` | un trozo del nombre del cliente **o del centro** |

Lo escrito con números se prefiere siempre. Lo escrito con nombres se deja porque funciona y porque
no todos los perfiles van a reescribirse a la vez, no porque sea igual de bueno. Hay una prueba que
renombra un centro y comprueba que el número sigue encajando y el nombre ya no.

Para saber qué números poner, el resumen de agregados trae `coge_centros` por perfil:

```json
"coge_centros": [
  {"num": "1001", "nombre": "AIRBUS GETAFE"},
  {"num": "1002", "nombre": "AIRBUS ILLESCAS"}
]
```

Se copian los `num` a `ambito.centros` y el perfil deja de depender de cómo se llame nada.

## Los diez números de AIRBUS

El resumen del 4 de octubre los dio, y `perfiles.json` ya va con ellos:

| número | centro |
|---|---|
| 500088 | AIRBUS GETAFE |
| 500089 | AIRBUS ILLESCAS |
| 500090 | AIRBUS ALBACETE |
| 500091 | AIRBUS TABLADA |
| 500092 | AIRBUS SAN PABLO SUR |
| 500093 | AIRBUS SAN PABLO NORTE |
| 500094 | AIRBUS ITC |
| 500095 | AIRBUS CBC |
| 500096 | AIRBUS PUERTO REAL |
| 500244 | AIRBUS ALBACETE (PARQUE CIENTÍFICO Y TECNOLÓGICO - UNIV. ALBACETE) |

Y `clientes_de_verdad` dijo lo que faltaba por confirmar: **`SERUNION, SA`**. Los centros de AIRBUS
no se han reasignado todavía; de ahí que ninguno de los 173 clientes lleve «AIRBUS» en el nombre.

El ámbito queda con **las dos cosas**: los diez números por delante y `"AIRBUS"` detrás. No es
indecisión. El ámbito es aditivo, así que una no estorba a la otra, y cubren huecos distintos:

- El **número** aguanta un renombrado, que es lo que acaba de pasar.
- El **nombre** cubre una máquina que todavía no se haya visto con número en ningún informe —de los
  ocho que se leen, sólo tres traen `num_centro`; el resto se resuelven por el mapa, y el mapa sólo
  sabe el número de las máquinas que han aparecido en alguno de esos tres—.

Hay una prueba que lee el `perfiles.json` de verdad y comprueba las dos vías contra los datos tal y
como los devolvió VenCloud ese día, renombrado incluido. Si alguien cambia un número, salta.

Cuando AIRBUS tenga su propio cliente en VenCloud, se pone su **código** en `clientes` y se puede
quitar la lista de centros entera.
