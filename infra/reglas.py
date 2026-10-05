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
# `estado_pdv` NO es un estado de alta o baja: es «tiene maquina puesta». Medido
# sobre el censo del 5 de octubre de 2026: de 3.200 con estado 1, las 3.200
# tienen maquina; de 2.005 con estado 0, ninguna. El 9 es el unico que significa
# baja, y esa fila ademas traia su fecha. Asi que lo que marca una baja es la
# fecha, y el estado solo sirve para no contar dos veces.
ESTADO_PDV_BAJA = 9

# Cuantos dias se considera «alta reciente». Un mes da tiempo a que alguien mire
# el panel el lunes siguiente y todavia lo vea.
DIAS_ALTA_RECIENTE = 30

# Y cuanto se le da a un punto de venta nuevo para que le pongan la maquina.
# Esto es mas largo a proposito: entre que se firma y se instala pasan semanas,
# y lo que interesa es la lista de lo que lleva demasiado esperando.
#
# POR QUE NO VALE «sin maquina» a secas: de los 2.006 puntos de venta sin
# maquina del censo real, 1.946 tienen `alta_pdv` a 1900-01-01 —el centinela de
# «nunca»— y solo 60 tienen fecha de verdad. Marcarlos todos habria llenado el
# panel de dos mil casos que nadie va a tocar, y entonces no lo abre nadie.
DIAS_INSTALACION_PENDIENTE = 90

# El sistema de telemetria. 0 es «ninguno»; 40 es NAYAX, que es el que tenemos.
SIN_TELEMETRIA = 0

# Cuantos dias se considera «alta reciente». Un mes da tiempo a que alguien mire
# el panel el lunes siguiente y todavia lo vea.
DIAS_ALTA_RECIENTE = 30

# Las cinco tarifas que valen. Cuelgan de tres sitios —punto de venta, centro y
# cliente— y en dos sabores: vending y OCS (el cafe de oficina). Basta con UNA:
# asi lo hace el informe 10 de VenCloud, que es el que lleva anos usandose.
CAMPOS_TARIFA = ("tarifa_vending_pdv", "tarifa_vending_centro", "tarifa_vending_cliente",
                 "tarifa_ocs_centro", "tarifa_ocs_cliente")


def _vivo(fila, campo_baja, campo_activo=None):
    if fecha_valida(v(fila, campo_baja, "")):
        return False
    if campo_activo is not None:
        activo = v(fila, campo_activo, None)
        if activo is not None and not int(activo):
            return False
    return True


def cliente_vivo(fila):
    return _vivo(fila, "baja_cliente", "cliente_activo")


def centro_vivo(fila):
    return _vivo(fila, "baja_centro", "centro_activo")


def pdv_vivo(fila):
    """Un punto de venta sin fecha de baja."""
    if not _vivo(fila, "baja_pdv"):
        return False
    estado = v(fila, "estado_pdv", None)
    return estado is None or int(estado) != ESTADO_PDV_BAJA


def dias_desde(fila, campo, hoy):
    """Dias desde una fecha del censo, o None si no la hay o es el centinela."""
    import datetime
    f = v(fila, campo, "")
    if not fecha_valida(f):
        return None
    try:
        return (hoy - datetime.date.fromisoformat(str(f)[:10])).days
    except ValueError:
        return None


def instalacion_pendiente(fila, hoy, dias=DIAS_INSTALACION_PENDIENTE):
    """Punto de venta dado de alta de verdad hace poco y todavia sin maquina."""
    if instalado(fila):
        return False
    d = dias_desde(fila, "alta_pdv", hoy)
    return d is not None and 0 <= d <= dias


def instalado(fila):
    """Hay maquina puesta en el punto de venta."""
    return bool(v(fila, "matricula", "")) and bool(v(fila, "cod_pdv", ""))


def sin_tarifa(fila):
    """Ninguno de los tres niveles tiene tarifa, ni de vending ni de OCS.

    Una maquina vendiendo sin tarifa configurada es dinero mal facturado o
    directamente perdido.
    """
    return not any(v(fila, campo, 0) for campo in CAMPOS_TARIFA)


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


# La fila centinela de VenCloud: el cliente 0 «Ventas Contado», con centro -1 y
# punto de venta -99. No es un cliente, igual que 00SE0000 no es una maquina.
CENTINELAS = {"cod_cliente": "0", "num_centro": "-1", "cod_pdv": "-99"}


def es_centinela(fila):
    return any(str(v(fila, campo, "")) == valor for campo, valor in CENTINELAS.items())


def incidencias_de(fila, hoy=None):
    """Las pegas de configuracion de una fila del censo, por su nombre.

    Se para en la primera que corta: un cliente sin centros no tiene sentido que
    salga ademas como «sin tarifa», porque no hay donde ponerla.
    """
    import datetime
    hoy = hoy or datetime.date.today()
    if es_centinela(fila) or not cliente_vivo(fila):
        return []
    if not v(fila, "num_centro", "") and not v(fila, "centro", ""):
        return ["cliente_sin_centros"]
    if not centro_vivo(fila):
        return []
    if not v(fila, "cod_pdv", ""):
        return ["centro_sin_pdv"]
    if not pdv_vivo(fila):
        return []
    if not instalado(fila):
        # Sin maquina solo es una incidencia si el sitio es nuevo. Los 1.946 que
        # llevan ahi desde siempre son huecos del parque, no trabajo pendiente.
        return ["instalacion_pendiente"] if instalacion_pendiente(fila, hoy) else []
    out = []
    if sin_tarifa(fila):
        out.append("sin_tarifa")
    if sin_planograma(fila):
        out.append("sin_planograma")
    if telemetria_sin_dato(fila):
        out.append("telemetria_sin_dato")
    return out


def altas_de(fila, hoy, dias=DIAS_ALTA_RECIENTE):
    """Que se ha dado de alta hace poco en esta fila, con su fecha de verdad.

    VenCloud si guarda la fecha de alta del cliente, del centro y del punto de
    venta, asi que esto no hay que adivinarlo comparando censos: se lee. La
    maquina no tiene fecha de instalacion —`fechacompra` es otra cosa—, y esa si
    hay que verla aparecer.
    """
    if es_centinela(fila):
        return {}
    out = {}
    for que, campo in (("clientes", "alta_cliente"), ("centros", "alta_centro"),
                       ("pdvs", "alta_pdv")):
        d = dias_desde(fila, campo, hoy)
        if d is not None and 0 <= d <= dias:
            out[que] = str(v(fila, campo, ""))[:10]
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
    "centro_sin_maquinas":  ("Centro sin una sola máquina",
                             "Tiene puntos de venta dados de alta y ni una máquina puesta en "
                             "ninguno. O se retiraron todas, o la instalación nunca llegó."),
    "instalacion_pendiente": ("Instalación pendiente",
                             "Punto de venta dado de alta hace menos de tres meses y todavía sin "
                             "máquina puesta."),
    "sin_tarifa":           ("Sin tarifa",
                             "Vende sin precio configurado —ni en el punto de venta, ni en el "
                             "centro, ni en el cliente—: dinero mal facturado o perdido."),
    "sin_planograma":       ("Sin planograma",
                             "No se puede saber qué debería haber en cada canal, así que tampoco "
                             "si estaba vacía o es que no había demanda."),
    "telemetria_sin_dato":  ("Telemetría sin dato electrónico",
                             "Tiene sistema de telemetría y no tiene dispositivo: la venta por "
                             "tarjeta no llega, y se descubre en el efectivo ciego meses después."),
}
