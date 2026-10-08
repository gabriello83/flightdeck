"""
La API de la plataforma. Un solo origen: todo esto se sirve en /api/* del mismo
dominio que la pagina, asi que el navegador no llama a nadie mas.

Como funciona el acceso, y por que asi:

  CONTRASENAS -> Cognito. Aqui no se guarda ningun hash: la politica de
  contrasenas, el cambio obligatorio del primer acceso y el cifrado son suyos.
  El NAVEGADOR NO HABLA CON COGNITO; si lo hiciera estaria llamando a
  cognito-idp.amazonaws.com, que es exactamente el dominio externo que no
  podemos usar. Habla con /api/acceso, y esta Lambda habla con Cognito desde
  dentro de AWS.

  SESION -> una fila nuestra con caducidad, y una cookie HttpOnly. No un JWT:
  con una fila propia se puede cerrar la sesion de alguien en el acto, y un
  token firmado no se puede retirar antes de que caduque.

  AMBITO -> el perfil sale de la sesion, nunca de la peticion.

Solo biblioteca estandar y boto3: nada que empaquetar.
"""

import datetime
import json
import os
import secrets

import boto3

import autorizacion as A
import catalogo as CAT
from comun import (abre_sesion, borra, cierra_sesion, config, cookie_sesion,
                   cuerpo, escribe, lee, lista, panel_de, quien_es, r, s3, BUCKET)

cog = boto3.client("cognito-idp")

POOL = os.environ.get("POOL", "")
CLIENTE = os.environ.get("CLIENTE_POOL", "")
INTENTOS_MAX = int(os.environ.get("INTENTOS_MAX", "6"))
MINUTOS_BLOQUEO = int(os.environ.get("MINUTOS_BLOQUEO", "15"))


# ----------------------------------------------------------------------
# freno a la fuerza bruta
# ----------------------------------------------------------------------
def _fallos(correo):
    return int((lee(f"FALLOS#{correo}", "CUENTA") or {}).get("n", 0))


def _suma_fallo(correo):
    import time
    n = _fallos(correo) + 1
    escribe(f"FALLOS#{correo}", {"n": n}, "CUENTA",
            expira=int(time.time()) + MINUTOS_BLOQUEO * 60)
    return n


def _limpia_fallos(correo):
    borra(f"FALLOS#{correo}", "CUENTA")


# ----------------------------------------------------------------------
# entrada
# ----------------------------------------------------------------------
def lambda_handler(evento, contexto):
    http = evento.get("requestContext", {}).get("http", {})
    metodo = http.get("method", "GET")
    # API Gateway entrega el path limpio, pero una barra final de mas convertiria
    # una ruta buena en un 404 sin que nadie entienda por que.
    ruta = (http.get("path") or "/").split("?")[0].rstrip("/") or "/"
    cab = {k.lower(): v for k, v in (evento.get("headers") or {}).items()}

    # Una escritura que venga de otro sitio no entra. Con la cookie en
    # SameSite=Strict el navegador ya no la manda; esto lo confirma donde el
    # propio navegador lo declara.
    if metodo not in ("GET", "HEAD") and cab.get("sec-fetch-site") not in (None, "same-origin"):
        return r(403, {"error": "Peticion de otro origen."})

    try:
        return encamina(evento, metodo, ruta)
    except PermissionError as e:
        return r(403, {"error": str(e) or "Sin permiso."})
    except ValueError as e:
        return r(400, {"error": str(e)})
    except Exception as e:  # noqa: BLE001
        print(f"ERROR {metodo} {ruta}: {type(e).__name__}: {e}")
        return r(500, {"error": "Error interno."})


