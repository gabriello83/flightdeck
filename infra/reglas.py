"""
Las reglas del modelo de VenCloud, en codigo.

Cada funcion de aqui es una trampa que nos costo encontrar. Van juntas y con su
procedencia escrita al lado para que nadie las vuelva a pisar: quien agregue un
indicador nuevo pasa por aqui y no por su cuenta.

Sin dependencias: se importa igual desde Lambda que desde una prueba local.
"""

import statistics

# El centinela de "nunca" en este modelo. No es nulo: es una fecha.
NUNCA = "1900-01-01"

# Las unicas denominaciones que son dinero. En auditmonbil y audittubos aparecen
# ademas valores como 12,75 / 2,55 / 48,00 / 0,45 que no son monedas de euro;
# si se suman, el efectivo sale disparado.
MONEDAS = (0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.00, 2.00)

# Matricula ficticia del CENTRO TEST. 6.497 de las 27.543 tareas de SAT del ano
# cuelgan de ella. No es una maquina.
MATRICULA_FICTICIA = "00SE0000"

# Los partes automaticos: tipo 2 y 3, empleado SYSTEM, ruta -99, 0 minutos.
TIPOS_VISITA_REAL = (0, 100)


def v(fila, campo, por_defecto=0):
    """Lee un campo tratando el 0 y el nulo igual.

    En este modelo "sin referencia" es 0, no nulo: articuloid 0, empleadoid 0.
    Comprobarlo con `is None` deja pasar filas vacias.
    """
    x = fila.get(campo)
    return por_defecto if x is None or x == "" else x


def sin_referencia(fila, campo):
    return not v(fila, campo, 0)


def fecha_valida(valor):
    """El 01/01/1900 significa 'nunca', no una fecha de 1900."""
    return bool(valor) and not str(valor).startswith(NUNCA)


# ----------------------------------------------------------------------
# visitas
# ----------------------------------------------------------------------
def es_visita_real(parte):
    """Dos tercios de partesvisita son cierres automaticos, no visitas.

    Medido el 25/09: 3.504 filas, 1.107 visitas de persona. Sin este filtro todo
    indicador de visita sale mas del triple. Se extraen igual porque traen
    lectura de maquina, pero no se cuentan como visita.
    """
    if sin_referencia(parte, "empleadoid") and str(v(parte, "empleado", "")).strip().upper() == "SYSTEM":
        return False
    return int(v(parte, "tipo_parte", 0)) in TIPOS_VISITA_REAL


def visitas_reales(partes):
    return [p for p in partes if es_visita_real(p)]


def coste_servicio(partes, coste_visita=8.0):
    """costevisita viene relleno a 8,00 EUR planos en todas las delegaciones.

    Lo dabamos por imposible cuando pdvs.costemediovisita salio al 0 %. No lo es.
    """
    reales = visitas_reales(partes)
    return {
        "visitas": len(reales),
        "coste": round(len(reales) * coste_visita, 2),
        "coste_unitario": coste_visita,
    }


# ----------------------------------------------------------------------
# reposiciones
# ----------------------------------------------------------------------
def valor_cargado(lineas):
    """El valor de lo cargado son las lineas CM, NO el campo cal_impcarga.

    cal_impcarga es carga NETA: CM - RC - RM - RR. Comprobado parte a parte el
    25/09, 0 descuadres. Leer el campo de la cabecera da de menos.
    """
    return round(sum(float(v(l, "cantidad")) * float(v(l, "precio_coste"))
                     for l in lineas if v(l, "tipo_linea") == "CM"), 2)


def unidades_cargadas(lineas):
    """cal_cm son unidades, no lineas. 154.312 exactas el 25/09."""
    return sum(float(v(l, "cantidad")) for l in lineas if v(l, "tipo_linea") == "CM")


def es_consumible_de_cafe(linea):
    """Las lineas sin etiqueta de canal son carriles de maquina caliente.

    El 62 % de las unidades cargadas son azucar, vasos y paletinas. Cualquier
    indicador de unidades que no separe esto no dice nada.
    """
    return not v(linea, "etiq_canal", "")


