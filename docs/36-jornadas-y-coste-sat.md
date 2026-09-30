# D5, D9 y D10: la jornada, el coste del SAT, y una alerta de cadena de frío

---

## 1. D5 · La jornada de ruta, y el GPS que llevábamos buscando

1.288 jornadas del 01 al 25 de septiembre: 77 rutas, 77 empleados, 68 vehículos.

El `select c.*` resolvió el error, y resulta que **todas las columnas que había puesto existen**
—`temperaturaini`, `coddispositivo`, las cuatro de GPS—. El fallo estaba en alguno de los cuatro
`join`, no en la tabla. **Se queda el `select c.*` como extracción definitiva**: los `rutaid`,
`empleadoid` y `vehiculoid` se resuelven contra los maestros en el almacén de datos, que además es
más limpio que arrastrar los nombres en cada fila.

### Corrección: el GPS existe, y está aquí

Dije que `vending.partesvisita.maplatitud` era el camino al GPS y venía vacío en las 1.107 visitas
del 25/09. Era cierto para el parte, pero la conclusión —«no hay GPS»— era precipitada.

**El GPS está en la jornada de ruta: 655 de 1.288 tienen coordenada de inicio (50,9 %) y 702 de
fin.** No sitúa cada máquina, pero sí **de dónde sale y dónde termina cada reponedor**, que es lo
que hace falta para verificar la ruta.

### Kilómetros: 75.167 en 25 días

| | |
|---|---:|
| Jornadas con km válidos | 1.063 |
| Mediana | **53 km** |
| Media | 71 km |
| Máximo | 500 km |
| **Total** | **75.167 km** |

Unos 3.000 km al día de flota. Es un dato de coste que no teníamos y sale del cuentakilómetros, no
de una estimación.

### Y las jornadas también se quedan abiertas

Mediana **8,35 h**, que es una jornada normal. Pero la media es **12,05 h**, el percentil 90
**23,23 h** y el máximo **179 h**. Mismo problema que los partes de visita: se abren y no se
cierran. 28 jornadas siguen abiertas.

**Para cualquier indicador de tiempo hay que usar la mediana**, y de paso sale sola una alarma de
«jornada sin cerrar».

## 2. La alerta que no esperaba: la temperatura del vehículo

`temperaturaini` viene **relleno en las 1.288 jornadas**. Es la temperatura del frigorífico del
vehículo al arrancar:

| | |
|---|---:|
| Mediana | **2,0 °C** |
| Mínimo | 0,0 °C |
| Máximo | **26,0 °C** |
| **Jornadas por encima de 8 °C** | **115 · 8,9 %** |

La mediana está donde debe. Pero **casi una de cada once jornadas arranca con la nevera del
vehículo por encima de 8 °C**, y alguna a 26 — temperatura ambiente, es decir, el frío apagado o
averiado.

En una empresa que transporta bocadillos, ensaladas y lácteos, **esto es cadena de frío**. Es el
hallazgo con más consecuencias de todo lo que llevamos, y sale de un campo que ni siquiera
buscábamos. Va directo al cuadro de mando como alarma diaria, con nombre de vehículo y de
reponedor.

## 3. D9 · El SAT cuesta 54.189 € al mes en mano de obra

1.655 visitas técnicas en septiembre sobre 1.536 averías, 62 técnicos y 939 máquinas.

| | |
|---|---:|
| `coste_hora` | **25 €/h** en 1.534 de 1.655 |
| Horas totales | 2.167 |
| **`coste_tiempo`** | **54.189,06 €** |
| `coste_visita` | **0,00 € en todas** |

La aritmética cuadra: 2.167 h × 25 €/h = 54.175 €. **El coste de la mano de obra técnica es
medible mes a mes**, y se puede repartir por máquina, por centro y por cliente.

Puesto en contexto: el servicio de reposición son ~23.000 visitas al mes × 8 € ≈ **184.000 €**, y
el SAT **54.189 €**. El técnico pesa un 29 % sobre el reponedor.

Dos huecos: **541 visitas traen tiempo 0** —un tercio, que baja el coste real— y `coste_visita`
está a cero en las 1.655, o sea que **el coste de desplazamiento no está configurado**. Otro campo
que existe y nadie ha rellenado.

## 4. D10 · Los repuestos se anotan pero no se valoran

100 líneas en septiembre: 70 recambios distintos en 68 máquinas. BOMBA ULKA, VASCHETTA GOCCE, LEVA
BLOCC. VANO EROG., MOTORE PENTAVALENTE.

**`coste_unidad` está relleno en 3 de 100, y el coste total del mes son 35,70 €.** El material del
SAT es invisible.

Y hay una segunda lectura: 100 líneas de material para ~710 averías técnicas al mes. **Sólo una de
cada siete reparaciones registra un repuesto.** O casi todo se arregla sin pieza, o el consumo de
material no se está anotando. Con el coste a cero, hoy no se puede saber cuál de las dos.

## Lo que queda configurado y lo que no

El patrón se repite por tercera vez en este bloque: **VenCloud trae el campo, y está vacío.**

| campo | para qué serviría | estado |
|---|---|---|
| `limite_recaudacion` | la regla de los 100 € en bolsa | **0 en 4.019** |
| `coste_visita` (SAT) | coste de desplazamiento del técnico | **0 en 1.655** |
| `coste_unidad` (repuestos) | coste del material | **0 en 97 de 100** |
| `hora_inicio`, `tiempo_ruta` | planificación de ruta | **vacíos en 161** |
| `maquina_parada` | tiempo de máquina parada | **False en 27.542** |

Ninguno de estos hace falta desarrollarlo. Hace falta rellenarlo.
