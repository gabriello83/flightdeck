# Despliegue en AWS · eu-west-1 (Irlanda)

Todo lo de este proyecto va con el prefijo **`flightdeck-`** y en su propio bucket, su propio
rol, su propia base de datos de Athena y su propio grupo de trabajo. No comparte nada con lo que
ya tengas en la cuenta: se puede revisar entero, o borrar entero, sin tocar nada más.

| recurso | nombre | para qué |
|---|---|---|
| Bucket S3 | `flightdeck-vending-NUMERODECUENTA` | todos los datos |
| Función Lambda | `flightdeck-extraccion` | llama a la API cada noche |
| Rol IAM | `flightdeck-extraccion-rol` | permisos de la Lambda |
| Programación | `flightdeck-nocturno` | el cron de las 3:00 |
| Base de datos Athena | `flightdeck` | las tablas para consultar |
| Grupo de trabajo Athena | `flightdeck` | separa consultas y costes |

`NUMERODECUENTA` son los 12 dígitos de tu cuenta AWS: los ves arriba a la derecha en la consola.
Los nombres de bucket son únicos en todo el mundo, por eso hay que añadirlos.

**Antes de empezar**: arriba a la derecha de la consola, comprueba que la región dice
**Europa (Irlanda) eu-west-1**. Si te equivocas de región no verás los recursos que creaste.

---

## Paso 1 · El bucket

Consola → busca **S3** → **Crear bucket**.

- Nombre: `flightdeck-vending-NUMERODECUENTA`
- Región: **Europa (Irlanda) eu-west-1**
- **Bloquear todo el acceso público**: déjalo marcado, que viene así por defecto
- Cifrado del lado del servidor: **SSE-S3**, que también viene por defecto
- Versionado: **activar** (protege de un borrado accidental)
- Lo demás, por defecto → **Crear bucket**

## Paso 2 · La función Lambda

Consola → **Lambda** → **Crear una función**.

- **Crear desde cero**
- Nombre: `flightdeck-extraccion`
- Tiempo de ejecución: **Python 3.12**
- Arquitectura: `arm64` (más barata, da igual para esto)
- Permisos: deja que cree un rol nuevo. Luego lo renombramos mentalmente; el que cree vale.
- **Crear función**

Ya dentro, en la pestaña **Código**: borra lo que hay en `lambda_function.py` y pega entero el
contenido de `lambda_extraccion.py` de esta carpeta. **Deploy**.

No hay que empaquetar nada ni subir ningún zip: el código sólo usa la biblioteca estándar de
Python y `boto3`, que Lambda ya trae puesto.

### Configuración → Configuración general → Editar

- Memoria: **512 MB**
- Tiempo de espera: **5 min** (viene con 3 segundos, que no llega ni de lejos)

### Configuración → Variables de entorno

| clave | valor |
|---|---|
| `VENCLOUD_ENDPOINT` | `https://vencloudpro.eac.es/2311_api/webservices//VenCloudExternalApi/VenCloudExternalApi.svc` |
| `VENCLOUD_TOKEN` | el token |
| `VENCLOUD_EMPRESA` | `2311` |
| `BUCKET` | `flightdeck-vending-NUMERODECUENTA` |
| `FORMATO_FECHA` | `%d/%m/%Y` |
| `INFORMES` | el JSON del paso 3 |

### Configuración → Permisos → pincha en el nombre del rol

Se abre IAM. **Agregar permisos → Crear política insertada → JSON**, pega el contenido de
`politica-s3.json` cambiando `NUMERODECUENTA`, y llámala `flightdeck-escribir-s3`.

Sin esto la Lambda llama bien a VenCloud pero no puede guardar nada.

## Paso 3 · Decirle qué informes bajar

La variable `INFORMES` es un JSON. **Los números de informe los tienes que poner tú**: son los
que VenCloud asigna a cada informe rápido que has creado. Se ven en el listado de informes.

```json
{
  "ventas_dia":   {"informe": "PON_EL_NUMERO", "fechas": "ayer",    "ruta": "crudo/ventas"},
  "maquina_dia":  {"informe": "PON_EL_NUMERO", "fechas": "ayer",    "ruta": "crudo/maquina_dia"},
  "resumen_dia":  {"informe": "PON_EL_NUMERO", "fechas": "ayer",    "ruta": "crudo/resumen"},
  "articulos":    {"informe": "PON_EL_NUMERO", "fechas": "ninguna", "ruta": "maestros/articulos"},
  "maquinas":     {"informe": "PON_EL_NUMERO", "fechas": "ninguna", "ruta": "maestros/maquinas"}
}
```

`fechas` admite tres valores: `ayer` (desde y hasta = ayer), `mes_actual`, o `ninguna` para los
informes sin parámetros.

**Empieza con uno solo.** Pon nada más `ventas_dia`, comprueba que funciona, y ve añadiendo.

## Paso 4 · Probar a mano

Pestaña **Probar** → crea un evento de prueba con `{}` dentro → **Probar**.

Lo que tiene que pasar: en el resultado aparece `primeros_200`, que son los primeros 200
caracteres de lo que devolvió VenCloud. **Eso es lo que necesito ver.** Cópiamelo y escribo el
intérprete que convierte la respuesta en tablas.

Si falla, el mensaje dirá si fue HTTP 401 (token), 404 (número de informe o endpoint), o si no
pudo conectar. El token nunca sale en los registros: va enmascarado.

## Paso 5 · La programación nocturna

Consola → **EventBridge** → **Programador** → **Crear programación**.

- Nombre: `flightdeck-nocturno`
- Patrón: **programación basada en cron**
- Expresión: `0 3 * * ? *`
- **Zona horaria: Europe/Madrid** ← importante, si no se te desplaza con el cambio de hora
- Ventana flexible: **desactivada**
- Destino: **AWS Lambda / Invoke** → función `flightdeck-extraccion`
- Deja que cree el rol de ejecución
- **Crear**

## Paso 6 · Athena (cuando ya haya datos)

Sólo tiene sentido después de saber qué formato devuelve la API, así que esto va al final.

Consola → **Athena** → **Editor**. La primera vez pide dónde dejar los resultados:
`s3://flightdeck-vending-NUMERODECUENTA/athena-resultados/`.

Después, crea el grupo de trabajo `flightdeck` y la base de datos:

```sql
create database if not exists flightdeck;
```

El `create table` lo escribo yo cuando vea el formato real de los ficheros.

---

## Lo que cuesta

Con vuestro volumen, **por debajo de 10 € al mes**: S3 son unos pocos GB a 0,023 $/GB, Lambda
entra en la capa gratuita de sobra (una ejecución diaria de segundos), EventBridge es gratis
hasta millones de invocaciones, y Athena cobra 5 $ por terabyte escaneado mientras nosotros
escaneamos megas gracias a las particiones por fecha.

## Por qué el token va en una variable de entorno y no en Secrets Manager

Para empezar, una variable de entorno de Lambda está cifrada en reposo y sólo la ve quien tenga
permiso sobre la función. Es suficiente y es un paso menos. Cuando esto esté en marcha, moverlo
a **Secrets Manager** es media hora y son 0,40 $ al mes: la ventaja real es que se puede rotar
el token sin tocar la función. Lo dejo apuntado como mejora, no como requisito.

Y recuerda: **el token actual ha circulado por un chat.** Cuando esto pase a producción, pídele
uno nuevo a EAC y deja este muerto.
