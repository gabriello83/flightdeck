# 60 · Utilizo: cuánto usa VenCloud cada persona

Lo pidió Gabriele el 18 de octubre de 2026: saber cada día cuánto utiliza VenCloud cada usuario,
en un cuadrado propio del informe general operativo, **Utilizo**, con su página (`/utilizo/`).
Dos personas trabajan con dos cuentas y se ven como una: **M. García** (`M.GARCIA` y
`M2.GARCIA`) y **J. Marcos** (`J.MARCOS` y `J2.MARCOS`). Esas dos, además, tienen su detalle en
la revisión de clientes (docs/59).

## Lo que enseña

| | qué es |
|---|---|
| **Cuadrado** | cuántos usuarios hicieron algo en VenCloud el último día completo, y cuántas acciones entre todos |
| **El día** | una fila por usuario, el que más primero: acciones, horas con actividad, primera y última, lo que más tocó y cuántos días ha trabajado en los últimos treinta. Con buscador y Excel |
| **El mes** | lo mismo para un mes entero: acciones, días con actividad, horas sumando las de cada día y media de acciones por día trabajado |
| **Un usuario** | pulsando su nombre: sus acciones hora a hora, qué tocó (alta, cambio o borrado de cada cosa), sus días del mes y su historia **mes a mes**, con su Excel |

Una **acción** es cada alta, cambio o borrado que VenCloud apunta en su registro de actividad.
Las **horas con actividad** son las horas distintas en las que hizo algo; con dos cuentas se
cuenta la unión: si las dos trabajaron a las 10, es una hora.

## De dónde sale

`control.activitylog` de VenCloud apunta cada cambio con su usuario y su hora (sonda M14Y, 18-oct).
El informe `M15 · EXT_ACTIVIDAD_USUARIOS` (docs/17, **informe 196**, `actividad_usuarios`) lleva
las dos fechas, como los de visitas, y se baja día a día a `crudo/actividad_usuarios/`, ya contado
por usuario, día y hora, y por usuario, día, cosa y acción. Los usuarios con id negativo son
procesos de VenCloud, no personas, y no entran.

## Con histórico

Gabriele lo quiere con histórico (18-oct). Cada noche se bajan los días de la ventana de reproceso
y la noche los suma a `cabina/_utilizo/actividad.json.gz`, que guarda **toda la historia** (hasta
800 días). Para los días de atrás:

1. Relleno de la extracción, sólo de este informe:
   `{"desde": "2025-01-01", "hasta": "<ayer>", "solo": ["actividad_usuarios"]}` (si se corta por
   tiempo, la respuesta dice desde dónde seguir).
2. Agregados con `{"utilizo_desde": "2025-01-01"}`: relee esos días, uno a uno, y los guarda.

La página lleva de cada día sus cifras (acciones, horas, primera y última) y, sólo de los dos
últimos meses, el detalle por hora y qué tocó: así pesa poco aunque haya años. Un día que vuelve a
llegar sustituye al guardado; el de hoy no se guarda, que va a medias. Si M15 no llega una noche,
se sigue enseñando lo guardado.

- `cabina/<perfil>/utilizo.json.gz` y `foto.utilizo` en `operativo.json`: sólo en los perfiles
  sin ámbito.

## Quién lo ve

Es lo que hace la gente, no un cliente: sólo dirección y administración, y sólo en un perfil sin
ámbito (un perfil de delegación no tiene por qué ver a la gente de otra). La regla está en
`autorizacion.cuadrados_de`, y la API (`/api/utilizo`) sirve el fichero del perfil de la sesión,
comprimido tal cual. Se prueba con `python3 infra/test_utilizo.py`.