def encamina(evento, metodo, ruta):
    # ---------------------------------------------------- publico
    if ruta == "/api/acceso" and metodo == "POST":
        return acceso(evento)
    if ruta == "/api/acceso/nueva-clave" and metodo == "POST":
        return nueva_clave(evento)

    # ---------------------------------------------------- hace falta sesion
    sesion = quien_es(evento)
    if not sesion:
        return r(401, {"error": "Sin sesion."})
    usuario, perfil = sesion["usuario"], sesion["perfil"]
    c = config()
    permisos = A.permisos_efectivos(perfil, usuario, c)

    if ruta == "/api/salir" and metodo == "POST":
        cierra_sesion(sesion["token"])
        return r(200, {"ok": True}, [cookie_sesion("")])

    if ruta == "/api/yo":
        ok_ia, motivo = A.asistente_habilitado(c, perfil, usuario)
        return r(200, {
            "correo": usuario["correo"],
            "nombre": usuario.get("nombre", ""),
            "tipo": perfil.get("tipo", "cliente"),
            "perfil": perfil.get("nombre") or perfil.get("perfil_id", ""),
            "perfil_id": perfil.get("perfil_id", ""),
            "sesiones": sesiones_visibles(perfil),
            "catalogo_sesiones": {k: v[0] for k, v in A.SESIONES.items()},
            # Que partes del cuadro ve, y que datos le llegan para ellas.
            "cuadro": {"secciones": A.secciones_cuadro(perfil),
                       "flujos": A.flujos_cuadro(perfil)},
            "permisos": permisos,
            "asistente": {"habilitado": ok_ia, "motivo": motivo},
            "umbral": perfil.get("reglas_negocio", {}).get(
                "umbral_rentabilidad_mes", c["umbral_rentabilidad_mes"]),
        })

    if ruta == "/api/panel":
        p = panel_de(perfil.get("perfil_id", ""))
        if p is None:
            return r(503, {"error": "El panel todavia no se ha calculado.",
                           "_nota": "Los agregados corren a las 4:45; recien desplegado, lanzalos a mano."})
        return r(200, A.recorta(p, perfil))

    # El cuadro de mando: el indice, o el fichero de un mes. Igual que el panel,
    # la carpeta sale del perfil de la sesion; lo unico que se pide es QUE mes, y
    # se valida contra la lista del propio indice antes de tocar S3.
    if ruta == "/api/cuadro" and metodo == "GET":
        if "cuadro" not in A.sesiones_de(perfil.get("tipo", "cliente"), perfil.get("sesiones", [])):
            raise PermissionError("Este perfil no tiene el cuadro de mando.")
        q = evento.get("queryStringParameters") or {}
        # Se mira si el parametro VIENE, no si trae algo: con `or`, un mes vacio
        # se colaba como «dame el indice» en vez de darse por no valido.
        # «trozo» es el nombre que uso la version de meses troceados.
        return cuadro(perfil, q["mes"] if "mes" in q else q.get("trozo"))

    # La serie diaria: el indice de meses, o un mes. Es lo que permite pedir hoy,
    # ayer, este mes, el mes pasado o un intervalo cualquiera desde 2025 sin que
    # la pagina tenga que bajarse la historia entera.
    if ruta == "/api/serie" and metodo == "GET":
        q = evento.get("queryStringParameters") or {}
        if "centros" in q:
            return serie_centros(perfil, q["centros"])
        return serie(perfil, q.get("mes"))

    # El orden lo elige el usuario y se guarda en el SERVIDOR: asi lo encuentra
    # igual desde otro ordenador. El navegador no es el sitio donde vive.
    if ruta == "/api/orden":
        clave = f"PREF#{usuario['correo']}"
        if metodo == "GET":
            return r(200, lee(clave, "ORDEN") or {"orden": []})
        if metodo == "PUT":
            if not permisos.get("reordenar"):
                raise PermissionError("Este perfil no puede reordenar los paneles.")
            orden = cuerpo(evento).get("orden")
            if not isinstance(orden, list) or len(orden) > 64:
                raise ValueError("Orden no valido.")
            escribe(clave, {"orden": [str(x)[:40] for x in orden]}, "ORDEN")
            return r(200, {"ok": True})

    # El catalogo lo sirve la API para que el formulario del navegador no lleve
    # una copia que se quede vieja en cuanto alguien anada una fuente.
    if ruta == "/api/catalogo-alarmas" and metodo == "GET":
        if not permisos.get("alarmas_ver"):
            raise PermissionError("Este perfil no ve las alarmas.")
        return r(200, {"catalogo": CAT.para_el_navegador()})

    if ruta == "/api/alarmas":
        if metodo == "GET":
            if not permisos.get("alarmas_ver"):
                raise PermissionError("Este perfil no ve las alarmas.")
            return r(200, {"alarmas": lista("ALARMA#"), "avisos": lista("AVISO#")[-100:]})
        if metodo == "POST":
            if not permisos.get("alarmas_crear"):
                raise PermissionError("Este perfil no puede crear alarmas.")
            return guarda_alarma(evento, usuario)

    if ruta.startswith("/api/alarmas/") and metodo == "DELETE":
        if not permisos.get("alarmas_crear"):
            raise PermissionError("Este perfil no puede borrar alarmas.")
        borra("ALARMA#" + ruta.rsplit("/", 1)[-1])
        return r(200, {"ok": True})

    if ruta == "/api/whatsapp" and metodo == "POST":
        if not permisos.get("whatsapp"):
            raise PermissionError("Este perfil no puede enviar WhatsApp.")
        return encola(evento, usuario, "whatsapp")

    if ruta == "/api/incidencia" and metodo == "POST":
        if not permisos.get("incidencia"):
            raise PermissionError("Este perfil no puede abrir incidencias.")
        return encola(evento, usuario, "incidencia")

    if ruta == "/api/estado-carga":
        if perfil.get("tipo") != "admin":
            raise PermissionError("Solo el administrador.")
        try:
            b = s3.get_object(Bucket=BUCKET, Key="cabina/_estado/carga.json")["Body"].read()
            return r(200, json.loads(b))
        except Exception:
            return r(200, {"_nota": "Todavia no hay ninguna carga registrada."})

    # ---------------------------------------------------- administracion
    if ruta.startswith("/api/admin/"):
        if perfil.get("tipo") != "admin":
            raise PermissionError("Solo el administrador.")
        return administra(evento, metodo, ruta, usuario)

    return r(404, {"error": "No existe esa ruta."})


