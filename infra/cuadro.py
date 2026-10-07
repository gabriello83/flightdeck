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

POR QUE CADA MES ES UN FICHERO QUE SE ENTIENDE SOLO. Con la historia desde el
1 de enero de 2025 ya no se puede recalcular todo cada noche —serian seiscientos
dias de lectura— ni bajarlo todo al navegador. Asi que cada mes lleva DENTRO su
lista de maquinas y de articulos y sus filas las citan por posicion dentro de
ese mes, no del indice. Eso compra dos cosas que antes no se podian hacer:

  · La noche solo reescribe los meses que ha mirado, y fusiona: los dias que no
    ha leido se quedan como estaban. La historia se acumula sin releerla.
  · El navegador baja SOLO los meses del periodo que el usuario elige. Una
    maquina retirada en marzo de 2025 sigue estando en el fichero de marzo de
    2025, aunque no este en el censo de hoy.

El indice lleva el censo de hoy —para los desplegables— y la lista de meses con
sus totales, que es lo que se pinta antes de bajar un solo mes.

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

# El fichero de un mes no puede pasar de aqui: la API lo devuelve en una sola
# respuesta de Lambda, que admite 6 MB. Con margen para la envoltura.
MAX_BYTES_MES = 4_500_000
MAX_BYTES_TROZO = MAX_BYTES_MES    # el nombre de antes, por si queda alguna cita

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
        self.ventas_imposibles = 0
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
            if R.venta_imposible(1, R.v(f, "precio", 0)):
                self.ventas_imposibles += 1
                continue
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
            # Se aparta y se cuenta: ver reglas.LIMITE_PRECIO_UNIDAD.
            if R.venta_imposible(R.v(f, "num_total", 0), R.v(f, "imp_total", 0)):
                self.ventas_imposibles += 1
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

    def _ficha(self, m):
        """Donde esta una maquina: el censo de hoy, o donde se la vio."""
        return self.censo.get(m) or self.vistas.get(m) or {}

    def meses(self, periodo):
        """{mes: fichero del mes}, cada uno completo y sin depender del indice.

        Solo los meses que TOCAN el periodo leido: los demas ya estan escritos
        de otra noche y no se vuelven a tocar. Un mes que el periodo toca se
        devuelve con los dias de ese periodo, y quien lo escribe lo fusiona con
        el que hubiera (ver `fusiona_mes`).
        """
        por_mes = defaultdict(lambda: {"ventas": [], "visitas": [], "incidencias": []})
        for (fecha, m, art), (u, imp) in sorted(self.ventas.items()):
            if periodo["desde"] <= fecha <= periodo["hasta"]:
                por_mes[fecha[:7]]["ventas"].append(
                    (fecha, m, art, round(u, 3), round(imp, 2)))
        for cuando, m in self.visitas:
            if periodo["desde"] <= cuando[:10] <= periodo["hasta"]:
                por_mes[cuando[:7]]["visitas"].append((cuando, m))
        for alta, fin, m, num, cat, op, est in self.incidencias.values():
            if periodo["desde"] <= alta <= periodo["hasta"]:
                por_mes[alta[:7]]["incidencias"].append((alta, fin, m, num, cat, op, est))

        salida = {}
        for mes, d in sorted(por_mes.items()):
            salida[mes] = codifica_mes(
                mes, d["ventas"], d["visitas"], d["incidencias"], self._ficha,
                en_censo=lambda m: m in self.censo,
                fuente=self.fuente_ventas_de(mes))
        return salida

    def fuente_ventas_de(self, mes):
        """Con que se lleno la venta de ese mes. Puede no ser la del conjunto."""
        tele = any(d[:7] == mes for d in self.dias_telemetria)
        parte = any(d[:7] == mes for d in self.dias_visita)
        if tele and not parte:
            return FUENTE_TELEMETRIA
        if parte and not tele:
            return FUENTE_VISITA
        return "mixta" if parte else None

    def indice(self, perfil, periodo, meses, generado=None):
        """La portada: el censo de hoy, la lista de meses y de donde sale la venta.

        `meses` son las lineas de todos los meses que hay en S3 —los de esta
        noche y los de antes—, no solo los recalculados: es lo que permite a la
        pagina ofrecer un intervalo de 2025 sin bajar nada todavia.
        """
        generado = generado or datetime.datetime.utcnow().isoformat() + "Z"
        centros, idx_c = [], {}

        def centro_i(nombre):
            nombre = nombre or "(sin centro)"
            if nombre not in idx_c:
                idx_c[nombre] = len(centros)
                centros.append(nombre)
            return idx_c[nombre]

        censo = [[m, centro_i(self.censo[m].get("centro", "")),
                  self.censo[m].get("ubicacion", ""), self.censo[m].get("pdv", "")]
                 for m in sorted(self.censo, key=lambda x: (self.censo[x]["centro"], x))]

        fuente = self.fuente_ventas()
        con_venta = {m for (_, m, _) in self.ventas}
        return {
            "generado": generado,
            "perfil": perfil.get("id"),
            "nombre": perfil.get("nombre", ""),
            # Lo que esta noche ha mirado. El detalle disponible es mas ancho:
            # es la union de los meses, y lo dice `meses`.
            "periodo": periodo,
            "centros": centros,
            "censo": censo,
            "_censo": "[matricula, centro, ubicacion, punto de venta]. El censo de HOY.",
            "meses": sorted(meses, key=lambda x: x["mes"]),
            "_meses": ("Un fichero por mes, con su propia lista de maquinas y articulos. "
                       "La pagina baja solo los del periodo que se elija."),
            "ventas": {
                "fuente": fuente,
                "dias_telemetria": len(self.dias_telemetria),
                "dias_visita": len(self.dias_visita),
                # Lecturas apartadas por precio imposible (reglas.LIMITE_PRECIO_UNIDAD).
                "lecturas_imposibles": self.ventas_imposibles,
                "maquinas_censo": len(self.censo),
                "maquinas_censo_con_venta": len(set(self.censo) & con_venta),
                "_nota": NOTA_FUENTE.get(fuente, NOTA_FUENTE[None]),
            },
            "preventivos": None,
            "_preventivos": ("Los mantenimientos preventivos del cuadro de David no estan en "
                             "ningun informe que se extraiga de VenCloud. No se rellenan."),
        }


