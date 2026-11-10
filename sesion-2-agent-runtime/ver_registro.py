"""Lista lo que Agent Registry conoce de tu proyecto: agentes, servidores MCP y skills.

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

# Skills: viven en "global". El catalogo trae cientos de skills de Google; aqui
# se muestran solo las TUYAS (las que publicaste: su id empieza con "private-")
# con sus revisiones y cual es la vigente.
print("\n== Skills publicadas en tu proyecto (global)")
mias, total, token = [], 0, None
while True:
  r = s.get(f"{API}/projects/{PROYECTO}/locations/global/skills",
            params={"pageSize": 100, **({"pageToken": token} if token else {})})
  if r.status_code != 200:
    print(f"  HTTP {r.status_code}: {r.text[:300]}")
    break
  datos = r.json()
  total += len(datos.get("skills", []))
  mias += [x for x in datos.get("skills", []) if x["name"].split("/")[-1].startswith("private-")]
  token = datos.get("nextPageToken")
  if not token:
    break
for sk in mias:
  print(f"  {sk['name'].split('/')[-1]}  ({sk.get('state')})  {sk.get('description', '')[:60]}")
  revs = s.get(f"{API}/{sk['name']}/revisions").json().get("skillRevisions", [])
  for rv in sorted(revs, key=lambda x: x.get("createTime", "")):
    version = rv.get("frontmatter", {}).get("metadata", {}).get("version", "?")
    vigente = "  <- vigente" if rv["name"] == sk.get("defaultRevision") else ""
    print(f"    version {version:8} {rv['name'].split('/')[-1]}  {rv.get('state')}{vigente}")
if not mias:
  print("  (ninguna todavia: sesion-2-agent-runtime/skills/publicar_skill.py)")
print(f"  El catalogo global tiene {total} skills en total, la mayoria de Google.")