# ----------------------------------------------------------------------
# el cuadro de mando
# ----------------------------------------------------------------------
def _crudo(clave):
    """El fichero de S3 tal cual, descomprimido si viene comprimido.

    Un mes de venta son un par de MB: leerlo como JSON y volver a escribirlo
    solo gastaria memoria y tiempo de una Lambda de 512 MB para devolver lo
    mismo. Los meses se guardan comprimidos —un mes de AIRBUS pasa de tres
    megas a unos cuatrocientos kilos—, asi que lo unico que se hace es
    descomprimirlos.
    """
    cuerpo = s3.get_object(Bucket=BUCKET, Key=clave)["Body"].read()
    if cuerpo[:2] == b"\x1f\x8b":
        import gzip
        cuerpo = gzip.decompress(cuerpo)
    return cuerpo


def _como_json(cuerpo):
    return {"statusCode": 200,
            "headers": {"content-type": "application/json; charset=utf-8",
                        "cache-control": "no-store"},
            "body": cuerpo.decode("utf-8")}


def _mes_valido(indice, mes):
    """Un mes que el indice de ese perfil cite, y nada mas.

    Asi no hay forma de componer otra clave: ni de otro mes inventado, ni —lo
    que importa— de otro perfil. El nombre no se concatena hasta despues de
    encontrarlo en la lista.
    """
    meses = [str(m.get("mes")) for m in (json.loads(indice).get("meses") or [])]
    if str(mes) not in meses:
        raise ValueError("Ese mes no existe en este cuadro.")
    return str(mes)


def _hay_cuadro(perfil_id):
    """Si el cuadro de este perfil esta calculado: una cabecera, nada mas."""
    if not perfil_id:
        return False
    try:
        s3.head_object(Bucket=BUCKET, Key=f"cabina/{perfil_id}/cuadro/indice.json")
        return True
    except Exception:
        return False