def merma(lineas_maquina):
    """La merma se cuenta UNA vez, en la maquina.

    Las lineas de caducidad de almacen y vehiculo son la misma merma vista en su
    viaje de vuelta: 6 + 52 = 58 lineas y 9,46 + 95,49 = 104,95 EUR el 25/09.
    Sumar los tres diarios la cuenta dos veces.

    Y se valora con `puc`, el coste de reposicion, no con `precio_coste`.
    """
    def total(motivo):
        f = [l for l in lineas_maquina if v(l, "motivo") == motivo]
        return {
            "lineas": len(f),
            "unidades": sum(abs(float(v(l, "cantidad"))) for l in f),
            "euros": round(sum(abs(float(v(l, "cantidad"))) * float(v(l, "puc")) for l in f), 2),
        }
    return {"caducidad": total("RC"), "rotura": total("RR"), "retirada": total("RM")}


# ----------------------------------------------------------------------
# dinero
# ----------------------------------------------------------------------
def efectivo_en_cajon(filas_monbil):
    """Teorico de la bolsa: suma(valor x encajon), solo denominaciones reales.

    Y no se agrega a nivel de parque: hay lecturas con 723.546 monedas de 2 EUR
    en una sola fila. Sirve por bolsa, donde un contador corrupto se ve como una
    alarma de esa maquina en vez de contaminar un total nacional.
    """
    return round(sum(float(v(f, "valor")) * float(v(f, "encajon"))
                     for f in filas_monbil if float(v(f, "valor")) in MONEDAS), 2)


# Una recaudacion de una maquina son 8,80 EUR de media (428.003 EUR en 48.443
# filas, agosto). Cien mil euros en UNA fila no es un mes bueno: es un contador
# roto. Junio del 2026 traia una fila de -7.521 millones que se llevaba por
# delante el mes entero y dejaba el porcentaje ciego en -0,0.
LIMITE_FILA_RECAUDACION = 100_000.0


def recaudacion_del_periodo(filas, anio, mes):
    """prefacrecauda se agrupa por anho/mes, nunca por `fecha`.

    `fecha` es la fecha de escritura. En agosto se escriben 57.452 filas de las
    que 52.161 son del periodo de julio. Y el cobro por tarjeta de un mes entero
    se escribe de golpe al mes siguiente, asi que el mes en curso se ve un 55 %
    mas pequeno de lo que es.

    Las filas imposibles se APARTAN Y SE CUENTAN, nunca se tiran en silencio:
    quien lea el panel tiene que poder ver que ese mes llevaba basura dentro. Es
    el mismo criterio que con las denominaciones que no son monedas.
    """
    f = [x for x in filas if int(v(x, "anho")) == anio and int(v(x, "mes")) == mes]
    buenas = [x for x in f if abs(float(v(x, "imp_recaudado"))) <= LIMITE_FILA_RECAUDACION
              and abs(float(v(x, "imp_pago_bancario"))) <= LIMITE_FILA_RECAUDACION]
    descartadas = len(f) - len(buenas)
    ef = round(sum(float(v(x, "imp_recaudado")) for x in buenas), 2)
    bk = round(sum(float(v(x, "imp_pago_bancario")) for x in buenas), 2)
    ciego = round(sum(float(v(x, "imp_recaudado")) for x in buenas
                      if int(v(x, "tipo_telemetria")) == 0), 2)
    out = {
        "periodo": f"{anio}-{mes:02d}",
        "registros": len(buenas),
        "efectivo": ef,
        "banco": bk,
        "total": round(ef + bk, 2),
        "efectivo_sin_telemetria": ciego,
        "pct_ciego": round(100 * ciego / ef, 1) if ef > 0 else 0.0,
    }
    if descartadas:
        out["filas_imposibles"] = descartadas
        out["_nota_imposibles"] = (
            f"{descartadas} fila(s) con importes por encima de "
            f"{LIMITE_FILA_RECAUDACION:,.0f} EUR apartadas: son contadores rotos, "
            "no recaudacion. Mirarlas en el crudo antes de dar el mes por bueno.")
    return out


