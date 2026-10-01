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


def recaudacion_del_periodo(filas, anio, mes):
    """prefacrecauda se agrupa por anho/mes, nunca por `fecha`.

    `fecha` es la fecha de escritura. En agosto se escriben 57.452 filas de las
    que 52.161 son del periodo de julio. Y el cobro por tarjeta de un mes entero
    se escribe de golpe al mes siguiente, asi que el mes en curso se ve un 55 %
    mas pequeno de lo que es.
    """
    f = [x for x in filas if int(v(x, "anho")) == anio and int(v(x, "mes")) == mes]
    ef = round(sum(float(v(x, "imp_recaudado")) for x in f), 2)
    bk = round(sum(float(v(x, "imp_pago_bancario")) for x in f), 2)
    ciego = round(sum(float(v(x, "imp_recaudado")) for x in f
                      if int(v(x, "tipo_telemetria")) == 0), 2)
    return {
        "periodo": f"{anio}-{mes:02d}",
        "registros": len(f),
        "efectivo": ef,
        "banco": bk,
        "total": round(ef + bk, 2),
        "efectivo_sin_telemetria": ciego,
        "pct_ciego": round(100 * ciego / ef, 1) if ef else 0.0,
    }


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
    """Solo una de cada cuatro tareas de SAT es una averia.

    27.543 tareas en nueve meses, de las que 16.754 son atencion al cliente y
    6.400 averias tecnicas. Llamar "averias" a la tabla entera infla por cuatro.
    """
    return v(tarea, "categoria") == "AVERIAS TECNICAS"


def es_preventivo(tarea):
    """tipo_tarea separa averia (A) de preventivo (E)."""
    return v(tarea, "tipo_tarea") == "E"


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