# ----------------------------------------------------------------------
# el fichero de un mes: codificar, leer y fusionar
# ----------------------------------------------------------------------
# Las tres funciones van juntas porque son la misma decision vista de tres
# lados: dentro del fichero de un mes, una fila cita su maquina y su articulo
# por POSICION en las listas DE ESE MES. Codificar las construye, descodificar
# las deshace y fusionar vuelve a empezar. Si alguna se desalinea, el mes
# entero queda atribuido a las maquinas equivocadas, asi que no se tocan por
# separado: `test_cuadro.py` las prueba de ida y vuelta.

COLUMNAS_VENTA = ["dia", "maquina", "articulo", "unidades", "importe"]


def codifica_mes(mes, ventas, visitas, incidencias, ficha=None, en_censo=None, fuente=None):
    """El fichero de un mes a partir de sus filas con nombres.

    `ventas` son (fecha, matricula, articulo, unidades, importe); `visitas`,
    (fecha y hora, matricula); `incidencias`, (alta, fin, matricula, numero,
    categoria, operacion, estado).
    """
    ficha = ficha or (lambda m: {})
    en_censo = en_censo or (lambda m: False)
    centros, idx_c = [], {}
    maquinas, idx_m = [], {}

    def centro_i(nombre):
        nombre = nombre or "(sin centro)"
        if nombre not in idx_c:
            idx_c[nombre] = len(centros)
            centros.append(nombre)
        return idx_c[nombre]

    def maquina_i(m):
        if m not in idx_m:
            d = ficha(m) or {}
            idx_m[m] = len(maquinas)
            maquinas.append([m, centro_i(d.get("centro", "")), d.get("ubicacion", ""),
                             d.get("pdv", ""), 1 if en_censo(m) else 0])
        return idx_m[m]

    articulos, idx_a = [], {}

    def articulo_i(a):
        if a not in idx_a:
            idx_a[a] = len(articulos)
            articulos.append(a)
        return idx_a[a]

    # Ordenadas antes de indexar: asi el mismo mes sale byte a byte igual de
    # una noche a otra y un diff dice algo.
    filas_v = [[int(fecha[8:10]), maquina_i(m), articulo_i(art), u, imp]
               for fecha, m, art, u, imp in sorted(ventas)]
    filas_vi = [[cuando, maquina_i(m)] for cuando, m in sorted(visitas)]
    filas_i = [[alta, fin, maquina_i(m), num, cat, op, est]
               for alta, fin, m, num, cat, op, est
               in sorted(incidencias, key=lambda x: (x[0], x[3]))]
    con_venta = {f[1] for f in filas_v}
    return {
        "mes": mes,
        "maquinas": maquinas,
        "_maquinas": "[matricula, centro, ubicacion, punto de venta, esta en el censo de hoy]",
        "centros": centros,
        "articulos": articulos,
        "_columnas": COLUMNAS_VENTA,
        "ventas": filas_v,
        "visitas": filas_vi,
        "_visitas": "[fecha y hora de inicio, maquina]. Solo visitas de persona.",
        "incidencias": filas_i,
        "_incidencias": "[alta, fin, maquina, numero, categoria, operacion, estado]",
        "fuente": fuente,
        "maquinas_con_venta": len(con_venta),
    }


