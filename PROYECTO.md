  # Proyecto: Narrador IA en vivo — Microsoft Premier League Hackathon 2026

> Documento base para construir el proyecto. Reúne los requisitos del hackathon, la idea del producto, la arquitectura de agentes, las tecnologías y la estructura del repo.
> Fuente de las reglas: [reglas/OFFICIAL RULES.md](reglas/OFFICIAL%20RULES.md).

---

## ✅ Estado de avance (19 oct 2026)
**Hecho (sin agentes ni Azure todavía):**
- [x] Generador de partidos sintéticos realista (`backend/src/matchvoice/engine/generator.py`), comparado con cifras reales en `matchvoice calibrate`
- [x] Analyst Engine: estadísticas en vivo y detección de momentos clave con su evidencia (`engine/analyst.py`)
- [x] Narración por plantillas ES/EN con tono de hincha, jugador favorito y modo accesible (`engine/narration.py`)
- [x] Resúmenes por plantilla: medio tiempo, final y "¿Qué me perdí?" (`engine/recap.py`)
- [x] API FastAPI + stream SSE en vivo con reanudación (`api/matches.py`)
- [x] Frontend Vue 3 + TS: cancha, chat, voz del navegador, modos Fan/Analista/Accesible, capas del analista, exportación
- [x] Tests (29 backend, 5 frontend), ruff, CI de GitHub Actions y Dockerfile

**Siguiente:** agentes de Foundry + orquestador con Agent Framework, Azure AI Speech, servidor MCP, chat Q&A, consultas del analista y despliegue en Container Apps.

---

## 0. Fechas (hora del Pacífico, PT)

| Hito | Fecha |
|---|---|
| **Cierre de registro** | **20 oct 2026, 12:00 pm PT**. Regístrate en https://aka.ms/insidethegame |
| **Entrega final** | **27 oct 2026, 11:59 pm PT** |
| Evaluación | 27 oct – 10 nov 2026 |
| Ganadores | a más tardar el 20 nov 2026 |

---

## 1. Requisitos del hackathon

### 1.1 Obligatorios para la entrega (si falta uno, quedas fuera)
- [ ] Proyecto **nuevo**, creado después del 29 sep 2026. Debe ser **obra original**: no se permite hacer fork ni copiar otro repo.
- [ ] **Repositorio de GitHub público**.
- [ ] **Video demo de menos de 2 min**, publicado en YouTube o Vimeo. Debe mostrar el proyecto funcionando de verdad, sin música con copyright ni marcas de terceros.
- [ ] **Pitch o descripción** breve: qué es, qué tecnologías de Microsoft y Azure usa, qué hace y qué problema resuelve.
- [ ] **Demo accesible** para los jueces (URL pública), gratis y sin restricciones hasta el 10 nov. Si pide login, incluye las credenciales en las instrucciones de prueba.
- [ ] **Todo en inglés**: video, README, descripción e instrucciones de prueba. Este documento puede quedar en español.
- [ ] Usar **solo datos sintéticos**: clubes y jugadores **ficticios**, sin nombres, escudos ni marcas reales.
- [ ] El proyecto se instala y funciona igual que como se ve en el video.
- [ ] Llenar todos los campos de la página "Projects" del sitio del hackathon.

### 1.2 El reto: pipeline de 5 etapas
| Etapa | Qué exige | Cómo lo cubrimos |
|---|---|---|
| **Ingest** | Recibir los eventos sintéticos en vivo | Generador de partidos más un stream de eventos en tiempo real (SSE) |
| **Interpret** | Convertir los eventos en estadísticas, patrones y contexto | Motor de análisis en código (stats y momentos clave) |
| **Explain** | Explicar *por qué* importa un momento | Agente Explainer más el comentarista |
| **Render** | Salida que pueda ir en pantalla junto al partido | Cancha en vivo, overlays en JSON con marcas de tiempo y chat de narración |
| **Personalize** | Experiencias realmente distintas para el analista y para el fan | Perfiles: club y jugador favorito, idioma, modo Fan o Analista |

### 1.3 Funciones recomendadas por las reglas (para ir al 100%)
- [ ] Identificación de jugadores en tiempo real, con indicadores de velocidad y distancia al superar un umbral.
- [ ] Calidad de pase: distancia, precisión y dificultad.
- [ ] Velocidad del balón y del tiro.
- [ ] Narrativas: historias clave, contexto de rendimiento, hitos y resumen del partido.
- [ ] Explicabilidad: control frente a caos, cambios de presión táctica y ritmo del juego.
- [ ] Innovación en datos: dataset sintético realista y propio.
- [ ] Varios idiomas.
- [ ] *(Opcional, difícil)* Auto-eventing desde video. Lo dejamos fuera del MVP.

