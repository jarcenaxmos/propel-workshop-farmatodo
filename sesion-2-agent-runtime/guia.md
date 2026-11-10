# Sesión II · Agent Runtime y Agent Registry: desplegar, registrar y versionar una skill (ejemplo corto, 18 min)

Acompaña la charla de Agent Runtime y Agent Registry. Despliegas el agente de la sesión IV como servicio gestionado, con Agent Identity, compruebas que quedó registrado y publicas una skill versionada que un agente consume desde el registro.

Requisito: haber ejecutado `./setup.sh`. Despliega la solución del paso 5, así que puedes hacerlo antes de terminar el hands-on.

```bash
cd propel-workshop-farmatodo && source .venv/bin/activate
```

## 1 · Despliega (1 min tuyo, 6 min de espera)

```bash
./sesion-2-agent-runtime/desplegar.sh
```

El script hace tres cosas, y vale la pena leerlo:

1. **Identidad (Agent Identity).** Crea una instancia vacía de Agent Runtime con `identity_type: AGENT_IDENTITY`. El agente recibe una identidad propia, única por instancia, que no es tu usuario ni una cuenta de servicio y no tiene llaves que guardar o rotar. La identidad se elige al crear la instancia y no se puede cambiar después. Luego `otorgar_roles.sh` le da, con mínimo privilegio, estos roles sobre el proyecto:
   - Leer señales: `roles/mcp.toolUser`, `roles/logging.viewer`, `roles/monitoring.viewer`.
   - Correr: `roles/aiplatform.user` (Gemini) y `roles/serviceusage.serviceUsageConsumer`.
   - Su propia telemetría: `roles/logging.logWriter`, `roles/monitoring.metricWriter`, `roles/telemetry.tracesWriter`.

   Su identidad es un principal con este formato (con organización; sin organización el dominio es `agents.global.proj-NUMERO_DE_PROYECTO.system.id.goog`):
   `principal://agents.global.org-ID_ORG.system.id.goog/resources/aiplatform/projects/NUMERO/locations/REGION/reasoningEngines/ID`
2. **Paquete.** Arma en `build/agente_obs/` una carpeta autocontenida: el agente, el servidor MCP de contexto, el catálogo, `requirements.txt` y `.env`.
3. **Despliegue.** Ejecuta `adk deploy agent_engine --agent_engine_id ID --otel_to_cloud` para subir el código a esa instancia. No lleva `--service_account`: con Agent Identity no se usa.

**Qué deberías ver.** Al final, `Deployed to Agent Platform: projects/.../reasoningEngines/NNN` y un enlace al playground de la consola. En la prueba tardó 6 minutos la primera vez y 3 minutos y medio al actualizar. Lánzalo y sigue escuchando la charla.

Los nombres cambiaron en 2026 y el código no: el producto se llama Agent Runtime, pero el comando sigue siendo `agent_engine` y el recurso `reasoningEngines`.

Para desplegar tu propia versión en lugar de la solución: `./sesion-2-agent-runtime/desplegar.sh --mio`. Si ya habías desplegado, actualiza el mismo recurso.

## 2 · Consulta el agente desplegado (2 min)

```bash
python sesion-2-agent-runtime/consultar.py
python sesion-2-agent-runtime/consultar.py "Que equipo atiende pedidos-api?"
```

**Qué deberías ver.** Las mismas líneas `[tool]` que en tu máquina y el diagnóstico del incidente. Ahora las llamadas a los MCP las hace la Agent Identity del agente, y el servidor MCP de contexto corre como proceso hijo dentro del contenedor.

`consultar.py` son 15 líneas útiles: `vertexai.Client(...).agent_engines.get(name=...)` y `async_stream_query(...)`.

## 3 · Míralo en Agent Registry (2 min)

```bash
python sesion-2-agent-runtime/ver_registro.py
```

**Qué deberías ver.**

- En `Agentes en REGION`: `agente-obs-farmalab`. Nadie lo registró a mano: Agent Runtime lo hace al desplegar.
- En `Servidores MCP en global`: `logging.googleapis.com`, `monitoring.googleapis.com` y los demás servidores MCP de las APIs que tienes habilitadas.

En la consola: **Agent Platform → Agent Registry**.

## 4 · Skills versionadas en Agent Registry (8 min, 2 de espera)

Una **skill** es un paquete de instrucciones (un `SKILL.md`) que un agente carga cuando la necesita. En Agent Registry se guardan con **revisiones inmutables** y una **revisión vigente**: el equipo dueño de la skill publica una versión nueva y todos los agentes que la usan la reciben sin cambiar código ni redesplegarse. Aquí la skill es `redactar-ticket-incidente`: el formato de ticket de Farmalab.

**4.1 Publica la versión 1.0.0** (la crea y espera el escaneo de seguridad: de 1 a 2 minutos)

