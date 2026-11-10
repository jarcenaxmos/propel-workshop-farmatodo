"""Lista lo que Agent Registry conoce de tu proyecto: agentes y servidores MCP.

Usa la API REST para no depender de la version de gcloud instalada.

Uso:  python sesion-2-agent-runtime/ver_registro.py
"""

import os
import pathlib

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROYECTO = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION = os.environ.get("REGION", "us-central1")
API = "https://agentregistry.googleapis.com/v1"

cred, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"])
s = AuthorizedSession(cred)
s.headers["x-goog-user-project"] = PROYECTO

# Los agentes viven en el registro de su region; los servidores MCP de Google
# Cloud aparecen en el registro "global".
for titulo, ubicacion, recurso, clave in (
    (f"Agentes en {REGION}", REGION, "agents", "agents"),
    ("Servidores MCP en global", "global", "mcpServers", "mcpServers")):
  r = s.get(f"{API}/projects/{PROYECTO}/locations/{ubicacion}/{recurso}",
            params={"pageSize": 100})
  print(f"\n== {titulo}")
  if r.status_code != 200:
    print(f"  HTTP {r.status_code}: {r.text[:300]}")
    continue
  for item in r.json().get(clave, []):
    interfaces = item.get("protocols") or item.get("interfaces") or []
    primera = interfaces[0] if interfaces else {}
    url = (primera.get("interfaces") or [primera])[0].get("url", "")
    print(f"  {item.get('displayName', ''):38} {primera.get('type', 'MCP'):10} {url}")