### 1.4 Cómo nos evalúan (5 criterios, 20% cada uno)
1. **Implementación técnica**: datos sintéticos creativos, buenas prácticas, uso de las tecnologías de Microsoft, código limpio y documentado, con tests.
2. **Diseño agéntico**: orquestación de agentes, MCP y colaboración entre varios agentes.
3. **Impacto real**: que se pueda desplegar en producción y que resuelva un problema importante.
4. **UX y presentación**: interfaz intuitiva, video claro y un equilibrio entre frontend y backend.
5. **Encaje con la categoría** elegida.

**Categoría objetivo:** 🎯 **Best Multi-Agent System**. Como secundaria también competimos en el Gran Premio, que se otorga a todos.
Los jueces de esa categoría buscan agentes con **roles distintos**, **estado compartido**, **traspasos (handoffs)** entre ellos, **recuperación ante fallos** y un resultado que un solo agente no lograría.

---

## 2. El producto

### 2.1 Idea en una frase
Un "estudio de transmisión" con IA: **la cancha en vivo a la izquierda** y, **a la derecha, un chat donde dos narradores con voz cuentan el partido**. Además el usuario puede **preguntarle cosas al narrador**, y la experiencia cambia según quién mira: un fan de un club, un analista o una persona ciega.

### 2.2 Qué nos diferencia del repo de referencia (matchday-crew)
1. **Narración jugada a jugada** de todo el partido, no solo de los momentos clave.
2. **Dos voces**: un narrador que cuenta la jugada y un comentarista que la analiza, con emoción vía SSML.
3. **Chat de ida y vuelta**: el usuario pregunta y un agente responde con datos reales del partido, usando herramientas MCP.
4. **Consultas del analista en lenguaje natural que redibujan la cancha**: "muéstrame los pases progresivos del #8".
5. **Modo accesible por audio descriptivo** para personas ciegas o con baja visión.
6. Botón **"¿Qué me perdí?"**: resumen hasta el minuto actual, personalizado.

### 2.3 Layout
```
┌────────────────────────────────────┬──────────────────────────────┐
│ 🏟 HOME 1 - 0 AWAY · 67' · momentum │ 🎙 NARRACIÓN EN VIVO   🔊 ⏸   │
│ ┌────────────────────────────────┐ │ 64' 🗣 Ruiz filtra a Okafor   │
│ │                                │ │ 65' 🗣 ¡TIRO de Okafor!       │
│ │          CANCHA (SVG)          │ │ 65' 🗣 ¡ATAJA Mendes! 🧤      │
│ │    22 jugadores + balón +      │ │     🎓 "Tercera atajada; el   │
│ │    capas (heatmap, pases...)   │ │      rival domina el xG 1.4"  │
│ │                                │ │ ──────────────────────────── │
│ └────────────────────────────────┘ │ 💬 Pregunta al narrador...  ▶ │
│ [Fan|Analista|Accesible] [ES|EN|..]│ [¿Qué me perdí?]              │
│ Línea de tiempo ▬▬▬▬●▬▬▬▬ (goles) │                              │
└────────────────────────────────────┴──────────────────────────────┘
```
En móvil la cancha queda arriba y el chat abajo.

### 2.4 Personalización: modo Fan
| Opción | Efecto en la cancha | Efecto en la narración y la voz |
|---|---|---|
| **Club favorito** | Tu equipo siempre ataca de izquierda a derecha. Tus jugadores se ven resaltados y el rival atenuado | El narrador habla como hincha: euforia en tus goles, lamento en los del rival |
| **Jugador favorito** | Anillo o brillo sobre él, estela de su recorrido y nombre siempre visible. Opcionalmente zoom que lo sigue. Al final, su mapa de calor | Tarjeta "⭐ Tu jugador": distancia, tiros, pases. Alertas cuando toca el balón o hace un sprint |
| **Intensidad** | — | Solo goles, jugadas importantes o todo |
| **Nivel** | — | Principiante: explica las reglas cuando pasan. Experto: más táctica |
| **Idioma y voz** | Textos de la UI | Idioma del chat y de la voz (ES, EN y uno más, por ejemplo JA o FR) |
| **¿Qué me perdí?** | — | Resumen hasta el minuto actual, enfocado en tu club |
| **Predicciones** *(extra)* | — | "¿Habrá gol antes del 75'?" y votar al jugador del partido |

### 2.5 Personalización: modo Analista
**Capas sobre la cancha (se activan y desactivan):**
- Mapa de tiros, con el tamaño de cada círculo según su xG.
- Red de pases: quién le pasa a quién y con qué frecuencia.
- Mapa de calor por jugador o por equipo.
- Pases progresivos, como flechas.
- Altura de la línea defensiva y zonas de presión.
- Zonas de peligro (xT).