def es_acto_de_recaudar(fila):
    """critcalculo 3 (y 2 y 4) es el acto de recaudar; el 1 es cobro diario.

    En agosto: 5.665 filas con critcalculo 3 y 393.578 EUR, el 92 % del efectivo,
    frente a 37.019 filas de critcalculo 1 con 3.396 EUR.
    """
    return int(v(fila, "criterio_calculo")) in (2, 3, 4)


def mes_provisional(anio, mes, hoy):
    """Un mes no esta cerrado hasta el final del siguiente: le falta la tarjeta."""
    siguiente = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    return (hoy.year, hoy.month) <= siguiente


# ----------------------------------------------------------------------
# SAT
# ----------------------------------------------------------------------
def tareas_de_maquina(tareas):
    """Fuera la matricula ficticia: son el 24 % de las tareas y no son una maquina."""
    return [t for t in tareas if v(t, "matricula") != MATRICULA_FICTICIA]


def es_averia_tecnica(tarea):
    """Tareas de la CATEGORIA "AVERIAS TECNICAS". 6.400 de 27.543 en 2026.

    OJO: esto mide el buzon, no el fallo. Para contar fallos tecnicos de verdad
    usa `es_fallo_tecnico`, que clasifica por operacion: la categoria se deja
    fuera 3.823 fallos que estan archivados en ATENCION AL CLIENTE y en
    operaciones retiradas (10.223 contra 6.400). Se conserva esta funcion porque
    el reparto por categoria sigue siendo correcto COMO reparto de buzones.
    """
    return v(tarea, "categoria") == "AVERIAS TECNICAS"


def es_preventivo(tarea):
    """tipo_tarea separa averia (A) de preventivo (E)."""
    return v(tarea, "tipo_tarea") == "E"


# ----------------------------------------------------------------------
# el catalogo de SAT (D11): clasificar por operacion, no por categoria
# ----------------------------------------------------------------------
# 101 operaciones, 6 categorias. La categoria dice en que LISTA se archivo la
# operacion, no si es un fallo tecnico: `C06 SNACK/BEBIDA - Distribuidor fuera de
# servicio` esta en ATENCION AL CLIENTE y su gemela de cafe `T08` en AVERIAS
# TECNICAS. Contando por categoria salen 6.400 fallos tecnicos en 2026; contando
# por operacion, 10.223. Medido en docs/41-catalogo-sat.md.

CATEGORIAS_SAT = ("ATENCION AL CLIENTE", "AVERIAS TECNICAS", "Devolucion dinero",
                  "Solicitudes cliente", "Solicitudes internas", "Obsoletas")

# Las 36 operaciones del catalogo que NO son un fallo tecnico, con su motivo.
# Las otras 65 si lo son. Es una PROPUESTA pendiente de que Gabriele la confirme:
# tres casos son discutibles y estan marcados como tal en carga/catalogo_sat.xlsx.
OPERACIONES_NO_TECNICAS = {
    "8888888": "preventivo de electrodomesticos",
    "888889": "solicitud interna",
    "999999999": "auditoria",
    "A036": "cajon de sastre: TECNICO - VARIOS",
    "C016": "reposicion: selecciones vacias",
    "C15": "configuracion: insertar contador",
    "C16": "calidad del producto, no de la maquina",
    "C20": "limpieza",
    "C22": "limpieza",
    "C24": "devolucion",
    "D01": "devolucion",
    "D03": "devolucion",
    "D04": "devolucion",
    "DEV01": "devolucion",
    "DEV02": "devolucion",
    "DEV03": "calidad del producto",
    "DEV04": "calidad del producto",
    "DEV05": "devolucion",
    "DEV06": "devolucion",
    "S001": "configuracion: planograma",
    "S002": "mover maquina",
    "S003": "instalar cashless",
    "S004": "instalar pago bancario",
    "S005": "cambiar maquina",
    "S006": "reforma",
    "S007": "administracion: saldo",
    "S008": "limpieza",
    "S009": "configuracion: etiqueta",
    "S010": "reponer",
    "S011": "configuracion: precio",
    "S012": "solicitud generica",
    "S013": "instalacion nueva",
    "S12": "ajuste de molino",
    "T47": "limpieza",
    "T49": "instalacion de cable DEX",
    "T55": "configuracion: precio",
}

