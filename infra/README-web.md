# La plataforma web · dashboard.digivend.es

Pila **separada** de la ingesta. Comparte con ella una sola cosa: el bucket de datos,
y de ese bucket sólo lee la carpeta `cabina/`.

| fichero | qué es |
|---|---|
| `plantilla-web.yaml` | CloudFormation: CloudFront, S3, Cognito, DynamoDB, API Gateway, tres Lambdas |
| `api/comun.py` | sesión, tabla y lectura del panel. **Compartido a propósito** |
| `api/autorizacion.py` | quién ve qué: el techo por tipo de perfil y el recorte del panel |
| `api/lambda_api.py` | acceso, panel, orden, alarmas, acciones, administración |
| `api/lambda_asistente.py` | el asistente |
| `api/lambda_alarmas.py` | evalúa las alarmas cada hora y vacía la cola de envíos |

Cuatro baterías de pruebas, todas sin AWS y sin red:

```
python3 infra/api/test_autorizacion.py   # el techo y el recorte
python3 infra/api/test_api.py            # la API entera contra un AWS falso
python3 infra/api/test_alarmas.py        # alarmas, silencio, cola de WhatsApp
python3 infra/api/test_asistente.py      # la llamada a Claude, falseada
```

---

## Un solo origen: cómo se cumple tu requisito

El navegador habla **sólo** con `dashboard.digivend.es`. No hay ni una excepción:

| lo que podría llamar fuera | cómo se evita |
|---|---|
| la API | `/api/*` es un comportamiento de la misma distribución de CloudFront. Mismo origen, y por eso **no hay CORS** |
| el login | el navegador **no habla con Cognito**. Manda correo y contraseña a `/api/acceso`, y la Lambda habla con Cognito desde dentro de AWS |
| las fuentes | van en el bucket, servidas desde el propio dominio |
| los gráficos | SVG escrito a mano, sin librería |
| el asistente | la página pregunta a `/api/pregunta`; quien llama a la API de Claude es la Lambda |
| WhatsApp | lo envía la Lambda de alarmas |
| VenCloud | lo llama la Lambda de ingesta, de madrugada |

La política de seguridad va como **cabecera HTTP** desde CloudFront, no en una etiqueta
`<meta>`: así vale también `frame-ancestors 'none'`, que en `<meta>` el navegador ignora.

```
default-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self';
frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'
```

Si algún día hiciera falta activar CORS, sería la señal de que algo se ha salido del
dominio. No debería hacer falta nunca.

---

## El acceso, pieza por pieza

**Las contraseñas las guarda Cognito.** Aquí no hay ni un hash: la política de
contraseñas (12 caracteres, mayúscula, minúscula y número), el cambio obligatorio en el
primer acceso y el cifrado son suyos. No hay registro abierto: **sólo el administrador
da de alta**, y la contraseña inicial que pone es de un solo uso.

**La sesión es una fila nuestra, no un JWT.** Es la decisión menos obvia de todo esto, y
tiene un motivo concreto: un token firmado **no se puede retirar** antes de que caduque.
Con una fila en DynamoDB, bloquear a alguien tiene efecto en la siguiente petición. De la
cookie se guarda sólo su `sha256`, así que un volcado de la tabla no entrega sesiones con
las que entrar. La cookie es `HttpOnly; Secure; SameSite=Strict`, y las escrituras
comprueban además `Sec-Fetch-Site`.

**Freno a la fuerza bruta:** seis intentos fallidos y la cuenta queda cerrada quince
minutos. El mensaje de error es **el mismo** si la contraseña es mala y si el correo no
existe: no se dice quién está dado de alta.

---

## El ámbito: por qué un usuario no puede ver el dato de otro

No es una comprobación, es la forma del sistema:

1. **El ámbito se aplica al escribir.** La Lambda de agregados ya dejó un panel por
   perfil, con los centros de ese perfil y ningún otro.
2. **La API lee `cabina/<perfil del usuario>/panel.json`**, y ese perfil sale de la fila
   de sesión. **No existe ningún parámetro con el que pedir otro**: ni por query, ni por
   cuerpo, ni cambiando la ruta. Hay una prueba para cada uno de los tres intentos.
3. **Y encima se recorta**: fuera los bloques que ninguna de sus sesiones necesita, y
   fuera el coste de servicio y el valor de nuestras existencias si no es dirección.
   Lo que no sale de la Lambda no llega al navegador, así que no hay nada que ocultar
   en el cliente.

### El techo de permisos

El administrador concede permisos, pero **no puede conceder lo que el tipo de perfil no
admite**. Marcar «WhatsApp» en un perfil de cliente no se lo da — y la respuesta del alta
**dice qué permisos se han ignorado**, para que el admin no crea que los ha dado.