**Herramientas:**
- **Consultas en lenguaje natural**: "pases progresivos del #8 en el 2T". Un agente lo traduce a un `OverlaySpec` en JSON y la cancha se redibuja.
- **Comparar dos jugadores** lado a lado.
- **Alertas personalizadas**, por ejemplo "avísame si el PPDA del rival baja de 8" o "si el #6 baja sus sprints" (señal de cansancio).
- **Detectar cambios tácticos**, por ejemplo "pasó de 4-3-3 a 5-4-1 en el 70'".
- **Panel de métricas**: xG acumulado, PPDA, field tilt, posesión por zonas, valoración de jugadores.
- **Línea de tiempo** para regresar a cualquier minuto.
- **Exportar**: CSV o JSON, informe en PDF y lista de momentos con su minuto para que producción arme los clips.

### 2.6 Modo accesible
- Narración más descriptiva: dónde está el balón y quién lo lleva ("balón en el carril derecho, cerca del área").
- Alto contraste, paletas aptas para daltonismo, todo navegable con teclado y compatible con lectores de pantalla (ARIA live region en el chat).

---

## 3. Arquitectura

### 3.1 Vista general
```
                ┌──────────────────── BACKEND (Python 3.12 + FastAPI + Agent Framework) ───────────┐
                │                                                                                   │
 Generador ───► │ Ingestor ──► Analyst Engine ──► Orquestador ──► [Agentes IA en Microsoft Foundry] │
 (sintético)    │ (eventos)    (stats+momentos)   (Workflow de       Explainer / Comentarista /     │
                │                  │               Agent Framework)  Personalizer / Recapper /      │
                │                  │               guardrails)       Chat Q&A / Analyst Query       │
                │                  ▼                    │                    ▲                      │
                │            Match State ◄──────────────┘          MCP Server (herramientas de     │
                │            (memoria + Cosmos DB)                  datos del partido) ─────────────┘
                │                  │
                │   Play-by-play por plantilla (instantáneo)     Azure AI Speech (texto → voz)
                └──────────────────┼──────────────────────────────────────┼──────────────────────────┘
                                   ▼  SSE (Server-Sent Events)            ▼ audio MP3
                         ┌──────────────── FRONTEND (Vue 3 + TS) ─────────────────┐
                         │  Cancha SVG + capas │ Chat de narración + voz + preguntas │
                         └─────────────────────────────────────────────────────────┘
```

### 3.2 Regla de oro: código para los números, IA para las palabras
- **Las estadísticas siempre las calcula el código**, porque es rápido, exacto y no cuesta nada. La IA **nunca inventa números**: solo usa los que le pasa el motor.
- **Narración en dos niveles**, para que la voz no se atrase respecto al partido:
  1. **Plantillas**, instantáneas, para jugadas rutinarias como pases, tiros y atajadas: "¡Tiro de {player}! ¡Ataja {keeper}!". Llevan varias variantes por evento e idioma para que no suenen repetitivas.
  2. **IA (LLM)**, para los momentos importantes como goles, ocasiones claras, cambios de momentum o una tarjeta roja. La línea de plantilla aparece primero y la de la IA llega 1–3 segundos después y la reemplaza o enriquece.

### 3.3 Componentes en código (no son IA)
| Componente | Responsabilidad |
|---|---|
| **Generator** | Crea partidos sintéticos realistas y repetibles a partir de una semilla: 4 clubes ficticios con estilo propio, plantillas de jugadores, xG, velocidades y un momentum "oculto" |
| **Ingestor** | Reproduce el partido en tiempo real o acelerado (`speed=30` → 90 min en unos 3 min) y publica cada evento |
| **Analyst Engine** | Lleva las estadísticas en vivo por equipo y por jugador, y detecta momentos clave con su importancia (0–1) y su evidencia (`facts`, `eventIds`) |
| **Play-by-play Templater** | Genera al instante una línea de narración para *cada* evento, en cada idioma |
| **Orquestador** (Microsoft Agent Framework) | Cola con prioridades (los goles van primero; si va atrasado, descarta lo de poco valor), estado compartido, traspasos entre agentes, timeouts, reintentos y plan B. Ver §3.4.1 |
| **Grounding Guard** | Revisa que cada número de la respuesta de la IA exista en la evidencia. Si no, reintenta una vez y después usa la plantilla |
| **Voice Service** | Convierte texto en audio con Azure AI Speech (SSML, una voz por personaje), con caché y límite de uso |

### 3.4 Agentes de IA (Microsoft Foundry)
Cada agente se registra en Foundry con sus instrucciones, versionado y un **output en JSON con esquema estricto**.

