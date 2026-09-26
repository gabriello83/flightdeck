# El modelo de datos de VenCloud

Volcado de `information_schema`: **587 tablas y 8.172 columnas** en doce esquemas
(`vending` 70 tablas, `configuracion` 100, `comercial` 61, `recursos` 58, `stocks` 55,
`telemetry` 46, `facturacion` 45, `importacion` 64, `compras` 25, `general` 25, `utils` 25,
`sat` 13), más 1.020 claves ajenas. Ficheros en `data/raw/estructura_*.xlsx`.

La conclusión general es que **VenCloud ya guarda casi todo lo que dábamos por perdido**.
Varias limitaciones que anoté analizando los informes eran limitaciones **de los informes**,
no de la base.

---

## Lo que corrige conclusiones anteriores

### 1. La venta de telemetría trae hora, día de la semana, coste y ruta

`telemetry.telemetrysales` (24 columnas):

```
id, creadoel, fechaventa, fechaventautc, seleccion, codcanal, lineaprecio,
tipoventaorigen, listaprecioorigen, precio, coste, articuloid, maquinaid, pdvid,
refexterna, telemetriadispositivo, tipotelemetria, regorigenid, transactionid,
diasemana, hora, rutaid, preciotokens, fechacreaorigen
```

Tres columnas cambian el análisis:

- **`hora` y `diasemana`** vienen ya calculadas, **en todas las ventas**. El análisis por
  franja horaria no estaba limitado a agosto: lo estaba el fichero que nos pasaron.
- **`coste`** está en la propia línea de venta. El margen por transacción no depende de
  cruzar con el maestro de artículos ni del factor de conversión.
- **`rutaid`** atribuye cada venta a una ruta directamente.

Y trae **`maquinaid` y `pdvid` a la vez**, que era la condición para no equivocarse con las
máquinas que cambian de sitio.

### 2. El factor de conversión existe

`stocks.articulos` (76 columnas) incluye **`unidcaja`**, `numunidart`, `unidpack`,
`pesocaja`, `pesounid`, `prepcajas` y `usarunidpackvta`. Con eso, el `puc` (precio de última
compra, por unidad de compra) se convierte a coste por unidad vendida. También hay
**`preciocoste`, `pmc` (precio medio de compra), `pcr` y `precioventa`** directamente.

El margen por artículo, que dimos por imposible al analizar el informe 2, se puede calcular.

### 3. La base sabe qué artículos son frescos

`fresco`, `caducidaddias`, `temperatura`, `autopedidofresco`, `clasalergeno`. Eso permite
por fin el indicador que faltaba en el control de temperatura: **qué máquinas llevan
producto fresco y por tanto deberían tener lectura**, en vez de contar solo las que la
tienen.

### 4. Capacidad por artículo y tipo de hueco

`huecosimple`, `huecounoymedio`, `huecodoble`, `huecotriple`, `huecocuadruple`, cada uno con
su `...cant`: cuántas unidades caben según el tipo de espiral. Y
`recursos.maquinascanales` añade **`stockseguridad`, `cargaminima`, `tipoespiral`, `fila` y
`columna`**. O sea: el `stockrecom` a cero que vimos en el planograma de la 24SE1983 no es
el único campo de reposición, y además se puede **dibujar el planograma real** con su
rejilla.

### 5. El parte de visita ya calcula el beneficio y las mermas

`vending.partesvisita` tiene **137 columnas**, muchas precalculadas:

| Campo | Qué es |
|---|---|
| `cal_beneficio` | **beneficio de la visita** |
| `cal_impcostecaducidad` · `cal_impcosterotura` · `cal_impcosteinv` | **mermas valoradas** |
| `cal_numvtasef/impvtasef`, `...tp`, `...tc` | venta desglosada por medio de pago |
| `cal_cm` · `cal_rm` · `cal_rc` · `cal_rr` | contadores por tipo de movimiento |
| `cal_impcajon` · `cal_impcajonmon` · `cal_impcajonbill` · `cal_imptubos` · `cal_impbilletes` | desglose del efectivo |
| `cal_haydifprecios` · `cal_haydifpreciosef` | **detecta diferencias de precio** |
| `roboenmaquina` | marca de robo |
| `fechavisitaanterior` · `cal_visitanumvtas` · `cal_visitaimpvtas` | venta desde la visita anterior |
| `cal_numinvitaciones` · `cal_numpruebas` | gratuidades y pruebas |
| `estadobolsa` · `fechaverificabolsa` | control de la bolsa de recaudación |

