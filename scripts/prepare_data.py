#!/usr/bin/env python3
"""Normaliza las fuentes de servicio de vending de Airbus a tablas limpias.

Entrada  (data/raw/):
  ventas.csv                                  ventas may-ago, todos los centros salvo agosto de
                                              Getafe / Illescas / Albacete
  ventas_agosto_getafe_illescas_albacete.xlsx agosto de esos tres centros (con hora)
  visitas.xlsx, averias.xlsx, preventivos.xlsx
  dashboard_david_sanpablo.html               dashboard de referencia; de el se saca el censo de maquinas

Salida (data/processed/, CSV UTF-8 comprimido, fechas ISO, punto decimal):
  ventas.csv.gz  visitas.csv.gz  averias.csv.gz  preventivos.csv.gz  censo_maquinas.csv
"""
import csv
import datetime as dt
import gzip
import json
import re
import sys
from pathlib import Path

import openpyxl

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "data" / "processed"

# El libro de agosto solapa con el ultimo dia de julio del CSV grande, que manda.
CORTE_AGOSTO = dt.date(2026, 8, 1)


def numero(valor):
    """'1.234,56' o '1234.56' -> float."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    txt = str(valor).strip()
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    return float(txt)


def fecha(valor):
    """Devuelve (fecha ISO, hora HH:MM o cadena vacia)."""
    if valor is None or valor == "":
        return "", ""
    if isinstance(valor, dt.datetime):
        hora = valor.strftime("%H:%M") if (valor.hour or valor.minute) else ""
        return valor.date().isoformat(), hora
    if isinstance(valor, dt.date):
        return valor.isoformat(), ""
    txt = str(valor).strip()
    for patron in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S",
                   "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            d = dt.datetime.strptime(txt, patron)
        except ValueError:
            continue
        hora = d.strftime("%H:%M") if ("%H" in patron and (d.hour or d.minute)) else ""
        return d.date().isoformat(), hora
    return txt, ""


def escribir(nombre, columnas, filas):
    OUT.mkdir(parents=True, exist_ok=True)
    destino = OUT / nombre
    abrir = gzip.open if destino.suffix == ".gz" else open
    with abrir(destino, "wt", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(columnas)
        w.writerows(filas)
    print(f"  {destino.name}: {len(filas)} filas")
    return len(filas)


def hoja(path, nombre_hoja=None):
    """Itera una hoja de Excel devolviendo dicts por cabecera."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[nombre_hoja] if nombre_hoja else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    cabecera = [str(c).strip() if c is not None else "" for c in next(it)]
    for fila in it:
        if fila is None or all(c is None or c == "" for c in fila):
            continue
        yield dict(zip(cabecera, fila))
    wb.close()


def ventas():
    print("ventas")
    filas = []
    with open(RAW / "ventas.csv", encoding="utf-8-sig", newline="") as f:
        lector = csv.reader(f, delimiter=";")
        next(lector)
        for fila in lector:
            if not fila or not fila[0]:
                continue
            f_iso, _ = fecha(fila[2])
            filas.append([fila[0].strip(), fila[1].strip(), f_iso, "", fila[3].strip(),
                          int(numero(fila[4])), round(numero(fila[5]), 2)])
    base = len(filas)

    for r in hoja(RAW / "ventas_agosto_getafe_illescas_albacete.xlsx", "Table2"):
        f_iso, hora = fecha(r["Fecha"])
        if f_iso and dt.date.fromisoformat(f_iso) < CORTE_AGOSTO:
            continue  # ya viene en el CSV grande
        filas.append([str(r["Centro"]).strip(), str(r["PDV"]).strip(), f_iso, hora,
                      str(r["Artículo"]).strip(), int(numero(r["Cantidad"])),
                      round(numero(r["Importe"]), 2)])
    print(f"  {base} filas del CSV + {len(filas) - base} del libro de agosto")
    escribir("ventas.csv.gz",
             ["centro", "maquina", "fecha", "hora", "articulo", "cantidad", "importe"], filas)


def visitas():
    print("visitas")
    filas = []
    for r in hoja(RAW / "visitas.xlsx"):
        f_iso, hora = fecha(r["Fecha"])
        filas.append([str(r["Centro"]).strip(), str(r["Máquina"]).strip(), f_iso, hora,
                      str(r["Pdv"]).strip(), str(r["Ubicacion"]).strip(),
                      str(r["Ruta"]).strip(), str(r["Empleado"]).strip(),
                      str(r["Vehículo"]).strip(), str(r["Id"]).strip()])
    escribir("visitas.csv.gz",
             ["centro", "maquina", "fecha", "hora", "pdv", "ubicacion", "ruta",
              "empleado", "vehiculo", "id"], filas)


def averias():
    print("averias")
    filas = []
    for r in hoja(RAW / "averias.xlsx"):
        alta, hora_alta = fecha(r["fecharecepcion"])
        cierre, _ = fecha(r.get("fecha_cierre"))
        horas = ""
        if alta and cierre:
            try:
                horas = round((dt.date.fromisoformat(cierre) - dt.date.fromisoformat(alta)).days * 24, 1)
            except ValueError:
                horas = ""
        filas.append([str(r["denominacentro"] or "").strip(), str(r["codigomaquina"] or "").strip(),
                      alta, hora_alta, cierre, horas,
                      str(r["numero"] or "").strip(), str(r.get("modelomaquina") or "").strip(),
                      str(r.get("tipomaquina") or "").strip(), str(r["ubicacionpdv"] or "").strip(),
                      str(r["categoriaoperacion"] or "").strip(), str(r["operacion"] or "").strip(),
                      str(r["estadoactual"] or "").strip(), str(r.get("tecnicoresolutor") or "").strip()])
    escribir("averias.csv.gz",
             ["centro", "maquina", "fecha_alta", "hora_alta", "fecha_cierre", "horas_resolucion",
              "numero", "modelo", "tipo_maquina", "ubicacion", "categoria", "operacion",
              "estado", "tecnico"], filas)


def preventivos():
    print("preventivos")
    filas = []
    for r in hoja(RAW / "preventivos.xlsx"):
        f_iso, hora = fecha(r["Fecha"])
        filas.append([str(r["Centro"] or "").strip(), str(r["Máquina"] or "").strip(), f_iso, hora,
                      str(r["Pdv"] or "").strip(), str(r["Ubicacion"] or "").strip(),
                      str(r["Operación"] or "").strip(), str(r["Estado"] or "").strip(),
                      str(r["Realizada por"] or "").strip()])
    escribir("preventivos.csv.gz",
             ["centro", "maquina", "fecha", "hora", "pdv", "ubicacion", "operacion",
              "estado", "realizada_por"], filas)


def censo():
    """El censo con ubicacion solo existe dentro del dashboard de David (San Pablo)."""
    print("censo de maquinas")
    html = (RAW / "dashboard_david_sanpablo.html").read_text(encoding="utf-8")
    m = re.search(r"/\*__EMBEDDED_DATA_START__\*/(.*?)/\*__EMBEDDED_DATA_END__\*/", html, re.S)
    if not m:
        print("  aviso: no hay datos incrustados en el HTML")
        return
    datos = json.loads(m.group(1))
    filas = [[x["center"], x["machine"], x.get("location", "")] for x in datos.get("machineCensus", [])]
    escribir("censo_maquinas.csv", ["centro", "maquina", "ubicacion"], filas)


def main():
    if not RAW.exists():
        sys.exit(f"No encuentro {RAW}")
    ventas()
    visitas()
    averias()
    preventivos()
    censo()
    print(f"\nListo en {OUT}")


if __name__ == "__main__":
    main()
