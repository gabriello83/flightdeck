"""
Pruebas de las reglas del modelo.

Cada prueba reproduce una cifra que medimos de verdad sobre los datos de
VenCloud. Si alguien cambia una regla y rompe una de estas, esta rompiendo un
numero que ya fue comprobado contra el ERP.

    python3 infra/test_reglas.py
"""

import datetime
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import reglas as R  # noqa: E402

fallos = []


def comprueba(que, obtenido, esperado):
    if obtenido == esperado:
        print(f"  ok    {que}")
    else:
        print(f"  FALLO {que}: {obtenido!r} != {esperado!r}")
        fallos.append(que)


# ----------------------------------------------------------------------
print("\nVisitas: los partes del sistema no son visitas")
partes = (
    [{"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 2} for _ in range(2394)]
    + [{"empleadoid": 0, "empleado": "SYSTEM", "tipo_parte": 3} for _ in range(3)]
    + [{"empleadoid": 12, "empleado": "Ana", "tipo_parte": 0} for _ in range(1103)]
    + [{"empleadoid": 12, "empleado": "Ana", "tipo_parte": 100} for _ in range(4)]
)
comprueba("3.504 filas", len(partes), 3504)
comprueba("1.107 visitas reales", len(R.visitas_reales(partes)), 1107)
comprueba("coste de servicio del 25/09", R.coste_servicio(partes)["coste"], 8856.0)

# ----------------------------------------------------------------------
print("\n«Sin referencia» es 0, no nulo")
comprueba("articuloid 0 es sin referencia", R.sin_referencia({"articuloid": 0}, "articuloid"), True)
comprueba("articuloid nulo tambien", R.sin_referencia({"articuloid": None}, "articuloid"), True)
comprueba("articuloid 5 no", R.sin_referencia({"articuloid": 5}, "articuloid"), False)
comprueba("1900 no es fecha", R.fecha_valida("1900-01-01 00:00:00"), False)
comprueba("2026 si", R.fecha_valida("2026-09-25"), True)

# ----------------------------------------------------------------------
print("\nReposiciones: el valor cargado son las lineas CM")
lineas = [
    {"tipo_linea": "CM", "cantidad": 10, "precio_coste": 1.0, "etiq_canal": "44"},
    {"tipo_linea": "CM", "cantidad": 5,  "precio_coste": 2.0, "etiq_canal": "45"},
    {"tipo_linea": "RC", "cantidad": 3,  "precio_coste": 1.0, "etiq_canal": "44"},
    {"tipo_linea": "RM", "cantidad": 2,  "precio_coste": 1.0, "etiq_canal": "44"},
    {"tipo_linea": "CM", "cantidad": 100,"precio_coste": 0.004, "etiq_canal": ""},
]
comprueba("valor cargado bruto", R.valor_cargado(lineas), 20.4)
comprueba("unidades cargadas", R.unidades_cargadas(lineas), 115)
comprueba("la linea sin etiqueta es consumible", R.es_consumible_de_cafe(lineas[4]), True)
comprueba("la linea con etiqueta no", R.es_consumible_de_cafe(lineas[0]), False)

# ----------------------------------------------------------------------
print("\nMerma: se cuenta una vez, en la maquina, y se valora con puc")
mov = (
    [{"motivo": "RC", "cantidad": -1, "puc": 0.644} for _ in range(58)]
    + [{"motivo": "RR", "cantidad": -1, "puc": 0.30} for _ in range(8)]
    + [{"motivo": "CM", "cantidad": 20, "puc": 0.50} for _ in range(10)]
)
m = R.merma(mov)
comprueba("58 lineas de caducidad", m["caducidad"]["lineas"], 58)
comprueba("caducidad valorada a puc", m["caducidad"]["euros"], 37.35)
comprueba("la carga no entra en la merma", m["retirada"]["lineas"], 0)

# ----------------------------------------------------------------------
print("\nDinero: solo denominaciones reales de euro")
monbil = [
    {"valor": 2.00,  "encajon": 10},
    {"valor": 0.50,  "encajon": 20},
    {"valor": 12.75, "encajon": 686343},   # contador corrupto, no es una moneda
    {"valor": 2.55,  "encajon": 100},
]
comprueba("30 EUR, no 8,7 millones", R.efectivo_en_cajon(monbil), 30.0)

# ----------------------------------------------------------------------
print("\nRecaudacion: se agrupa por periodo contable, no por fecha de escritura")
rec = (
    [{"anho": 2026, "mes": 7, "imp_recaudado": 10, "imp_pago_bancario": 0,  "tipo_telemetria": 40, "criterio_calculo": 3}] * 5
    + [{"anho": 2026, "mes": 8, "imp_recaudado": 100,"imp_pago_bancario": 50, "tipo_telemetria": 40, "criterio_calculo": 3}] * 2
    + [{"anho": 2026, "mes": 8, "imp_recaudado": 30, "imp_pago_bancario": 0,  "tipo_telemetria": 0,  "criterio_calculo": 3}]
)
r = R.recaudacion_del_periodo(rec, 2026, 8)
comprueba("solo el periodo de agosto", r["registros"], 3)
comprueba("efectivo", r["efectivo"], 230.0)
comprueba("total = efectivo + banco", r["total"], 330.0)
comprueba("efectivo ciego", r["efectivo_sin_telemetria"], 30.0)
comprueba("porcentaje ciego", r["pct_ciego"], 13.0)
comprueba("critcalculo 1 no es recaudar", R.es_acto_de_recaudar({"criterio_calculo": 1}), False)
comprueba("critcalculo 3 si", R.es_acto_de_recaudar({"criterio_calculo": 3}), True)

print("\nEl mes en curso es provisional hasta el cierre del siguiente")
comprueba("septiembre visto en octubre", R.mes_provisional(2026, 9, datetime.date(2026, 10, 15)), True)
comprueba("agosto visto en octubre", R.mes_provisional(2026, 8, datetime.date(2026, 10, 15)), False)

# ----------------------------------------------------------------------
print("\nSAT: fuera la matricula ficticia, y una de cada cuatro es averia")
tareas = (
    [{"matricula": "00SE0000", "categoria": "ATENCION AL CLIENTE", "tipo_tarea": "A"}] * 6497
    + [{"matricula": "18FE1538", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "A"}] * 6400
    + [{"matricula": "18FE1538", "categoria": "ATENCION AL CLIENTE", "tipo_tarea": "A"}] * 14257
    + [{"matricula": "18FE1538", "categoria": "AVERIAS TECNICAS", "tipo_tarea": "E"}] * 389
)
comprueba("27.543 tareas en total", len(tareas), 27543)
comprueba("21.046 sobre maquinas reales", len(R.tareas_de_maquina(tareas)), 21046)
comprueba("6.400 averias tecnicas de tipo A",
          sum(1 for t in tareas if R.es_averia_tecnica(t) and not R.es_preventivo(t)), 6400)
comprueba("389 preventivos", sum(1 for t in tareas if R.es_preventivo(t)), 389)

# ----------------------------------------------------------------------
print("\nEl catalogo de SAT: se clasifica por operacion, no por categoria")
comprueba("101 operaciones menos 65 tecnicas = 36 no tecnicas",
          len(R.OPERACIONES_NO_TECNICAS), 36)
comprueba("22 retiradas", len(R.OPERACIONES_RETIRADAS), 22)

# C06 y T08 son la MISMA averia en dos categorias distintas: es el caso que
# demuestra que la categoria no clasifica.
c06 = {"cod_operacion": "C06", "categoria": "ATENCION AL CLIENTE"}
t08 = {"cod_operacion": "T08", "categoria": "AVERIAS TECNICAS"}
comprueba("T08 es fallo tecnico", R.es_fallo_tecnico(t08), True)
comprueba("y C06 tambien, aunque su categoria diga otra cosa", R.es_fallo_tecnico(c06), True)
comprueba("pero por categoria C06 no cuenta", R.es_averia_tecnica(c06), False)

comprueba("la limpieza no es fallo tecnico",
          R.es_fallo_tecnico({"cod_operacion": "C20"}), False)
comprueba("ni una devolucion de dinero",
          R.es_fallo_tecnico({"cod_operacion": "DEV01"}), False)
comprueba("ni cambiar un precio",
          R.es_fallo_tecnico({"cod_operacion": "S011"}), False)
comprueba("ni el cajon de sastre TECNICO - VARIOS",
          R.es_fallo_tecnico({"cod_operacion": "A036"}), False)
comprueba("una obsoleta tecnica si cuenta en el historico",
          R.es_fallo_tecnico({"cod_operacion": "C01"}), True)
comprueba("sin codigo, cae a la categoria",
          R.es_fallo_tecnico({"categoria": "AVERIAS TECNICAS"}), True)
comprueba("T55 esta retirada", R.operacion_retirada({"cod_operacion": "T55"}), True)
comprueba("T08 no", R.operacion_retirada({"cod_operacion": "T08"}), False)

print("\nLa cuenta de 2026, reproducida con el reparto medido")
# 27.543 tareas: 6.400 en la categoria AVERIAS TECNICAS, 3.410 fallos tecnicos
# archivados en ATENCION AL CLIENTE y 413 en operaciones retiradas.
tareas_2026 = ([dict(t08, n=1)] * 6400 + [dict(c06, n=1)] * 3410
               + [{"cod_operacion": "C01", "categoria": "Obsoletas"}] * 413
               + [{"cod_operacion": "D01", "categoria": "ATENCION AL CLIENTE"}] * 17320)
comprueba("27.543 tareas", len(tareas_2026), 27543)
comprueba("por categoria salen 6.400", sum(1 for x in tareas_2026 if R.es_averia_tecnica(x)), 6400)
comprueba("por operacion salen 10.223", sum(1 for x in tareas_2026 if R.es_fallo_tecnico(x)), 10223)

# ----------------------------------------------------------------------
print("\nTiempos: mediana, porque la media miente")
t = R.resumen_tiempos([1, 2, 3, 4, 5, 6, 7, 8, 9, 387])
comprueba("mediana 5,5", t["mediana"], 5.5)
comprueba("media arrastrada por el maximo", t["media"], 43.2)
comprueba("maximo", t["max"], 387.0)
comprueba("lista vacia no revienta", R.resumen_tiempos([])["n"], 0)

# ----------------------------------------------------------------------
print("\nInventario: las que nunca se contaron van aparte")
hoy = datetime.date(2026, 9, 29)
maq = (
    [{"ultimo_inventario": "2026-09-01"}] * 275
    + [{"ultimo_inventario": "2026-04-01"}] * 583
    + [{"ultimo_inventario": "2024-09-01"}] * 1579
    + [{"ultimo_inventario": "1900-01-01"}] * 763
)
c = R.cumplimiento_inventario(maq, hoy)
comprueba("3.200 maquinas", c["maquinas"], 3200)
comprueba("275 en norma", c["en_norma"], 275)
comprueba("763 nunca inventariadas", c["nunca"], 763)
comprueba("8,6 % en norma", c["pct_en_norma"], 8.6)

# ----------------------------------------------------------------------
print()
if fallos:
    print(f"{len(fallos)} PRUEBAS FALLIDAS: {', '.join(fallos)}")
    sys.exit(1)
print("Todas las reglas pasan.")
