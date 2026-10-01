# Separado de lo que ya tienes

Requisito tuyo: **nada de lo que montemos en AWS puede mezclarse con lo que ya hay**.
Esto es lo que lo garantiza, de la separación más fuerte a la más fina.

---

## 1. La separación fuerte: cuenta aparte (lo recomendado)

Una **cuenta AWS nueva**, dentro de tu Organization, sólo para digivend.

Es la única frontera que AWS garantiza de verdad. Todo lo demás —prefijos, etiquetas,
políticas— son convenciones que alguien puede saltarse por descuido. Un límite de cuenta
no se salta por descuido.

Lo que te da, concretamente:

| | |
|---|---|
| **Factura** | el gasto de digivend llega como una línea propia. No hay que repartir nada |
| **Permisos** | un error de dedo en una política de digivend no puede alcanzar nada tuyo: no están en el mismo espacio de nombres |
| **Límites de servicio** | las cuotas de Lambda, S3 y CloudWatch son por cuenta. Si digivend consume, consume lo suyo |
| **Apagar** | si algún día se para el proyecto, se cierra la cuenta y no queda nada suelto |
| **Auditoría** | CloudTrail de esa cuenta es sólo de este proyecto; se lee en diez minutos |

Se crea en **AWS Organizations → Add an AWS account**. Tarda unos minutos y no cuesta nada:
pagas los recursos, no la cuenta. Desde tu cuenta actual entras con *switch role*, sin otra
contraseña.

**Qué hace falta de tu parte:** un correo que no esté ya usado en AWS (vale un alias del
tipo `aws-digivend@…`) y decidir si la cuenta va bajo la Organization que ya tienes o suelta.

## 2. Si ha de ir en la cuenta que ya usas

También está resuelto, sin tocar nada existente. La plantilla ya lo trae:

### El prefijo es la frontera
Todos los recursos se llaman `digivend-*` o `digivend/*`. El bucket, además, lleva el número
de cuenta: `digivend-vending-<cuenta>`. Cambiar el parámetro `Prefijo` levanta **una instalación
entera aparte** —para pruebas, por ejemplo— sin enterarse la otra.

### La frontera de permisos es lo que de verdad aísla
Los dos roles de Lambda llevan una **permissions boundary** (`digivend-frontera`) que sólo
permite tres cosas:

- S3 **sobre el bucket de digivend y ninguno más**
- leer **el secreto de digivend y ninguno más**
- escribir **sus propios registros y ninguno más**

Esto es un **techo**, no una política. Aunque mañana alguien le añadiera a uno de esos roles
una política que diga «S3 en todo», **seguiría sin poder leer tus buckets actuales**: la frontera
manda sobre lo que se le sume después. Es la diferencia entre «no le hemos dado permiso» y
«no puede».

### La plantilla no referencia nada tuyo
Puedes comprobarlo: no hay un solo `Fn::ImportValue`, ni un ARN escrito a mano, ni un id de
VPC, ni un bucket existente. **Todos los recursos se crean**; ninguno se adopta. Si borras la
pila, no se lleva nada por delante (y el bucket queda con `Retain`, para no perder el crudo
por un `delete stack` a destiempo).

### Los horarios van en su propio grupo
EventBridge Scheduler pone los horarios en el grupo `default` si no se le dice otra cosa.
Los nuestros van a `digivend-horarios`: no se mezclan en la lista con nada que ya tengas,
y se ven de un golpe.

### Los registros caducan
Los log groups se crean aquí, con 30 días de retención. Si los crea Lambda sola, se guardan
**para siempre** y se pagan para siempre.

### La etiqueta de coste
Todo lleva `Proyecto=digivend`. Hay que **activarla una vez** en
*Billing → Cost allocation tags*, y desde ese día el gasto del proyecto sale aparte en Cost
Explorer. Tarda 24 h en empezar a aparecer.

### Una región aparte
Si quieres el corte aún más visible, despliega en una región que no uses para nada más
(`eu-west-1` si lo tuyo está en `eu-west-3`, o al revés). La consola de AWS filtra por región,
así que el proyecto no aparece ni de refilón cuando mires lo tuyo.

---

## Cómo subir la pila

Sube `plantilla.yaml` en **CloudFormation → Create stack → Upload a template file**.

Al final del asistente hay que marcar la casilla:

> ☑ *I acknowledge that AWS CloudFormation might create IAM resources with custom names*

Hace falta porque los roles llevan nombre propio (`digivend-rol-extraccion`) en vez de uno
generado al azar — precisamente para que se vea de quién es cada cosa en la lista de IAM.
Es `CAPABILITY_NAMED_IAM`.

## Qué comprobar después, en un minuto

```
# Todo lo del proyecto, y nada más que lo del proyecto:
aws resourcegroupstaggingapi get-resources --tag-filters Key=Proyecto,Values=digivend

# Que la frontera está puesta en los dos roles:
aws iam get-role --role-name digivend-rol-extraccion --query Role.PermissionsBoundary
aws iam get-role --role-name digivend-rol-agregados  --query Role.PermissionsBoundary
```

Si lo segundo devuelve el ARN de `digivend-frontera`, el aislamiento está puesto.

---

## Lo que viene después también va aparte

Cuando montemos la parte web (dominio, acceso, API, asistente) se aplica lo mismo y en la
misma cuenta o pila nueva: **una pila por pieza**, todas con el mismo prefijo y la misma
etiqueta, ninguna tocando nada que ya exista. La ingesta y la web son dos pilas separadas
a propósito: se puede rehacer la web sin rozar el dato.
