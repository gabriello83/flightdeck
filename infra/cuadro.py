"""
El cuadro de mando de David, calculado por perfil.

David (AIRBUS San Pablo Sur) monto un cuadro que se alimenta arrastrando
cuatro Excel: Ventas, Visitas, Averias y Preventivos (referencia/dashboard-david).
Esto le da los mismos datos sin Excel, cada noche, y para todos los centros
del perfil: lo calcula la Lambda de agregados con lo que ya lee.

POR QUE VA APARTE DEL PANEL. El panel es un resumen de unos pocos KB que lee
tambien el asistente y las alarmas. El cuadro filtra en el navegador por dia,
centro, maquina y articulo, asi que necesita el detalle: venta por dia,
maquina y articulo. Para AIRBUS son cientos de miles de combinaciones en 120
dias. Meterlo en panel.json lo pondria en el contexto del asistente y rozaria
el limite de 6 MB de respuesta de una Lambda. Va en su carpeta,
`cabina/<perfil>/cuadro/`, y troceado por mes.

Lo calculan todos los perfiles de cliente (los que tienen ambito); quien lo
VE lo decide la sesion «cuadro», que se marca en la consola al editar el
perfil. El interno tiene todo el parque y no lo calcula.

DE DONDE SALE CADA HOJA DE DAVID

  Ventas       telemetria_ventas (venta a venta, con su fecha) si esta;
               si no, visita_ventas, que es PARCIAL: solo trae las maquinas
               que se leen en el parte y fecha la venta el dia de la lectura.
               El indice dice cual se uso, y la pagina lo avisa.
  Visitas      visita_cabecera, solo visitas de persona (reglas.visitas_reales).
  Averias      sat_averias, series A y E: David mete las dos («Reponer
               distribuidor automatico» es serie E y esta en su hoja).
  Preventivos  NO HAY FUENTE. Los «Mantenimiento preventivo» de David no estan
               en ningun informe que extraigamos. Se dice, no se rellena.

Sin dependencias: se prueba con `python3 infra/test_cuadro.py`.
"""

import datetime
import json
from collections import defaultdict

import reglas as R

# Un trozo de venta no puede pasar de aqui: la API lo devuelve en una sola
# respuesta de Lambda, que admite 6 MB. Con margen para la envoltura.
MAX_BYTES_TROZO = 4_500_000

FUENTE_TELEMETRIA = "telemetria"
FUENTE_VISITA = "visita_ventas"


def _txt(x, n=70):
    return str(x if x is not None else "").strip()[:n]


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


