# D7 · Las averías, y una corrección grande sobre las devoluciones

27.543 tareas técnicas de enero a septiembre de 2026. 2.722 máquinas, 434 centros, 101 técnicos.
El sistema arranca a finales de enero —182 tareas ese mes— y desde febrero va a **~3.400 al mes**.

---

## 1. Corrección: las devoluciones sí se registran, y son 15.583

Cuando analicé el A10 (devoluciones en la visita) dije que 167 devoluciones y 409,10 € en 25 días
eran «prácticamente nada» y que **el proceso no se registraba**. Estaba mirando el sitio
equivocado.

**Se registran aquí, y son 15.583 en nueve meses — el 57 % de todas las tareas de SAT.**

| operación | tareas |
|---|---:|
| DEVOLUCIÓN · Transferencia bancaria | 4.946 |
| DEVOLUCIÓN · In situ | 4.614 |
| Devolución dinero in situ | 2.946 |
| DEVOLUCIÓN · Tarjeta de crédito | 1.811 |
| DEVOLUCIÓN · Tarjeta empleado | 1.266 |

Unas **1.730 al mes**, contra las 167 en 25 días del A10. **Diez veces más.**

Y se entiende por qué: el cliente **no espera al reponedor**. Llama, abre ticket, y se le devuelve
por **transferencia bancaria (32 %) o tarjeta (20 %)**. El A10 sólo ve el caso minoritario —el
reponedor que estaba allí y devolvió en mano— y por eso salía tan pequeño.

**Lo que dije del A10 sigue siendo cierto en lo suyo** (el DNI sólo en el 15,6 %, dos reponedores
concentran la mitad), pero la conclusión de que «el proceso no se registra» era falsa. Se registra,
en SAT.

Para el cuadro de mando: **las devoluciones se miden desde D7, no desde A10.** El A10 queda como
el subconjunto de las que se pagan en mano.

## 2. Sólo una de cada cuatro tareas es una avería técnica

| categoría | tareas | % |
|---|---:|---:|
| **ATENCIÓN AL CLIENTE** | 16.754 | 60,8 % |
| **AVERÍAS TÉCNICAS** | 6.400 | 23,2 % |
| Devolución dinero | 2.951 | 10,7 % |
| Solicitudes cliente | 995 | 3,6 % |
| Obsoletas | 423 | 1,5 % |

Llamar «averías» a esta tabla es engañoso: es **el buzón de atención al cliente**. Las averías de
verdad son 6.400 en nueve meses, unas 710 al mes sobre 3.200 máquinas operativas — **una avería
por máquina cada cuatro meses y medio**.

Las operaciones más frecuentes que sí son técnicas: distribuidor fuera de servicio en snack/bebida
(2.694) y en café (1.617), reponer distribuidor (949), carril fuera de servicio (461) y calidad no
conforme en café (458).

## 3. Se resuelve rápido

| | |
|---|---:|
| Cerradas | 26.766 |
| Sin fecha de cierre | 777 |
| **Mismo día** | **11.542 · 43,1 %** |
| Mediana | **1 día** |
| Percentil 90 | 10 días |
| Más de 30 días | 1.370 |
| Máximo | 211 días |

43 % se cierra el mismo día y la mediana es de un día. El problema no es la velocidad: es la
**cola larga**, 1.370 tareas de más de un mes y 777 que nunca se cerraron.

## 4. Reincidencia: 198 máquinas con veinte averías o más

| matrícula | tareas |
|---|---:|
| `00SE0000` | 6.497 |
| `18FE1538` | **355** |
| `21SE1806` | 130 |
| `20FE1597` | 115 |
| `22FE1651` | 111 |

**`00SE0000` no es una máquina**: es la matrícula ficticia del CENTRO TEST, delegación CENTRAL.
Son 6.497 tickets sin máquina asignada, el 24 % del total. **Hay que excluirla de cualquier
indicador**, y de paso preguntar por qué una de cada cuatro incidencias no se asocia a una máquina
real.

Descontada, quedan **21.046 tareas sobre máquinas reales**. Y ahí:

- 420 máquinas con una sola tarea,
- **1.317 con cinco o más**,
- **198 con veinte o más**.

`18FE1538` acumula 355 tareas en nueve meses: más de una cada dos días. Eso no es una máquina que
se avería, es una máquina que hay que retirar.

## 5. Dos campos que no sirven

- **`maquina_parada` es `False` en 27.542 de 27.543.** No se puede medir tiempo de máquina parada
  desde aquí.
- **`facturable` es `True` en las 27.543.** Sin uso.

## Entregable

[`carga/sat_averias_2026.xlsx`](../carga/sat_averias_2026.xlsx): máquinas reincidentes con su
desglose y tiempo de cierre, catálogo de operaciones por volumen, y resumen por delegación.
