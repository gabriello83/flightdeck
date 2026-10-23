# 75 · La historia desde el 1 de enero de 2025, en todas las secciones

> `infra/operativo.py` (`historia_por_mes`, `meses_dias`, `dias_por_mes`, `rutas_por_mes`,
> `furgonetas_por_mes`), `infra/lambda_agregados.py` (`escribe_operativo`,
> `escribe_rutas_por_mes`, `escribe_furgonetas_por_mes`), `infra/api/lambda_api.py`
> (`?mes=` en `/api/operativo`, `/api/rutas` y `/api/furgonetas`) y las páginas `operativo/`,
> `cifras/`, `rutas/` y `furgonetas/`.

Lo pidió Gabriele el 23 de octubre de 2026: *«yo quiero el histórico desde el 01/01/2025 de
todo»*. Y la regla, en el mismo rato: *«dado que los meses una vez cerrados no se modifican, una
vez descargado el histórico no se modificarán»*.

## Qué había el 23-oct

| sección | desde | por qué |
|---|---|---|
| Serie y cuadro de mando | 2025-01-01 | el relleno del 7/8-oct (docs/48) |
| Informe general | 2026-10-06 | el código del relleno estaba (docs/66), nunca se lanzó |
| Rutas | ~13 días | el plan de visitas (D12, informe 184) solo se bajaba desde el 6-oct |
| Furgonetas | 62 días; km acumulados desde 2025 | la página guardaba 62 días |
| Incidencias | 2025-07-18 | M13 (informe 192) trae `current_date - 400` |
| Devoluciones | 2025-10-01 | M16 (informe 198) trae `current_date - 400` |
| Utilizo | 2026-08-22 | M15 (informe 196) no usa las fechas que se le pasan |
| Tarifas, revisión, telemetría | foto de hoy | no tienen pasado (abajo) |

En S3 estaba el crudo diario desde el 1-ene-2025 de todos los informes con fecha, menos el plan de
visitas y la actividad de usuarios. El plan sí lo guarda VenCloud (el 4-mar-2025 trae 1.914 visitas
previstas): se bajó con la extracción `{"desde": "2025-01-01", "hasta": "2026-10-05",
"solo": ["rutas_plan_visitas"]}`.

## Un fichero por mes

Cada sección que tiene días guarda su historia en un fichero por mes, como la serie:

| en S3 | qué es |
|---|---|
| `cabina/<perfil>/operativo/dias-AAAA-MM.json.gz` | los cuadrados del informe general de cada día |
| `cabina/<perfil>/rutas/dias-AAAA-MM.json.gz` | cada día de la página de rutas, sin la lista máquina a máquina, con quién hizo cada ruta (`quien`) |
| `cabina/<perfil>/furgonetas/dias-AAAA-MM.json.gz` | cada día, los km de cada furgoneta (`km`) y las que visitaron (`v`) |

El fichero de cada página sigue llevando los últimos 62 días, que es lo que abre, y ahora además
`meses_dias`: qué días tiene cada mes de la historia (`{"2025-03": [1, 2, …]}`). La página enseña
todos en su calendario o su lista de días y pide un mes (`?mes=AAAA-MM`) solo cuando se elige un
día suyo.

**Un mes cerrado no se reescribe.** La noche escribe los meses de los días que calcula (los
últimos siete) y nada más; el relleno, los de su tramo. Un día que ya estaba lo sustituye el
recalculado, sin pisar lo que sabe mejor la noche (la telemetría con el censo de ese día y las
averías con M13). La primera noche, los días que el fichero de la página tenía y su mes no, pasan
a él; un mes que ya los tiene todos no se toca.

La API sirve el mes de la carpeta del perfil de la sesión, como todo lo demás: el mes es
`AAAA-MM` y nada más, y no hay parámetro con el que pedir el de otro. Las tablas quitadas a un
usuario (docs/61) se quitan también de cada día del mes.

## Lo que no tiene historia

- **Telemetría auditable** de un día del relleno: no hay foto del censo de ese día, así que no se
  sabe qué máquinas llevaban telemetría. El cuadrado lo dice.
- **Furgonetas**: la flota es la de hoy (maestro M12). Una furgoneta dada de baja no sale en los
  meses de antes.
- **Tarifas**: VenCloud no guarda las tarifas antiguas; comparar la venta de 2025 con la tarifa de
  hoy sería inventar una diferencia.
- **Revisión de clientes**: es la configuración de hoy (sin planograma, sin tarifa). Los
  planogramas creados no tienen historia en VenCloud (docs/59).
- **Telemetría por ficheros** (docs/53): los ficheros de Nayax, Prodelfi y Nebula son los de hoy.

## Lo que espera a VenCloud

Tres informes se cambian en VenCloud (el SQL entero, en
`/mnt/project-files/despliegue/historico-secciones/VENCLOUD.md`):

- **196 · M15 · EXT_ACTIVIDAD_USUARIOS**: que use FECHA DESDE (Orden 0) y FECHA HASTA (Orden 1).
  Después, extracción `{"desde": "2025-01-01", "hasta": "<ayer>", "solo": ["actividad_usuarios"]}`
  y agregados `{"utilizo_desde": "2025-01-01"}` (docs/60).
- **192 · M13** y **198 · M16**: `'2025-01-01'` en lugar de `current_date - 400`. Con eso la página
  de incidencias y la de devoluciones tienen 2025 entero; los ficheros pasan a ir por meses como
  los de arriba.

## El relleno

Los mismos tramos de agregados del relleno de la serie (docs/48), de más antiguo a más nuevo:
`{"desde": "2025-01-01", "hasta": "2025-03-31"}` y siguientes hasta el 5-oct-2026. Cada tramo
escribe serie, cuadro, informe general, rutas y furgonetas; si se acaba el tiempo, la respuesta
dice `continuar_desde`. No se lanza nunca a la vez que la noche (03:15–05:15 en Madrid).

## Despliegue

`agregados.zip` primero (el relleno lo necesita), luego `api.zip` y `alarmas.zip` (llevan
`autorizacion.py`) y las páginas `operativo/`, `cifras/`, `rutas/` y `furgonetas/` con
`Cache-Control: no-cache`, más la invalidación. Sin cambios en las pilas: el rol de agregados ya
escribe en todo el bucket y el de la API lee `cabina/*`. Hasta que suban las páginas, las de
producción siguen viendo los últimos 62 días.

Pruebas: `infra/test_operativo.py` (la historia por meses y que un mes cerrado no se reescribe),
`infra/test_agregados.py` (el relleno escribe los tres), `infra/api/test_api.py` (el mes, solo de
su carpeta) y `app/comun/prueba_pantallas.js` («La historia desde 2025»).