| # | Agente | Cuándo actúa | Entrada | Salida |
|---|---|---|---|---|
| 1 | **Explainer** | En cada momento clave | Momento y contexto en vivo | `why`, `tacticalAngle`, `keyNumbers[]`, `confidence` |
| 2 | **Comentarista** (dúo) | Después del Explainer | Momento, explicación, idiomas y últimas líneas en pantalla | `lines[]` con `{speaker: "narrator"\|"pundit", lang, text, emotion}` |
| 3 | **Personalizer** | Después del Comentarista | Líneas y perfil (club, jugador, nivel, modo) | Versión adaptada: tono de hincha, modo principiante, accesible |
| 4 | **Recapper** | Medio tiempo, final y "¿qué me perdí?" | Stats, momentos, explicaciones y perfil | `headline`, `recap`, `playerOfTheMatch` |
| 5 | **Chat Q&A** | Cuando el usuario pregunta | Pregunta y perfil, con **herramientas MCP** | Respuesta con base en datos y las fuentes (`eventIds`) |
| 6 | **Analyst Query** | Consulta en lenguaje natural del analista | Consulta, con **herramientas MCP** | `OverlaySpec` en JSON, que el front dibuja en la cancha |

**Flujo y traspasos:**
```
Evento ─► Analyst Engine ─► (¿momento clave?) ─► Explainer ─► Comentarista ─► Personalizer ─► Voice ─► UI
                │                                                       ▲
                └─► Templater ─► UI (instantáneo) ──────────────────────┘ (la IA reemplaza/enriquece)
Medio tiempo / final / "¿qué me perdí?" ─► Recapper ─► Personalizer ─► UI + voz
Pregunta del usuario ─► Chat Q&A ⇄ MCP tools ─► UI + voz
Consulta del analista ─► Analyst Query ⇄ MCP tools ─► OverlaySpec ─► Cancha
```

**Costo de la personalización:** no se llama a la IA una vez por usuario. Se personaliza por **"bucket" de perfil** (`club × modo × idioma`) y el resultado se guarda en caché. Lo único individual es el chat Q&A.

**Recuperación ante fallos** (lo evalúa la categoría Multi-Agent):
- Si un agente tarda demasiado, da error o devuelve números inventados, se reintenta una vez con el error como retroalimentación y luego se usa la plantilla.
- Tras 3 fallos seguidos, ese agente pasa a "modo degradado" y la UI lo muestra.
- Un **Crew Panel** en la UI muestra el estado de cada agente, su latencia y si la línea vino de la IA o de una plantilla. Así los jueces ven la orquestación.

#### 3.4.1 Orquestación con Microsoft Agent Framework (Python)
**Microsoft Agent Framework** (`pip install agent-framework`) es el SDK de Microsoft para crear agentes y **workflows multi-agente**. Lo usamos así:

| Necesidad (criterio de los jueces) | Pieza del Agent Framework |
|---|---|
| **Roles distintos** | Un `ChatAgent` por cada agente, conectado a Foundry (cliente de Azure AI / Foundry Agent Service) |
| **Traspasos (handoffs)** | Un **Workflow** (grafo de *executors* y *edges*): Explainer → Comentarista → Personalizer. El Recapper se activa por eventos de medio tiempo y final |
| **Estado compartido** | Estado del workflow con el `MatchState`: últimas líneas, momentos y explicaciones. Cada agente ve lo anterior para no repetirse |
| **Ejecución en paralelo** | Ejecución *concurrent*: el Personalizer genera los buckets de perfil (club × modo × idioma) en paralelo |
| **Recuperación ante fallos** | *Middleware*: timeout, grounding y reintento con retroalimentación, y luego la plantilla. Con *checkpoints* el workflow se reanuda si el proceso se reinicia |
| **Herramientas** | Los agentes Chat Q&A y Analyst Query consumen el servidor MCP (§3.5) como *tools* |
| **Observabilidad** | Telemetría OpenTelemetry integrada, enviada a Application Insights |

> El Agent Framework es nuevo y su API cambia rápido. Antes de escribir código, revisa los ejemplos oficiales en `github.com/microsoft/agent-framework` (carpeta `python/samples`) y fija la versión exacta en `pyproject.toml`.

### 3.5 Servidor MCP (herramientas de datos del partido)
Un servidor MCP propio, en Python con el SDK `mcp` (FastMCP), expone el estado del partido como herramientas. Lo usan los agentes Chat Q&A y Analyst Query, y también sirve para conectarlo a GitHub Copilot u otro cliente MCP en la demo.

