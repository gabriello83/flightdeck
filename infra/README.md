# La ingesta: Lambda y S3

> **Está en producción desde el 02/10/2026.** 120 días de dato, carga nocturna de 90 segundos,
> agregados de 84. Y comprobado: la cabina reproduce al céntimo las cifras que sacamos a mano
> durante la campaña. Ver [docs/42](../docs/42-la-cabina-en-produccion.md).

Lo que convierte el prototipo en un sistema vivo. Cinco ficheros:

| fichero | qué es |
|---|---|
| `plantilla.yaml` | **CloudFormation**: bucket, secreto, roles, dos Lambdas, horario y alarma |
| `manifiesto.json` | las 30 tablas, con su clave de fecha y su destino |
| `lambda_extraccion.py` | llama a VenCloud y deja el crudo en S3 |
| `reglas.py` | **las trampas del modelo, en código** |
| `lambda_agregados.py` | lee el crudo, aplica las reglas y escribe lo que leen los paneles |
| `AISLAMIENTO.md` | **por qué esto no toca nada de lo que ya tienes en AWS** |

Y dos baterías de pruebas que se ejecutan sin AWS: `test_reglas.py` y `test_agregados.py`.

**La plataforma web es la otra pila**, documentada en [`README-web.md`](README-web.md):
`dashboard.digivend.es`, el acceso, la API, el asistente y las alarmas. Las seis baterías
del proyecto se lanzan de una vez con `sh infra/pruebas.sh`.

---

## La llamada a VenCloud, resuelta

Durante todo el proyecto esto fue el único hueco: el host está bloqueado desde mi entorno, así
que nunca pude comprobar la forma real de `GetReportV2`. **Ya está cerrado**, con una sonda que
probó quince formas de llamada en una sola ejecución (`{"sonda": true}` como evento de prueba).

```
GET  .../VenCloudExternalApi.svc/GetReportV2/{token}/{empresa}/{informe}%7C{desde}%7C{hasta}/
```

Tres detalles, y cada uno costó una respuesta distinta del servidor:

| detalle | cómo se supo |
|---|---|
| **GET**, no POST | con la barra final, un POST devuelve **405** — y un 405 no es «no existe», es «existe y el método no es ése». El `Allow` lo confirma: `GET` |
| **barra final** | sin ella el servicio devuelve **307** redirigiendo a la misma URL con barra |
| **fecha `aaaa-mm-dd`** | con `30/09/2026` devuelve **404** y con `2026-09-30`, 307. La barra de la fecha cae dentro de la *ruta*, e **IIS rechaza por defecto cualquier barra codificada ahí** — es su protección contra el doble escapado y no se puede sortear desde el cliente |

El endpoint se normaliza al arrancar para quitarle la doble barra que arrastrábamos de las notas:
dejarla costaba una redirección en cada una de las 74 llamadas de la noche, para acabar en la
misma URL.

Dos cosas más que dijo la sonda. El servicio **no publica contrato**: `?wsdl` falla porque la
operación `GetReport` devuelve un `Message` en crudo, y no hay página de ayuda REST. Por eso no
había nada que consultar y hubo que medirlo. Y una fecha con hora (`2026-09-30 00:00:00`) da
**400**, lo que confirma de paso que el parámetro se valida de verdad y no se ignora.

### El filtro de fechas: comprobado

La primera carga completa (02/10/2026) cerró **74 de 74 descargas, cero errores, 143,8 MB**.
Y el filtro quedó demostrado sin lugar a dudas: `visita_inventario` devolvió **1.212, 9 y 131
filas** en tres días consecutivos. Un informe que ignorase la fecha no puede producir eso.

Volúmenes medidos, que son los que hay que esperar cada noche:

| | |
|---|---|
| incrementales | **43 MB al día** repartidos en 22 informes |
| maestros | **13,8 MB**, enteros cada noche |
| una noche en régimen | unos **57 MB en crudo**, que comprimidos son muchos menos |

Los conteos cuadran con lo que medimos informe a informe durante la campaña: 10.447 líneas de
tubos al día contra 10.167 esperadas, 6.827 de monedero contra 6.667, 143 tareas de SAT contra
113. Todo dentro de la variación normal entre meses.

### Dos informes que devuelven cero, y está bien

