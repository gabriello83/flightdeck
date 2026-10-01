"""
Agregados de la cabina.

Lee el crudo que dejo la extraccion, aplica las reglas de `reglas.py` y escribe
los ficheros que leen los paneles. La pagina no consulta nada: abre un JSON.

Se ejecuta despues de la extraccion, encadenada por el planificador.

Variables de entorno:
  BUCKET       el mismo de la extraccion
  DIAS         (opcional) dias hacia atras que se agregan; por defecto 120
  PERFILES     (opcional) clave del fichero de perfiles; por defecto config/perfiles.json
"""

import datetime
import gzip
import json
import os
from collections import defaultdict

import boto3

import reglas as R

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
DIAS = int(os.environ.get("DIAS", "120"))
CLAVE_PERFILES = os.environ.get("PERFILES", "config/perfiles.json")


# ----------------------------------------------------------------------
# lectura del crudo
# ----------------------------------------------------------------------
def _json_de(clave):
    try:
        cuerpo = s3.get_object(Bucket=BUCKET, Key=clave)["Body"].read()
    except s3.exceptions.NoSuchKey:
        return None
    if clave.endswith(".gz"):
        cuerpo = gzip.decompress(cuerpo)
    return json.loads(cuerpo)


def _filas(dato):
    """Saca la lista de filas sea cual sea la envoltura que use el informe."""
    if dato is None:
        return []
    if isinstance(dato, list):
        return dato
    if isinstance(dato, dict):
        for k in ("Rows", "rows", "Data", "data", "Table", "Result", "d"):
            v = dato.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for k2 in ("Rows", "rows", "Table", "results"):
                    if isinstance(v.get(k2), list):
                        return v[k2]
    return []


def lee_dias(destino, id_informe, dias):
    """Concatena los ficheros diarios de un informe."""
    out = []
    for d in dias:
        clave = (f"{destino}/anio={d.year}/mes={d.month:02d}/dia={d.day:02d}/"
                 f"{id_informe}.json.gz")
        out.extend(_filas(_json_de(clave)))
    return out


def lee_maestro(destino, id_informe):
    return _filas(_json_de(f"{destino}/{id_informe}.json.gz"))


def escribe(clave, obj):
    s3.put_object(
        Bucket=BUCKET,
        Key=clave,
        Body=json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        ContentType="application/json",
        CacheControl="max-age=300",
        ServerSideEncryption="AES256",
    )
    return clave


# ----------------------------------------------------------------------
# filtrado por ambito
# ----------------------------------------------------------------------
def en_ambito(fila, ambito):
    """El ambito es aditivo: basta con encajar en uno de los tres.

    Un ambito vacio es "todo", y eso solo lo tienen los perfiles internos.
    """
    if not (ambito.get("clientes") or ambito.get("centros") or ambito.get("delegaciones")):
        return True
    centro = str(R.v(fila, "centro", ""))
    deleg = str(R.v(fila, "delegacion", ""))
    for c in ambito.get("clientes", []):
        if c.upper() in centro.upper():
            return True
    return centro in ambito.get("centros", []) or deleg in ambito.get("delegaciones", [])


# ----------------------------------------------------------------------
# los bloques del panel
# ----------------------------------------------------------------------
def bloque_servicio(partes, lineas, mov_maquina):
    reales = R.visitas_reales(partes)
    por_dia = defaultdict(int)
    for p in reales:
        por_dia[str(R.v(p, "fecha_ini", ""))[:10]] += 1
    return {
        "visitas": len(reales),
        "partes_totales": len(partes),
        "_nota_partes": "La diferencia son partes automaticos: leen maquina, no son visitas.",
        "maquinas": len({R.v(p, "matricula") for p in reales}),
        "centros": len({R.v(p, "centro") for p in reales}),
        "coste_servicio": R.coste_servicio(partes),
        "duracion_min": R.resumen_tiempos([R.v(p, "minutos") for p in reales]),
        "visitas_por_dia": [{"f": f, "v": n} for f, n in sorted(por_dia.items()) if f],
        "carga": {
            "valor": R.valor_cargado(lineas),
            "unidades_total": R.unidades_cargadas(lineas),
            "unidades_vendibles": R.unidades_cargadas([l for l in lineas if not R.es_consumible_de_cafe(l)]),
            "_nota": "Dos de cada tres unidades son consumibles de cafe: azucar, vasos y paletinas.",
        },
        "merma": R.merma(mov_maquina),
    }