def sesiones_visibles(perfil):
    """Las sesiones que se ensenan, sin el cuadro si el perfil no lo tiene.

    El administrador ve todas las sesiones sin que nadie se las conceda, y el
    cuadro solo se calcula para los perfiles de cliente (los que tienen
    ambito). Con el perfil interno, el boton «Cuadro de mando» llevaba a una
    pagina que decia que no se habia calculado, y la entrada le mandaba alli
    a quien lo tuviera. Lo que no existe no se ofrece. /api/cuadro sigue
    contestando 503 a quien lo pida a mano.
    """
    sesiones = A.sesiones_de(perfil.get("tipo", "cliente"), perfil.get("sesiones", []))
    if "cuadro" in sesiones and not _hay_cuadro(perfil.get("perfil_id", "")):
        sesiones.remove("cuadro")
    return sesiones


def cuadro(perfil, mes=None):
    """El indice del cuadro, o el fichero de un mes, con lo que el perfil ve.

    Si el perfil ve todas las secciones, el fichero sale tal cual, sin leerlo
    como JSON. Si se le ha quitado alguna, se quitan del fichero los flujos
    que ya no necesita (docs/49): ocultar la seccion en la pagina no basta,
    porque el dato seguiria llegando al navegador.
    """
    base = f"cabina/{perfil.get('perfil_id', '')}/cuadro/"
    entero = A.flujos_cuadro(perfil) == list(A.TODOS_FLUJOS)
    try:
        indice = _crudo(base + "indice.json")
    except Exception:
        return r(503, {"error": "El cuadro de mando todavia no se ha calculado.",
                       "_nota": "Lo escriben los agregados (4:45) para cada perfil de "
                                "cliente con ambito."})
    if mes is None:
        if entero:
            return _como_json(indice)
        return r(200, A.recorta_cuadro_indice(json.loads(indice), perfil))
    fichero = _crudo(f"{base}mes-{_mes_valido(indice, mes)}.json.gz")
    if entero:
        return _como_json(fichero)
    return r(200, A.recorta_cuadro_mes(json.loads(fichero), perfil))


def serie(perfil, mes=None):
    """La serie diaria del perfil de la sesion: el indice de meses, o un mes.

    El recorte es el mismo que el del panel y por lo mismo: una fila de la serie
    lleva los mismos bloques —servicio, dinero, sat, jornadas—, asi que un
    perfil que no ve el dinero en el panel tampoco puede verlo aqui dia a dia.
    Si no se recortara, la serie seria la puerta de atras del panel.
    """
    perfil_id = perfil.get("perfil_id", "")
    base = f"cabina/{perfil_id}/serie/"
    try:
        indice = _crudo(base + "indice.json")
    except Exception:
        return r(503, {"error": "El historico todavia no se ha calculado.",
                       "_nota": "Lo escriben los agregados cada noche; la historia "
                                "anterior se rellena a mano una vez."})
    if mes is None:
        return r(200, indice_serie_visible(json.loads(indice), perfil))
    mes = _mes_valido(indice, mes)
    datos = json.loads(_crudo(f"{base}{mes}.json.gz"))
    return r(200, {"mes": mes,
                   "filas": [A.recorta_dia(f, perfil) for f in datos.get("filas", [])]})


def ve_delegaciones(perfil):
    """La delegacion es organizacion interna de Serunion: un cliente no la ve,
    ni como filtro ni en la ficha de sus centros."""
    return A.nivel_de(perfil.get("tipo", "cliente")) >= A.NIVEL["operaciones"]


def indice_serie_visible(indice, perfil):
    """El indice de la serie como lo puede ver este perfil.

    Las fichas de los centros llevan cliente y delegacion para poder filtrar.
    Un perfil de cliente se queda sin la delegacion: no es suya, es nuestra.
    Los centros que salen son solo los de su serie, que ya se calculo con su
    ambito: no hay forma de ver un centro de otro.
    """
    interno = ve_delegaciones(perfil)
    indice = dict(indice)
    indice["centros"] = {k: {c: x for c, x in (v or {}).items()
                             if interno or c != "delegacion"}
                         for k, v in (indice.get("centros") or {}).items()}
    indice["filtros"] = ["delegacion", "cliente", "centro"] if interno else ["cliente", "centro"]
    return indice


