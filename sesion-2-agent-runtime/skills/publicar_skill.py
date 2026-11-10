"""Publica una skill en Agent Registry, versionada, o la borra.

Uso (desde la raiz del repo, con el entorno activado):
  python sesion-2-agent-runtime/skills/publicar_skill.py                # publica la version de SKILL.md
  python sesion-2-agent-runtime/skills/publicar_skill.py --default 1.0.0   # vuelve a una version anterior
  python sesion-2-agent-runtime/skills/publicar_skill.py --borrar       # borra la skill y sus revisiones

Como funciona (API REST v1 de Agent Registry, ubicacion "global"):
  - Skill: el contenedor logico (nombre estable, p. ej. redactar-ticket-incidente).
  - SkillRevision: una version inmutable del paquete (un zip con SKILL.md).
  - defaultRevision: la revision que se sirve por defecto. Los agentes que la
    consumen reciben la nueva version sin cambiar su codigo ni redesplegarse.
La version sale de `metadata.version` en SKILL.md. Se puede ejecutar varias
veces: no duplica nada.
"""

import argparse
import base64
import io
import os
import pathlib
import re
import sys
import time
import zipfile

import dotenv

RAIZ = pathlib.Path(__file__).resolve().parents[2]
dotenv.load_dotenv(RAIZ / ".env")

import google.auth
from google.auth.transport.requests import AuthorizedSession

PROYECTO = os.environ.get("PROJECT_ID") or os.environ["GOOGLE_CLOUD_PROJECT"]
# Las skills viven en "global": en regiones como us-east1 el servicio de
# skills responde 503 (verificado el 10-nov-2026).
UBICACION = os.environ.get("SKILLS_LOCATION", "global")
API = "https://agentregistry.googleapis.com/v1"
PADRE = f"projects/{PROYECTO}/locations/{UBICACION}"

parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
parser.add_argument("--dir", default=str(pathlib.Path(__file__).parent / "redactar-ticket-incidente"),
                    help="carpeta de la skill (con SKILL.md)")
parser.add_argument("--default", metavar="VERSION",
                    help="no publica nada: fija esta version (ya publicada) como la vigente")
parser.add_argument("--borrar", action="store_true", help="borra la skill y todas sus revisiones")
args = parser.parse_args()

carpeta = pathlib.Path(args.dir).resolve()
skill_md = (carpeta / "SKILL.md").read_text(encoding="utf-8")
frontmatter = skill_md.split("---")[1]
nombre = re.search(r"^name:\s*(\S+)", frontmatter, re.M).group(1)
descripcion = re.search(r"^description:\s*(.+)$", frontmatter, re.M).group(1).strip()
version = re.search(r'^\s+version:\s*"?([\w.\-]+)"?', frontmatter, re.M).group(1)


def id_revision(v: str) -> str:
  return "v" + v.replace(".", "-")


cred, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
s = AuthorizedSession(cred)
s.headers["x-goog-user-project"] = PROYECTO
SKILL = f"{PADRE}/skills/{nombre}"


def llamar(metodo, ruta, **kw):
  r = s.request(metodo, f"{API}/{ruta}", **kw)
  if r.status_code >= 400 and r.status_code != 404:
    sys.exit(f"[!] {metodo} {ruta}: HTTP {r.status_code}\n{r.text[:600]}")
  return r


def esperar(r):
  """Si la respuesta es una operacion de larga duracion, espera a que termine."""
  datos = r.json()
  while datos.get("name", "").find("/operations/") > 0 and not datos.get("done"):
    time.sleep(2)
    datos = llamar("GET", datos["name"]).json()
  if "error" in datos:
    sys.exit(f"[!] La operacion fallo: {datos['error']}")
  return datos.get("response", datos)


def zip_de_la_skill() -> str:
  """Empaqueta la carpeta de la skill (SKILL.md en la raiz del zip), en base64."""
  buf = io.BytesIO()
  with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for ruta in sorted(carpeta.rglob("*")):
      if ruta.is_file():
        z.write(ruta, ruta.relative_to(carpeta).as_posix())
  return base64.b64encode(buf.getvalue()).decode()


if args.borrar:
  r = llamar("DELETE", SKILL, params={"force": "true"})
  print("skill borrada" if r.status_code < 300 else "no habia skill")
  sys.exit(0)

existe = llamar("GET", SKILL).status_code == 200

if args.default:
  rev = f"{SKILL}/revisions/{id_revision(args.default)}"
  if llamar("GET", rev).status_code != 200:
    sys.exit(f"[!] No existe la version {args.default}. Publicala primero.")
else:
  archivo = {"archiveUploadSource": {"archiveContent": zip_de_la_skill()}}
  rev = f"{SKILL}/revisions/{id_revision(version)}"
  if not existe:
    print(f"Creando la skill {nombre} con la version {version}...")
    esperar(llamar("POST", f"{PADRE}/skills", params={"skillId": nombre}, json={
        "displayName": nombre, "description": descripcion[:2000],
        "type": "SIMPLE", "targetState": "TARGET_STATE_ACTIVE",
        "initialRevision": archivo}))
    # La revision inicial recibe un id generado por el servicio: se busca.
    revs = llamar("GET", f"{SKILL}/revisions").json().get("skillRevisions", [])
    rev = revs[0]["name"] if revs else rev
  elif llamar("GET", rev).status_code == 200:
    print(f"La version {version} ya estaba publicada.")
  else:
    print(f"Publicando la version {version} como nueva revision...")
    esperar(llamar("POST", f"{SKILL}/revisions", params={"skillRevisionId": id_revision(version)},
                   json=archivo))

# Fija la revision vigente (el "default" que sirven los agentes).
esperar(llamar("PATCH", SKILL, params={"updateMask": "defaultRevision"},
               json={"defaultRevision": rev}))
print(f"Vigente: {rev}")
