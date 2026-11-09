"""Verifica que el entorno esta listo para los labs. No crea ni modifica nada.

Uso:  python scripts/verificar.py
"""

import os
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROYECTO = os.environ.get("GOOGLE_CLOUD_PROJECT")
MODELO = os.environ.get("MODEL", "gemini-3.8-flash")
fallas = 0


def paso(nombre: str, ok: bool, ayuda: str = "") -> None:
  global fallas
  print(f"  [{'ok' if ok else 'FALLA'}] {nombre}")
  if not ok:
    fallas += 1
    if ayuda:
      print(f"         -> {ayuda}")


def llamar_mcp(s: AuthorizedSession, host: str, tool: str, args: dict):
  r = s.post(f"https://{host}/mcp", timeout=60,
             headers={"Accept": "application/json, text/event-stream"},
             json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                   "params": {"name": tool, "arguments": args}})
  cuerpo = r.json() if r.headers.get("content-type", "").startswith(
      "application/json") else {}
  resultado = cuerpo.get("result", {})
  ok = r.status_code == 200 and "result" in cuerpo and not resultado.get("isError")
  return ok, (r.text[:200] if not ok else resultado.get("structuredContent", {}))


def main() -> None:
  print("Verificacion del entorno")
  paso("Python 3.11 o superior", sys.version_info >= (3, 11))
  paso(".env con GOOGLE_CLOUD_PROJECT", bool(PROYECTO), "ejecuta ./setup.sh")
  if not PROYECTO:
    sys.exit(1)
  try:
    cred, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"])
    s = AuthorizedSession(cred)
    s.headers["x-goog-user-project"] = PROYECTO
    paso("Credenciales por defecto (ADC)", True)
  except Exception as e:  # pylint: disable=broad-except
    paso("Credenciales por defecto (ADC)", False,
         f"ejecuta: gcloud auth application-default login   ({e})")
    sys.exit(1)

  r = s.post(
      f"https://aiplatform.googleapis.com/v1/projects/{PROYECTO}/locations/"
      f"global/publishers/google/models/{MODELO}:generateContent", timeout=60,
      json={"contents": [{"role": "user", "parts": [{"text": "Responde solo: ok"}]}]})
  paso(f"Gemini responde ({MODELO} en global)", r.status_code == 200,
       f"HTTP {r.status_code}: {r.text[:200]}")

  ok, detalle = llamar_mcp(s, "logging.googleapis.com", "list_log_entries", {
      "resourceNames": [f"projects/{PROYECTO}"],
      "filter": f'logName="projects/{PROYECTO}/logs/farmalab-app" AND severity>=ERROR',
      "orderBy": "timestamp desc", "pageSize": 50})
  paso("MCP de Cloud Logging responde", ok,
       f"revisa roles/mcp.toolUser y roles/logging.viewer. {detalle}")
  if ok:
    paso("Hay logs de ejemplo (farmalab-app)", bool(detalle.get("entries")),
         "aun no aparecen: espera 1 minuto o ejecuta python scripts/sembrar_senales.py")

  ok, detalle = llamar_mcp(s, "monitoring.googleapis.com", "list_alert_policies",
                           {"name": f"projects/{PROYECTO}"})
  paso("MCP de Cloud Monitoring responde", ok,
       f"revisa roles/mcp.toolUser y roles/monitoring.viewer. {detalle}")
  if ok:
    nombres = [p.get("displayName", "") for p in detalle.get("alertPolicies", [])]
    paso("Existe la politica de alertas de Farmalab",
         any("Farmalab" in n for n in nombres),
         "vuelve a ejecutar python scripts/sembrar_senales.py en unos minutos"
         " (el lab funciona sin ella)")

  print("Todo listo." if not fallas else f"{fallas} verificacion(es) fallaron.")
  sys.exit(1 if fallas else 0)


if __name__ == "__main__":
  main()
