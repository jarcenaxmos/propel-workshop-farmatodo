"""Lista lo que Agent Registry conoce de tu proyecto: agentes, servidores MCP y skills.

Usa la API REST para no depender de la version de gcloud instalada.

Uso:
  python sesion-2-agent-runtime/ver_registro.py            # tus agentes, MCP y skills
  python sesion-2-agent-runtime/ver_registro.py --google   # ademas, las skills oficiales de Google
  python sesion-2-agent-runtime/ver_registro.py --google logging   # solo las que contienen "logging"
"""

import collections
import os
import pathlib
import sys

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
mias, todas, total, token = [], [], 0, None
while True:
  r = s.get(f"{API}/projects/{PROYECTO}/locations/global/skills",
            params={"pageSize": 100, **({"pageToken": token} if token else {})})
  if r.status_code != 200:
    print(f"  HTTP {r.status_code}: {r.text[:300]}")
    break
  datos = r.json()
  total += len(datos.get("skills", []))
  todas += datos.get("skills", [])
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

# --google: las skills oficiales, agrupadas por publisher. La consola (pestana
# Skills) solo muestra las privadas; por API se ve el catalogo completo.
if "--google" in sys.argv:
  filtro = [a.lower() for a in sys.argv[1:] if not a.startswith("--")]
  grupos = collections.defaultdict(list)
  for sk in todas:
    if sk["name"].split("/")[-1].startswith("private-"):
      continue
    nombre = sk.get("displayName") or sk["name"].split("/")[-1]
    texto = f"{nombre} {sk.get('description', '')}".lower()
    if filtro and not all(f in texto for f in filtro):
      continue
    grupos[sk.get("publisher", "").split("/")[-1] or "?"].append(sk)
  print("\n== Skills oficiales en el catalogo global"
        + (f" (filtro: {' '.join(filtro)})" if filtro else ""))
  for publisher, lista in sorted(grupos.items()):
    print(f"\n  Publisher {publisher}: {len(lista)}")
    for sk in sorted(lista, key=lambda x: x.get("displayName", "")):
      nombre = sk.get("displayName") or sk["name"].split("/")[-1]
      print(f"    {nombre:48} {sk.get('description', '')[:70]}")
  if not grupos:
    print("  (ninguna coincide)")
