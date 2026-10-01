# Qué hacer ahora, paso a paso

Orden real: cada paso depende del anterior. Lo que está **entre corchetes** es una decisión tuya;
lo demás es mecánico.

Al final de la parte 1 ya tienes dato cargándose solo cada noche. La parte 2 (la web) puede
esperar días o semanas sin que eso estorbe.

---

# Parte 1 · La ingesta  ·  *una hora, y queda funcionando*

## Paso 0 · [Decidir dónde] — 5 min

**Recomendado: una cuenta AWS nueva, sólo para digivend.** `AWS Organizations → Add an AWS
account`. Necesitas un correo que no esté ya usado en AWS (vale un alias tipo
`aws-digivend@…`). No cuesta nada: pagas los recursos, no la cuenta. Entras con *switch role*
desde la que ya usas, sin otra contraseña.

Si tiene que ir en la cuenta de siempre, **también está resuelto** y no hay que cambiar nada:
está explicado en [AISLAMIENTO.md](AISLAMIENTO.md).

**Elige región y no la cambies: `eu-west-1`.**

## Paso 1 · Subir la pila — 10 min

`CloudFormation → Create stack → With new resources → Upload a template file` →
**`infra/plantilla.yaml`**.

Parámetros: deja todos los valores por defecto excepto **`AvisoCorreo`**, donde pones tu correo
para que te avise si una noche falla.

Al final del asistente, **marca la casilla**:

> ☑ *I acknowledge that AWS CloudFormation might create IAM resources with custom names*

Tarda unos tres minutos. Cuando ponga `CREATE_COMPLETE`, ve a la pestaña **Outputs** y apunta
`NombreBucket` — lo vas a usar dos veces.

## Paso 2 · El token de VenCloud — 2 min

`Secrets Manager → digivend/vencloud/token → Retrieve secret value → Edit`.

Pega **sólo el token**, en texto plano, sin comillas y sin espacios al final. Guarda.

## Paso 3 · Subir los dos ficheros de configuración — 3 min

`S3 → el bucket del paso 1 → Create folder → config`. Dentro, **Upload** de los dos:

- `infra/manifiesto.json`
- `infra/perfiles.json`

Tienen que quedar exactamente en `config/manifiesto.json` y `config/perfiles.json`.

## Paso 4 · El código de las dos Lambdas — 10 min

**`digivend-extraccion`** es un solo fichero, así que se pega:
`Lambda → digivend-extraccion → pestaña Code`. Borra lo que hay en `index.py`, pega el contenido
de **`infra/lambda_extraccion.py`**, y pulsa **Deploy**.

**`digivend-agregados`** son dos ficheros, así que va en zip. En tu ordenador:

```bash
cd infra && zip agregados.zip lambda_agregados.py reglas.py
```

`Lambda → digivend-agregados → Code → Upload from → .zip file` → ese `agregados.zip` → **Save**.

## Paso 5 · La primera carga, a mano — 5 min + espera

`Lambda → digivend-extraccion → pestaña Test → Create new event` (cualquier nombre, el JSON
`{}` vale) → **Test**.

Tarda varios minutos: son 30 informes por 4 días cada uno.

## Paso 6 · **Mirar el registro. Este es el paso que importa** — 10 min

`S3 → el bucket → registro/extraccion/anio=…/mes=…/` → abre el JSON del día.

Busca `"filas"` en las entradas de `"ok"`:

| lo que ves | qué significa |
|---|---|
| `"filas": 3504` y números parecidos | **Perfecto.** La respuesta se entiende y el dato está |
| `"filas": null` pero `"bytes"` con miles | La descarga fue bien y **lo que no entiende es mi lector**. Pásame el JSON y lo arreglo: son diez líneas |
| entradas en `"errores"` | Mándame el mensaje. Si dice `HTTP 404`, el número de informe de ése no es el que creíamos |

**El dato crudo ya está guardado en `crudo/` pase lo que pase**, porque se graba antes de
intentar interpretarlo. Ninguna noche se pierde por un error de lectura.

## Paso 7 · Los agregados — 3 min

Sólo cuando el paso 6 esté limpio: `Lambda → digivend-agregados → Test → {}` → **Test**.

Comprueba en S3 que aparecen `cabina/interno/panel.json` y `cabina/cli-airbus/panel.json`.
Ábrelos: si las cifras te cuadran con lo que ya sabemos, **la ingesta está terminada**.

A partir de aquí va sola: extracción a las 3:15 y agregados a las 4:45, hora de Madrid.

---

# Parte 2 · La plataforma web  ·  *cuando quieras*

## Paso 8 · [El certificado] — 10 min de trabajo, horas de espera

Es lo único con plazo, así que conviene empezarlo pronto aunque el resto espere.

`Certificate Manager`, **y aquí sí cambias de región: `us-east-1`**. Es la única excepción de
todo el proyecto, y es porque CloudFront sólo acepta certificados de ahí.

