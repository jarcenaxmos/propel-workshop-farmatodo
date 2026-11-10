"""Resume la ultima traza del agente en Cloud Trace: modelo, herramientas y tokens.

Uso:
  python sesion-5-produccion/ver_trazas.py            # ultimos 30 minutos
  python sesion-5-produccion/ver_trazas.py 120        # ultimos 120 minutos
"""

import datetime as dt
import os
import pathlib
import sys

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROYECTO = os.environ["GOOGLE_CLOUD_PROJECT"]
MINUTOS = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def hora(texto: str) -> dt.datetime:
  # Cloud Trace devuelve nanosegundos; Python acepta hasta microsegundos.
  base, _, fraccion = texto.rstrip("Z").partition(".")
  return dt.datetime.fromisoformat(f"{base}.{(fraccion or '0')[:6]:0<6}+00:00")


def main() -> None:
  cred, _ = google.auth.default(
      scopes=["https://www.googleapis.com/auth/cloud-platform"])
  s = AuthorizedSession(cred)
  desde = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=MINUTOS)
  r = s.get(
      f"https://cloudtrace.googleapis.com/v1/projects/{PROYECTO}/traces",
      params={"view": "COMPLETE", "pageSize": 50,
              "startTime": desde.strftime("%Y-%m-%dT%H:%M:%SZ")})
  r.raise_for_status()
  trazas = [t for t in r.json().get("traces", [])
            if any(sp["name"].startswith("invoke_agent") for sp in t["spans"])]
  if not trazas:
    sys.exit(f"No hay trazas del agente en los ultimos {MINUTOS} minutos."
             " Consulta el agente desplegado y espera 1 minuto.")
  traza = max(trazas, key=lambda t: max(sp["startTime"] for sp in t["spans"]))
  spans = sorted(traza["spans"], key=lambda sp: sp["startTime"])
  inicio = hora(spans[0]["startTime"])
  print(f"Traza {traza['traceId']}  ({len(spans)} spans,"
        f" {len(trazas)} trazas del agente en la ventana)")
  print(f"{'inicio':>8} {'duracion':>9}  span")
  tokens_in = tokens_out = 0
  for sp in spans:
    etiquetas = sp.get("labels", {})
    operacion = etiquetas.get("gen_ai.operation.name")
    # Se muestran los spans del agente, del modelo y de las herramientas.
    if not operacion or not sp["name"].startswith(
        ("invoke_agent", "generate_content", "execute_tool", "tools/call")):
      continue
    duracion = (hora(sp["endTime"]) - hora(sp["startTime"])).total_seconds()
    extra = ""
    if operacion == "generate_content":
      entrada = int(etiquetas.get("gen_ai.usage.input_tokens", 0))
      salida = int(etiquetas.get("gen_ai.usage.output_tokens", 0))
      tokens_in += entrada
      tokens_out += salida
      extra = f"  [{entrada} tokens de entrada, {salida} de salida]"
    if sp["name"].startswith("tools/call"):
      extra = "  [span del servidor MCP de Google]"
    print(f"{(hora(sp['startTime']) - inicio).total_seconds():>7.1f}s"
          f" {duracion:>8.2f}s  {sp['name']}{extra}")
  print(f"Total de tokens: {tokens_in} de entrada, {tokens_out} de salida")
  print("Explorador: https://console.cloud.google.com/traces/explorer"
        f"?project={PROYECTO}")


if __name__ == "__main__":
  main()