def serie_centros(perfil, mes):
    """El mismo dia partido por centro, para el filtro de delegacion, cliente y
    centro. Con la misma tijera que la fila del dia, centro a centro."""
    base = f"cabina/{perfil.get('perfil_id', '')}/serie/"
    try:
        indice = json.loads(_crudo(base + "indice.json"))
    except Exception:
        return r(503, {"error": "El historico todavia no se ha calculado."})
    if str(mes) not in [str(m) for m in (indice.get("meses_centros") or [])]:
        raise ValueError("Ese mes no tiene el reparto por centro.")
    mes = str(mes)
    datos = json.loads(_crudo(f"{base}centros-{mes}.json.gz"))
    filas = []
    for f in datos.get("filas", []):
        centros = {}
        for clave, c in (f.get("centros") or {}).items():
            x = A.recorta_dia(dict(c, f=None), perfil)
            x.pop("f", None)
            if x:
                centros[clave] = x
        filas.append({"f": f.get("f"), "centros": centros})
    return _json_grande({"mes": mes, "filas": filas})


def _json_grande(datos):
    """Una respuesta que puede pasar del limite de una Lambda (6 MB): por encima
    de 1 MB va comprimida, y el navegador la descomprime solo. El mes del
    interno partido por centro es la que lo necesita."""
    cuerpo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    cabeceras = {"content-type": "application/json; charset=utf-8", "cache-control": "no-store"}
    if len(cuerpo) <= 1_000_000:
        return {"statusCode": 200, "headers": cabeceras, "body": cuerpo.decode("utf-8")}
    import base64
    import gzip
    return {"statusCode": 200, "headers": dict(cabeceras, **{"content-encoding": "gzip"}),
            "isBase64Encoded": True,
            "body": base64.b64encode(gzip.compress(cuerpo)).decode("ascii")}


# ----------------------------------------------------------------------
# acceso
# ----------------------------------------------------------------------
def acceso(evento):
    d = cuerpo(evento)
    correo = str(d.get("correo", "")).strip().lower()
    clave = str(d.get("clave", ""))
    if not correo or not clave:
        raise ValueError("Falta el correo o la contrasena.")

    if _fallos(correo) >= INTENTOS_MAX:
        return r(429, {"error": f"Demasiados intentos. Prueba en {MINUTOS_BLOQUEO} minutos."})

    try:
        res = cog.admin_initiate_auth(
            UserPoolId=POOL, ClientId=CLIENTE,
            AuthFlow="ADMIN_USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": correo, "PASSWORD": clave},
        )
    except (cog.exceptions.NotAuthorizedException,
            cog.exceptions.UserNotFoundException):
        _suma_fallo(correo)
        # Mismo texto en los dos casos: no se dice si la cuenta existe.
        return r(401, {"error": "Correo o contrasena incorrectos."})

    if res.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
        # Primer acceso: la contrasena que puso el admin es de un solo uso.
        return r(200, {"cambio_requerido": True, "reto": res["Session"], "correo": correo})

    if not lee(f"USUARIO#{correo}"):
        return r(403, {"error": "La cuenta no esta configurada. Avisa al administrador."})

    _limpia_fallos(correo)
    return r(200, {"ok": True}, [cookie_sesion(abre_sesion(correo))])


