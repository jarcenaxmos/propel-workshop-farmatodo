"""Ejecuta un agente ADK una vez, sin interfaz, y muestra que herramientas uso.

Sirve como punto de control de cada paso y para probar en CI.

Uso:
  python scripts/probar_agente.py RUTA_AL_AGENTE "pregunta"
  python scripts/probar_agente.py RUTA_AL_AGENTE "pregunta" --aprobar
  python scripts/probar_agente.py RUTA_AL_AGENTE "pregunta" --rechazar

--aprobar / --rechazar responden de forma automatica a la confirmacion humana
que pide una tool con require_confirmation (paso 5).
"""

import argparse
import asyncio
import importlib
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore")

import dotenv

# Carga el .env de la raiz del repo (lo crea setup.sh) antes de importar el agente.
dotenv.load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

from google.adk.runners import InMemoryRunner
from google.genai import types

CONFIRMACION = "adk_request_confirmation"


def cargar_agente(ruta: str):
  carpeta = pathlib.Path(ruta).resolve()
  sys.path.insert(0, str(carpeta.parent))
  return importlib.import_module(f"{carpeta.name}.agent").root_agent


async def turno(runner, sesion, mensaje: types.Content) -> list:
  """Envia un mensaje y devuelve las confirmaciones que quedaron pendientes."""
  pendientes = []
  async for evento in runner.run_async(
      user_id=sesion.user_id, session_id=sesion.id, new_message=mensaje):
    if not evento.content or not evento.content.parts:
      continue
    for parte in evento.content.parts:
      if parte.function_call:
        llamada = parte.function_call
        if llamada.name == CONFIRMACION:
          pendientes.append(llamada)
          original = (llamada.args or {}).get("originalFunctionCall", {})
          print(f"[confirmacion pedida] {original.get('name')}"
                f" {str(original.get('args'))[:300]}")
        else:
          print(f"[tool] {llamada.name} {str(llamada.args)[:160]}")
      elif parte.function_response:
        respuesta = parte.function_response
        if respuesta.name != CONFIRMACION:
          print(f"[resultado] {respuesta.name}: {str(respuesta.response)[:160]}")
      elif parte.text and not parte.thought:
        print(f"[agente] {parte.text}")
  return pendientes


async def main() -> None:
  p = argparse.ArgumentParser()
  p.add_argument("agente")
  p.add_argument("pregunta")
  decision = p.add_mutually_exclusive_group()
  decision.add_argument("--aprobar", action="store_true")
  decision.add_argument("--rechazar", action="store_true")
  args = p.parse_args()

  agente = cargar_agente(args.agente)
  runner = InMemoryRunner(agent=agente, app_name="probar")
  sesion = await runner.session_service.create_session(
      app_name="probar", user_id="participante")
  print(f"[usuario] {args.pregunta}")
  pendientes = await turno(runner, sesion, types.Content(
      role="user", parts=[types.Part(text=args.pregunta)]))
  if pendientes and (args.aprobar or args.rechazar):
    print(f"[humano] {'APRUEBA' if args.aprobar else 'RECHAZA'}")
    respuestas = [types.Part(function_response=types.FunctionResponse(
        id=llamada.id, name=CONFIRMACION,
        response={"confirmed": args.aprobar})) for llamada in pendientes]
    await turno(runner, sesion, types.Content(role="user", parts=respuestas))
  elif pendientes:
    print("[info] Quedo una confirmacion pendiente."
          " Repite con --aprobar o --rechazar.")
  await runner.close()


if __name__ == "__main__":
  asyncio.run(main())
