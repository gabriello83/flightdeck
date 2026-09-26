# Septiembre 2026: el mes completo de telemetría

Del 1 al 26 de septiembre, 26 días: **1.199.550 transacciones y 1.088.439,33 €.**

## 1. La cifra que faltaba

El informe 68 daba **881.793,77 €** para septiembre. La telemetría sola, y sólo hasta el día 26,
da **1.088.439,33 €**: un 23 % más, con cuatro días del mes todavía por contar. Proyectando el
mes entero (19 laborables a 50.084 € y 7 fines de semana a 19.550 €) salen unos **1,26 M€**.

No es un matiz, es una diferencia de casi 400.000 € al mes. Antes de poner ninguna cifra de
ingresos en la cabina hay que saber qué mide cada una. Las hipótesis razonables: que el 68
excluya el prepago (184.016 €, 16,9 % del mes), que filtre por algún estado de PDV, o que corte
por fecha de recaudación en vez de fecha de venta. Se resuelve mirando su SQL al lado de este
resultado.

## 2. El mes por medio de pago

| medio | importe | peso |
|---|---|---|
| Tarjeta crédito | 628.638,63 € | 57,8 % |
| Efectivo | 258.490,96 € | 23,7 % |
| Prepago | 184.015,63 € | 16,9 % |
| Otros (`lineaprecio = 11`) | 17.294,11 € | 1,6 % |

Casi seis de cada diez euros entran por tarjeta. El efectivo, que es lo que obliga a recaudar y
lo que genera riesgo de robo y de cuadre, es menos de una cuarta parte — pero son 258.491 € al
mes repartidos en bolsas por toda España, y la regla de los 100 € en bolsa se aplica sobre eso.

Los 17.294 € de `lineaprecio = 11` siguen sin identificar. Es el único medio de pago del que no
sabemos el nombre y ya no es residual.

## 3. La semana tiene dos mitades

| día | días | importe medio | transacciones | máquinas con venta |
|---|---|---|---|---|
| lunes | 3 | 50.797 € | 57.276 | 1.928 |
| martes | 4 | 50.635 € | 56.992 | 1.920 |
| miércoles | 4 | **52.172 €** | 58.284 | 1.938 |
| jueves | 4 | 51.132 € | 57.441 | 1.918 |
| viernes | 4 | 45.861 € | 50.463 | 1.880 |
| sábado | 4 | 20.351 € | 20.235 | **1.251** |
| domingo | 3 | **18.481 €** | 18.021 | **1.101** |

Un laborable medio hace 50.084 € y un día de fin de semana 19.550 €: **el fin de semana es el
39 % de un día normal**. El viernes ya baja un 12 % respecto al miércoles.

Lo más útil para la operación no es el importe, es la última columna. **En laborable venden unas
1.930 máquinas y en fin de semana 1.100.** Esas 830 máquinas que callan el sábado no están
averiadas: están en centros cerrados. Cualquier alarma de falta de ventas que no sepa esto
generará 830 falsos positivos cada sábado y se volverá ruido en una semana. El calendario de
apertura por centro no es un adorno del sistema de alarmas, es su requisito previo.

## 4. El coste sigue cubriendo menos de la mitad

`pct_con_coste` va del **41,6 % al 56,2 %** según el día, y sube justo en fin de semana. Tiene
sentido: el café es lo que no tiene coste, y en fin de semana se vende menos café porque las
oficinas están cerradas. Es la misma conclusión del día suelto, confirmada sobre 1,2 millones de
transacciones: **mientras no se cargue la receta de `stocks.articulosdetalle`, más de la mitad de
las líneas no tienen coste y el margen del mes no se puede cerrar.**

El coste conocido del mes es 252.258,66 € sobre 1.088.439,33 € de venta.

## 5. Dos defectos de mi consulta

1. **`pct_sin_articulo` sale 0 todos los días, y es falso.** En el detalle del día 24, el 20 % de
   las líneas no tienen artículo. La causa: `articuloid` no viene a nulo, viene a **0**. VenCloud
   usa 0 como «sin referencia» en vez de nulo, así que `articuloid is null` nunca se cumple
   mientras el `left join` sí falla. Hay que escribirlo:

   ```sql
   case when coalesce(articuloid,0) = 0 then 1 else 0 end as sin_articulo
   ```

   Esto afecta a cualquier comprobación de clave ajena que hagamos de aquí en adelante: en este
   modelo, «sin referencia» es 0, no nulo.

2. **La venta huérfana no aparece.** El resumen la incluye en el importe (bien), pero no la
   distingue. Conviene una columna más:

   ```sql
   case when coalesce(maquinaid,0) = 0 then precio else 0 end as imp_sin_maquina
   ```
