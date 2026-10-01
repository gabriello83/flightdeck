# El catálogo de SAT · D11

**101 operaciones, 6 categorías.** Es el diccionario que le faltaba al SAT: D7 trae el código
de operación de cada tarea, pero hasta ahora no sabíamos qué operaciones existen, cuáles están
retiradas, ni con qué criterio se agrupan.

Las dos sondas confirmaron las doce columnas que había inferido del modelo. **Todas existen.**
El SQL definitivo está en [17-sql-extraccion-completa.md](17-sql-extraccion-completa.md), D11.

---

## 1. Lo importante: la categoría no clasifica

Esto es lo que el catálogo cambia, y cambia una cifra que yo ya había publicado.

La categoría de una operación dice **en qué lista se archivó**, no si es un fallo técnico. El
caso que lo demuestra sin discusión:

| operación | categoría |
|---|---|
| `T08 · CAFÉ - Distribuidor fuera de servicio` | AVERÍAS TÉCNICAS |
| `C06 · SNACK/BEBIDA - Distribuidor fuera de servicio` | **ATENCIÓN AL CLIENTE** |

La misma avería. La única diferencia es si la máquina es de café o de snack. Y `C06` no es un
caso marginal: son **2.694 tareas**, la cuarta operación más usada de todo el SAT.

Peor: **`TECNICO - Vandalismo` existe dos veces, con el mismo nombre y las dos activas** —
`C14` en ATENCIÓN AL CLIENTE y `00000012` en AVERÍAS TÉCNICAS. El técnico elige, y según lo
que elija el vandalismo cuenta como avería o no.

### Las nueve operaciones de ATENCIÓN AL CLIENTE que son fallo técnico

| código | operación | severidad |
|---|---|---|
| C06 | SNACK/BEBIDA - Distribuidor fuera de servicio | 2 |
| C11 | TECNICO - No funciona pantalla | 2 |
| C12 | CAFÉ - Avería sistema de pago | 1 |
| C13 | SNACK/BEBIDA - Producto no entregado | 1 |
| C14 | TECNICO - Vandalismo | 1 |
| C18 | TECNICO - Puerta abierta | 2 |
| C19 | TECNICO - Luz del distribuidor apagada | 0 |
| C23 | PAGO - No devuelve cambio | 1 |
| T40 | TECNICO - No funciona display | 1 |


### Lo que eso le hace a la cifra

| | tareas de 2026 |
|---|---|
| Total del SAT | 27.543 |
| «Averías técnicas» **contando por categoría** | 6.400 |
| **Fallos técnicos contando por operación** | **10.223** |

Un **60 % más**. El desglose de los 3.823 que faltaban: 3.410 estaban en ATENCIÓN AL CLIENTE
y 413 en operaciones ya retiradas (Obsoletas). Las 83 operaciones usadas en 2026 casan todas
con el catálogo, sin una sola huérfana, así que la cuenta cierra.

**Esto corrige [34-sat-averias.md](34-sat-averias.md)**, donde escribí que una de cada cuatro
tareas era avería técnica. Es más de una de cada tres.

---

## 2. Las seis categorías

| id | tipo | nombre | operaciones |
|---|---|---|---|
| 1 | 1 | ATENCION AL CLIENTE | 20 |
| 2 | 3 | Solicitudes cliente | 14 |
| 9 | 3 | Devolución dinero | 6 |
| 10 | 1 | AVERIAS TECNICAS | 36 |
| 11 | 1 | Obsoletas | 23 |
| 12 | 3 | Solicitudes internas | 2 |


`tipo` vale **1** (avería o incidencia) o **3** (solicitud), y `op.tipo` repite exactamente el
de su categoría en las 101 filas: es redundante, no hace falta extraer los dos.

---

## 3. «Obsoletas» es el cementerio, y tiene un vivo dentro

23 operaciones, **22 desactivadas**. La convención de nombre es clara: las retiradas empiezan
por `Z.` — `Z.No sale café`, `Z.Snack - Atasco en espiral`, `Z.Precio no correcto`.

La que no empieza por `Z.` es exactamente la que sigue **activa**:

> **`A036 · TECNICO - VARIOS`**, severidad 1, descripción: *«Solo Peticiones internas»*.

Un cajón de sastre aparcado en la carpeta de obsoletas pero todavía usable. Cualquier tarea
que caiga ahí queda sin clasificación real. No ha salido en el top de 2026, pero conviene
decidir si se desactiva o se saca de Obsoletas, porque ahora mismo está en el peor sitio
posible: disponible y escondido.

---

## 4. Lo que el catálogo NO nos da

Fui a buscar un tiempo estimado por operación para poder comparar lo previsto con lo real en
SAT. **No existe**: `tiempoestimado` es 0 en 98 de las 101. Las tres que lo tienen no son
averías:

| código | operación | minutos | categoría |
|---|---|---|---|
| S010 | Reponer distribuidor automatico | 4 | Solicitudes cliente |
| S12 | Ajuste molino | 15 | Solicitudes internas |
| S013 | Instalación nueva maquina | 30 | Solicitudes cliente |


Así que **no hay línea base de tiempo esperado**. Si queremos medir si una avería tardó más de
lo normal, el patrón hay que sacarlo del histórico de D8, no del catálogo.

Tampoco hay fabricante: `fabricanteid` es **nulo en las 101**, así que la relación con
`general.fabricantes` que había escrito es una join que no devuelve nada. Fuera.

Y tres columnas son constantes: `notificaemail` (`false` en todas), `qrcs` (`false` en todas)
y `causaccep` (nula en todas). No se extraen.

---

## 5. La severidad está a medias

Vale 0, 1 o 2 — y en este modelo **0 es «sin referencia»**, no «severidad cero». Hay **12
operaciones sin severidad asignada**, y 5 de ellas están en AVERÍAS TÉCNICAS:

| código | operación |
|---|---|
| T21 | PAGO - Atasco billetes |
| T22 | PAGO - No acepta billetes |
| T29 | SNACK/BEBIDA - Atasco producto |
| T37 | TECNICO - Compresor ruidoso |
| T45 | CAFÉ - Recoge gota roto |


Un atasco de billetes y un compresor ruidoso no son severidad cero: es que nadie la puso.
Cualquier priorización por severidad trataría estas cinco como las menos urgentes de todas.

---

## 6. `averiarapida` sí dice algo

47 operaciones marcadas como «avería rápida», 54 no. Y el reparto tiene sentido: dentro de
AVERÍAS TÉCNICAS **casi todas son rápidas menos cuatro**, y las cuatro son justo las que
necesitan pieza o especialista:

| operación | por qué no es rápida |
|---|---|
| `C08 · CAFÉ - Distribuidor pierde agua` | fuga: hay que abrir |
| `C09 · SNACK/BEBIDA - Distribuidor no enfría` | circuito de frío |
| `T02 · CAFÉ - Atasco paletinas` | (llama la atención que esta no lo sea) |
| `00000012 · TECNICO - Vandalismo` | depende del daño |

Es el campo que mejor sirve para separar «lo arregla el reponedor en la visita» de «hay que
mandar un técnico», y hoy no lo estamos usando.

---

## 7. El código no es una clave que se pueda interpretar

Los prefijos no clasifican nada. `C` aparece en tres categorías distintas, `T` también:

| prefijo | categorías en las que aparece |
|---|---|
| `T` | AVERÍAS TÉCNICAS (31), Obsoletas (7), ATENCIÓN AL CLIENTE (2) |
| `C` | ATENCIÓN AL CLIENTE (14), Obsoletas (7), AVERÍAS TÉCNICAS (3) |
| `A` | Obsoletas (9) |
| `S` | Solicitudes cliente (13), internas (1) |
| `DEV` | Devolución dinero (6) |
| `D` | ATENCIÓN AL CLIENTE (3), AVERÍAS TÉCNICAS (1) |

Y hay cuatro códigos hechos a mano que rompen cualquier patrón: `999999999` (auditoría de
máquina), `8888888` (preventivo de electrodomésticos de AIRBUS), `888889` (sugerencias del
responsable de AIRBUS) y `00000012` (el vandalismo duplicado). **No parsear el código.**

Además hay una operación con **`id = -1`**: `T55 · Z.Precio no correcto`, desactivada. Se
suma a la lista de centinelas del modelo, con el 0 de «sin referencia» y el `01/01/1900` de
«nunca». Código que asuma que los identificadores son positivos se la salta.

---

## 8. La clasificación propuesta

Con el catálogo cerrado se puede clasificar por operación en vez de por categoría. He marcado
**65 de las 101 como fallo técnico**, y las 36 restantes con el motivo por el que no lo son:
limpieza, devolución de dinero, configuración, reposición, trabajos de instalación y la
auditoría.

Está en `carga/catalogo_sat.xlsx`, con una columna por operación para que la revises. **Es
una propuesta, no un hecho**: tres casos son discutibles y los dejo señalados —
`T49 · Instalar Cable DEX` (es un trabajo, no una avería), `C16 · Producto caducado` (calidad
del producto, no de la máquina) y `C016 · SELECCIONES VACÍAS` (reposición). Si cambias alguno,
cambia la cifra de 10.223.

La propuesta vive también en `infra/reglas.py`, con sus pruebas, para que ningún indicador
futuro vuelva a contar por categoría sin querer.