| tipo | de serie | se puede conceder |
|---|---|---|
| **cliente** | ver, reordenar, exportar | asistente |
| **operaciones** | + ver alarmas | + WhatsApp, incidencia |
| **dirección** | + ver costes, crear alarmas | — |
| **admin** | todo | — |

Lo que sólo sirve para **mirar** viene de serie con el nivel que lo permite. Lo que sirve
para **actuar hacia fuera** (WhatsApp, incidencias) o **cuesta dinero** (el asistente) hay
que concederlo a mano.

Las 16 sesiones del catálogo tienen el mismo techo: un cliente al que le marquen
«Rentabilidad» no la recibe.

---

## El asistente

Lo que lo hace seguro no es el prompt, es **la vía de datos**: recibe exactamente el mismo
panel recortado que el navegador de ese usuario, y no tiene ninguna otra forma de llegar al
dato. No consulta VenCloud, no lee S3 por su cuenta, no escribe SQL. **Si un dato no está
en el panel de ese usuario, el asistente tampoco lo tiene**, así que no puede filtrarlo ni
porque alguien le insista en el chat.

Lo que sí hace el prompt es otra cosa, y también importa: **las diez trampas del modelo van
escritas en el recetario**. Los partes del sistema, el `01/01/1900`, el mes provisional, la
matrícula `00SE0000`, la mediana en vez de la media. El asistente no repite el error que
nosotros tardamos semanas en encontrar.

Tres interruptores en serie, y los tres tienen que estar puestos: **global** (panel de
admin), **por perfil** y **por usuario**. Más un límite diario de preguntas por usuario.
Cuando está apagado, la respuesta **dice cuál de los tres** falta.

### Lo que cuesta

Modelo `claude-opus-5-5`, pensamiento adaptativo, esfuerzo `medium`. El recetario es fijo,
así que viaja en **caché**: se paga entero la primera pregunta y a una décima parte el
resto. Con los precios de hoy (4 $/millón de entrada, 20 $ de salida, 0,20 $ leído de
caché), una pregunta típica sale por **dos o tres céntimos**. Con 40 preguntas al día son
unos 25 € al mes.

Cada respuesta deja en el registro los tokens y el coste. **Si `cache_lectura` sale 0
pregunta tras pregunta**, el recetario no está cacheando y cada pregunta cuesta diez veces
más: se ve ahí, no hay que adivinarlo. Por eso el recetario no lleva **nada** variable —
ni la fecha, ni el nombre del usuario, ni el ámbito. Todo eso va en el mensaje, después
del corte de caché.

Si el modelo declina una pregunta por seguridad, la API reintenta sola en otro modelo
dentro de la misma llamada, así que el usuario no se queda sin respuesta. Si esa opción no
estuviera disponible en la cuenta, la pregunta se hace igual, sin ella.

---

## Las alarmas

Cada hora: evalúa, avisa y vacía la cola. Con una regla que vale más que las demás:

> **Una alarma que no se puede evaluar se dice, no se da por buena.**

Si su fuente todavía no está calculada en los agregados, **no se evalúa a 0 en silencio**:
queda marcada como no evaluable, con el motivo, y sale en el panel de administración. Una
alarma que calla porque no sabe medirse es peor que no tenerla, porque alguien confía en
ella. Del catálogo de 17 fuentes, **6 están pendientes** de que los agregados las calculen
(las de telemetría, días sin visita, días sin contar, cambio en tubos, artículos sin coste
y devoluciones) y la plataforma lo dice en lugar de fingir.

Lo demás: horas de silencio que admiten cruzar la medianoche, y un mismo aviso no se repite
en 24 h. El correo sale por SES; el WhatsApp por la Cloud API de Meta. **Mientras el
secreto de WhatsApp esté vacío, no se envía y se dice el motivo en la bandeja** — no se
finge un envío.

El alta de incidencia en VenCloud es una **escritura en el ERP**. Hasta tener el endpoint y
el permiso confirmados, la petición queda en la cola, visible, y nadie cree que se ha dado
de alta.

---

## La tabla

Una sola, `digivend-plataforma`, con `pk` y `sk`:

| clave | qué guarda |
|---|---|
| `USUARIO#<correo>` / `FICHA` | nombre, perfil, estado, asistente, límite, teléfono |
| `PERFIL#<id>` / `FICHA` | tipo, ámbito, sesiones, paneles, permisos, umbrales |
| `SESION#<sha256>` / `FICHA` | la sesión abierta. **Caduca sola** |
| `PREF#<correo>` / `ORDEN` | el orden de los paneles **de ese usuario** |
| `ALARMA#<id>` / `FICHA` | la alarma |
| `ESTADO_ALARMA#<id>` / `ULTIMO` | cuándo avisó, para no repetir |
| `AVISO#<id>` / `FICHA` | la bandeja |
| `COLA#<id>` / `FICHA` | WhatsApp y altas pendientes |
| `TELEFONO#<empleado>` / `FICHA` | la agenda de técnicos y reponedores |
| `CONFIG` / `GLOBAL` | interruptor del asistente, límite, umbral |
| `USO#<correo>` / `<fecha>` | preguntas y gasto del día. **Caduca a los 40 días** |
| `FALLOS#<correo>` / `CUENTA` | intentos fallidos. **Caduca a los 15 min** |

El orden de los paneles se guarda **en el servidor**, no en el navegador: así el cliente
se lo encuentra igual desde otro ordenador.

---

## Separado de lo que ya tienes

El mismo criterio que la ingesta, y con los mismos mecanismos:

- **Frontera de permisos** `digivend-frontera-web` sobre las tres Lambdas: su tabla, los
  paneles del bucket de datos, su pool, sus dos secretos, sus registros. Nada más.
- **`Deny` explícito sobre `restringido/`**: las devoluciones llevan nombre y DNI y la web
  no las toca nunca.
- Roles con nombre propio, grupo de horarios propio, `Proyecto=digivend` en todo.
- **No referencia ningún recurso existente.** El único enlace con la ingesta es el nombre
  del bucket, que se pasa como parámetro.
- Pila aparte de la ingesta **a propósito**: se puede rehacer la web sin rozar el dato.

---

## Cómo se despliega

### 1. El certificado (lo primero, porque tiene espera)

En **ACM, región `us-east-1`** — no Europa: para CloudFront el certificado tiene que estar
ahí, es la única excepción. Pide `dashboard.digivend.es`, valida por DNS, y guarda el ARN.

Si el DNS de `digivend.es` está en Route 53, la validación se añade con un clic. Si está en
otro registrador, hay que crear un `CNAME` a mano y esperar a que propague.

### 2. La pila

`CloudFormation → Create stack → plantilla-web.yaml`. Marca la casilla de **IAM con
nombres propios** (`CAPABILITY_NAMED_IAM`).

**En el primer despliegue deja `Dominio` y `CertificadoArn` vacíos.** Todo funciona igual en
la URL que da CloudFront, y el dominio se añade después actualizando la pila, sin tocar una
línea de código: la página no tiene ningún dominio escrito dentro.

Pide también `BucketDatos` (el de la ingesta) y `RemitenteAvisos` (una dirección verificada
en SES; sin ella las alarmas por correo no salen y lo dice).

### 3. El código de las Lambdas

Dos de las tres son sólo biblioteca estándar:

```bash
# API y alarmas: nada que instalar
cd infra/api && zip ../api.zip comun.py autorizacion.py lambda_api.py lambda_alarmas.py
```

El asistente lleva el SDK de Anthropic, así que va aparte:

```bash
mkdir -p paquete && pip install anthropic -t paquete/
cp infra/api/{comun.py,autorizacion.py,lambda_asistente.py} paquete/
cd paquete && zip -r ../asistente.zip .
```

### 4. Lo que falta por rellenar

- **Secrets Manager → `digivend/asistente/clave-anthropic`**: la clave de la API de Claude.
  Sin ella el asistente no funciona; el resto de la plataforma, sí.
- **Secrets Manager → `digivend/avisos/whatsapp`**: `{"token": "...", "numero_id": "..."}`.
  Mientras esté vacío, las alarmas de correo funcionan y las de WhatsApp dicen por qué no
  han salido.
- **El primer administrador.** Es el único alta que no se puede hacer desde el panel,
  porque todavía no hay con quién entrar: se crea el usuario en Cognito desde la consola
  y se añaden a mano las dos filas `PERFIL#interno` (tipo `admin`) y `USUARIO#<correo>`
  en DynamoDB. Desde ahí, todo lo demás se hace desde el panel.

### 5. El DNS, al final

Un `CNAME` de `dashboard.digivend.es` al nombre que devuelve la salida `DondeApuntaElDns`.
Actualiza la pila con `Dominio` y `CertificadoArn` rellenos, y listo.

---

## Lo que cuesta

| | |
|---|---|
| CloudFront + S3 | ~1 €/mes con este tráfico |
| DynamoDB por demanda | céntimos |
| Cognito | gratis hasta 10.000 usuarios activos |
| API Gateway + Lambda | ~1 €/mes |
| El asistente | unos 25 €/mes con 40 preguntas al día |

Unos **30 € al mes**, el asistente incluido. Sin él, menos de cinco.
