# Consum en Murcia: qué hay, y por qué no aparecía

## La corrección

Busqué Consum en el día de telemetría del 24 de septiembre y sólo salieron dos máquinas, en
Ciudad Real y Toledo. Concluí que quizá no estaba en Murcia. **Estaba equivocado, y el motivo es
interesante: 54 de sus 58 máquinas de Murcia no tienen telemetría.** Buscar a Consum en la
telemetría es como buscar a alguien por la lista de llamadas cuando no tiene teléfono.

## El parque

**58 máquinas en Levante ‑ Murcia**, todas en estado Operativa, más dos fuera de la delegación
(Ciudad Real y Toledo): 60 en total a nivel nacional.

| centro | calientes | frías | snack | total |
|---|---|---|---|---|
| CONSUM S COOP V (305021) | 16 | 27 | 10 | **53** |
| CONSUM LOGÍSTICA INVERSA (305020) | 1 | 2 | 1 | 4 |
| CONSUM COX (500226) | 1 | 0 | 0 | 1 |

Las atiende la **Ruta Murcia Consum (R301, código 3)**, 57 de las 58; la de Cox la lleva la ruta
del Hospital Morales Meseguer.

## Lo que sale al cruzar informes

**1 · Sin telemetría: 54 de 58.** Sólo cuatro llevan Nayax, y en septiembre únicamente una
—26CE5204, la de Cox— registró venta telemétrica: 63,20 € en 21 días.

Esto cambia el diseño de su cuadro de mando. Para AIRBUS, que es casi todo telemetría, la cabina
va de venta en tiempo real. **Para Consum no hay venta en tiempo real que mostrar**: todo tiene
que salir de la visita —reposiciones, inventarios, recaudación— y de la recaudación oficial. Son
dos clientes con el mismo servicio y datos de naturaleza distinta.

Es también la explicación de por qué el informe 52 daba 0 € de ventas para Consum en las dos
delegaciones: no es que no venda, es que nadie se lo mide.

**2 · Tres máquinas sin planograma cargado**, y todas con producto:

| matrícula | modelo | centro | ubicación |
|---|---|---|---|
| `17CE1556` | LEI 700 2 C | CONSUM S COOP V | Camioneros |
| `14FP0266` | SVE 217 | CONSUM S COOP V | Expediciones Muelle 137 |
| `17FP95044` | SVE 217 | CONSUM S COOP V | Seco |

**3 · Los inventarios son viejos.** El más reciente es del 26 de marzo y la mayoría de enero:
entre seis y ocho meses. Y la de Cox (26CE5204) no tiene inventario ninguno, con valor 0.

**4 · Veinte modelos distintos para 58 máquinas.** Cinco de caliente (WINNING T 2 C con 11
unidades es el dominante), diez de frío y cinco de snack. Cada modelo tiene su plantilla de
canales, así que cuanta más variedad, más difícil es estandarizar el planograma y más recambios
distintos hay que llevar.

**5 · `costecompra` está a cero en las 58.** Consistente con el 10,9 % de relleno nacional: la
amortización de este parque no se puede calcular desde el maestro.

## Qué se puede analizar de Consum hoy

Con lo que ya existe, sin pedir nada nuevo: **planograma** de las 55 que lo tienen cargado,
**cargas por artículo** (informe 7, con 136 líneas de Consum), **visitas plan contra realizadas**
(informe 44, 493 líneas), **cargas medias por visita** (informe 45), **temperaturas de la ruta**
(informe 46, 21 jornadas), **recaudación de 12 meses** (informes 42 y 43) e **inventario
valorado**.

Lo que no se puede: venta por hora, mix real de producto vendido, margen por artículo y alarma de
máquina muda. Todo eso necesita telemetría, y aquí no la hay.

## La conversación que esto abre

Cincuenta y cuatro máquinas operativas sin telemetría en un solo cliente es, según se mire, una
carencia o una oportunidad comercial. Con telemetría, Consum tendría el mismo cuadro de mando que
AIRBUS. Sin ella, su servicio se gestiona a ciegas entre visita y visita, y la única señal de que
una máquina está vacía o parada llega cuando el reponedor pasa por allí.