| Herramienta | Qué devuelve |
|---|---|
| `get_match_state` | Marcador, minuto, posesión y momentum |
| `get_team_stats(team)` | Tiros, xG, pases, PPDA… |
| `get_player_stats(playerId)` | Distancia, sprints, pases, tiros, valoración |
| `find_events(filter)` | Eventos filtrados por tipo, jugador, periodo o zona |
| `get_key_moments(since?)` | Momentos clave con su explicación |
| `compare_players(a, b)` | Comparación lado a lado |

### 3.6 Contratos de datos (resumen)
**Una sola fuente de verdad:** los modelos se definen en Python con **Pydantic**. FastAPI publica el esquema OpenAPI y el front genera sus tipos TypeScript a partir de él con `openapi-typescript` (`npm run gen:types`). Así el backend y el front nunca quedan desalineados.

**Evento del partido** (se muestra en TS, que es como lo verá el front; en Python es un `BaseModel` equivalente):
```ts
interface MatchEvent {
  id: string; seq: number; matchId: string;
  type: 'pass'|'carry'|'shot'|'save'|'goal'|'tackle'|'interception'|'pressure'
      |'foul'|'card'|'corner'|'substitution'|'possession_change'
      |'kickoff'|'period_start'|'period_end'|'match_start'|'match_end';
  period: 1|2; elapsed: number;             // segundos desde el inicio
  clock: { minute: number; second: number; display: string };
  team: 'home'|'away'|null;
  player: { id: string; name: string; number: number; position: string } | null;
  location: { x: number; y: number } | null; // cancha de 105 x 68 m
  score: { home: number; away: number };
  data: Record<string, unknown>;             // específico por tipo (xg, speedKmh, distance, outcome...)
}
```
**Mensajes del stream SSE** (`GET /api/matches/:id/stream?speed=30&profile=...`):
| `event:` | Contenido |
|---|---|
| `match_event` | Un `MatchEvent` |
| `pbp` | Línea de narración por plantilla `{eventId, lang, text}` |
| `moment` | Momento clave detectado por el Analyst Engine |
| `commentary` | Líneas de la IA `{momentId, speaker, lang, text, emotion, source: 'ai'\|'template', latencyMs}` |
| `stats` | Snapshot de estadísticas en vivo |
| `overlay` | Overlay con tiempo, para el render: `{at, kind, ttlMs, payload}` |
| `recap` | Resumen de medio tiempo o final |
| `crew_status` | Estado de los agentes, para el Crew Panel |

**OverlaySpec** (lo que el agente Analyst Query devuelve y la cancha dibuja):
```ts
interface OverlaySpec {
  layer: 'shot_map'|'pass_network'|'heatmap'|'progressive_passes'|'def_line'|'pressure_zones';
  filter: { team?: 'home'|'away'; playerId?: string; period?: 1|2; fromMinute?: number; toMinute?: number };
  title: string;          // "Pases progresivos de #8 — 2T"
  eventIds?: string[];    // evidencia
}
```

---

## 4. Tecnologías

> No hace falta saber Azure de antemano: abajo va qué es cada pieza y para qué la usamos.

### 4.1 Stack
| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | **Vue 3 + TypeScript + Vite**, **Pinia** (estado), **vue-i18n** (idiomas), cancha en **SVG** | Lo que pediste. SVG es fácil de animar con Vue y nítido en cualquier pantalla |
| Gráficas | **Chart.js** con `vue-chartjs`, o SVG a mano | Momentum y stats |
| Backend / API | **Python 3.12 + FastAPI + Uvicorn**, SSE con `sse-starlette` | Asíncrono, rápido y con OpenAPI automático (los tipos del front salen de ahí) |
| Orquestación de agentes | **Microsoft Agent Framework** (Python) | Workflows multi-agente, handoffs, checkpoints y telemetría (§3.4.1) |
| Modelos de datos | **Pydantic v2** | Validación y esquemas JSON estrictos para la salida de los agentes |
| Gestor de paquetes Python | **uv** (`pyproject.toml`) | Instala y crea el entorno en segundos |
| Calidad Python | **ruff** (lint y formato) + **mypy** | Código limpio, lo que puntúa en Implementación técnica |
| Tests | **pytest** (backend) y **Vitest** (front) | Estándar de cada lado |
| Tipos para el front | **openapi-typescript** | Genera los tipos TS desde FastAPI |

