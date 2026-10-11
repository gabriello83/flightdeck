# 50 · Los preventivos salen de la SAT, y dejan de contar como averías

> `infra/reglas.py` (`es_operacion_preventiva`), `infra/cuadro.py`,
> `infra/api/autorizacion.py` (`SECCIONES_CUADRO`), `app/cuadro/`.

El 11 de octubre de 2026 Gabriele enseñó el «Histórico de tareas técnicas» de VenCloud filtrado por
*Solicitud especial*: los técnicos de AIRBUS registran los preventivos ahí, con la operación
`8888888` **«Preventivo Electrodomésticos Airbus (Interno)»**. David lo había dicho el día 9: *«los
mantenimientos los están registrando en el bloque de SAT (Solicitudes especiales)»*.

## Lo que hay en el crudo

En `crudo/sat_averias/anio=2026/` hay 42 tareas con esa operación, todas de serie E y categoría
«Solicitudes internas»: una el 14 de septiembre y 41 del 5 de octubre en adelante (34 en Getafe, 6 en
Illescas, 2 en San Pablo Sur). Es decir, **se empezaron a registrar en la SAT a primeros de octubre**.

Los 463 «Mantenimineto preveentivo» de enero a septiembre del Excel de David no están: se buscó el texto
en todas las columnas de texto de VenCloud el 8 de octubre y no apareció. Esos no se rellenan.

## Lo que estaba mal

El cuadro cuenta como avería toda tarea de SAT de una máquina (series A y E, como David). Así que los
preventivos de octubre **sumaban averías** a AIRBUS.

## Lo que cambia

- `reglas.es_operacion_preventiva` dice si una operación es de preventivo, por el nombre y sin acentos.
  No vale `es_preventivo` (serie E): la serie E también es reposición, devoluciones y planograma
  (docs/46). La página tiene la misma regla en `isPreventiveOperation`.
- Los preventivos **siguen viajando en las filas de incidencias** de cada mes. Es la página la que los
  aparta: no cuentan como avería en ninguna parte y salen en «Mantenimientos preventivos». Como el
  fichero de mes no cambia, no hay que recalcular la historia.
- El índice ya no dice `preventivos: null`, así que la tabla deja de enseñar «Sin fuente de datos».
  Columnas: fecha, centro, máquina, ubicación, nº de tarea y estado. «Realizada por» se quita: la SAT
  trae el técnico asignado, que no siempre es quien lo hizo (docs/46).
- La parte «Mantenimientos preventivos» pide ahora el flujo de incidencias: un cliente que solo vea esa
  parte recibe las filas de SAT, y nada de venta ni visitas.
- Si un periodo no tiene ninguno, la tabla dice «No hay mantenimientos preventivos registrados en la
  SAT para este filtro»: es lo que se sabe, no que no se hicieran.

## Lo que no cambia

El indicador `sat.preventivos` del panel interno sigue contando la serie E. Está mal por lo mismo, pero
es otra página y otro número; se deja para cuando se pida.
