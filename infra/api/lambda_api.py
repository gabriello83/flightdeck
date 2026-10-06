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
            "sesiones": A.sesiones_de(perfil.get("tipo", "cliente"), perfil.get("sesiones", [])),
            "catalogo_sesiones": {k: v[0] for k, v in A.SESIONES.items()},
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

    # El cuadro de mando: el indice, o un trozo de venta. Igual que el panel, la
    # carpeta sale del perfil de la sesion; lo unico que se pide es QUE trozo, y
    # se valida contra la lista del propio indice antes de tocar S3.
    if ruta == "/api/cuadro" and metodo == "GET":
        if "cuadro" not in A.sesiones_de(perfil.get("tipo", "cliente"), perfil.get("sesiones", [])):
            raise PermissionError("Este perfil no tiene el cuadro de mando.")
        return cuadro(perfil.get("perfil_id", ""),
                      (evento.get("queryStringParameters") or {}).get("trozo"))

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
def cuadro(perfil_id, trozo=None):
    """Devuelve el fichero TAL CUAL esta en S3, sin abrirlo.

    Un trozo de venta son un par de MB: leerlo como JSON y volver a escribirlo
    solo gastaria memoria y tiempo de una Lambda de 512 MB para devolver lo mismo.
    """
    base = f"cabina/{perfil_id}/cuadro/"
    try:
        indice = s3.get_object(Bucket=BUCKET, Key=base + "indice.json")["Body"].read()
    except Exception:
        return r(503, {"error": "El cuadro de mando todavia no se ha calculado.",
                       "_nota": "Lo escriben los agregados (4:45) para cada perfil de "
                                "cliente con ambito."})
    cuerpo = indice
    if trozo is not None:
        # Solo un trozo que el indice cite: asi no hay forma de componer otra
        # clave, ni de este perfil ni de ningun otro.
        if trozo not in json.loads(indice).get("trozos", []):
            raise ValueError("Ese trozo no existe.")
        cuerpo = s3.get_object(Bucket=BUCKET, Key=f"{base}ventas-{trozo}.json")["Body"].read()
    return {"statusCode": 200,
            "headers": {"content-type": "application/json; charset=utf-8",
                        "cache-control": "no-store"},
            "body": cuerpo.decode("utf-8")}


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
