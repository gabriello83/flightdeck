# La ingesta: Lambda y S3

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

## Lo único que no está probado contra la API real

**Nunca hemos hecho una llamada a VenCloud desde aquí**: el host está bloqueado por la política de
red del entorno. Lo que no sabemos con certeza es **la forma exacta de la respuesta** de
`GetReportV2`.

Por eso la extracción está escrita para que eso no pueda costar una noche de datos:

1. **Primero guarda los bytes tal cual**, comprimidos, en `crudo/`. Pase lo que pase después, el
   dato está.
2. **Después intenta contar las filas** con un lector tolerante que reconoce las envolturas
   habituales (`Rows`, `Data`, `Table`, `d`, lista pelada). Si no reconoce ninguna, **devuelve
   `null` en vez de inventarse un número**.
3. El registro de cada noche queda en `registro/extraccion/`, con bytes y filas por informe.

La primera carga se lanza **a mano**, se mira ese registro, y si el lector no reconoció la
envoltura se ajusta una función de diez líneas. No hay nada más que adivinar.

## Los números de informe están a null, a propósito

En `manifiesto.json`, el campo `informe` de cada entrada está vacío. Hay que rellenarlo con el
número que VenCloud asigne a cada `EXT_*` al crearlos. **La extracción se niega a arrancar si falta
alguno** y dice cuáles: preferimos parar a bajar el informe equivocado en silencio.

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
