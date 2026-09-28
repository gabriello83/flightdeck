# La cabecera de visita, leída el 25/09/2026

Primera extracción real de `vending.partesvisita` (informe `EXT_VISITA_CABECERA`, bloque A1 de
[17-sql-extraccion-completa.md](17-sql-extraccion-completa.md)). Un solo día, **2 segundos** de
ejecución, 3.504 filas y 62 columnas.

Dos de los hallazgos cambian el proyecto; el resto son avisos para no equivocarse al construir
las tablas hijas.

---

## 1. De 3.504 partes, sólo 1.107 son visitas de verdad

| `tipo_parte` | filas | qué es |
|---|---:|---|
| 0 | 1.103 | visita real de reponedor |
| 2 | 2.394 | parte del sistema |
| 3 | 3 | parte del sistema |
| 100 | 4 | visita real |

Los 2.397 partes del sistema se reconocen a simple vista: `empleado = SYSTEM`, `cod_ruta = -99`,
`minutos = 0`, `costevisita = 0` y todos con la misma marca de tiempo, `00:00:09`. Nadie estuvo
delante de la máquina.

**Pero no son basura.** 1.270 de ellos traen venta (`vtas_imp`) y 925 traen cajón: son la lectura
automática de máquinas a las que no fue nadie. Carga sí que no traen ninguno — 0 de 2.397 en
`imp_carga` y en `lineas_carga` —, que es exactamente lo que cabe esperar de un parte sin persona.

De ahí las dos reglas, que no son la misma:

- **La extracción no filtra.** Se bajan las 3.504 filas; la lectura de máquina es dato bueno.
- **La cabina filtra siempre que cuente visitas**, tiempos o coste de servicio:
  `coalesce(empleadoid,0) <> 0 and tipo in (0, 100)`.

Sin ese segundo filtro, cualquier indicador sobre visitas sale **más del triple** de lo que es:
3.504 en vez de 1.107, 227 centros en vez de 157, 1.717 máquinas en vez de 1.061.

## 2. `costevisita` viene relleno, y vale 8,00 €

Dábamos el coste de servicio por imposible cuando `pdvs.costemediovisita` salió al 0 %. No lo es:
la cabecera del parte lo trae. En 1.103 de las 1.107 visitas reales, y con **un único valor, 8,00 €**,
igual en todas las delegaciones (los otros 4 partes van a 0).

Es una tarifa interna plana, no un coste calculado, pero sirve: es el número que la casa usa para
valorar una visita.

| | 25/09/2026 |
|---|---:|
| Visitas reales | 1.107 |
| Coste de servicio | **8.824,00 €** |
| Venta telemetría del día | 50.990,43 € |
| Coste de servicio / venta | **17,3 %** |

Extrapolado a los 19 días laborables de septiembre: ~167.656 € de coste de visita contra
1.088.439 € de venta del mes. **Con esto la rentabilidad por máquina vuelve a ser calculable**:
venta − coste de producto − (visitas × 8 €).

La comprobación que falta es cuántas visitas recibe al mes cada máquina. Se responde con el mismo
informe lanzado sobre el mes entero; a 2 segundos por día, cabe de sobra.

## 3. El importe recaudado no está en la visita

340 partes llevan la marca `recaudacion`, pero **sólo 12 traen importe**, y suman 220,80 € — todo
monedas, cero billetes. En 327 de los 340 el `estado_contaje` es 0.

El importe no se escribe cuando el reponedor recoge la bolsa, sino después, al contar. Es decir:
**`imprecauda` no sirve para el día en curso**, y el control de recaudación depende por entero del
informe A5 (contajes) y su detalle. El `cod_bolsa` sí está en los 340, así que la bolsa se puede
seguir desde que sale hasta que se cuenta.

## 4. Corrección: el GPS no está aquí

Dije que `vending.partesvisita.maplatitud` era el camino al GPS. **En las 1.107 visitas del día hay
0 coordenadas.** Los campos existen pero nadie los rellena. Si queremos verificar presencia en
sitio hay que buscarlo en otro lado (la app del reponedor, o el vehículo), no en el parte.

## 5. Qué se rellena y qué no, sobre las 1.107 visitas reales

| campo | relleno |
|---|---:|
| `imp_carga` (29.265,13 € cargados en el día) | 95,9 % |
| `lineas_carga` | 96,0 % |
| `cod_bolsa` | 30,7 % |
| `vtas_imp` | 10,9 % |
| `temp_marcada` | 10,7 % |
| `limpieza` | 8,9 % |
| `imp_cajon` | 7,5 % |
| `beneficio` | 6,9 % |
| `coste_caducidad` | 2,0 % |
| `coste_rotura` | 0,7 % |
| `canales_vacios` | 0,0 % |
| `robo` | 0,0 % |

La carga es fiable: casi todas las visitas dicen qué metieron y por cuánto. Lo demás no: venta,
beneficio y cajón salen de la lectura de la máquina y sólo aparecen en una de cada diez visitas,
así que **el análisis de venta sigue siendo de telemetría, no de parte**. `canales_vacios` al 0 %
confirma que ese campo no se usa; los huecos hay que deducirlos del inventario, no de aquí.

## 6. Duraciones: hay partes mal cerrados

Mediana 6,8 minutos, media 20,2, máximo 387. 189 visitas por debajo de 2 minutos.

La media triplica la mediana por unas pocas rutas con partes que se quedan abiertos:

| ruta | minutos | visitas |
|---|---:|---:|
| Madrid 11 Corredor del Henares | 4.827,3 | 22 |
| Madrid HUPA Secundaria | 1.683,9 | 7 |
| Sevilla 1 - ITC - NORTE | 1.048,9 | 28 |

219 minutos de media por visita en la primera es imposible. Para cualquier indicador de tiempo hay
que usar la mediana, o recortar por encima de un umbral, y de paso sale sola una alarma de
«partes mal cerrados».

## 7. Dimensión de un día

1.061 máquinas visitadas, 157 centros, 58 rutas, 58 empleados. Sobre un parque de ~2.000 máquinas
con venta diaria, **la mitad del parque se toca cada día**.
