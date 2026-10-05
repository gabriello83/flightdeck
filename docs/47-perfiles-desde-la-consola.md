# 47 · Un cliente nuevo se da de alta en la consola

> `infra/lambda_agregados.py` (`perfiles_de_la_consola`, `junta_perfiles`), `infra/plantilla.yaml`
> (el permiso), `app/consola/` (los avisos).

Hasta ahora un perfil vivía en dos sitios. En la **consola** (DynamoDB) estaban sus sesiones,
permisos y usuarios; en **`config/perfiles.json`** (S3), la lista de paneles que se calculan cada
noche con su ámbito. Dar de alta un cliente en la consola no bastaba: había que añadir además su
fila al fichero y subirlo, y si se olvidaba, sus usuarios entraban a «todavía no hay datos».

Ahora la Lambda de agregados lee también los perfiles de la consola. **Crear el perfil en la consola,
con su ámbito, basta**: esa noche, a las 4:45, se le calculan su panel y su cuadro.

## Cómo se juntan las dos fuentes

| el perfil está… | qué se calcula |
|---|---|
| sólo en la consola, **con** ámbito | su panel, con ese ámbito |
| sólo en la consola, **sin** ámbito | **nada**, y el resumen lo dice (`consola.sin_ambito`) |
| en los dos | la **suma** de los dos ámbitos: la consola añade, nunca quita |
| sólo en el fichero | como antes |

Dos decisiones a propósito:

- **Sin ámbito no se calcula.** Un ámbito vacío es «todo el parque». Un perfil de cliente creado con
  los tres campos sin rellenar vería los datos de todos los clientes. «Todo el parque» sólo se
  declara en `perfiles.json`, a mano: es el perfil `interno`, y la consola no lo recorta ni lo amplía.
- **La consola suma, no sustituye.** El día que se despliega, la ficha de AIRBUS en la consola puede
  tener el ámbito vacío o a medias. Si mandara la consola, AIRBUS se quedaría sin centros esa noche.
  Sumando, no se puede perder nada.

Los centros nuevos de un cliente no piden nada: el ámbito por nombre («AIRBUS») ya coge cualquier
centro que se llame así (`docs/44`). Para un cliente con su propio código en VenCloud, lo mejor es
poner ese código en «clientes»: coge todos sus centros, presentes y futuros.

## Si no puede leer la consola

Si la tabla no se puede leer (falta el permiso, o la pila web no está), la Lambda sigue sólo con
`perfiles.json`, como antes, y lo dice en el registro y en el resumen (`consola.error`). Un fallo
aquí no deja a nadie sin el panel de ayer.

## El permiso

La Lambda de agregados necesita `dynamodb:Scan` sobre la tabla `digivend-plataforma`, y sólo sobre
ella. La tabla es de la pila web, pero lleva el mismo prefijo. Hay que darlo en dos sitios de
`plantilla.yaml`, y los dos hacen falta: el rol (`RolAgregados`) y la frontera (`Frontera`), que es el
techo. `infra/test_permisos.py` comprueba ahora también esta pila.

El nombre de la tabla **no** va como variable de entorno en la plantilla. Cambiar cualquier cosa de la
Lambda en la plantilla haría que actualizar la pila le pisara el código con el marcador. El código lo
saca de su propio nombre: `digivend-agregados` → `digivend-plataforma`. Así la actualización de la pila
sólo toca los dos permisos.

## Desplegarlo

1. **Lambda de agregados.** `Lambda → digivend-agregados → Code → Upload from → .zip file` →
   `agregados.zip` → **Save**. Va primero y no rompe nada: sin el permiso, sigue con el fichero.
2. **Lambda de la API.** `Lambda → digivend-api → Code → Upload from → .zip file` → `api.zip` →
   **Save**. Sólo cambia el texto de un aviso.
3. **La consola.** `S3 → digivend-web-… → consola/` → sube `index.html` y comprueba que se llame
   así y no `index (1).html`. Luego `CloudFront → Invalidations → Create invalidation` → `/consola/*`.
4. **El permiso: actualizar la pila de ingesta**, con un conjunto de cambios para verlo antes:
   - `CloudFormation → Stacks → digivend-ingesta → Stack actions → Create change set for current stack`.
   - **Replace current template** → **Upload a template file** → `plantilla.yaml` → **Next**.
   - Parámetros: todos como están (**Use existing value**). **Next**.
   - Opciones: nada. Abajo, marca **I acknowledge that AWS CloudFormation might create IAM resources
     with custom names** → **Submit**.
   - En la pestaña **Changes** tienen que salir **exactamente dos** filas, las dos *Modify* y
     *Replacement: False*: `Frontera` (`AWS::IAM::ManagedPolicy`) y `RolAgregados`
     (`AWS::IAM::Role`). Si sale cualquier otra (sobre todo `Agregados` o `Extraccion`, que son las
     Lambdas), **no lo ejecutes**: bórralo con **Delete** y avísame.
   - Si salen esas dos: **Execute change set** → **Execute change set**. Tarda un minuto.
5. **Comprobarlo.** `Lambda → digivend-agregados → Test → {}` → **Test**. En el resultado,
   `consola` tiene que decir `"error": null` y en `leidos` el número de perfiles de la consola. Si
   dice `AccessDenied`, falta el paso 4.

## Lo que sigue en el fichero

`perfiles.json` no desaparece: sigue teniendo el `interno` (todo el parque) y la fila de AIRBUS, que
se queda como red. Cuando la ficha de AIRBUS en la consola tenga sus diez centros, la fila del
fichero se puede quitar, pero no hace falta.