`stock_balance` y `stock_balance_prod` dieron **cero filas los tres días**. No es un fallo: los
dos filtran por `infinventarioresumenes.fecha`, que es la fecha de un **cierre mensual**. Sólo
hay filas el día que se genera el cierre, y ese día no cayó dentro de la ventana.

Tiene dos consecuencias prácticas:

1. **El agregado no puede sumar varios cierres.** En una ventana de 120 días caben tres o cuatro,
   y sumarlos multiplicaría las existencias por cuatro y contaría cada máquina cuatro veces en el
   cumplimiento de inventario. `bloque_inventario` se queda con la foto más reciente y publica de
   qué periodo es.
2. **Si la carga nocturna falla cuatro días seguidos justo en el cierre, ese mes se pierde** hasta
   que se rellene a mano. Es el caso que justifica el modo de relleno histórico.

## Los números de informe · **los 30 rellenos**

Los 30 informes `EXT_*` están creados en VenCloud y el manifiesto lleva su número: del **105 al
172**, sin ninguno repetido. La extracción ya puede arrancar.

La comprobación de que se niega a arrancar con un número ausente sigue ahí, y hace falta: este
fichero se edita a mano y a veces directamente en GitHub. Un número mal copiado no se nota al
guardarlo, se nota a las 3:15 de la mañana — bajando el informe equivocado, que es el fallo más
caro de descubrir después. Por eso `test_manifiesto.py` lo valida antes: números presentes, sin
repetir, claves de fecha del vocabulario, maestro y fecha coherentes, un único informe en
`restringido/` y ninguna tabla muerta colada entre las vivas.

---

## Cómo se despliega

Todo desde la consola de AWS, en **eu-west-1**. No hace falta tener nada instalado.

0. **Decidir dónde.** Lo recomendado es una **cuenta AWS nueva** sólo para esto; si ha de ir en la
   que ya usas, la plantilla está escrita para no tocar nada existente. Está explicado en
   [`AISLAMIENTO.md`](AISLAMIENTO.md).
1. **CloudFormation → Crear pila → Subir `plantilla.yaml`.** Pide prefijo, etiqueta de coste,
   endpoint, empresa, horas de carga y un correo para los avisos. Al final hay que **marcar la
   casilla de IAM con nombres propios** (`CAPABILITY_NAMED_IAM`): los roles se llaman
   `digivend-rol-*` para que se vea de quién son.
2. **Secrets Manager → el secreto `digivend/vencloud/token` → poner el token.** No va en una
   variable de entorno a la vista: así no aparece en la consola de Lambda ni en una captura.
3. **Subir al bucket** `config/manifiesto.json` (con los números rellenos) y `config/perfiles.json`.
4. **Pegar el código** de `lambda_extraccion.py` en la función de extracción, y
   `lambda_agregados.py` + `reglas.py` en la de agregados (esta como zip, porque son dos ficheros).
5. **Lanzar la extracción a mano una vez** y mirar `registro/extraccion/`.

A partir de ahí va sola: extracción a las 3:15 y agregados a las 4:45, hora de Madrid — el
planificador lleva `Europe/Madrid`, así que el horario de verano se arregla solo.

Hay **dos alarmas**, no una: una salta si la carga falla, y la otra si la carga **no ha corrido**
en 24 h. Una noche que no se ejecuta no produce ningún error, así que sin la segunda alarma el
silencio sería indistinguible del éxito.

## Cómo está puesto el bucket

- **Cifrado, sin acceso público y con versiones.**
- El crudo pasa a almacenamiento frío a los 30 días y a Glacier a los 180: se consulta poco después
  del primer mes.
- **`restringido/` es un prefijo aparte** para las devoluciones, que llevan nombre y DNI. El rol de
  agregados tiene un `Deny` explícito sobre él: aunque alguien lo añadiera a un agregado por
  descuido, no podría leerlo.
- El rol de extracción **sólo puede escribir**, no borrar.
- Una política de bucket **rechaza cualquier petición sin cifrar**.

## Y está separado de lo que ya tienes