# Las 22 desactivadas. Siguen apareciendo en tareas antiguas, asi que no se
# pueden ignorar al contar historico; solo al ofrecer opciones nuevas.
OPERACIONES_RETIRADAS = frozenset(["A004", "A005", "A012", "A014", "A021", "A028", "A029", "A035", "C01", "C02", "C03", "C04", "C05", "C17", "C21", "T23", "T28", "T34", "T42", "T47", "T50", "T55"])


def es_fallo_tecnico(tarea):
    """Si la tarea es un fallo de la maquina, clasificando por OPERACION.

    Prefiere el codigo de operacion, que es el dato bueno. Si la tarea no lo
    trae, cae a la categoria y acepta su error: la categoria subestima los
    fallos tecnicos en un 60 %, asi que esa rama es un apano, no una medida.
    """
    codigo = str(v(tarea, "cod_operacion", "") or "").strip()
    if codigo:
        return codigo not in OPERACIONES_NO_TECNICAS
    return v(tarea, "categoria") == "AVERIAS TECNICAS"


def operacion_retirada(tarea):
    """La tarea usa una operacion que ya esta desactivada en el catalogo."""
    return str(v(tarea, "cod_operacion", "") or "").strip() in OPERACIONES_RETIRADAS


# ----------------------------------------------------------------------
# tiempos
# ----------------------------------------------------------------------
def resumen_tiempos(valores):
    """Mediana siempre: partes y jornadas se quedan abiertos y la media miente.

    Visitas del 25/09: mediana 6,8 min, media 20,2, maximo 387.
    Jornadas del mes: mediana 8,35 h, media 12,05, maximo 179.
    """
    vs = sorted(float(x) for x in valores if x is not None)
    if not vs:
        return {"n": 0}
    return {
        "n": len(vs),
        "mediana": round(statistics.median(vs), 2),
        "media": round(statistics.mean(vs), 2),
        "p90": round(vs[min(len(vs) - 1, int(len(vs) * 0.9))], 2),
        "max": round(vs[-1], 2),
    }


# ----------------------------------------------------------------------
# inventario
# ----------------------------------------------------------------------
def cumplimiento_inventario(maquinas, hoy, dias_norma=90):
    """Inventario cada tres meses, y uno antes de instalar.

    De 3.200 maquinas operativas, 275 estaban en norma y 763 no se habian
    inventariado nunca. Las que nunca se contaron van aparte: no son "muy
    caducadas", son otra cosa.
    """
    import datetime
    en_norma = caducado = muy_caducado = nunca = 0
    for m in maquinas:
        f = v(m, "ultimo_inventario", "")
        if not fecha_valida(f):
            nunca += 1
            continue
        d = (hoy - datetime.date.fromisoformat(str(f)[:10])).days
        if d <= dias_norma:
            en_norma += 1
        elif d <= 365:
            caducado += 1
        else:
            muy_caducado += 1
    total = len(maquinas)
    return {
        "maquinas": total,
        "en_norma": en_norma,
        "caducado": caducado,
        "muy_caducado": muy_caducado,
        "nunca": nunca,
        "pct_en_norma": round(100 * en_norma / total, 1) if total else 0.0,
    }


# ----------------------------------------------------------------------
# instalaciones: lo que esta puesto, y lo que esta puesto a medias
# ----------------------------------------------------------------------
# Un punto de venta de baja no es una incidencia: es una baja. Y uno que todavia
# no se ha instalado tampoco. Solo cuenta lo que esta vivo.
ESTADOS_PDV_VIVO = (0, 1)