class Cuadro:
    """Lo que el cuadro de un perfil lleva sumado. Nada guarda filas enteras.

    La venta se guarda sumada por (dia, maquina, articulo): es la menor
    granularidad que usa el cuadro de David —filtra por dia y por articulo—,
    asi que sumar ahi no pierde nada de lo que la pagina ensena.
    """

    def __init__(self):
        # matricula -> {centro, ubicacion, pdv}: la poblacion de maquinas.
        self.censo = {}
        # Lo que se sabe de una maquina que no esta en el censo de hoy (se
        # retiro o se movio dentro de la ventana): su venta cuenta igual.
        self.vistas = {}
        self.ventas = defaultdict(lambda: [0.0, 0.0])
        self.dias_telemetria = set()
        self.dias_visita = set()
        self.visitas = []
        self.incidencias = {}

    # ------------------------------------------------------------- censo
    def come_instalaciones(self, filas):
        for f in filas:
            m = _txt(R.v(f, "matricula", ""), 20)
            if not m or R.es_centinela(f):
                continue
            if not (R.cliente_vivo(f) and R.centro_vivo(f) and R.pdv_vivo(f)):
                continue
            self.censo[m] = {"centro": _txt(R.v(f, "centro", "")),
                             "ubicacion": _txt(R.v(f, "ubicacion", "")),
                             "pdv": _txt(R.v(f, "cod_pdv", ""), 20)}

    def _ve(self, fila):
        """Apunta de que centro es una maquina que aparece en una fila con centro."""
        m = _txt(R.v(fila, "matricula", ""), 20)
        centro = _txt(R.v(fila, "centro", ""))
        if m and centro and m not in self.vistas:
            self.vistas[m] = {"centro": centro,
                              "ubicacion": _txt(R.v(fila, "ubicacion", "")),
                              "pdv": _txt(R.v(fila, "cod_pdv", ""), 20)}

    # ------------------------------------------------------------- venta
    def hay_telemetria(self, dia):
        """Ese dia hay telemetria en el crudo, sea o no de este perfil.

        Lo marca el handler con el fichero entero, antes de filtrar: si se
        marcara solo cuando al perfil le tocan filas, un dia sin venta de
        telemetria para el se rellenaria con la venta del parte.
        """
        self.dias_telemetria.add(dia.isoformat())

    def come_ventas_telemetria(self, filas, dia):
        """Venta a venta, con su fecha y hora. Es la fuente buena."""
        for f in filas:
            m = _txt(R.v(f, "matricula", ""), 20)
            if not m:
                continue
            self._ve(f)
            fecha = str(R.v(f, "fecha_venta", ""))[:10] or dia.isoformat()
            a = self.ventas[(fecha, m, _txt(R.v(f, "articulo", "Sin artículo")))]
            a[0] += 1
            a[1] += float(R.v(f, "precio", 0) or 0)

    def come_ventas_visita(self, filas, dia):
        """La venta que trae el parte: lo vendido desde la lectura anterior.

        Si ese dia ya hay telemetria no se usa: serian las mismas ventas
        contadas dos veces.
        """
        if dia.isoformat() in self.dias_telemetria:
            return
        self.dias_visita.add(dia.isoformat())
        for f in filas:
            m = _txt(R.v(f, "matricula", ""), 20)
            if not m or m == R.MATRICULA_FICTICIA:
                continue
            fecha = str(R.v(f, "fecha_visita", ""))[:10] or dia.isoformat()
            a = self.ventas[(fecha, m, _txt(R.v(f, "articulo", "Sin artículo")))]
            a[0] += float(R.v(f, "num_total", 0) or 0)
            a[1] += float(R.v(f, "imp_total", 0) or 0)

    # ------------------------------------------------------------- servicio
    def come_partes(self, filas):
        # Todos los partes, tambien los automaticos, ensenan de que centro es
        # la maquina: la venta del parte no trae centro y lo saca de aqui.
        for p in filas:
            self._ve(p)
        for p in R.visitas_reales(filas):
            m = _txt(R.v(p, "matricula", ""), 20)
            cuando = str(R.v(p, "fecha_ini", ""))[:16]
            if m and cuando:
                self.visitas.append((cuando, m))

    def come_sat(self, filas):
        for t in R.tareas_de_maquina(filas):
            m = _txt(R.v(t, "matricula", ""), 20)
            alta = str(R.v(t, "fecha_alta", ""))[:10]
            if not m or not R.fecha_valida(alta):
                continue
            self._ve(t)
            numero = f"{_txt(R.v(t, 'serie', ''), 4)}-{R.v(t, 'numero', '')}"
            fin = str(R.v(t, "fecha_fin", ""))[:10]
            # Por numero: la misma tarea puede llegar en dos noches (ventana de
            # reproceso) y se queda la ultima, que es la del estado mas nuevo.
            self.incidencias[numero] = (
                alta, fin if R.fecha_valida(fin) else "", m, numero,
                _txt(R.v(t, "categoria", "Sin categoría"), 40),
                _txt(R.v(t, "operacion", ""), 80),
                estado_de(t))

    # ------------------------------------------------------------- salida
    def fuente_ventas(self):
        if self.dias_telemetria and not self.dias_visita:
            return FUENTE_TELEMETRIA
        if self.dias_visita and not self.dias_telemetria:
            return FUENTE_VISITA
        return "mixta" if self.dias_visita else None

    def ficheros(self, perfil, periodo, generado=None):
        """{nombre de fichero: objeto}. El indice y un fichero de venta por trozo.

        Las maquinas y los articulos van una vez, en el indice, y el resto los
        cita por posicion: un nombre de articulo repetido 400.000 veces es la
        mitad del peso.
        """
        generado = generado or datetime.datetime.utcnow().isoformat() + "Z"
        centros, maquinas, idx_c, idx_m = [], [], {}, {}

        def centro_i(nombre):
            nombre = nombre or "(sin centro)"
            if nombre not in idx_c:
                idx_c[nombre] = len(centros)
                centros.append(nombre)
            return idx_c[nombre]

        def maquina_i(m):
            if m not in idx_m:
                d = self.censo.get(m) or self.vistas.get(m) or {}
                idx_m[m] = len(maquinas)
                maquinas.append([m, centro_i(d.get("centro", "")), d.get("ubicacion", ""),
                                 d.get("pdv", ""), 1 if m in self.censo else 0])
            return idx_m[m]

        # El censo primero y ordenado: asi la lista sale estable de una noche a otra.
        for m in sorted(self.censo, key=lambda x: (self.censo[x]["centro"], x)):
            maquina_i(m)

        articulos, idx_a = [], {}
        por_trozo = defaultdict(list)
        for (fecha, m, art), (u, imp) in sorted(self.ventas.items()):
            if not (periodo["desde"] <= fecha <= periodo["hasta"]):
                continue
            if art not in idx_a:
                idx_a[art] = len(articulos)
                articulos.append(art)
            por_trozo[fecha[:7]].append(
                [int(fecha[8:10]), maquina_i(m), idx_a[art], round(u, 3), round(imp, 2)])

        trozos = {}
        for mes, filas in sorted(por_trozo.items()):
            for i, parte in enumerate(_parte(filas)):
                nombre = mes if i == 0 else f"{mes}.{i + 1}"
                trozos[nombre] = {"trozo": nombre, "mes": mes,
                                  "_columnas": ["dia", "maquina", "articulo", "unidades", "importe"],
                                  "filas": parte}

        visitas = sorted(([c, maquina_i(m)] for c, m in self.visitas
                          if periodo["desde"] <= c[:10] <= periodo["hasta"]),
                         key=lambda x: x[0])
        incid = sorted(([alta, fin, maquina_i(m), num, cat, op, est]
                        for alta, fin, m, num, cat, op, est in self.incidencias.values()
                        if periodo["desde"] <= alta <= periodo["hasta"]),
                       key=lambda x: (x[0], x[3]))

        fuente = self.fuente_ventas()
        con_venta = {f[1] for t in trozos.values() for f in t["filas"]}
        en_censo = {i for i, x in enumerate(maquinas) if x[4]}
        indice = {
            "generado": generado,
            "perfil": perfil.get("id"),
            "nombre": perfil.get("nombre", ""),
            "periodo": periodo,
            "centros": centros,
            "maquinas": maquinas,
            "_maquinas": "[matricula, centro, ubicacion, punto de venta, esta en el censo de hoy]",
            "articulos": articulos,
            "trozos": list(trozos),
            "ventas": {
                "fuente": fuente,
                "dias_telemetria": len(self.dias_telemetria),
                "dias_visita": len(self.dias_visita),
                "maquinas_censo": len(en_censo),
                "maquinas_censo_con_venta": len(en_censo & con_venta),
                "_nota": NOTA_FUENTE.get(fuente, NOTA_FUENTE[None]),
            },
            "visitas": visitas,
            "_visitas": "[fecha y hora de inicio, maquina]. Solo visitas de persona.",
            "incidencias": incid,
            "_incidencias": "[alta, fin, maquina, numero, categoria, operacion, estado]",
            "preventivos": None,
            "_preventivos": ("Los mantenimientos preventivos del cuadro de David no estan en "
                             "ningun informe que se extraiga de VenCloud. No se rellenan."),
        }
        salida = {"indice.json": indice}
        for nombre, t in trozos.items():
            salida[f"ventas-{nombre}.json"] = t
        return salida


