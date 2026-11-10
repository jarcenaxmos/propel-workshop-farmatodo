# Sesión III · Evaluar el agente (ejemplo corto, 13 min)

Acompaña la demo de Gen AI evaluation. Evalúas el agente de la sesión IV con `adk eval` de dos formas: contra una trayectoria esperada y con rúbricas que califica un modelo juez.

Requisito: haber ejecutado `./setup.sh`. Usa la solución del paso 5, así que puedes hacerlo antes o después del hands-on.

```bash
cd propel-workshop-farmatodo && source .venv/bin/activate
```

## 1 · Trayectoria y respuesta esperadas (3 min)

`contexto.evalset.json` tiene tres preguntas con respuesta determinística. Cada caso declara qué herramienta debe llamar el agente, con qué argumentos, y una respuesta de referencia.

```bash
adk eval sesion-4-adk-mcp/solucion/paso-5/agente_obs \
  sesion-3-evaluacion/contexto.evalset.json \
  --config_file_path sesion-3-evaluacion/contexto.config.json \
  --print_detailed_results
```

**Qué deberías ver.** `Tests passed: 3` y, por caso:

- `tool_trajectory_avg_score: PASSED (1.0)`: llamó exactamente a la herramienta esperada.
- `final_response_match_v2: PASSED`: un modelo juez comparó la respuesta con la de referencia.
- Métricas informativas que nunca fallan: `tool_call_count_v1`, `token_usage_v1`, `invocation_duration_v1`.

Tarda cerca de un minuto (medido: 1 min).

## 2 · Rúbricas para el caso abierto (5 min)

"Investiga qué pasa con pagos-gateway" no tiene una única trayectoria correcta: los filtros llevan horas y el orden de las consultas puede variar. Ahí se evalúa con rúbricas. Abre `incidente.config.json`: cada rúbrica es una frase que el juez marca como cumplida o no.

```bash
adk eval sesion-4-adk-mcp/solucion/paso-5/agente_obs \
  sesion-3-evaluacion/incidente.evalset.json \
  --config_file_path sesion-3-evaluacion/incidente.config.json \
  --print_detailed_results
```

**Qué deberías ver.** `Tests passed: 1`, con el puntaje de cada rúbrica (`error_dominante`, `despliegue`, `usa_metricas`, `no_crea_ticket`, etc.) y la razón que dio el juez. Tarda unos dos minutos (medido: 2 min).

## 3 · Provoca una regresión (5 min)

Evalúa una versión anterior del agente con el mismo evalset. El paso 3 todavía no tiene el contexto del negocio:

```bash
adk eval sesion-4-adk-mcp/solucion/paso-3/agente_obs \
  sesion-3-evaluacion/contexto.evalset.json \
  --config_file_path sesion-3-evaluacion/contexto.config.json
```

**Qué deberías ver.** `Tests failed: 3`, tras unos cinco minutos: sin el contexto del negocio el agente se pone a buscar con otras herramientas antes de rendirse, y eso es lo que tarda. Eso es lo que detiene un pull request cuando alguien cambia un prompt, una herramienta o el modelo.

Otras pruebas: cambia el modelo con `MODEL=gemini-3.5-flash-lite adk eval ...`, o repite cada caso con `--num_runs 3` para medir estabilidad.

## Para tener en cuenta

- El juez por defecto de ADK 2.14 es `gemini-2.5-flash`, que ya fue retirado. Por eso los archivos de configuración fijan `judge_model` en `gemini-3.8-flash`. Sin eso, las métricas con juez fallan.
- Estas métricas con juez corren con Gemini en tu proyecto. Los criterios `safety_v1` y `multi_turn_*` de ADK delegan en el Gen AI evaluation service. No se probaron en este repo.
- `adk eval` devuelve un código de salida distinto de cero cuando hay casos fallidos, así que sirve tal cual en un pipeline.
- El evalset de contexto depende de `datos/catalogo_servicios.json`. El de incidente depende de las señales sembradas: si pasó más de una hora desde `./setup.sh`, vuelve a ejecutar `python scripts/sembrar_senales.py --forzar`.