def nueva_clave(evento):
    d = cuerpo(evento)
    correo = str(d.get("correo", "")).strip().lower()
    reto, clave = str(d.get("reto", "")), str(d.get("clave", ""))
    if not (correo and reto and clave):
        raise ValueError("Faltan datos para cambiar la contrasena.")
    try:
        cog.admin_respond_to_auth_challenge(
            UserPoolId=POOL, ClientId=CLIENTE,
            ChallengeName="NEW_PASSWORD_REQUIRED", Session=reto,
            ChallengeResponses={"USERNAME": correo, "NEW_PASSWORD": clave},
        )
    except cog.exceptions.InvalidPasswordException:
        raise ValueError("La contrasena no cumple la politica: 12 caracteres, "
                         "con mayuscula, minuscula y numero.") from None
    except Exception:
        raise ValueError("No se ha podido cambiar la contrasena. Vuelve a entrar.") from None
    # La misma comprobacion que en /api/acceso, y por lo mismo: una cuenta de
    # Cognito sin ficha no es un usuario de la plataforma. Sin esto, quien
    # llegara aqui sin ficha se gastaba su clave de un solo uso, recibia una
    # cookie buena y luego se encontraba un 401 en todas las pantallas, sin
    # entender por que. Ahora lo lee antes de gastar nada.
    if not lee(f"USUARIO#{correo}"):
        return r(403, {"error": "La cuenta no esta configurada. Avisa al administrador."})

    _limpia_fallos(correo)
    return r(200, {"ok": True}, [cookie_sesion(abre_sesion(correo))])


# ----------------------------------------------------------------------
# acciones hacia fuera
# ----------------------------------------------------------------------
def encola(evento, usuario, tipo):
    """WhatsApp y altas de incidencia se dejan en cola; las envia la de alarmas.

    Encolar en vez de enviar aqui tiene dos razones: si el proveedor tarda o
    falla, quien pulso el boton no se queda esperando y el mensaje no se pierde;
    y un alta en VenCloud es una ESCRITURA en el ERP, asi que queda registrado
    quien la pidio.
    """
    d = cuerpo(evento)
    ident = secrets.token_hex(8)
    fila = {"tipo": tipo, "pedido_por": usuario["correo"],
            "cuando": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "estado": "en_cola"}

    if tipo == "whatsapp":
        destino = str(d.get("empleado_id") or d.get("telefono") or "").strip()
        texto = str(d.get("texto", "")).strip()
        if not destino or not texto:
            raise ValueError("Falta el destinatario o el texto.")
        if len(texto) > 900:
            raise ValueError("El mensaje es demasiado largo.")
        fila.update(destino=destino[:60], texto=texto)
    else:
        matricula = str(d.get("matricula", "")).strip()
        descripcion = str(d.get("descripcion", "")).strip()
        if not matricula or not descripcion:
            raise ValueError("Falta la matricula o la descripcion.")
        fila.update(matricula=matricula[:20], descripcion=descripcion[:900],
                    prioridad=str(d.get("prioridad", "normal"))[:20])

    escribe(f"COLA#{ident}", fila)
    return r(202, {"ok": True, "id": ident, "estado": "en cola"})


def guarda_alarma(evento, usuario):
    d = cuerpo(evento)
    ident = str(d.get("id") or secrets.token_hex(6))[:40]
    if not d.get("nombre") or not d.get("fuente"):
        raise ValueError("Una alarma necesita nombre y fuente.")
    escribe(f"ALARMA#{ident}", {
        "nombre": str(d["nombre"])[:120],
        "fuente": str(d["fuente"])[:60],
        "campo": str(d.get("campo", ""))[:60],
        "comparacion": str(d.get("comparacion", ">"))[:4],
        "umbral": float(d.get("umbral", 0)),
        "canal": [x for x in (d.get("canal") or ["correo"]) if x in ("correo", "whatsapp")],
        "destinos": [str(x)[:120] for x in (d.get("destinos") or [])][:20],
        "silencio": d.get("silencio") or {"desde": 22, "hasta": 7},
        "perfil": str(d.get("perfil", "interno"))[:40],
        "activa": bool(d.get("activa", True)),
        "creada_por": usuario["correo"],
    })
    return r(200, {"ok": True, "id": ident})


