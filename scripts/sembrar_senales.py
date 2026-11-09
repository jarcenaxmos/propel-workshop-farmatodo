"""Siembra senales de ejemplo en Cloud Logging y Cloud Monitoring de TU proyecto.

Simula un incidente en la cadena ficticia Farmalab: el servicio pagos-gateway
empieza a fallar con UPSTREAM_TIMEOUT poco despues de un despliegue.

Crea:
  - Entradas en el log `farmalab-app` (ultimos 60 minutos).
  - Metricas custom.googleapis.com/farmalab/error_rate y latency_p95_ms.
  - Una politica de alertas "Farmalab: tasa de error alta en pagos-gateway".
  - El archivo datos/.incidente.json con la hora del incidente (lo lee el
    servidor MCP de contexto).

Uso:
  python scripts/sembrar_senales.py                # siembra todo
  python scripts/sembrar_senales.py --en-vivo 5    # ademas emite puntos 5 min
                                                   # para que la alerta dispare
  python scripts/sembrar_senales.py --forzar       # incidente nuevo desde cero
  python scripts/sembrar_senales.py --borrar       # elimina lo sembrado

Si lo ejecutas de nuevo dentro de la misma hora no duplica nada: completa el
tramo que falta y el incidente sigue abierto.

Solo usa google-auth y requests (vienen con google-adk).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import random
import sys
import time

import google.auth
from google.auth.transport.requests import AuthorizedSession

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARCHIVO_INCIDENTE = RAIZ / "datos" / ".incidente.json"
LOG_ID = "farmalab-app"
PREFIJO_METRICA = "custom.googleapis.com/farmalab"
NOMBRE_POLITICA = "Farmalab: tasa de error alta en pagos-gateway"
VENTANA_MIN = 60          # minutos de historia que se siembran
INICIO_INCIDENTE_MIN = 22  # el incidente empieza hace 22 minutos
SERVICIOS = {
    # servicio: (version, error_rate normal, p95 normal en ms)
    "pagos-gateway": ("3.8.2", 0.006, 420.0),
    "pedidos-api": ("5.14.0", 0.004, 310.0),
    "inventario-sync": ("2.2.7", 0.002, 150.0),
}
TIENDAS = ["BOG-014", "BOG-027", "MED-003", "CAL-008", "BAQ-002", "BGA-005"]


def sesion() -> tuple[AuthorizedSession, str]:
  credenciales, proyecto_adc = google.auth.default(
      scopes=["https://www.googleapis.com/auth/cloud-platform"])
  proyecto = (os.environ.get("PROJECT_ID")
              or os.environ.get("GOOGLE_CLOUD_PROJECT") or proyecto_adc)
  if not proyecto:
    sys.exit("No hay proyecto. Ejecuta: export PROJECT_ID=tu-proyecto")
  s = AuthorizedSession(credenciales)
  s.headers["x-goog-user-project"] = proyecto
  return s, proyecto


def rfc3339(t: dt.datetime) -> str:
  return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def revisar(r, que: str, tolerar: tuple[int, ...] = ()) -> bool:
  if r.status_code < 300 or r.status_code in tolerar:
    return r.status_code < 300
  sys.exit(f"[!] Fallo {que}: HTTP {r.status_code} {r.text[:400]}")


# ---------------------------------------------------------------- logs

def minutos(desde: dt.datetime, hasta: dt.datetime) -> list[dt.datetime]:
  """Un instante por minuto en el intervalo (desde, hasta]."""
  n = int((hasta - desde).total_seconds() // 60)
  return [hasta - dt.timedelta(minutes=i) for i in range(n - 1, -1, -1)]


def entradas_de_log(proyecto: str, desde: dt.datetime, hasta: dt.datetime,
                    inicio: dt.datetime) -> list[dict]:
  rnd = random.Random(int(hasta.timestamp()))
  despliegue = inicio - dt.timedelta(minutes=3)
  entradas = []

  def entrada(cuando: dt.datetime, servicio: str, severidad: str, carga: dict):
    version = SERVICIOS[servicio][0]
    # Antes del despliegue, pagos-gateway corria la version anterior.
    if servicio == "pagos-gateway" and cuando < despliegue:
      version = "3.8.1"
    entradas.append({
        "logName": f"projects/{proyecto}/logs/{LOG_ID}",
        "resource": {"type": "global", "labels": {"project_id": proyecto}},
        "timestamp": rfc3339(cuando),
        "severity": severidad,
        "labels": {"service": servicio, "version": version, "env": "prod",
                   "workshop": "farmatodo"},
        "jsonPayload": {"service": servicio, "version": version, **carga},
    })

  for i, t in enumerate(minutos(desde, hasta)):
    def antes() -> dt.datetime:  # un instante al azar dentro de ese minuto
      return t - dt.timedelta(seconds=rnd.uniform(0, 59))
    for servicio in SERVICIOS:
      entrada(antes(), servicio, "INFO",
              {"message": "request ok", "status": 200,
               "tienda_id": rnd.choice(TIENDAS),
               "latency_ms": rnd.randint(80, 400)})
    if t > inicio:
      for _ in range(rnd.randint(3, 5)):
        entrada(antes(), "pagos-gateway", "ERROR", {
            "message": ("Timeout llamando al adquirente: no hubo respuesta en"
                        " 2000 ms (POST /v2/autorizaciones)"),
            "status": 504, "error_code": "UPSTREAM_TIMEOUT",
            "upstream": "adquirente-co", "timeout_ms": 2000,
            "tienda_id": rnd.choice(TIENDAS),
            "latency_ms": rnd.randint(2001, 2080)})
      for _ in range(rnd.randint(1, 2)):
        entrada(antes(), "pedidos-api", "WARNING", {
            "message": ("Pedido queda en PAGO_PENDIENTE: pagos-gateway"
                        " respondio 504"),
            "status": 202, "error_code": "PAGO_PENDIENTE",
            "dependencia": "pagos-gateway",
            "tienda_id": rnd.choice(TIENDAS)})
    elif i % 9 == 0:
      entrada(antes(), "pagos-gateway", "ERROR", {
          "message": "Tarjeta rechazada por el emisor", "status": 402,
          "error_code": "CARD_DECLINED", "tienda_id": rnd.choice(TIENDAS)})
    if i % 13 == 0:
      entrada(antes(), "inventario-sync", "WARNING", {
          "message": "Stock desactualizado en una tienda, se reintenta",
          "error_code": "STOCK_DESACTUALIZADO",
          "tienda_id": rnd.choice(TIENDAS)})
  # El despliegue que dispara el incidente tambien deja huella en los logs.
  if desde < despliegue <= hasta:
    entrada(despliegue, "pagos-gateway", "NOTICE", {
        "message": "Despliegue completado: pagos-gateway 3.8.2 (antes 3.8.1)",
        "evento": "DEPLOY", "config": {"adquirente_timeout_ms": 2000}})
  return entradas


def sembrar_logs(s: AuthorizedSession, proyecto: str, desde, hasta, inicio) -> int:
  entradas = entradas_de_log(proyecto, desde, hasta, inicio)
  for i in range(0, len(entradas), 200):
    r = s.post("https://logging.googleapis.com/v2/entries:write",
               json={"entries": entradas[i:i + 200]})
    revisar(r, "al escribir logs")
  return len(entradas)


# ------------------------------------------------------------- metricas

def valores(servicio: str, cuando: dt.datetime, inicio: dt.datetime,
            rnd: random.Random):
  _, err, p95 = SERVICIOS[servicio]
  transcurrido = (cuando - inicio).total_seconds() / 60
  if transcurrido >= 0 and servicio == "pagos-gateway":
    avance = min(1.0, transcurrido / 4)  # sube en 4 minutos y se queda arriba
    err = 0.02 + 0.16 * avance
    p95 = 900 + 3900 * avance
  if transcurrido >= 0 and servicio == "pedidos-api":
    err, p95 = 0.012, 520.0
  return (round(err * rnd.uniform(0.85, 1.15), 4),
          round(p95 * rnd.uniform(0.9, 1.1), 1))


def series(proyecto: str, cuando: dt.datetime, inicio: dt.datetime,
           rnd: random.Random) -> list[dict]:
  resultado = []
  for servicio in SERVICIOS:
    err, p95 = valores(servicio, cuando, inicio, rnd)
    for nombre, valor in (("error_rate", err), ("latency_p95_ms", p95)):
      resultado.append({
          "metric": {"type": f"{PREFIJO_METRICA}/{nombre}",
                     "labels": {"service": servicio}},
          "resource": {"type": "global", "labels": {"project_id": proyecto}},
          "metricKind": "GAUGE", "valueType": "DOUBLE",
          "points": [{"interval": {"endTime": rfc3339(cuando)},
                      "value": {"doubleValue": valor}}],
      })
  return resultado


def escribir_punto(s, proyecto, cuando, inicio, rnd) -> bool:
  r = s.post(
      f"https://monitoring.googleapis.com/v3/projects/{proyecto}/timeSeries",
      json={"timeSeries": series(proyecto, cuando, inicio, rnd)})
  # 400 = ya habia un punto mas nuevo para esa serie.
  return revisar(r, "al escribir metricas", tolerar=(400,))


def crear_descriptores(s, proyecto: str) -> None:
  # Se crean de forma explicita para que la politica de alertas pueda
  # referenciar la etiqueta `service` sin esperar al descubrimiento automatico.
  for nombre, unidad, texto in (
      ("error_rate", "1", "Fraccion de requests con error (0 a 1), por servicio."),
      ("latency_p95_ms", "ms", "Latencia p95 en milisegundos, por servicio.")):
    r = s.post(
        f"https://monitoring.googleapis.com/v3/projects/{proyecto}/metricDescriptors",
        json={"type": f"{PREFIJO_METRICA}/{nombre}", "metricKind": "GAUGE",
              "valueType": "DOUBLE", "unit": unidad,
              "displayName": f"Farmalab {nombre}", "description": texto,
              "labels": [{"key": "service", "valueType": "STRING",
                          "description": "Nombre del servicio"}]})
    revisar(r, "al crear el descriptor de metrica")


def sembrar_metricas(s, proyecto: str, desde, hasta, inicio) -> int:
  crear_descriptores(s, proyecto)
  rnd = random.Random(7)
  return sum(escribir_punto(s, proyecto, t, inicio, rnd)
             for t in minutos(desde, hasta))


def crear_politica(s, proyecto: str) -> str:
  base = f"https://monitoring.googleapis.com/v3/projects/{proyecto}/alertPolicies"
  r = s.get(base, params={"filter": f'display_name="{NOMBRE_POLITICA}"'})
  revisar(r, "al listar politicas de alerta")
  existentes = r.json().get("alertPolicies", [])
  if existentes:
    return existentes[0]["name"] + " (ya existia)"
  cuerpo = {
      "displayName": NOMBRE_POLITICA,
      "combiner": "OR",
      "userLabels": {"workshop": "farmatodo"},
      "severity": "CRITICAL",
      "documentation": {
          "mimeType": "text/markdown",
          "content": ("La tasa de error de **pagos-gateway** supero 5%."
                      " Runbook: revisar el error_code dominante en el log"
                      " `farmalab-app`, comparar con el ultimo despliegue y"
                      " abrir ticket de severidad alta al equipo Pagos."),
      },
      "conditions": [{
          "displayName": "error_rate de pagos-gateway mayor a 5%",
          "conditionThreshold": {
              "filter": (f'metric.type="{PREFIJO_METRICA}/error_rate" AND '
                         'resource.type="global" AND '
                         'metric.labels.service="pagos-gateway"'),
              "comparison": "COMPARISON_GT",
              "thresholdValue": 0.05,
              "duration": "60s",
              "aggregations": [{"alignmentPeriod": "60s",
                                "perSeriesAligner": "ALIGN_MEAN"}],
          },
      }],
  }
  # Una metrica nueva puede tardar unos minutos en poder usarse en una politica.
  for _ in range(9):
    r = s.post(base, json=cuerpo)
    if r.status_code < 300:
      return r.json()["name"]
    if r.status_code not in (404, 500, 503):
      break
    print("  la metrica aun no esta disponible para alertas, reintento en 20 s...")
    time.sleep(20)
  print(f"[!] No se pudo crear la politica (HTTP {r.status_code}). El resto del"
        " lab funciona igual. Reintenta en unos minutos con este mismo script.")
  return "PENDIENTE"


def emitir_en_vivo(s, proyecto: str, cuantos_min: int, inicio) -> None:
  rnd = random.Random()
  print(f"Emitiendo puntos en vivo durante {cuantos_min} min (Ctrl+C para parar)...")
  fin = time.time() + cuantos_min * 60
  while time.time() < fin:
    escribir_punto(s, proyecto, dt.datetime.now(dt.timezone.utc), inicio, rnd)
    print("  punto escrito", dt.datetime.now().strftime("%H:%M:%S"))
    time.sleep(30)


# --------------------------------------------------------------- borrar

def borrar(s, proyecto: str) -> None:
  base = f"https://monitoring.googleapis.com/v3/projects/{proyecto}"
  r = s.get(f"{base}/alertPolicies",
            params={"filter": f'display_name="{NOMBRE_POLITICA}"'})
  for politica in r.json().get("alertPolicies", []) if r.ok else []:
    print("borrando", politica["name"], s.delete(
        f"https://monitoring.googleapis.com/v3/{politica['name']}").status_code)
  for nombre in ("error_rate", "latency_p95_ms"):
    r = s.delete(f"{base}/metricDescriptors/{PREFIJO_METRICA}/{nombre}")
    print("borrando metrica", nombre, r.status_code)
  r = s.delete(
      f"https://logging.googleapis.com/v2/projects/{proyecto}/logs/{LOG_ID}")
  print("borrando log", LOG_ID, r.status_code)
  ARCHIVO_INCIDENTE.unlink(missing_ok=True)


def main() -> None:
  p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
  p.add_argument("--en-vivo", type=int, default=0, metavar="MIN",
                 help="sigue emitiendo puntos MIN minutos para disparar la alerta")
  p.add_argument("--borrar", action="store_true", help="elimina lo sembrado")
  p.add_argument("--forzar", action="store_true",
                 help="siembra un incidente nuevo aunque ya haya uno reciente")
  args = p.parse_args()
  s, proyecto = sesion()
  if args.borrar:
    borrar(s, proyecto)
    return
  ahora = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
  desde = ahora - dt.timedelta(minutes=VENTANA_MIN)
  inicio = ahora - dt.timedelta(minutes=INICIO_INCIDENTE_MIN)
  # Si ya se sembro hace menos de una hora, no se duplica: solo se completa el
  # tramo que falta y el incidente sigue abierto desde su inicio original.
  if ARCHIVO_INCIDENTE.exists() and not args.forzar:
    previo = json.loads(ARCHIVO_INCIDENTE.read_text())
    if previo.get("proyecto") == proyecto:
      sembrado = dt.datetime.fromisoformat(previo["sembrado"].replace("Z", "+00:00"))
      if ahora - sembrado < dt.timedelta(minutes=VENTANA_MIN):
        desde = sembrado
        inicio = dt.datetime.fromisoformat(
            previo["inicio_incidente"].replace("Z", "+00:00"))
        print("Ya habia senales recientes: se completa desde", rfc3339(desde))
  print(f"Proyecto: {proyecto}")
  print("logs escritos:", sembrar_logs(s, proyecto, desde, ahora, inicio))
  print("puntos de metricas (minutos) escritos:",
        sembrar_metricas(s, proyecto, desde, ahora, inicio))
  print("politica de alertas:", crear_politica(s, proyecto))
  ARCHIVO_INCIDENTE.write_text(json.dumps(
      {"proyecto": proyecto, "inicio_incidente": rfc3339(inicio),
       "sembrado": rfc3339(ahora)}))
  print("inicio del incidente simulado:", rfc3339(inicio))
  if args.en_vivo:
    emitir_en_vivo(s, proyecto, args.en_vivo, inicio)


if __name__ == "__main__":
  main()