```bash
python sesion-2-agent-runtime/skills/publicar_skill.py
```

**Qué deberías ver.** `Creando la skill ... con la version 1.0.0` y al final `Vigente: version 1.0.0 -> .../revisions/rev-...`. Se puede repetir sin duplicar nada. Mira cómo quedó:

```bash
python sesion-2-agent-runtime/ver_registro.py | tail -5
```

En la consola: **Agent Platform → Agent Registry → Skills**. La skill aparece como `private-redactar-ticket-incidente`: sin un publisher verificado, el registro antepone `private-`.

**4.2 Un agente que la usa.** El agente `skills/agente_con_skill/agent.py` no tiene las reglas del ticket: tiene un `SkillToolset` conectado a `GCPSkillRegistry`, y su instrucción dice que cargue la skill antes de escribir.

```bash
python scripts/probar_agente.py sesion-2-agent-runtime/skills/agente_con_skill "Redacta el ticket: pagos-gateway tiene error_rate 15.7% desde las 09:18 UTC, 8 errores UPSTREAM_TIMEOUT (504) en 2 minutos, p95 4300 ms. Se desplego la version 3.8.2 a las 09:10 UTC y redujo el timeout hacia adquirente-co de 8 s a 2 s. Criticidad alta, runbook: rollback a 3.8.1 por el equipo Pagos."
```

**Qué deberías ver.** Una línea `[tool] load_skill {'skill_name': 'private-redactar-ticket-incidente'}` y un ticket cuyo título es `[ALTA] pagos-gateway: ...`.

**4.3 Publica la versión 1.1.0.** La carpeta `skills/versiones/redactar-ticket-incidente-1.1.0/` tiene la skill con un cambio de formato: el título empieza con `INC | ` y mide como máximo 80 caracteres. Compara con `diff` si quieres.

```bash
python sesion-2-agent-runtime/skills/publicar_skill.py --dir sesion-2-agent-runtime/skills/versiones/redactar-ticket-incidente-1.1.0
```

Vuelve a ejecutar el agente del paso 4.2 **sin tocarlo**: ahora el título es `INC | [ALTA] pagos-gateway: ...`. El código del agente es el mismo; cambió la revisión vigente. Y si la nueva versión da problemas, vuelves a la anterior con un comando:

```bash
python sesion-2-agent-runtime/skills/publicar_skill.py --default 1.0.0
```

Notas de lo que se verificó:

- La versión se lee de `metadata.version` en el `SKILL.md`. Las revisiones reciben un id generado (`rev-...`).
- Las skills viven en la ubicación `global`. En una región como `us-east1` el servicio de skills responde `503`.
- La skill nace con escaneo de seguridad obligatorio (`ENABLED_BLOCKING`): una revisión solo puede ser la vigente cuando el escaneo terminó, por eso el script espera.
- Permisos: publicar pide `roles/agentregistry.editor`; leer, `roles/agentregistry.viewer` (o `roles/owner`). El agente de este ejemplo corre en tu máquina con tu usuario. Si lo desplegaras en Agent Runtime, su Agent Identity necesitaría `roles/agentregistry.viewer`.
- `gcloud` todavía no trae comandos para skills (`gcloud agent-registry` no existe en la versión 553): por eso el script usa la API REST `v1`. ADK usa por defecto `v1alpha` y funciona igual.

## Para tener en cuenta

- **Con Agent Identity el token va ligado al certificado del agente (mTLS).** Las librerías de Google lo manejan solas, pero el cliente HTTP del MCP no: con el endpoint normal (`logging.googleapis.com/mcp`) el servidor responde `401`. Por eso `agente_obs/conexion_google.py` usa `logging.mtls.googleapis.com/mcp` con el certificado cuando corre desplegado. En tu máquina no hay certificado y usa el endpoint normal.
- Para ver la identidad en la consola: **Agent Platform → Agent Runtime → tu agente → Identity**.
- Dentro de Agent Runtime, `GOOGLE_CLOUD_PROJECT` trae el **número** del proyecto. Los filtros de logs necesitan el id, y por eso el paquete define `SIGNALS_PROJECT_ID`.
- La aprobación humana del paso 5 también funciona desplegada: el pedido de confirmación llega como un evento y se responde con otro mensaje en la misma sesión. Se probó por API, no en el playground de la consola.
- Los tickets se escriben en `/tmp/tickets` del contenedor y se pierden. En producción la herramienta llamaría a la mesa de ayuda real.
- No hay región de Agent Runtime en Colombia. En Sudamérica solo existe `southamerica-east1`.
- Cuota por defecto: 90 consultas por minuto por proyecto y región.
- Para borrarlo (agente, roles de su identidad y skill): `./cleanup.sh`.