### 4.2 Servicios de Microsoft y Azure (las "hero technologies")
| Servicio | Qué es | Para qué lo usamos | ¿MVP? |
|---|---|---|---|
| **Microsoft Foundry** (ai.azure.com) | Portal para desplegar modelos de IA y crear agentes | Desplegar un modelo rápido y barato (tipo `gpt-5-mini`) y registrar los 6 agentes. SDK: `azure-ai-projects` + `azure-identity` (Python) | ✅ |
| **Microsoft Agent Framework** | SDK de Microsoft para agentes y workflows multi-agente | El orquestador del crew (§3.4.1) | ✅ |
| **Foundry Agent Service** | Agentes con instrucciones, herramientas y versiones dentro de Foundry | Los agentes se ven y se versionan en el portal (puntúa en "Best Use of Foundry") | ✅ |
| **Azure AI Speech** | Texto a voz con voces neuronales | Voz del narrador y del comentarista. SSML para la emoción (`mstts:express-as`: hay que revisar en la *Voice Gallery* qué voces lo soportan). Voces sugeridas: `es-MX-JorgeNeural` y `es-MX-DaliaNeural`, `en-GB-RyanNeural` y `en-US-AriaNeural`. SDK: `azure-cognitiveservices-speech`, o la API REST | ✅ |
| **Azure Container Apps** | Ejecuta contenedores Docker sin administrar servidores | Hospedar el backend y el front compilado en una URL pública | ✅ |
| **Managed Identity + Entra ID** | El login de Azure: la app se autentica sin llaves en el código | Seguridad. `az login` en local e identidad administrada en la nube | ✅ |
| **GitHub Actions** | CI/CD | Tests, construir la imagen Docker y desplegar | ✅ |
| **Model Context Protocol (MCP)** | Estándar para darle herramientas a un agente | Nuestro servidor MCP de datos del partido. SDK: `mcp` (Python, FastMCP) | ✅ |
| **GitHub Copilot (Agent Mode)** | Asistente de código | Usarlo durante el desarrollo y mencionarlo en el pitch | ✅ |
| **Application Insights** | Monitoreo, logs y métricas | Latencia de cada agente, errores y uso de plan B (puntúa en "Enterprise") | ⭐ extra |
| **Azure Cosmos DB** (serverless) | Base de datos NoSQL | Guardar perfiles de usuario, partidos generados y resúmenes | ⭐ extra |
| **Azure Key Vault** | Bóveda de secretos | Solo si hiciera falta alguna llave | ⭐ extra |
| **Azure Event Hubs** | Ingesta de eventos a gran escala | Ingesta "nivel broadcast" (suma en la categoría Cloud Native) | ⭐ extra |

### 4.3 Primeros pasos (desde cero)
0. Instalar las herramientas locales: **Python 3.12**, **uv** (`winget install astral-sh.uv`), **Node.js 22** (para el front) y **Docker Desktop**.
1. Crear una cuenta en https://azure.microsoft.com/free (incluye crédito gratis) e instalar la **Azure CLI**: `winget install Microsoft.AzureCLI`.
2. `az login` y crear un grupo de recursos, que es una "carpeta" de recursos: `az group create -n rg-hackathon -l eastus2`.
3. En **ai.azure.com**: crear un **Foundry project**, ir a *Models + endpoints*, desplegar un modelo (por ejemplo `gpt-5-mini` o `gpt-4.1-mini`) y anotar el **endpoint del proyecto** y el **nombre del deployment**.
4. Darte el rol **Azure AI User** sobre el recurso de Foundry, para poder llamar a los agentes con tu login.
5. Speech: el recurso de Foundry también sirve para Speech. Anota la **región** y el **resource ID**, y date el rol **Cognitive Services Speech User**.
6. Copiar `.env.example` a `.env` y llenar esas variables.
7. Despliegue: `az containerapp up` (o el script en `infra/`), activando la **identidad administrada** y asignándole los dos roles anteriores.
8. 💰 **Control de costos:** límite de partidos con IA en simultáneo (`MAX_AI_STREAMS=3`), caché de audio y de respuestas, y Container Apps con escala a 0 cuando no hay uso.

**Variables de entorno (`.env.example`):**
```bash
FOUNDRY_PROJECT_ENDPOINT=https://<recurso>.services.ai.azure.com/api/projects/<proyecto>
FOUNDRY_MODEL_DEPLOYMENT=<nombre-del-deployment>
SPEECH_REGION=eastus2
SPEECH_RESOURCE_ID=/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<recurso>
MAX_AI_STREAMS=3
PORT=4000
```

---

## 5. Estructura del repo