def descodifica_mes(fichero):
    """Deshace un fichero de mes: devuelve las filas con sus nombres.

    Tolera que falte algo: un fichero a medias se lee como lo que tenga en vez
    de tumbar la fusion y perder el mes entero.
    """
    f = fichero or {}
    mes = f.get("mes", "")
    centros = f.get("centros") or []
    maquinas = f.get("maquinas") or []

    def nombre(i):
        try:
            return maquinas[i][0]
        except (IndexError, TypeError):
            return ""

    def ficha(i):
        try:
            m = maquinas[i]
        except (IndexError, TypeError):
            return {}
        try:
            centro = centros[m[1]]
        except (IndexError, TypeError):
            centro = ""
        return {"centro": centro, "ubicacion": m[2] if len(m) > 2 else "",
                "pdv": m[3] if len(m) > 3 else "", "en_censo": bool(m[4]) if len(m) > 4 else False}

    articulos = f.get("articulos") or []
    ventas = []
    for fila in f.get("ventas") or []:
        dia, m, a, u, imp = fila
        nom = nombre(m)
        if nom:
            ventas.append((f"{mes}-{int(dia):02d}", nom,
                           articulos[a] if a < len(articulos) else "Sin artículo", u, imp))
    visitas = [(cuando, nombre(m)) for cuando, m in (f.get("visitas") or []) if nombre(m)]
    incid = [(alta, fin, nombre(m), num, cat, op, est)
             for alta, fin, m, num, cat, op, est in (f.get("incidencias") or []) if nombre(m)]
    fichas = {nombre(i): ficha(i) for i in range(len(maquinas)) if nombre(i)}
    return {"mes": mes, "ventas": ventas, "visitas": visitas, "incidencias": incid,
            "fichas": fichas, "fuente": f.get("fuente")}


def fusiona_mes(viejo, nuevo, dias=None):
    """El mes que ya habia, con los dias recalculados encima.

    `dias` son los dias que esta ejecucion ha leido de verdad (AAAA-MM-DD). Los
    dias de esa lista se SUSTITUYEN por lo nuevo —es el mismo dia visto otra
    vez, no mas dato— y los demas se quedan. Sin la lista se toman los dias que
    aparezcan en lo nuevo, que es lo mismo salvo en un dia que haya quedado a
    cero: por eso quien la tiene la pasa.

    Una maquina que solo esta en lo viejo —retirada desde entonces— conserva su
    ficha: el fichero de marzo de 2025 tiene que seguir sabiendo de que centro
    era una maquina que ya no existe.
    """
    if not viejo:
        return nuevo
    if not nuevo:
        return viejo
    v, n = descodifica_mes(viejo), descodifica_mes(nuevo)
    tocados = set(dias) if dias else {f[0] for f in n["ventas"]} | \
        {c[:10] for c, _ in n["visitas"]} | {i[0] for i in n["incidencias"]}

    ventas = [f for f in v["ventas"] if f[0] not in tocados] + list(n["ventas"])
    visitas = [x for x in v["visitas"] if x[0][:10] not in tocados] + list(n["visitas"])
    # Las incidencias van por numero, no por dia: la misma tarea se vuelve a
    # bajar mientras siga en la ventana y lo nuevo es su estado mas reciente.
    nuevas = {i[3] for i in n["incidencias"]}
    incid = [i for i in v["incidencias"] if i[3] not in nuevas and i[0] not in tocados]
    incid += list(n["incidencias"])

    fichas = dict(v["fichas"])
    fichas.update(n["fichas"])        # lo de hoy manda: una maquina se muda
    fuentes = {x for x in (v.get("fuente"), n.get("fuente")) if x}
    fuente = n.get("fuente") or v.get("fuente")
    if len(fuentes) > 1:
        fuente = "mixta"
    return codifica_mes(n["mes"] or v["mes"], ventas, visitas, incid,
                        ficha=lambda m: fichas.get(m, {}),
                        en_censo=lambda m: bool(fichas.get(m, {}).get("en_censo")),
                        fuente=fuente)


def resumen_mes(fichero):
    """La linea de un mes en el indice. Se calcula del fichero ya fusionado."""
    f = fichero or {}
    ventas = f.get("ventas") or []
    return {
        "mes": f.get("mes", ""),
        "filas": len(ventas),
        "unidades": round(sum(float(x[3] or 0) for x in ventas), 2),
        "importe": round(sum(float(x[4] or 0) for x in ventas), 2),
        "visitas": len(f.get("visitas") or []),
        "incidencias": len(f.get("incidencias") or []),
        "maquinas_con_venta": f.get("maquinas_con_venta", 0),
        "fuente": f.get("fuente"),
        # Cuanto pesa el mes sin comprimir. Lo lee la pagina para avisar antes
        # de bajar medio ano de detalle de golpe, y para que se vea de un mes
        # para otro si alguno se esta acercando al limite de respuesta.
        "bytes": len(_json(f)),
    }


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


def cabe_en_una_respuesta(fichero):
    """Si el mes cabe en una respuesta de Lambda. Se mira, no se supone.

    Antes los meses se partian en trozos cuando pasaban del limite. Con el mes
    como fichero que se entiende solo eso no vale: un trozo con media lista de
    maquinas no se puede fusionar. Asi que ahora no se parte y se COMPRUEBA: si
    un mes no cabe, lo dice el resumen del indice y se arregla donde toca
    —agrupando mas la venta— en vez de descubrirlo con un 500 en el navegador.
    """
    return len(_json(fichero)) <= MAX_BYTES_MES
