"""
El catalogo de alarmas: la UNICA lista de lo que se puede vigilar.

Vive aqui, y no dentro de la Lambda de alarmas, porque lo necesitan dos sitios:
la Lambda que evalua y la API, que se lo sirve al navegador para construir el
formulario. Una lista repetida en el navegador se queda vieja el dia que alguien
anade una fuente y nadie se entera hasta que una alarma no salta.
"""

# fuente.campo -> (ruta dentro del panel, etiqueta, unidad)
# ruta None = todavia no esta en los agregados. No se evalua, se avisa.
CATALOGO = {
    "jornadas.temperatura_inicio": ("jornadas.temperatura_fuera", "Jornadas fuera de temperatura", "jornadas"),
    "jornadas.km":                 ("jornadas.km_total", "Kilometros del periodo", "km"),
    "jornadas.duracion":           ("jornadas.km.mediana", "Duracion mediana de jornada", "h"),
    "visitas.duracion_min":        ("servicio.duracion_min.mediana", "Duracion mediana de visita", "min"),
    "visitas.dias_sin_inventario": ("inventario.cumplimiento.pct_en_norma", "Inventario en norma", "%"),
    "visitas.dias_sin_visita":     (None, "Dias sin visita por maquina", "d"),
    "recaudacion.efectivo_ciego_mes": ("dinero.periodos.-1.efectivo_sin_telemetria", "Efectivo sin telemetria", "EUR"),
    "recaudacion.efectivo_sin_lectura": ("dinero.periodos.-1.pct_ciego", "Porcentaje ciego", "%"),
    "recaudacion.dias_sin_contar": (None, "Dias desde la recogida sin contar", "d"),
    "stock.caducidad_mes":         ("servicio.merma.caducidad.euros", "Caducidad del periodo", "EUR"),
    "stock.articulos_sin_coste":   (None, "Articulos cargados sin coste", ""),
    "stock.cambio_tubos":          (None, "Cambio parado en tubos", "EUR"),
    "sat.incidencias_30d":         ("sat.averias_tecnicas", "Averias tecnicas del periodo", ""),
    "sat.horas_abierta":           ("sat.horas_cierre.mediana", "Horas medianas hasta el cierre", "h"),
    "sat.devoluciones_30d":        (None, "Devoluciones en 30 dias", ""),
    "telemetria.horas_sin_venta":  (None, "Horas sin venta", "h"),
    "telemetria.venta_mes":        (None, "Venta mensual", "EUR"),
}


def para_el_navegador():
    """Lo mismo, en la forma que necesita un formulario.

    `evaluable` es la parte honesta: hay fuentes del catalogo que todavia no se
    calculan en los agregados. Se pueden crear igual —la alarma queda escrita y
    esperando—, pero el formulario lo dice en vez de dejar que alguien crea que
    esta vigilada.
    """
    return [{"clave": k, "fuente": k.split(".", 1)[0], "campo": k.split(".", 1)[1],
             "etiqueta": etiqueta, "unidad": unidad, "evaluable": ruta is not None}
            for k, (ruta, etiqueta, unidad) in sorted(CATALOGO.items())]
