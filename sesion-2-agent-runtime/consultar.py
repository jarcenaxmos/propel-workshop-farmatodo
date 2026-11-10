"""Consulta el agente desplegado en Agent Runtime.

Uso:
  python sesion-2-agent-runtime/consultar.py
  python sesion-2-agent-runtime/consultar.py "tu pregunta"
"""

import asyncio
import os
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")

import dotenv

AQUI = pathlib.Path(__file__).resolve().parent
dotenv.load_dotenv(AQUI.parent / ".env")

import vertexai

PROYECTO = os.environ["GOOGLE_CLOUD_PROJECT"]
REGION = os.environ.get("REGION", "us-central1")
ARCHIVO_ID = AQUI / ".agent_engine_id"
PREGUNTA = (sys.argv[1] if len(sys.argv) > 1 else
            "Investiga que pasa con pagos-gateway y dime la causa probable."
            " No abras ticket.")


async def main() -> None:
  if not ARCHIVO_ID.exists():
    sys.exit("No hay agente desplegado. Ejecuta primero ./desplegar.sh")
  nombre = (f"projects/{PROYECTO}/locations/{REGION}/reasoningEngines/"
            f"{ARCHIVO_ID.read_text().strip()}")
  cliente = vertexai.Client(project=PROYECTO, location=REGION)
  agente = cliente.agent_engines.get(name=nombre)
  print(f"Agente: {nombre}\n[usuario] {PREGUNTA}")
  async for evento in agente.async_stream_query(
      user_id="participante", message=PREGUNTA):
    for parte in (evento.get("content") or {}).get("parts", []):
      if "function_call" in parte:
        llamada = parte["function_call"]
        print(f"[tool] {llamada['name']} {str(llamada.get('args'))[:160]}")
      elif parte.get("text") and not parte.get("thought"):
        print(f"[agente] {parte['text']}")


if __name__ == "__main__":
  asyncio.run(main())