```
/
├─ backend/                         # Python 3.12 (uv) — API + motor + agentes + MCP
│  ├─ pyproject.toml                # dependencias fijadas: fastapi, agent-framework, azure-*, mcp, pydantic
│  ├─ src/matchvoice/
│  │  ├─ models/                    # Pydantic: MatchEvent, Moment, OverlaySpec, mensajes SSE, Profile
│  │  ├─ engine/                    # código sin IA
│  │  │  ├─ generator/              # partidos sintéticos (semilla, clubes ficticios, momentum oculto)
│  │  │  ├─ analyst/                # stats en vivo + detección de momentos
│  │  │  └─ templater/              # play-by-play por plantilla (multi-idioma)
│  │  ├─ agents/
│  │  │  ├─ definitions/            # instrucciones + esquema (Pydantic) de cada agente
│  │  │  ├─ client.py               # conexión a Foundry (azure-ai-projects + azure-identity)
│  │  │  └─ deploy.py               # registra/actualiza los agentes en Foundry
│  │  ├─ orchestrator/
│  │  │  ├─ workflow.py             # Workflow de Agent Framework: executors + edges + handoffs
│  │  │  ├─ priority_queue.py       # goles primero, descarta lo de poco valor si va atrasado
│  │  │  ├─ grounding.py            # verificación de números (middleware)
│  │  │  └─ fallback.py             # plan B con plantillas
│  │  ├─ mcp_server/                # FastMCP: get_match_state, find_events, compare_players...
│  │  ├─ voice/speech.py            # Azure AI Speech (SSML, caché)
│  │  ├─ api/                       # routers FastAPI: matches, stream (SSE), ask, query, voice, health
│  │  ├─ cli.py                     # generate / stream / analyse / crew-check
│  │  └─ main.py                    # app FastAPI (sirve también el front compilado)
│  └─ tests/                        # pytest: generator, analyst, grounding, workflow (con agentes simulados)
├─ frontend/                        # Vue 3 + TS + Vite
│  ├─ src/
│  │  ├─ components/
│  │  │  ├─ pitch/
│  │  │  │  ├─ PitchView.vue         # cancha SVG, jugadores, balón
│  │  │  │  ├─ PlayerMarker.vue      # jugador (resaltado si es favorito)
│  │  │  │  ├─ BallTrail.vue
│  │  │  │  └─ layers/               # ShotMap, PassNetwork, Heatmap, DefLine...
│  │  │  ├─ chat/
│  │  │  │  ├─ CommentaryChat.vue    # feed de narración (ARIA live)
│  │  │  │  ├─ ChatMessage.vue       # narrador / comentarista / IA o plantilla
│  │  │  │  └─ AskBox.vue            # preguntas al narrador + "¿Qué me perdí?"
│  │  │  ├─ ScoreBar.vue             # marcador, reloj, momentum
│  │  │  ├─ Timeline.vue             # línea de tiempo para regresar a un minuto
│  │  │  ├─ ProfileSetup.vue         # elegir club, jugador, idioma, modo
│  │  │  ├─ AnalystPanel.vue         # capas, métricas, consulta en lenguaje natural, exportar
│  │  │  ├─ FavoritePlayerCard.vue
│  │  │  ├─ RecapModal.vue
│  │  │  └─ CrewPanel.vue            # estado de los agentes (para los jueces)
│  │  ├─ composables/
│  │  │  ├─ useMatchStream.ts        # conexión SSE
│  │  │  ├─ useVoice.ts              # cola de audio, una línea a la vez
│  │  │  └─ useTeamShape.ts          # posiciones simuladas de los 22 jugadores
│  │  ├─ stores/                     # Pinia: match, profile, ui
│  │  ├─ api/types.gen.ts            # tipos generados desde OpenAPI (npm run gen:types)
│  │  ├─ i18n/                       # es.json, en.json, ...
│  │  ├─ App.vue
│  │  └─ main.ts
│  ├─ package.json
│  └─ vite.config.ts                 # proxy /api → backend en desarrollo
├─ data/                            # partidos generados de ejemplo (JSON)
├─ infra/                           # scripts de despliegue Azure (az CLI / Bicep)
├─ docs/
│  ├─ architecture.md               # diagramas (en inglés, para los jueces)
│  └─ SCHEMA.md                     # esquema de eventos
├─ .github/workflows/ci.yml         # ruff + mypy + pytest + vitest → imagen Docker → despliegue
├─ Dockerfile                       # multi-stage: compila el front (Node) y lo sirve desde FastAPI (Python)
├─ .env.example
└─ README.md                        # EN INGLÉS: pitch, demo, cómo correrlo, tecnologías Azure
```

**Comandos de desarrollo:**
```bash
cd backend  && uv sync && uv run uvicorn matchvoice.main:app --reload --port 4000   # API
cd frontend && npm install && npm run dev                                          # front en :5173
cd backend  && uv run pytest                                                       # tests backend
```

Un **solo contenedor** en producción: FastAPI sirve la API y los archivos estáticos del front compilado.

