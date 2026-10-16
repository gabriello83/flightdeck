# 55 · La página de rutas

Es lo que abre el cuadrado de **Rutas** del informe general (docs/51). Gabriele lo eligió el 16
de octubre de 2026 como primer cuadrado con página propia. El 13 de octubre había pedido además:

> apuntate que en la pagina de la ruta esta bien que por cada delegacion la dashboard controle
> que lo festivo de cada ciudad tengan muchas menos visitas.

`/rutas/?dia=AAAA-MM-DD` enseña, del día elegido (ayer si no se dice):

- **El total y cada delegación**: los puntos de venta del plan, los que tuvieron visita, el %
  con el semáforo del informe (verde > 95 %, amarillo 75–95 %, rojo < 75 %), las visitas fuera
  de plan, y los últimos siete días en cuadritos de color.
- **Cada ruta**, de todas o de la delegación pulsada.
- **Punto de venta a punto de venta**: los del plan que no se visitaron y las visitas fuera de
  plan, con centro, ruta y reponedor. Se pueden buscar y bajar en CSV.
- **El control de festivos**, delegación por delegación.

## Las cuentas

Son las mismas del cuadrado, partidas:

- **Prevista** = un punto de venta en el plan de visitas de ese día (D12 · EXT_RUTAS_PLAN_VISITAS,
  informe 184). Si un punto de venta está en dos rutas, en el total y en su delegación cuenta
  como una sola visita prevista, y en cada una de sus rutas cuenta una vez.
- **Hecha** = ese punto de venta tiene ese día un parte de reponedor. Las lecturas automáticas
  de SYSTEM no cuentan como visita (`reglas.es_visita_real`).
- **Fuera de plan** = punto de venta con parte de reponedor que no estaba en el plan. En la
  tabla de rutas se apunta a la ruta del parte.
- La delegación de una prevista es la que trae el plan; la de una visita fuera de plan, la que
  trae el parte.

## Los festivos

VenCloud no descuenta los festivos del plan: el 12 de octubre de 2026 (Fiesta Nacional) el plan
traía 913 visitas previstas, se hicieron 161 y el cuadrado salió al 17,6 %. Esta página no toca el
%: lo que hace es comprobar que el festivo se comporta como tal.

El calendario está en `config/festivos.json` del bucket de datos (en el repositorio,
`infra/festivos.json`). Lleva los festivos nacionales de 2026 y, por delegación, los locales. **Los
locales están vacíos**: no los tenemos y no se inventan. Hay que apuntarlos a mano y volver a subir
el fichero.

Para cada delegación, **un día normal** es la mediana de sus visitas en los laborables (de lunes
a viernes) sin festivo, con al menos tres días. Con esa mediana se marca:

| Control | Cuándo |
|---|---|
| Bien | un festivo apuntado con menos de la mitad de las visitas de un día normal |
| Visitas de día normal | un festivo apuntado con la mitad o más: se trabajó, o el calendario está mal |
| ¿Festivo sin apuntar? | un laborable sin festivo y con menos de la mitad de visitas: un festivo local que falta, o un día que falló. No se decide cuál de las dos |
| Sin día normal | la delegación no visita nada en sus días normales y no hay con qué comparar |

Además, el plan **sin descontar** marca un festivo cuyo plan trae la mitad o más de las
previstas de un día normal.

Con los datos del 6 al 15 de octubre, el 12 de octubre sale bien en casi todas las delegaciones,
pero con el plan entero sin descontar. Granada y Málaga visitaron como un día normal. Oviedo,
León y Cádiz tienen laborables con muchas menos visitas de lo normal.

## El fichero

`cabina/<perfil>/rutas.json.gz` lo escriben los agregados cada noche (`operativo.detalle_rutas`),
con el ámbito del perfil aplicado al escribir. Se sirve por `/api/rutas`, con la misma regla que el
cuadrado: hace falta perfil de operaciones o más y la sesión de servicio. Lo que guarda:

- las cifras de cada día durante 62 días, que son las que hacen falta para el día normal;
- las listas punto a punto sólo de los últimos siete días. Un día más viejo enseña las cifras y
  avisa de que no tiene lista.

Sale en unos 50 KB comprimidos para el perfil interno.

Pruebas: `infra/test_operativo.py` (cuentas y festivos), `infra/test_agregados.py` (el ámbito),
`infra/api/test_api.py` (quién la ve) y `app/comun/prueba_pantallas.js` (la página en Chromium,
en claro, oscuro y móvil, sin peticiones fuera del dominio).
