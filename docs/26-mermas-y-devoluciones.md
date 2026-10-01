# Mermas y devoluciones, 01 al 25 de septiembre de 2026

Los dos últimos informes grandes de la tanda A. Uno está vacío y el otro es pequeño, y las dos
cosas significan algo.

---

## A9 · Incidencias: vacía. La merma no se registra aquí

`vending.partesvisitaincidencias` devuelve **0 filas** en 25 días. Es la cuarta tabla muerta, tras
`partesvisitainvcanales`, `partesvisitacontajes` y `recogidasbolsasrec`.

No es una pérdida, porque **el dato de caducado sí existe, en otro sitio**: son las líneas `RC`
(retirada por caducidad) y `RR` (retirada por rotura) del A2, que además cuadran al céntimo con
los campos `cal_impcostecaducidad` y `cal_impcosterotura` de la cabecera.

**La merma se mide desde las reposiciones, no desde las incidencias.** El 25/09: 58 líneas `RC`
por 85,26 € y 8 líneas `RR` por 8,42 €. Con artículo, canal, unidades y coste, que es todo lo que
hacía falta.

A9 queda descartada y fuera de la carga nocturna.

## A10 · Devoluciones al cliente: viva, pero casi sin usar

167 devoluciones en 25 días, **409,10 € en toda España**. 112 máquinas, 66 centros, 19 días.

| | |
|---|---:|
| Importe total | 409,10 € |
| Mediana | 2,00 € |
| Media | 2,45 € |
| Máximo | 5,00 € |
| A cero | 0 |

Los importes son creíbles uno a uno —son monedas que se ha tragado la máquina— pero **el total no
lo es**. 167 devoluciones al mes en un parque que mueve 258.000 € de efectivo es prácticamente
nada: una sola máquina con el monedero sucio genera más reclamaciones que eso en una semana.

La lectura no es que no pase, es que **no se registra**. Y hay dos indicios que lo confirman.

### El primero: lo registran dos personas

| reponedor | devoluciones | % |
|---|---:|---:|
| Gerson Eddy Espinoza Moreno | 54 | 32,3 % |
| Miguel Beltran Monzon | 30 | 18,0 % |
| Raúl Sanchez Sarda | 11 | 6,6 % |
| resto (30 personas) | 72 | 43,1 % |

Dos reponedores acumulan la mitad de las devoluciones del país. Con 58 rutas al día y importes de
2 €, lo verosímil no es que a ellos les reclamen diez veces más: es que **ellos lo apuntan y los
demás no**.

### El segundo: el DNI sólo está en el 15,6 %

El nombre del cliente está en las 167. El **DNI sólo en 26**. Si el procedimiento pide identificar
a quien recibe el dinero, se cumple en una de cada seis devoluciones.

### Y aun así hay señal aprovechable

Dos centros concentran el 21 % de todas las devoluciones del país:

| centro | devoluciones |
|---|---:|
| MERIT AUTOMOTIVE ELECTRONICS | 18 |
| AMES BARCELONA SINTERING | 17 |
| PRESEC GAVA | 9 |

Y por máquina, la `22CE4678` con 8 devoluciones y 18,40 €. **Devoluciones repetidas en la misma
máquina son una avería de monedero**, no un problema de caja: esa máquina se está quedando el
dinero de la gente y nadie ha abierto un parte. Eso es un aviso de SAT que sale solo de este
informe, aunque el registro esté incompleto.

## Qué hacer con esto en el cuadro de mando

- **Merma** se calcula del A2 (`RC` y `RR`), no de A9.
- **Devoluciones** entra como alarma de máquina, no como control de dinero: umbral de dos o más
  devoluciones en la misma máquina en un mes, y aviso a SAT.
- El indicador de cumplimiento asociado es **el porcentaje con DNI**, hoy el 15,6 %.
- Y va en su propio prefijo de S3 con acceso restringido, porque lleva nombre y DNI. En la consola
  de cliente no aparece nunca.