Los informes que hemos catalogado usan cuatro o cinco de estas columnas. Hay mucho más
calculado de lo que se está explotando.

### 6. El coste del servicio está en el punto de venta

`vending.pdvs` incluye **`costemediovisita`**, **`costefijomensual`**,
**`impminrentabilidad`**, `impminrecaudacion` y **`actalarmasrentrec`** (activar alarmas de
rentabilidad y recaudación). También `consumoobjetivo`, `consumosabado`, `consumodomingo`,
`consumofestivo`, los acuerdos de alquiler, comisión y subvención con sus importes y fechas,
los medios de pago habilitados (`vtaefectivo`, `vtatprivada`, `vtatcredito`, `vtapmovil`,
`vtagratuita`), `dtofranjahoraria` y **`gpslatitud` / `gpslongitud`**.

Con el coste medio por visita y el fijo mensual, **la rentabilidad por máquina se puede
calcular de verdad**, no estimar. Y hay coordenadas para un mapa.

### 7. Amortización y cesión ya están en la ficha de máquina

`recursos.maquinas` trae **`cedida`** —el campo que le faltaba al informe 81—,
**`cuotaamortizacion`, `mesesamortizacion`, `fechafinamortizacion`**, `tipopropiedad`,
`proveedorexterno`, `fechafingarantia`, `tipoexplotacion`, `serviciotecnico`,
`fechaultcambioplanograma`, `consumomaximo`, `auditgenalarmas` y `sinplanograma`.

No hace falta aplicar la regla de 8,3 años a mano: la cuota y los meses están configurados
máquina a máquina.

---

## Lo que habilita funciones nuevas

### El motor de alarmas por falta de ventas ya existe

`configuracion.criteriosalarmasnovtas`:

```
id, activa, latencia, modohoras, horadesde1, horahasta1, horadesde2, horahasta2,
lunes, martes, miercoles, jueves, viernes, sabado, domingo, festivos,
clientecentroid, pdvid, ...
```

Es exactamente la alerta de "máquina muda" que diseñamos en la cabina: **latencia** de horas
sin venta, **franjas horarias** y **días de la semana** en los que cuenta, configurable por
centro o por punto de venta. En vez de reinventarla, el cuadro de mando debería leer esta
configuración y respetarla.

### Alarmas de máquina en tiempo real

`telemetry.telemetryalarms`: `firedon`, `code`, `eventdescription`, `definition`, `status`,
`maquinaid`, `pdvid`, `telemetrysource`. Es el canal de averías que reporta la propia
máquina, sin esperar a que alguien abra una incidencia. Junto con
`vending.partesvisitaauditalarmas` (alarmas detectadas en el audit) y
`telemetry.telemetrydevices` (`alarmsenable`, `monitorize`, `phonenumber`, `simnumber`), es
la base de la cabina en vivo.

### A quién avisar: la tabla ya está

`recursos.empleados` tiene **`telefono`**, `email`, `coddispositivo`, `actmobile` y las
marcas de rol: **`responsablesat`**, **`responsableven`**, `esoperaciones`, `escallcenter`,
`esinstalaciones`, `taller`, `directivo`, más `delegacionid`.

O sea: el destinatario de cada aviso —responsable de vending o de SAT de esa delegación, con
su teléfono— se puede resolver con una consulta. Y `recursos.empleadosnotificacionesmobile`
(`tiponotificacion`, `texto`, `leida`) indica que **ya hay un canal de notificación móvil**
hacia el empleado; conviene ver cómo se usa antes de montar WhatsApp por fuera.

Para el cliente, los contactos están en `comercial.clientescontactos` (`email`,
`telefonofijo`, `telefonomovil`), y la configuración de correos en
`configuracion.confemails`.

### Recargas de tarjeta

`telemetry.telemetryrecharges`: importe, fecha, cliente, dispositivo. Es el dinero prepago
de las tarjetas de empleado, que explica buena parte del 67% de venta con tarjeta.

---

## Advertencia

**Que un campo exista no significa que esté relleno.** Ya hemos visto el caso: `stockrecom`
existe y está a cero en los 70 canales de la 24SE1983, `costecompra` solo está en el 15% de
las máquinas y `fechacompra` en el 30%. Antes de construir sobre cualquiera de estos campos
hay que medir su grado de cumplimentación.

La siguiente tanda de SQL debería ser justo eso: **volcado de los maestros y un recuento de
relleno** por columna crítica.