def bloque_dinero(recaudacion, hoy):
    periodos = sorted({(int(R.v(x, "anho")), int(R.v(x, "mes"))) for x in recaudacion})
    out = []
    for anio, mes in periodos[-13:]:
        r = R.recaudacion_del_periodo(recaudacion, anio, mes)
        r["provisional"] = R.mes_provisional(anio, mes, hoy)
        if r["provisional"]:
            r["_nota"] = ("Mes sin cerrar: le falta el cobro por tarjeta, que se escribe "
                          "al mes siguiente y es el 55 % de la facturacion. No comparar "
                          "con un mes cerrado.")
        out.append(r)
    return {"periodos": out}


def bloque_sat(tareas, eventos):
    reales = R.tareas_de_maquina(tareas)
    por_maquina = defaultdict(int)
    for t in reales:
        por_maquina[R.v(t, "matricula")] += 1
    cierres = []
    por_averia = defaultdict(list)
    for e in eventos:
        por_averia[R.v(e, "averia_id")].append(e)
    for _, evs in por_averia.items():
        evs.sort(key=lambda e: str(R.v(e, "fecha", "")))
        cerrado = [e for e in evs if int(R.v(e, "estado", -1)) == 99]
        if evs and cerrado:
            try:
                a = datetime.datetime.fromisoformat(str(R.v(evs[0], "fecha"))[:19])
                b = datetime.datetime.fromisoformat(str(R.v(cerrado[0], "fecha"))[:19])
                cierres.append((b - a).total_seconds() / 3600)
            except Exception:
                pass
    return {
        "tareas": len(reales),
        "tareas_con_ficticia": len(tareas),
        "_nota_ficticia": f"{R.MATRICULA_FICTICIA} no es una maquina: se excluye.",
        "averias_tecnicas": sum(1 for t in reales if R.es_averia_tecnica(t) and not R.es_preventivo(t)),
        "preventivos": sum(1 for t in reales if R.es_preventivo(t)),
        "horas_cierre": R.resumen_tiempos(cierres),
        "reincidentes": sorted(
            [{"m": m, "n": n} for m, n in por_maquina.items() if n >= 5],
            key=lambda x: -x["n"])[:25],
    }


def bloque_jornadas(jornadas):
    temps = [float(R.v(j, "temperaturaini")) for j in jornadas if R.v(j, "temperaturaini", None) is not None]
    km = []
    for j in jornadas:
        a, b = float(R.v(j, "kminiciales")), float(R.v(j, "kmfinales"))
        if b > a > 0:
            km.append(b - a)
    con_gps = sum(1 for j in jornadas if R.v(j, "maplatitudini", 0))
    return {
        "jornadas": len(jornadas),
        "temperatura": R.resumen_tiempos(temps),
        "temperatura_fuera": sum(1 for t in temps if t > 8),
        "_nota_temp": "Frigorifico del vehiculo al arrancar. Por encima de 8 °C es cadena de frio.",
        "km": R.resumen_tiempos(km),
        "km_total": round(sum(km)),
        "gps": {"con": con_gps, "pct": round(100 * con_gps / len(jornadas), 1) if jornadas else 0},
    }


def bloque_inventario(balance, hoy):
    maquinas = [b for b in balance if R.v(b, "tipo_elemento") == "M"]
    return {
        "cumplimiento": R.cumplimiento_inventario(
            [{"ultimo_inventario": R.v(b, "fecha_ult_inventario", "")} for b in maquinas], hoy),
        "existencias": {
            t: round(sum(float(R.v(b, "valor_total")) for b in balance if R.v(b, "tipo_elemento") == t), 2)
            for t in ("A", "M", "V")
        },
    }