`Request certificate → Request a public certificate` → nombre **`dashboard.digivend.es`** →
validación **DNS**.

- Si el DNS de `digivend.es` está en **Route 53**: hay un botón *Create records in Route 53*. Un clic.
- Si está en **otro registrador** (IONOS, GoDaddy, Arsys…): ACM te da un `CNAME` con nombre y
  valor. Hay que crearlo a mano ahí y esperar. **Esto es lo que puede tardar horas.**

Cuando pase a `Issued`, copia el **ARN**.

## Paso 9 · La pila web — 10 min

`CloudFormation → Create stack` → **`infra/plantilla-web.yaml`**. Vuelve a `eu-west-1`.

| parámetro | qué poner |
|---|---|
| `BucketDatos` | el `NombreBucket` del paso 1 |
| `RemitenteAvisos` | una dirección verificada en SES, para las alarmas por correo |
| `Dominio` y `CertificadoArn` | **déjalos vacíos de momento** |

Marca otra vez la casilla de IAM con nombres propios.

Dejarlos vacíos no es pereza: la plataforma funciona igual en la URL que da CloudFront, y el
dominio se añade después **sin tocar una línea de código**, porque la página no tiene ningún
dominio escrito dentro. Así no esperas al certificado para ver si funciona.

Apunta de Outputs: `UrlProvisional`, `BucketWeb`, `Tabla`, `PoolUsuarios`.

## Paso 10 · La clave del asistente — 2 min

`Secrets Manager → digivend/asistente/clave-anthropic` → pega la clave de la API de Claude.

Sin ella **el asistente no funciona y el resto de la plataforma sí**. Si todavía no la tienes,
sáltate este paso y vuelve luego.

## Paso 11 · El código de las tres Lambdas — 10 min

```bash
cd infra/api
zip api.zip comun.py autorizacion.py lambda_api.py
zip alarmas.zip comun.py autorizacion.py lambda_alarmas.py

mkdir -p paquete && pip install anthropic -t paquete/
cp comun.py autorizacion.py lambda_asistente.py paquete/
cd paquete && zip -r ../asistente.zip . && cd ..
```

Sube cada zip a su función: `api.zip` → `digivend-api`, `alarmas.zip` → `digivend-alarmas`,
`asistente.zip` → `digivend-asistente`.

El del asistente pesa unos megas porque lleva el SDK; los otros dos son de kilobytes, porque sólo
usan biblioteca estándar.

## Paso 12 · El primer administrador — 10 min

Es **el único alta que no se puede hacer desde el panel**, porque todavía no hay nadie con quien
entrar. Tres cosas:

**a)** `Cognito → digivend-usuarios → Users → Create user`. Correo el tuyo, marca *Mark email
address as verified*, y pon una contraseña de 12 caracteres con mayúscula, minúscula y número.

**b)** `DynamoDB → Tables → digivend-plataforma → Explore items → Create item → JSON view`, y crea
**dos** elementos. El primero:

```json
{ "pk": {"S": "PERFIL#interno"}, "sk": {"S": "FICHA"},
  "dato": {"S": "{\"nombre\":\"Serunion\",\"tipo\":\"admin\",\"sesiones\":[],\"permisos\":{}}"} }
```

El segundo, **cambiando el correo por el tuyo** (en minúsculas, las dos veces):

```json
{ "pk": {"S": "USUARIO#tu.correo@serunion.es"}, "sk": {"S": "FICHA"},
  "dato": {"S": "{\"nombre\":\"Gabriele\",\"perfil_id\":\"interno\",\"estado\":\"activo\",\"asistente\":true}"} }
```

Las comillas escapadas del campo `dato` son a propósito: dentro va un texto que contiene JSON.

**c)** Sube la página: `S3 → el bucket `digivend-web-…` → Upload` del contenido de `app/consola/`
y `app/airbus/`.

## Paso 13 · Entrar — 2 min

Abre la `UrlProvisional` del paso 9. Entra con tu correo y la contraseña del paso 12a. Te pedirá
cambiarla: es de un solo uso.

Desde dentro ya puedes crear el perfil de AIRBUS y sus usuarios sin volver a tocar la consola de
AWS.

## Paso 14 · El dominio, al final — 5 min + propagación

Un `CNAME` de `dashboard.digivend.es` al nombre que da la salida `DondeApuntaElDns`. Después,
`CloudFormation → la pila web → Update stack → Use existing template`, y rellena `Dominio` con
`dashboard.digivend.es` y `CertificadoArn` con el del paso 8.

---

# Lo que no es tuyo, es mío

Cuando termines el paso 6, pásame el registro y **cierro el único hueco que queda** en todo el
sistema: la forma exacta de la respuesta de `GetReportV2`.

Y queda pendiente enchufar las dos páginas a la API: hoy el acceso de la consola es un prototipo
que no valida contraseñas, y el orden de los paneles se guarda en el navegador en vez de en el
servidor. El backend ya está; es trabajo mío, no tuyo.
