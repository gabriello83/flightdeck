# D8 · El log de SAT, y el catálogo de extracción cerrado

---

## D8 · La trazabilidad del ticket

10.456 eventos sobre **3.037 averías** de septiembre, 1.108 máquinas, 79 personas. Mediana de
**3 eventos por avería**, máximo 12.

Es el único sitio donde se ve **cómo se mueve un ticket**, no sólo cómo empieza y acaba.

### Se asigna al instante, y una de cada nueve cambia de manos

| | |
|---|---:|
| Averías con asignado | 3.014 |
| **Asignadas en menos de un minuto** | **3.011** |
| Reasignadas a otra persona | **349 · 11,6 %** |
| Averías que cambian de área | **1.770 · 58 %** |

La asignación es **automática e inmediata** —mediana de 0,0 minutos—, así que el reparto inicial lo
hace el sistema, no una persona. Lo interesante es lo que pasa después: **el 11,6 % se reasigna** y
**el 58 % cambia de área**, o sea que más de la mitad de los tickets pasan por más de un
departamento antes de cerrarse.

Ese es un indicador de proceso que no teníamos: **cuántas manos toca un ticket antes de resolverse.**

### Y el tiempo de cierre, ahora bien medido

| | |
|---|---:|
| Averías cerradas | 2.809 |
| **Mediana** | **5,5 h** |
| Media | 32,0 h |
| Percentil 90 | 94,4 h |
| Máximo | 522 h |
| **Cerradas en menos de 24 h** | **1.948 · 69,3 %** |

El D7 daba «mediana 1 día» porque sólo tiene fechas sin hora. Con el log, la mediana real es de
**cinco horas y media**, y siete de cada diez se cierran el mismo día. El servicio responde mejor
de lo que parecía.

Lo que sigue siendo el problema es la cola: el percentil 90 está en **casi cuatro días** y hay
tickets de 522 horas.

### Nota

2.940 averías se crean en septiembre y 2.864 se cierran: **el pendiente se mantiene estable**, no
se acumula.

`maquina_parada` vuelve a venir `False` (10.454 de 10.456). Tercera tabla donde ese campo existe y
nadie lo usa. **El tiempo de máquina parada no es medible en VenCloud**, y eso hay que decirlo
claro cuando se hable de disponibilidad.

---

# El catálogo, cerrado

**45 informes lanzados.** Éste es el inventario de lo que alimenta el almacén de datos y lo que
hay que tachar.

## Vivos · 30 informes

| bloque | informes |
|---|---|
| **Visita** | A1 cabecera · A2 reposiciones · A3 inventario · A3B cumplimiento · A3C último · A7 monbil · A8 tubos · A10 devoluciones · A11 ventas |
| **Dinero** | B3 recaudación · B4 detalle IVA |
| **Stock** | C1 almacén · C2 vehículo · C3 máquina · C4 traspasos · C5 regularizaciones · C8 retornos · C9 balance · C10 detalle |
| **Rutas y SAT** | D1 rutas · D2 PDVs · D3 criterios · D4 operarios · D5 jornadas · D6 fondos · D7 averías · D8 eventos · D9 visitas · D10 materiales · D11 catálogo |
| **Maestros** | M1 carriles · M2 recetas |

## Descartados · 11 tablas vacías o inservibles

`partesvisitainvcanales` · `partesvisitacontajes` · `partesvisitacontajesdetalle` ·
`partesvisitaincidencias` · `recogidasbolsasrec` · `recogidasbolsasrecdetalles` ·
`pdvstransbancariasdetalles` · `partesvisitaauditcashlessgroups` · `planrecogida` ·
`plancargarutavehiculo` (una ruta de 58) · `sat.tareatecnica.maquinaparada`

**Una de cada cuatro tablas del modelo no se usa.** No se podía saber sin lanzarlas, y por eso ha
valido la pena ir una a una en vez de programar la Lambda contra el catálogo teórico.

## Las siete reglas del motor, ganadas a base de errores

1. Nada de `::`; los castes van como `cast(x as text)`.
2. Nunca `sum(alias.columna)` en un informe con parámetros: la agregación va dentro de una
   subconsulta y se suma fuera sobre nombres sin prefijo.
3. «Sin referencia» es **0**, no nulo: `coalesce(campo,0) = 0`.
4. Toda consulta necesita `from`, aunque sólo tenga agregados.
5. Nada de varias tablas derivadas cruzadas; una tabla, un `group by`.
6. Los partes del sistema se extraen pero no se cuentan como visitas.
7. Lo que ocurre después de la visita se filtra por su propia fecha, no por la de la madre.

Y una octava, de método: **cuando un informe falle por nombres de columna, `select tabla.*`** —
resolvió `prefacrecauda`, `auditmonbil` y `rutascontrol`.

## Lo que queda antes de construir

- **Aclarar el signo de `dif_inventario`**, que hoy sólo da sobrantes.
- **Comprobar las 1.277 máquinas en más de una ruta activa**, o el coste por ruta se duplicará.
- **Excluir siempre `00SE0000`** de los indicadores de SAT: son 6.497 tickets sin máquina.
- **Pedir los costes de los frescos**, que son los que más caducan y entran a cero.