**Endpoints:**
| Método y ruta | Uso |
|---|---|
| `GET /api/clubs` | Clubes y plantillas ficticias, para el perfil |
| `GET /api/matches/:seed` | Partido completo |
| `GET /api/matches/:seed/stream?speed=&langs=&mode=&club=&player=` | Stream SSE en vivo |
| `POST /api/matches/:seed/ask` | Pregunta del chat → agente Q&A |
| `POST /api/matches/:seed/query` | Consulta del analista → `OverlaySpec` |
| `POST /api/matches/:seed/catchup` | "¿Qué me perdí?" |
| `POST /api/voice` | Texto → MP3 (Azure Speech) |
| `GET /api/matches/:seed/export?format=csv\|json` | Exportar |
| `GET /api/health` | Estado y modo de cada agente |

---

## 6. Plan de trabajo (18 → 27 oct)

| Día | Objetivo | Entregable |
|---|---|---|
| **18–19 oct** | **Registrarse.** Crear el monorepo, la cuenta de Azure, el proyecto de Foundry y desplegar el modelo | Repo público vacío con la estructura y una llamada de prueba a Foundry OK |
| **19–20 oct** | Generator + Analyst Engine + tests | `uv run pytest` en verde, partido JSON y stats realistas |
| **20–21 oct** | Server con SSE + Templater + front: cancha y chat básicos | Partido en vivo en el navegador con narración por plantilla |
| **21–22 oct** | Agentes Explainer + Comentarista + Workflow de Agent Framework + grounding + plan B | Narración con IA en el chat y Crew Panel |
| **22 oct** | Azure Speech: dos voces, cola de audio, emoción | El partido se escucha |
| **23 oct** | Personalización Fan (club y jugador, tono de hincha) + idiomas + Recapper + "¿Qué me perdí?" | Dos experiencias distintas |
| **24 oct** | Servidor MCP + Chat Q&A + Analyst Query + capas de la cancha | Preguntar y redibujar la cancha |
| **25 oct** | Despliegue en Container Apps + CI/CD + modo accesible | URL pública funcionando |
| **26 oct** | Pulir la UX, README en inglés, diagramas, grabar el video | Video de menos de 2 min |
| **27 oct** | **Entregar** con margen (antes de las 11:59 pm PT) | ✅ |

**Si el tiempo no alcanza, este es el orden de prioridad:**
1. Pipeline completo con cancha + chat + voz + modos Fan y Analista.
2. Chat Q&A.
3. Consultas del analista.
4. Modo accesible.
5. Extras (Cosmos DB, App Insights, predicciones).

---

## 7. Guion del video (menos de 2 min, en inglés)
1. **0:00–0:15. Problema:** "Los partidos son iguales para todos; las estadísticas no cuentan historias."
2. **0:15–0:45. Fan:** elige su club y su jugador, arranca el partido, la cancha y el chat narran con voz y llega un gol con euforia.
3. **0:45–1:10. Analista:** cambia al modo analista, escribe una consulta en lenguaje natural y la cancha dibuja la red de pases y el mapa de tiros.
4. **1:10–1:25. Chat y accesibilidad:** "¿Por qué cambió el partido?", "¿Qué me perdí?" y el modo accesible.
5. **1:25–1:50. Bajo el capó:** diagrama de agentes, Crew Panel, Foundry, Speech, MCP y Container Apps.
6. **1:50–2:00. Cierre:** "Every match, made for every fan."

---

## 8. Checklist final de entrega
- [ ] Registro hecho antes del 20 oct, 12 pm PT
- [ ] Repo **público** con README en inglés (pitch, arquitectura, cómo correrlo, tecnologías de Microsoft usadas)
- [ ] Demo pública en Azure Container Apps + instrucciones de prueba
- [ ] Video en inglés de menos de 2 min en YouTube o Vimeo, sin música con copyright
- [ ] Pitch que mencione Foundry, Agent Service, AI Speech, Container Apps, MCP y GitHub Copilot
- [ ] Solo clubes y jugadores ficticios, sin marcas reales
- [ ] Tests pasando en CI
- [ ] Formulario "Projects" lleno y categoría elegida: **Best Multi-Agent System**

---

## Glosario rápido
- **xG (expected goals):** probabilidad de que un tiro termine en gol (0 a 1).
- **PPDA:** pases que el rival completa antes de que tu equipo intente recuperar el balón. Un número bajo significa que se presiona mucho.
- **Field tilt:** porcentaje de las acciones del partido que ocurren en el último tercio del rival.
- **xT (expected threat):** cuánto aumenta el peligro cuando el balón llega a una zona.
- **SSE (Server-Sent Events):** el servidor empuja datos al navegador en tiempo real por una conexión HTTP.
- **SSML:** XML que le indica a Azure Speech cómo hablar: voz, velocidad, emoción.
- **MCP (Model Context Protocol):** estándar para que un agente de IA use herramientas externas.
- **Grounding:** obligar a la IA a basarse solo en datos reales, sin inventar.
