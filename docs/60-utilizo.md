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
| **Un usuario** | pulsando su nombre: sus acciones hora a hora, qué tocó (alta, cambio o borrado de cada cosa) y su historia día a día, con su Excel |

Una **acción** es cada alta, cambio o borrado que VenCloud apunta en su registro de actividad.
Las **horas con actividad** son las horas distintas en las que hizo algo; con dos cuentas se
cuenta la unión: si las dos trabajaron a las 10, es una hora.

## De dónde sale

`control.activitylog` de VenCloud apunta cada cambio con su usuario y su hora (sonda M14Y, 18-oct).
El informe `M15 · EXT_ACTIVIDAD_USUARIOS` (docs/17) baja cada noche los tres últimos días, ya
contados por usuario, día y hora, y por usuario, día, cosa y acción. Los usuarios con id negativo
son procesos de VenCloud, no personas, y no entran. Hasta que M15 esté en el manifiesto la página
y el cuadrado dicen que falta.

## Lo que escribe la noche

- `cabina/_utilizo/actividad.json.gz`: la historia, dos meses. Un día que vuelve a llegar
  sustituye al guardado; el de hoy no se guarda, que va a medias. Si M15 no llega una noche, se
  sigue enseñando lo guardado.
- `cabina/<perfil>/utilizo.json.gz` y `foto.utilizo` en `operativo.json`: sólo en los perfiles
  sin ámbito.

## Quién lo ve

Es lo que hace la gente, no un cliente: sólo dirección y administración, y sólo en un perfil sin
ámbito (un perfil de delegación no tiene por qué ver a la gente de otra). La regla está en
`autorizacion.cuadrados_de`, y la API (`/api/utilizo`) sirve el fichero del perfil de la sesión,
comprimido tal cual. Se prueba con `python3 infra/test_utilizo.py`.