# ----------------------------------------------------------------------
# administracion
# ----------------------------------------------------------------------
def _hay_panel(perfil_id):
    """Si el perfil tiene panel calculado, y de cuando es.

    Los agregados calculan cada noche el panel de cada perfil de esta consola
    que tenga ambito, sumado a lo que diga config/perfiles.json. Uno recien
    creado no lo tiene hasta esa noche, y uno sin ambito no lo tiene nunca: sus
    usuarios entrarian a una pantalla que dice que todavia no hay datos y nadie
    sabria por que.

    Esto lo mira de frente: una cabecera por perfil, que son unos pocos.
    """
    if not perfil_id:
        return {"existe": False}
    try:
        cab = s3.head_object(Bucket=BUCKET, Key=f"cabina/{perfil_id}/panel.json")
        return {"existe": True, "calculado": cab["LastModified"].isoformat()}
    except Exception:
        return {"existe": False}


def administra(evento, metodo, ruta, admin):
    resto = ruta[len("/api/admin/"):]
    d = cuerpo(evento)

    if resto == "usuarios" and metodo == "GET":
        return r(200, {"usuarios": lista("USUARIO#")})

    if resto == "usuarios" and metodo == "POST":
        correo = str(d.get("correo", "")).strip().lower()
        nombre = str(d.get("nombre", "")).strip()
        perfil_id = str(d.get("perfil_id", "")).strip()
        clave = str(d.get("clave", ""))
        if "@" not in correo or not nombre or not perfil_id:
            raise ValueError("Hacen falta nombre, correo y perfil.")
        if not lee(f"PERFIL#{perfil_id}"):
            raise ValueError("Ese perfil no existe.")
        nuevo = not lee(f"USUARIO#{correo}")
        if nuevo:
            if len(clave) < 12:
                raise ValueError("La contrasena inicial necesita 12 caracteres.")
            try:
                cog.admin_create_user(
                    UserPoolId=POOL, Username=correo,
                    UserAttributes=[{"Name": "email", "Value": correo},
                                    {"Name": "email_verified", "Value": "true"}],
                    TemporaryPassword=clave,
                    MessageAction="SUPPRESS",  # la clave la entrega el admin a mano
                )
            except cog.exceptions.UsernameExistsException:
                pass
        escribe(f"USUARIO#{correo}", {
            "nombre": nombre[:80], "perfil_id": perfil_id,
            "estado": "bloqueado" if d.get("estado") == "bloqueado" else "activo",
            "asistente": bool(d.get("asistente", True)),
            "limite_preguntas_dia": max(0, int(d.get("limite_preguntas_dia", 0))),
            "telefono": str(d.get("telefono", ""))[:30],
            "alta_por": admin["correo"],
        })
        return r(200, {"ok": True, "nuevo": nuevo})

    if resto.startswith("usuarios/") and resto.endswith("/clave") and metodo == "POST":
        correo = resto.split("/")[1].lower()
        clave = str(d.get("clave", ""))
        if len(clave) < 12:
            raise ValueError("La contrasena necesita 12 caracteres.")
        cog.admin_set_user_password(UserPoolId=POOL, Username=correo,
                                   Password=clave, Permanent=False)
        return r(200, {"ok": True, "_nota": "El usuario la cambiara al entrar."})

    if resto.startswith("usuarios/") and metodo == "DELETE":
        correo = resto.split("/", 1)[1].lower()
        if correo == admin["correo"]:
            raise ValueError("No puedes borrar tu propia cuenta.")
        borra(f"USUARIO#{correo}")
        try:
            cog.admin_delete_user(UserPoolId=POOL, Username=correo)
        except Exception:
            pass
        return r(200, {"ok": True})

    if resto == "perfiles" and metodo == "GET":
        return r(200, {
            "perfiles": [dict(p, panel=_hay_panel(p.get("_id", ""))) for p in lista("PERFIL#")],
            "catalogo_sesiones": {k: {"nombre": v[0], "minimo": v[1]} for k, v in A.SESIONES.items()},
            # Las partes del cuadro, para las casillas de «Qué ve en el cuadro».
            "catalogo_cuadro": {k: {"nombre": v[0], "flujos": list(v[1])}
                                for k, v in A.SECCIONES_CUADRO.items()},
            # El techo se envia para que el panel de admin pueda avisar de que
            # un permiso marcado no va a tener efecto en ese tipo de perfil.
            "techo": {k: sorted(v) for k, v in A.TECHO.items()},
            # Y el orden de los tipos, para que la consola sepa que una sesion
            # de «operaciones» no se le puede dar a un perfil de cliente sin
            # tener que llevar esa escalera escrita por su cuenta.
            "niveles": A.NIVEL,
            "implicitos": {k: sorted(v) for k, v in A.IMPLICITOS.items()},
        })

    if resto == "perfiles" and metodo == "POST":
        pid = str(d.get("perfil_id", "")).strip()[:40]
        tipo = str(d.get("tipo", "cliente"))
        if not pid or tipo not in A.TECHO:
            raise ValueError("Perfil o tipo no validos.")
        amb = d.get("ambito") or {}
        escribe(f"PERFIL#{pid}", {
            "nombre": str(d.get("nombre", pid))[:80],
            "tipo": tipo,
            "ambito": {k: [str(x)[:80] for x in (amb.get(k) or [])][:200]
                       for k in ("clientes", "centros", "delegaciones")},
            "sesiones": [s for s in (d.get("sesiones") or []) if s in A.SESIONES],
            "paneles": [str(x)[:40] for x in (d.get("paneles") or [])][:64],
            # Las partes del cuadro que se le QUITAN; vacio = las ve todas.
            "cuadro_ocultas": [s for s in (d.get("cuadro_ocultas") or [])
                               if s in A.SECCIONES_CUADRO],
            # Se guarda lo que marque el admin; el techo se aplica al servir.
            "permisos": {k: bool(v) for k, v in (d.get("permisos") or {}).items()},
            "reglas_negocio": d.get("reglas_negocio") or {},
            "creado_por": admin["correo"],
        })
        return r(200, {
            "ok": True, "id": pid,
            "permisos_efectivos": sorted(
                p for p, v in (d.get("permisos") or {}).items()
                if v and p in A.TECHO.get(tipo, set())),
            "ignorados": sorted(
                p for p, v in (d.get("permisos") or {}).items()
                if v and p not in A.TECHO.get(tipo, set())),
        })

    if resto.startswith("perfiles/") and metodo == "DELETE":
        pid = resto.split("/", 1)[1]
        if any(u.get("perfil_id") == pid for u in lista("USUARIO#")):
            raise ValueError("Hay usuarios con ese perfil: cambialos antes.")
        borra(f"PERFIL#{pid}")
        return r(200, {"ok": True})

    if resto == "config" and metodo == "GET":
        return r(200, config())

    if resto == "config" and metodo == "PUT":
        c = config()
        if "asistente_global" in d:
            c["asistente_global"] = bool(d["asistente_global"])
        if "limite_preguntas_dia" in d:
            c["limite_preguntas_dia"] = max(0, int(d["limite_preguntas_dia"]))
        if "umbral_rentabilidad_mes" in d:
            c["umbral_rentabilidad_mes"] = float(d["umbral_rentabilidad_mes"])
        escribe("CONFIG", c, "GLOBAL")
        return r(200, c)

    if resto == "telefonos" and metodo == "GET":
        return r(200, {"telefonos": lista("TELEFONO#")})

    if resto == "telefonos" and metodo == "POST":
        eid = str(d.get("empleado_id", "")).strip()[:20]
        tel = str(d.get("telefono", "")).strip()
        if not eid or not tel.startswith("+"):
            raise ValueError("Hace falta el id del empleado y un telefono con prefijo (+34...).")
        escribe(f"TELEFONO#{eid}", {
            "nombre": str(d.get("nombre", ""))[:80],
            "telefono": tel[:20],
            "oficio": str(d.get("oficio", "reponedor"))[:20],
            "alta_por": admin["correo"],
        })
        return r(200, {"ok": True})

    if resto.startswith("telefonos/") and metodo == "DELETE":
        borra("TELEFONO#" + resto.split("/", 1)[1])
        return r(200, {"ok": True})

    if resto == "cola" and metodo == "GET":
        return r(200, {"cola": lista("COLA#")[-100:]})

    return r(404, {"error": "No existe esa ruta de administracion."})