# El sistema de telemetria. 0 es «ninguno»; 40 es NAYAX, que es el que tenemos.
SIN_TELEMETRIA = 0


def pdv_vivo(fila):
    """Un punto de venta sin fecha de baja y en estado de alta."""
    if fecha_valida(v(fila, "baja_pdv", "")):
        return False
    estado = v(fila, "estado_pdv", None)
    return estado is None or int(estado) in ESTADOS_PDV_VIVO


def instalado(fila):
    """Hay maquina puesta en el punto de venta."""
    return bool(v(fila, "matricula", "")) and bool(v(fila, "cod_pdv", ""))


def sin_tarifa(fila):
    """Ni el punto de venta ni el cliente tienen tarifa de vending.

    Una maquina vendiendo sin tarifa configurada es dinero mal facturado o
    directamente perdido. Faltan las tarifas de PRODUCTOS del cliente y del
    centro —el informe 10 de VenCloud las tiene y aqui no estan sus columnas—,
    asi que esto es un minimo: lo que marque, lo esta de verdad.
    """
    return not (v(fila, "tarifa_vending_pdv", 0) or v(fila, "tarifa_vending_cliente", 0))


def sin_planograma(fila):
    """Marcada como sin planograma, o sin un solo canal con articulo.

    Las dos cosas, porque son dos fallos distintos: la bandera es una decision
    («esta maquina no lleva planograma») y los canales son el hecho. Sin
    planograma no se puede distinguir «no habia demanda» de «estaba vacia».
    """
    if int(v(fila, "sin_planograma", 0) or 0):
        return True
    return int(v(fila, "canales_con_articulo", 0) or 0) == 0


def telemetria_sin_dato(fila):
    """Tiene sistema de telemetria y no tiene dispositivo que lo mande.

    Es la peor de las tres porque no se nota: la maquina vende, el parte se
    cierra, y la venta por tarjeta no llega nunca. Se ve en el efectivo ciego
    tres meses despues.
    """
    if int(v(fila, "telemetria", 0) or 0) == SIN_TELEMETRIA:
        return False
    return not str(v(fila, "dispositivo_telemetria", "")).strip()


def incidencias_de(fila):
    """Las pegas de configuracion de una fila del censo, por su nombre."""
    out = []
    if not v(fila, "num_centro", "") and not v(fila, "centro", ""):
        return ["cliente_sin_centros"]
    if not v(fila, "cod_pdv", ""):
        return ["centro_sin_pdv"]
    if not pdv_vivo(fila):
        return []
    if not instalado(fila):
        return ["pdv_sin_maquina"]
    if sin_tarifa(fila):
        out.append("sin_tarifa")
    if sin_planograma(fila):
        out.append("sin_planograma")
    if telemetria_sin_dato(fila):
        out.append("telemetria_sin_dato")
    return out


# El titulo de cada incidencia y por que importa. Viaja al panel para que la
# pantalla no tenga que llevar una copia que se quede vieja.
# Estos textos los lee una persona en la pantalla, asi que van acentuados: es lo
# unico de este fichero que no es codigo.
CATALOGO_INCIDENCIAS = {
    "cliente_sin_centros":  ("Cliente sin centros",
                             "Dado de alta y sin un solo centro colgando."),
    "centro_sin_pdv":       ("Centro sin puntos de venta",
                             "El centro existe y no tiene nada instalado."),
    "pdv_sin_maquina":      ("Punto de venta sin máquina",
                             "Hay sitio dado de alta y no hay máquina puesta."),
    "sin_tarifa":           ("Sin tarifa",
                             "Vende sin precio configurado: dinero mal facturado o perdido."),
    "sin_planograma":       ("Sin planograma",
                             "No se puede saber qué debería haber en cada canal, así que tampoco "
                             "si estaba vacía o es que no había demanda."),
    "telemetria_sin_dato":  ("Telemetría sin dato electrónico",
                             "Tiene sistema de telemetría y no tiene dispositivo: la venta por "
                             "tarjeta no llega, y se descubre en el efectivo ciego meses después."),
}