Los dos roles llevan una **frontera de permisos** (`digivend-frontera`) que sólo les deja tocar
el bucket de digivend, el secreto de digivend y sus propios registros. Es un techo: aunque
mañana alguien les añadiera una política de «S3 en todo», seguirían sin poder leer ningún otro
bucket de la cuenta. La plantilla **no referencia ni adopta ningún recurso existente** —todo lo
crea—, los horarios van en su propio grupo de Scheduler, y todo lleva la etiqueta
`Proyecto=digivend` para que el gasto salga aparte en la factura. El detalle, en
[`AISLAMIENTO.md`](AISLAMIENTO.md).

## El relleno histórico

La carga nocturna trae tres días. **La cabina necesita nueve meses**, y esa historia no la trae
nunca una ventana de tres días: hay que rellenarla una vez.

```json
{"desde": "2026-01-01", "hasta": "2026-01-31"}
```

Como evento de prueba de la Lambda de extracción. Carga ese rango **del día más antiguo al más
nuevo**, y si se le acaba el tiempo **para a los 90 segundos del límite y dice por dónde
continuar**:

```json
{"descargas_ok": 440, "incompleto": true, "continuar_desde": "2026-01-21",
 "_siguiente": "Relanza con {\"desde\": \"2026-01-21\", \"hasta\": \"...\"}"}
```

Se relanza con esa fecha y se sigue. Como los días se cargan en orden, lo ya cargado queda
siempre seguido: no hay huecos que buscar después.

Dos detalles pensados: **un relleno no vuelve a bajar los maestros** —son la foto de hoy, no
tienen historia que rellenar— y **su registro va a `registro/extraccion/historico/`**, para no
pisar el de la noche. Admite también `"solo": ["visita_cabecera"]` para rellenar un informe
suelto, y `"pausa"` para espaciar las llamadas; con esto último, cuidado, que es su ERP.

## La carga es idempotente

Cada fila lleva su `id` y cada día se escribe en su clave
`crudo/<informe>/anio=/mes=/dia=/<informe>.json.gz`. Repetir una noche **sobrescribe la misma clave**;
no duplica.

Y hay una **ventana de reproceso de tres días**: cada noche se vuelven a pedir los tres días
anteriores, porque hay filas que llegan tarde. Son unos pocos megas y evitan agujeros.

---

## `reglas.py` es la pieza que más vale

Cada función de ahí es una trampa que costó encontrar, con su procedencia escrita al lado. Quien
añada un indicador pasa por ahí y no por su cuenta:

| regla | lo que evita |
|---|---|
| `es_visita_real` | contar los partes automáticos como visitas — 3.504 en vez de 1.107 |
| `valor_cargado` | leer `cal_impcarga`, que es carga **neta** |
| `merma` | sumar la caducidad de los tres diarios y contarla dos veces |
| `efectivo_en_cajon` | sumar denominaciones que no son monedas — 8,7 millones en vez de 30 € |
| `recaudacion_del_periodo` | agrupar por fecha de escritura en vez de por periodo contable |
| `mes_provisional` | comparar un mes en curso con uno cerrado y ver una caída del 55 % |
| `tareas_de_maquina` | contar `00SE0000`, que no es una máquina, como el 24 % del SAT |
| `resumen_tiempos` | usar la media cuando los partes se quedan abiertos |
| `v` / `sin_referencia` | tratar el 0 como un valor cuando significa «sin referencia» |
| `fecha_valida` | tomarse el `01/01/1900` como una fecha de 1900 |

## Las pruebas

```
python3 infra/test_reglas.py      # 34 comprobaciones sobre las reglas
python3 infra/test_agregados.py   # la Lambda entera contra un S3 falso
```

No necesitan AWS ni red. Cada comprobación reproduce **una cifra medida de verdad** contra
VenCloud: las 1.107 visitas del 25/09, los 880 € de coste de servicio, el 8,6 % de cumplimiento de
inventario, las 21.046 tareas de SAT sobre máquinas reales. Si alguien cambia una regla y rompe una
prueba, está rompiendo un número ya comprobado contra el ERP.

El test de agregados monta un S3 en memoria, ejecuta el handler y comprueba **el panel que sale**:
que el ámbito de AIRBUS deja fuera a Consum, que el mes en curso sale marcado como provisional con
su aviso, que la matrícula ficticia no cuenta, y que **si falta un informe la carga no se rompe**.

## Lo que cuesta

Unos **10 € al mes**: S3 con el crudo en frío, dos Lambdas que corren una vez al día, y el
planificador. Nada está encendido el resto del tiempo.