# ----------------------------------------------------------------------
# estado de la carga, para el panel de administracion
# ----------------------------------------------------------------------
def estado_de_la_carga(hoy):
    """Resume la ultima extraccion en cabina/, donde la web si puede leer.

    La API solo tiene permiso sobre cabina/, a proposito: no se le abre el
    registro entero para ensenar cuatro cifras. Se le deja aqui lo justo.
    """
    for atras in range(0, 4):
        d = hoy - datetime.timedelta(days=atras)
        clave = (f"registro/extraccion/anio={d.year}/mes={d.month:02d}/"
                 f"{d.isoformat()}.json")
        reg = _json_de(clave)
        if not reg:
            continue
        return {
            "ultima_carga": reg.get("ejecucion"),
            "dias_pedidos": reg.get("dias", []),
            "descargas_ok": reg.get("resumen", {}).get("descargas_ok"),
            "descargas_fallidas": reg.get("resumen", {}).get("descargas_fallidas"),
            "bytes": reg.get("resumen", {}).get("bytes"),
            "filas_por_informe": {x["id"]: x.get("filas") for x in reg.get("ok", [])},
            "errores": reg.get("errores", [])[:20],
            "retraso_dias": atras,
            "_nota": ("Si retraso_dias es mayor que 0, la carga de esta noche no "
                      "ha corrido y lo que se ve es de una noche anterior."),
        }
    return {"_nota": "No hay ningun registro de extraccion de los ultimos cuatro dias.",
            "retraso_dias": None}


# ----------------------------------------------------------------------
# ejecucion
# ----------------------------------------------------------------------
def lambda_handler(event, context):
    hoy = datetime.date.today()
    dias = [hoy - datetime.timedelta(days=d) for d in range(1, DIAS + 1)]

    crudo = {
        "partes":      lee_dias("crudo/visita_cabecera", "visita_cabecera", dias),
        "lineas":      lee_dias("crudo/visita_reposiciones", "visita_reposiciones", dias),
        "mov_maquina": lee_dias("crudo/stock_maquina", "stock_maquina", dias),
        "recaudacion": lee_dias("crudo/recaudacion", "recaudacion", dias),
        "sat":         lee_dias("crudo/sat_averias", "sat_averias", dias),
        "sat_eventos": lee_dias("crudo/sat_eventos", "sat_eventos", dias),
        "jornadas":    lee_dias("crudo/jornadas", "jornadas", dias),
        "balance":     lee_dias("crudo/stock_balance", "stock_balance", dias),
    }

    perfiles = _json_de(CLAVE_PERFILES) or {"perfiles": [{"id": "interno", "ambito": {}}]}
    escritos = []

    for p in perfiles["perfiles"]:
        amb = p.get("ambito", {})
        sel = {k: [f for f in v if en_ambito(f, amb)] for k, v in crudo.items()}
        panel = {
            "generado": datetime.datetime.utcnow().isoformat() + "Z",
            "perfil": p["id"],
            "periodo": {"desde": dias[-1].isoformat(), "hasta": dias[0].isoformat(), "dias": DIAS},
            "servicio":   bloque_servicio(sel["partes"], sel["lineas"], sel["mov_maquina"]),
            "dinero":     bloque_dinero(sel["recaudacion"], hoy),
            "sat":        bloque_sat(sel["sat"], sel["sat_eventos"]),
            "jornadas":   bloque_jornadas(sel["jornadas"]),
            "inventario": bloque_inventario(sel["balance"], hoy),
        }
        escritos.append(escribe(f"cabina/{p['id']}/panel.json", panel))

    resumen = {
        "ejecucion": datetime.datetime.utcnow().isoformat() + "Z",
        "dias": DIAS,
        "filas_leidas": {k: len(v) for k, v in crudo.items()},
        "ficheros": escritos,
    }
    escribe("cabina/_estado/carga.json", estado_de_la_carga(hoy))
    escribe(f"registro/agregados/anio={hoy.year}/mes={hoy.month:02d}/{hoy.isoformat()}.json", resumen)
    print(json.dumps(resumen, ensure_ascii=False))
    return resumen
