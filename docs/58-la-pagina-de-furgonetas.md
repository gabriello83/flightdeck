# 58 · La página de furgonetas

> Gabriele, 16-oct-2026, al revisar el informe general: el cuadrado de Furgonetas era el único que
> no llevaba a ningún sitio («Sin sección todavía»). «Arréglalos los 3 y sube.»

Es lo que abre el cuadrado de **Furgonetas** del informe general (docs/51), en el día del cuadrado
(`/furgonetas/?dia=AAAA-MM-DD`).

## La cifra del cuadrado

Una furgoneta activa es un vehículo **distinto** con alguna visita real ese día en los partes de
VenCloud (`reglas.es_visita_real`: sin los partes automáticos de SYSTEM). No se suman de un día a
otro. VenCloud rellena con «xxxx-xxx» o «xxxxxxx» el vehículo que no se informó
(`operativo.vehiculo_real`): esas visitas están hechas, pero no se sabe en qué furgoneta, y no
cuentan.

## La página, /furgonetas/

> Gabriele, 19-oct-2026: «Quiero ver el listado de todas las furgonetas activas. No me importa
> saber las visitas que han hecho, sí saber si hay furgonetas sin visitas y desde cuántos días.
> Quiero saber los km de cada día y que me ponga en rojo si son menos de 10 o más de 400.»

La primera versión (16-oct) contaba visitas por vehículo; se rehízo entera. Ahora:

- **La flota.** Las furgonetas activas del maestro de vehículos (M12, informe 191): ficha activa
  y no obsoleta, con matrícula, sin SYSTEM, sin las fichas «Ficticio …» que VenCloud usa en los
  sitios fijos (RTVE, Torrespaña, La Paz…) y sin el «Vehiculo Test». Una por matrícula: VenCloud
  tiene matrículas con dos fichas activas (0636MPK, 1424MVF, 5133LWL), y también fichas de baja
  con la matrícula de una activa (1532KFH); las jornadas de cualquiera de ellas son de la misma
  furgoneta. Un perfil de delegación ve las de sus delegaciones y las que visitaron su ámbito; uno
  acotado por clientes o centros, solo las que visitaron su ámbito.
- **Desde cuándo no visita.** Una visita es la de un reponedor en los partes (sin SYSTEM) o la de
  un técnico de la SAT (informe 163), con su furgoneta. Los técnicos no hacen partes de
  reposición: sin la SAT, las CADDY de los técnicos salían siempre sin visitas. La visita de la
  SAT se fecha por su `inicio`, no por el fichero: el informe 163 va por la fecha de la avería, y
  un tercio de las visitas de octubre caen en otro día. Lo de antes del primer día que leyó la
  noche no se sabe, y la página dice «más de N días».
- **Los km de cada día.** Del control de jornada (D5, informe 161): km finales menos iniciales.
  Si una furgoneta tiene varias jornadas el mismo día se suma la unión de sus tramos de
  cuentakilómetros: VenCloud guarda a veces la misma jornada dos veces (3742KFL, 16-oct) y sumarlas
  daba el doble. Rojo si son menos de 10 o más de 400 (`KM_MIN`, `KM_MAX`, viajan
  en el fichero). Lo que no está no es un cero: «sin km» (también en rojo) es una jornada con el
  cuentakilómetros sin anotar (1 o 2, el 30 % de las de septiembre), sin cerrar o con el final por
  debajo del inicio; «—» es que no abrió jornada; «s/d», que no se leyeron las jornadas de ese día.

## Por áreas

> Gabriele, 19-oct-2026: «Cuando entras en furgoneta dame cada cuadrante por área y en el cuadrante
> el porcentaje de las furgonetas que tienen todo correcto. […] La tabla tiene que tener
> matrícula, modelo, km acumulados desde 01/01/2025 hasta ayer, persona que hace la ruta a la que
> la furgoneta está asociada. Una vez entrado en el área están bien los cuatro cuadrantes actuales.
> Seleccionando cada cuadrante filtra la tabla.»

La página abre en una portada con un cuadrante por área (Centro, Sur, Cataluña, Levante, Norte;
la misma `zona_de` de la delegación que usan Incidencias y Rutas, ahora en `operativo.py`). Cada
uno da el porcentaje de sus furgonetas **bien** y cuántas fallan por cada motivo. Una furgoneta
está bien si en los 7 días hasta el día elegido (`SEMANA`) se usó (alguna visita o alguna
jornada) y ninguno de esos días tuvo los km en rojo, ni la jornada sin km. El color sigue los
umbrales de siempre (verde desde 95 %, ámbar desde 75 %). Un perfil con una sola área entra
directo en ella; `?area=` en la dirección abre un área.

Dentro del área, las cuatro cifras de antes, y cada una es un botón que filtra la tabla (pulsarla
otra vez la quita). La tabla lleva:

- **Matrícula** y **Modelo.** El modelo es el de la ficha de VenCloud (`recursos.vehiculosmodelos`,
  informe 191); hoy está vacío en todas las fichas, y la página enseña «—» con la denominación
  debajo, que suele decir el modelo («CRAFTER - Taller»). Cuando lo rellenen en VenCloud saldrá
  solo.
- **Persona de la ruta.** El reponedor titular de la ruta activa que lleva esa furgoneta
  (`m_rutas`); si ninguna ruta activa la lleva, el empleado de su última jornada (M11, informe
  190), y la página lo dice («sin ruta · su última jornada»).
- **Km desde 01/01/2025** hasta el día anterior a la noche que calcula: la suma de los km de todas
  sus jornadas desde `KM_DESDE`, con cuántas jornadas no traían km (esas no suman, y se dice).
- **Estado:** «Bien» o los motivos («sin usar en 7 días», «2 días con km en rojo»).

Lo que se vio con los datos del 16-oct: Centro 11,5 % (3 de 26), Sur 53,3 %, Cataluña 60 %,
Levante 60 %, Norte 44,4 %. Lo que más baja el porcentaje son las jornadas sin km.

## Dentro del área

Arriba, cuatro cifras del día elegido: furgonetas activas, con visitas, sin visitas (y cuántas
llevan más de 7 días) y con km en rojo. La lista va primero con las que llevan más días sin
visitar, con los km de los últimos 7 días; se filtra por delegación, por «sin visitas ese día» o
«con km en rojo», y se descarga en CSV. Debajo, cuántas de la flota visitaron cada día.

Lo que se vio con los datos del 16-oct: de 80 furgonetas activas, 25 no tienen ninguna visita en
45 días (fichas que siguen activas sin usarse, alquileres, «YYYYY»…), y varias rutas de Madrid no
anotan nunca el cuentakilómetros (0636MPK, 2037MRZ, 4909NCJ, 7035NCM).

## El fichero

`cabina/<perfil>/furgonetas.json.gz`, que escriben los agregados cada noche con
`Operativo.detalle_furgonetas`, con el ámbito del perfil aplicado al escribir:

- `flota`: por furgoneta `{m: matrícula, n: nombre(s), d: delegación(es), z: área, mod: modelo,
  p: persona, pr: de dónde sale ("ruta", "jornada" o ""), r: ruta, km: km desde KM_DESDE,
  skm: jornadas sin km}`; `km_desde` es null si la noche aún no tiene el histórico.
- `semana` y `umbrales`: los 7 días de «bien» y los colores del porcentaje.
- `visitas`: por matrícula, los días con visita, `DIAS_VISITAS` (180) hacia atrás; `desde`, el
  primer día leído.
- `km`: por día y matrícula, `[km, jornadas, lo que falta]`; `km` es null si ninguna jornada trae
  el cuentakilómetros bien. Hasta `DIAS_GUARDADOS` (62) días; `dias`, los que se ofrecen.

La noche lee las visitas y las jornadas de toda su ventana (120 días), no solo de los días que
publica, y acumula sobre lo que ya había. Las jornadas no traen centro ni delegación: se leen
enteras y de quién es cada furgoneta lo decide el maestro.

Los km acumulados necesitan todas las jornadas desde el 1-ene-2025, más que la ventana. La noche
guarda un estado compacto, `cabina/_furgonetas/jornadas.json.gz` (por día y vehículo, los tramos
de cuentakilómetros y el empleado), le añade lo que leyó esa noche y lee los días que le falten
mientras le quede tiempo (deja dos minutos de margen). La primera noche lee unos 650 ficheros de
jornadas; si no le da tiempo, sigue a la siguiente, y mientras tanto la columna dice lo que lleva. Se sirve por `/api/furgonetas`, con la
misma regla que el cuadrado: perfil de operaciones o más que vea el cuadrado de Furgonetas
(`autorizacion.CUADRADOS`). No hay parámetro con el que pedir otro perfil. Las tablas que se
pueden quitar a un usuario (docs/61) son la lista (`vehiculos`, sin ella no llegan los km) y el
día a día (`dias`).

El cuadrado del informe general no cambia: furgonetas distintas con alguna visita real ese día.

Pruebas: `infra/test_operativo.py` (la flota, las visitas, los km, el área, la persona, el acumulado y el ámbito),
`infra/test_agregados.py` (un fichero por perfil, con las jornadas sin centro, y el estado del histórico de km),
`infra/api/test_autorizacion.py` (qué se quita con la lista), `infra/api/test_api.py` (quién lo
ve) y `app/comun/prueba_pantallas.js` (la página, en claro, oscuro y móvil, sin peticiones fuera
del dominio).