NOTA_FUENTE = {
    FUENTE_TELEMETRIA: "Venta de telemetria, venta a venta y con su fecha.",
    FUENTE_VISITA: ("Venta leida en el parte (visita_ventas). Es PARCIAL: solo trae las "
                    "maquinas que se leen en el parte, y fecha la venta el dia de la lectura, "
                    "no el de la venta. Para tenerla entera hace falta el informe "
                    "EXT_TELEMETRIA_VENTAS (docs/46)."),
    "mixta": ("Unos dias con telemetria y otros con la venta del parte, que es parcial. "
              "Los dias sin telemetria se quedan cortos."),
    None: "No hay ningun dato de venta en la ventana.",
}


def estado_de(tarea):
    """El texto del estado. tipo_estado 9 es cerrada; el resto, abierta.

    Comprobado contra el Excel de David: las 122 que el marca «Finalizado» y
    cruzan por numero tienen tipo_estado 9, y su fecha de cierre es nuestra
    fecha_fin.
    """
    te = int(R.v(tarea, "tipo_estado", 0) or 0)
    if te == 9:
        return "Finalizado"
    if te == 2:
        return "En pausa"
    return "Pendiente"


def _parte(filas):
    """Parte un mes en trozos que quepan en una respuesta, cortando por dia."""
    if len(_json(filas)) <= MAX_BYTES_TROZO or len({f[0] for f in filas}) < 2:
        return [filas]
    dias = sorted({f[0] for f in filas})
    corte = dias[len(dias) // 2]
    return (_parte([f for f in filas if f[0] < corte])
            + _parte([f for f in filas if f[0] >= corte]))
