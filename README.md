# Travelia — Planificador de viajes asistido por IA

Travelia es una plataforma web que ayuda al viajero a planificar su viaje a partir de un **cuestionario dinámico en forma de árbol de decisión**. Un modelo de lenguaje (LLM) genera las preguntas, y con las respuestas se crea un **itinerario completo** (destinos, actividades y clima). Además, el usuario puede controlar sus **gastos**, generar una **lista de equipaje**, exportar el itinerario a **PDF** y pasarse al plan **PREMIUM** pagando con **Wompi**.

| Repositorio | Rol en MVC | URL |
|---|---|---|
| `travelia-backend` (este) | **Controlador + Modelo** | https://github.com/Cristian024/travelia-backend |
| `travelia-frontend` | **Vista** | https://github.com/Cristian024/travelia-frontend |

---

## Tabla de contenido

1. [Stack tecnológico](#1-stack-tecnológico)
2. [Arquitectura de la aplicación (MVC)](#2-arquitectura-de-la-aplicación-mvc)
3. [Patrones de diseño](#3-patrones-de-diseño)
4. [Modelo C4](#4-modelo-c4)
5. [Diagrama de despliegue](#5-diagrama-de-despliegue)
6. [Historias de usuario](#6-historias-de-usuario)
7. [Estructura del repositorio](#7-estructura-del-repositorio)
8. [Ejecución local](#8-ejecución-local)
9. [Resumen de la API](#9-resumen-de-la-api)

---

## 1. Stack tecnológico

| Capa | Tecnologías |
|---|---|
| Vista (frontend) | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui + Radix, React Router, React Query, axios, react-hook-form + zod |
| Controlador (backend) | Python 3.11, FastAPI, Uvicorn, Pydantic v2, python-jose (JWT), passlib/argon2 |
| Modelo (datos) | MongoDB (Motor, async) como base principal · PostgreSQL (asyncpg) como respaldo |
| Inteligencia artificial | Groq, Google Gemini, OpenAI, Anthropic Claude (se puede cambiar de proveedor) |
| Integraciones | OpenWeatherMap (clima), Wompi (pagos, sandbox), wkhtmltopdf + Jinja2 (PDF) |
| Infraestructura | Azure App Service (Linux), GitHub Actions (CI/CD con OIDC), Azure Log Stream |

---

## 2. Arquitectura de la aplicación (MVC)

La solución sigue el patrón **Modelo – Vista – Controlador**, repartido en dos repositorios: la **Vista** es una SPA en React que corre en el navegador, y el **Controlador** y el **Modelo** viven en la API FastAPI. Las capas se comunican por HTTP/JSON con un contrato tipado: `app/schemas/*.py` en el backend y `src/types/api.ts` en el frontend.

![Diagrama de Contenedores](<docs/Diagrama de Contenedores.jpg>)

### 2.1 Mapeo de capas a código

| Capa MVC | Responsabilidad | Dónde está en el código |
|---|---|---|
| **Vista (UI)** | Presentación e interacción con el usuario | `travelia-frontend/src/pages/*` (Login, Register, Profile, Itineraries, ItineraryDetail, NewPlanning, Planning, AdminDashboard) · `src/components/*` (DynamicQuestions, BudgetPanel, PackingListPanel, ReplaceDestinationDialog, SubscriptionPlans, componentes `ui/`) |
| **Controlador (Backend)** | Recibir solicitudes, autenticar, validar, orquestar los casos de uso y devolver la respuesta | `app/api/v1/*.py` (rutas/controladores) · `app/dependencies.py` (inyección y autorización) · `app/services/*.py` (lógica de aplicación) · `app/schemas/*.py` (DTOs de entrada y salida) · `app/core/exceptions.py` (traducción de errores a HTTP) |
| **Modelo (Data)** | Entidades, reglas de dominio y acceso a la persistencia | `app/models/*.py` (entidades) · `app/services/subscription_policy.py` y `app/llm/decision_tree.py` (reglas de dominio) · `app/ports/*.py` (contratos) · `app/repositories/**` (acceso a MongoDB/PostgreSQL) · `app/core/database.py`, `app/core/mongo_database.py` |

### 2.2 Justificación: dónde se ve el MVC

**Vista: solo presenta y delega.** Las páginas de React no tienen reglas de negocio. Muestran datos y envían las acciones del usuario a la API mediante `src/lib/endpoints.ts`:

```tsx
// travelia-frontend/src/pages/ItineraryDetailPage.tsx
const { data, isLoading, isError } = useQuery({
  queryKey: ["itinerary", itineraryId],
  queryFn: () => itinerariesApi.get(itineraryId!),
})
const exportMutation = useMutation({
  mutationFn: () => itinerariesApi.exportPdf(itineraryId!),
  onSuccess: (blob) => { /* descarga el archivo */ },
})
```

**Controlador: recibe la petición, autentica y delega en el caso de uso.** Las rutas son delgadas: ninguna accede a la base de datos (todas importan solo servicios, nunca repositorios):

```python
# app/api/v1/itineraries.py
@router.post("/generate/{planning_id}", response_model=ItineraryResponse, status_code=201)
async def generate_itinerary(
    planning_id: str,
    user_id: CurrentUser,                                              # autenticación (JWT)
    service: Annotated[ItineraryService, Depends(get_itinerary_service)],  # inyección
) -> ItineraryResponse:
    return await service.generate_from_planning(user_id, planning_id)  # delega
```

Los servicios (`app/services/`) forman la parte de **lógica de aplicación** del controlador: coordinan modelo, IA y adaptadores. En `ItineraryService.generate_from_planning()` se consultan los límites del plan, se lee la planificación, se llama al LLM, se guarda el itinerario y se marca la planificación como completada.

**Modelo: entidades, reglas y persistencia.**
- Entidades de dominio en Pydantic: `UserDocument`, `PlanningDocument`, `QuestionTree`/`QuestionTreeNode`, `ItineraryDocument`, `Expense`, `PackingList`, `Order`, `Payment`, `Plan`.
- Reglas de dominio: `SubscriptionPolicy` (límites FREE/PREMIUM: días, destinos, profundidad del árbol, planificaciones por mes) y `DecisionTreeManager` (operaciones sobre el árbol de preguntas).
- Persistencia: repositorios que implementan los puertos de `app/ports/repositories.py`, en versión MongoDB (`app/repositories/mongo/`) y PostgreSQL (`app/repositories/*.py`).

**Separación en la práctica:**
- Las rutas nunca importan repositorios ni conexiones de base de datos.
- Los servicios no conocen HTTP: lanzan excepciones de dominio (`NotFoundError`, `BusinessRuleError`, `ForbiddenError`) y `app/core/exceptions.py` las convierte en códigos HTTP.
- La Vista no conoce la base de datos. Solo maneja los contratos JSON tipados en `src/types/api.ts`.

### 2.3 Flujo MVC completo (ejemplo: generar itinerario)

```
[Vista]  PlanningPage.tsx ── POST /api/v1/itineraries/generate/{id} (axios + JWT) ──►
[Controlador]  itineraries.py → dependencies.py (auth + DI) → ItineraryService
[Modelo]  SubscriptionPolicy.limits_for() → PlanningRepository.find() → LLM → ItineraryRepository.insert()
[Controlador]  ItineraryResponse (DTO) ── JSON 201 ──►
[Vista]  ItineraryDetailPage.tsx muestra destinos, actividades y clima
```

### 2.4 Refinamiento por capas dentro del backend

Dentro del backend, el MVC se divide en capas más finas siguiendo la **arquitectura hexagonal (puertos y adaptadores)**. El Controlador se separa en *rutas + servicios* y el Modelo en *entidades + puertos + repositorios/adaptadores*. Esto no contradice MVC: lo hace más preciso y permite cambiar MongoDB por PostgreSQL, o un proveedor de IA por otro, sin tocar controladores ni vistas.

---

## 3. Patrones de diseño

| # | Patrón | Tipo | Dónde se aplica | Justificación arquitectónica |
|---|---|---|---|---|
| 1 | **MVC** | Arquitectónico | Frontend (Vista) + `app/api` y `app/services` (Controlador) + `app/models` y `app/repositories` (Modelo) | Separa presentación, control y datos. Frontend y backend evolucionan y se despliegan por separado. |
| 2 | **Arquitectura hexagonal (puertos y adaptadores)** | Arquitectónico | `app/ports/` (contratos) y `app/adapters/`, `app/repositories/` (implementaciones) | Los servicios dependen de abstracciones (inversión de dependencias, la D de SOLID), así la infraestructura se puede cambiar sin tocar la lógica de negocio. |
| 3 | **Repository** | Acceso a datos | `UserRepositoryPort`, `ItineraryRepositoryPort`… con versiones `Mongo*Repository` y `*Repository` (SQL) | Aísla la persistencia. Los servicios ignoran si los datos vienen de MongoDB o de PostgreSQL. |
| 4 | **Factory Method / Simple Factory** | Creacional | `app/repositories/factory.py`, `LLMProviderFactory` (`app/llm/factory.py`), `build_logging_adapter()` (`app/adapters/logging_factory.py`) | Centraliza en un único punto la decisión de qué implementación concreta crear. |
| 5 | **Registry** | Creacional | `LLMProviderFactory._registry` + `register()` | Para agregar un proveedor de IA basta con registrarlo, sin modificar otras clases (abierto/cerrado). |
| 6 | **Strategy** | Comportamiento | `LLMProvider` → `AnthropicProvider`, `OpenAIProvider`, `GroqProvider`, `GeminiProvider` · `LoggingAdapterPort` → local / Azure | El algoritmo (qué IA o qué destino de logs se usa) se elige en tiempo de ejecución con una misma interfaz. |
| 7 | **Router / enrutamiento por política** | Comportamiento | `LLMRouter` + `_SUBSCRIPTION_ROUTING` | FREE usa modelos económicos y PREMIUM modelos de mayor razonamiento, según el plan y el tipo de operación (preguntas o itinerario). |
| 8 | **Adapter** | Estructural | `WompiApiClient`, `OpenWeatherMapProvider`, `PdfKitItineraryExporter`, `LocalFileLoggingAdapter`, `AzureLogStreamLoggingAdapter` | Traducen APIs externas a los contratos internos (`PaymentGatewayPort`, `WeatherProviderPort`, etc.). |
| 9 | **Facade** | Estructural | `MongoUserRepository`: unifica las colecciones `clients` y `admins` en un solo `UserDocument` | Oculta que las cuentas se guardan por separado; los servicios ven un único modelo de usuario. |
| 10 | **Decorator / Proxy** | Estructural | `LoggedPool` (`app/core/db_logging.py`) envuelve el pool de `asyncpg` | Añade el registro de las consultas SQL (`LOG_SQL_QUERIES`) sin modificar los repositorios. |
| 11 | **Dependency Injection** | Arquitectónico | `app/dependencies.py` con `Depends()` de FastAPI | Arma los servicios con sus repositorios y adaptadores. Mantiene bajo el acoplamiento y facilita las pruebas. |
| 12 | **Circuit Breaker / Fallback** | Resiliencia | `app/core/backend.py` → `connect_with_fallback()` | Si MongoDB no responde al arrancar, la app pasa automáticamente a PostgreSQL. |
| 13 | **Singleton** | Creacional | `get_settings()` con `@lru_cache` (`app/config.py`) | Una sola instancia de la configuración para toda la aplicación. |
| 14 | **DTO (Data Transfer Object)** | Estructural | `app/schemas/*.py` ↔ `src/types/api.ts` | Contrato explícito entre Vista y Controlador, separado de las entidades internas. |
| 15 | **Composite / Árbol de decisión** | Estructural (estructura de datos no lineal) | `QuestionTree` y `QuestionTreeNode` (`parent_id`, `children_ids`, `depth`), gestionados por `DecisionTreeManager` | Cada nodo es una ronda de preguntas generadas por la IA. El árbol crece según las respuestas, la profundidad máxima depende del plan, y el contexto se arma recorriendo de la raíz al nodo actual. |
| 16 | **Policy / Specification** | Dominio | `SubscriptionPolicy` → `PlanLimits` | Concentra las reglas de negocio FREE/PREMIUM en un solo lugar en vez de repetirlas en cada servicio. |
| 17 | **Template View** | Presentación | `app/templates/itinerary_pdf.html` (Jinja2) | Separa el diseño del PDF de los datos del itinerario. |

**Patrones en la Vista (frontend):**

| Patrón | Dónde | Justificación |
|---|---|---|
| **Provider / Context** | `src/context/AuthContext.tsx` | Comparte la sesión, el usuario y la suscripción con todo el árbol de componentes. |
| **Interceptor** | `src/lib/api.ts` (interceptores de axios) | Agrega el JWT a cada petición y renueva el token de forma transparente ante un 401. |
| **API Gateway del cliente** | `src/lib/endpoints.ts` | Un único punto con todas las llamadas al backend, agrupadas por módulo (`authApi`, `itinerariesApi`…). |
| **Guard / Protected Route** | `ProtectedRoute`, `PublicOnlyRoute`, `AdminProtectedRoute` | Controla el acceso a las rutas según la autenticación y el rol. |
| **Observer (caché reactiva)** | React Query (`useQuery`, `useMutation`) | Los componentes se suscriben a datos del servidor y se vuelven a dibujar cuando cambian. |
| **Composición de componentes** | `src/components/ui/*` (shadcn/Radix) | Componentes reutilizables y accesibles. |

---

## 4. Modelo C4

### 4.1 Nivel 1 — Contexto

![Diagrama de Contexto](<docs/Diagrama de Contexto.jpg>)

Muestra a Travelia como un único sistema y a sus actores:
- **Viajero** (FREE o PREMIUM): planifica viajes, consulta itinerarios y paga la suscripción.
- **Administrador**: gestiona planes, usuarios, órdenes y pagos.
- **Sistemas externos**:
  - **Proveedores LLM** (Groq, Gemini, OpenAI, Anthropic): generan preguntas, itinerarios, equipaje y reemplazos de destino.
  - **OpenWeatherMap**: pronóstico del clima por ciudad.
  - **Wompi**: pasarela de pagos en COP; crea transacciones y notifica por webhook.
  - **Azure App Service**: hosting y Log Stream.

### 4.2 Nivel 2 — Contenedores

![Diagrama de Contenedores](<docs/Diagrama de Contenedores.jpg>)

Descompone el sistema en unidades desplegables:
- **Cliente Travelia (Vista):** la SPA en React del repositorio `travelia-frontend`. Se comunica con la API por REST con Bearer JWT.
- **Travelia API (Controlador):** FastAPI con Uvicorn, expone `/api/v1`.
- **MongoDB (Modelo):** persistencia principal, en las colecciones `clients`, `admins`, `plans`, `plannings`, `itineraries`, `expenses`, `packing_lists`, `orders` y `payments`.
- **PostgreSQL (Modelo):** respaldo automático, con esquema relacional y migraciones SQL (`migrations/`).
- **wkhtmltopdf:** genera el PDF del itinerario.
- **Logs:** archivo rotativo o Azure Log Stream, según `LOG_TARGET`.

### 4.3 Nivel 3 — Componentes (Travelia API)

![Diagrama de Componentes](<docs/Diagrama de Componentes.jpg>)

Muestra la estructura interna de la API:
- **Routers API v1** (controladores): reciben la petición y la pasan a **Dependencies / Seguridad**, que valida el JWT, verifica el rol ADMIN e inyecta los servicios.
- **Servicios:** `AuthService/UserService`, `PlanningService`, `ItineraryService`, `PackingListService`, `ExpenseService`, `SubscriptionService/PlanService/SubscriptionPolicy` y `PaymentService`. Implementan los casos de uso.
- **Módulo LLM:** elige el modelo según la suscripción y gestiona el árbol de decisión.
- **Puertos y Adaptadores externos:** aíslan OpenWeatherMap, Wompi, el PDF y el logging.
- **Repository Factory + Backend selector:** crea los repositorios de MongoDB o PostgreSQL según la base que esté activa.

### 4.4 Nivel 4 — Código

![Diagrama de Código](<docs/Diagrama de Código.jpg>)

Diagramas de clases de los subsistemas clave:
- **Subsistema LLM:** `LLMRouter` usa `LLMProviderFactory`, que crea alguna implementación de `LLMProvider` (Anthropic, OpenAI, Groq o Gemini). `LLMClient` se apoya en ese proveedor para generar preguntas, itinerarios, equipaje y reemplazos. `DecisionTreeManager` maneja el árbol de preguntas (crear raíz, responder nodo, agregar hijos, controlar profundidad, armar el contexto).
- **Persistencia:** cada puerto (`UserRepositoryPort`, `ItineraryRepositoryPort`…) tiene una implementación para MongoDB (que hereda de `MongoBaseRepository`) y otra para PostgreSQL. `repository_factory` consulta a `backend_module` cuál base está activa (`Backend.mongo` o `Backend.postgres`).
- **Puertos externos:** `WeatherProviderPort`, `ItineraryExporterPort`, `PaymentGatewayPort` y `LoggingAdapterPort`, cada uno con su adaptador concreto.
- **Modelo de dominio:** `USER` crea `PLANNING` (que contiene un `QUESTION_TREE` de `QUESTION_NODE`). Una planificación genera un `ITINERARY` con `DESTINATION` y `ACTIVITY`, `EXPENSE` y `PACKING_LIST`. El `PLAN` define la suscripción, y la compra se registra como `ORDER` pagada con `PAYMENT`.

---

## 5. Diagrama de despliegue

### 5.1 Infraestructura de producción

![Diagrama de Despliegue - Producción](<docs/Diagrama de Despliegue - Producción.jpg>)

| Nodo | Entorno | Artefacto | Comunicación |
|---|---|---|---|
| Dispositivo del usuario | Navegador | Cliente Travelia (SPA en React) | HTTPS/JSON con Bearer JWT hacia la API (`*.mexicocentral-01.azurewebsites.net`) |
| GitHub | SaaS | GitHub Actions (`main_travelia.yml`) | Despliega en cada push a `main` usando `azure/login` (OIDC) + `azure/webapps-deploy` |
| Microsoft Azure: App Service **Travelia** | Linux, slot Production, build con Oryx | Runtime Python 3.11 → Uvicorn :8000 → **Travelia API** (`main:app`) + **wkhtmltopdf** | Las App Settings inyectan los secretos (URLs de BD, JWT, claves de IA y de Wompi) |
| Microsoft Azure: Log Stream | Azure | Logs de la aplicación | `LOG_TARGET=azure` (stdout) |
| Hosting de bases de datos | Proveedor externo | MongoDB (principal) y PostgreSQL (respaldo) | TLS mediante `MONGODB_PROD_URL` / `DATABASE_PROD_URL` |
| Servicios externos | Internet | Proveedores LLM, OpenWeatherMap, Wompi Sandbox | HTTPS/SDK. Wompi además llama al webhook `/api/v1/webhooks/wompi` |

El frontend se despliega por separado, con un flujo equivalente desde su propio repositorio (`main_traveliaapp.yml`, Node 24, `vite build`) hacia el App Service **TraveliaApp**.

### 5.2 Pipeline CI/CD

![Diagrama de Despliegue - Pipeline CI/CD](<docs/Diagrama de Despliegue (Pipeline CI_CD).jpg>)

1. **Disparador:** `git push` a `main` (o ejecución manual con `workflow_dispatch`).
2. **Job `build`** (ubuntu-latest): checkout → Python 3.11 → venv + `pip install -r requirements.txt` → sube el artefacto `python-app` (sin `antenv/`).
3. **Job `deploy`:** descarga el artefacto → `azure/login` con OIDC (sin contraseñas guardadas) → `azure/webapps-deploy` al App Service `Travelia`, slot `Production`.
4. **En Azure:** Oryx instala las dependencias (`SCM_DO_BUILD_DURING_DEPLOYMENT=true`, en `.deployment`) y arranca con `uvicorn main:app --host 0.0.0.0 --port 8000`.
5. **Verificación:** `GET /health` responde `{"status": "ok", "version": ...}`.

---

## 6. Historias de usuario

El detalle completo, con criterios de aceptación y mockups, está en **[docs/Historias de Usuario.md](<docs/Historias de Usuario.md>)**.

| ID | Título | Como… | Quiero… | Prioridad |
|---|---|---|---|---|
| HU-01 | Registro y autenticación | Viajero | Registrarme e iniciar sesión de forma segura con correo y contraseña | Alta |
| HU-02 | Cuestionario de preferencias | Usuario que no sabe qué hacer en su viaje | Responder un cuestionario inteligente que adapta las preguntas a mis respuestas | Alta |
| HU-03 | Generar itinerario con IA | Usuario | Que el sistema genere automáticamente un plan de viaje detallado a partir de mis respuestas | Alta |
| HU-04 | Persistencia de sesiones de planificación | Usuario de la plataforma | Que se guarde el progreso de mis respuestas en el cuestionario | Media |
| HU-05 | Administrar y visualizar itinerarios | Viajero en ruta | Consultar mis viajes, ver el detalle por día, editar o eliminar | Media |
| HU-06 | Actualizar perfil de viajero | Viajero autenticado | Actualizar mi nombre, estilo de viaje y moneda preferida | Media |
| HU-07 | Regenerar un plan desde una sesión guardada | Viajero autenticado | Regenerar un plan ajustando los parámetros de una sesión guardada | Media |
| HU-08 | Eliminar un itinerario cancelado | Viajero autenticado | Eliminar un itinerario cuando el viaje se cancela | Baja |
| HU-09 | Cerrar sesión de forma segura | Viajero autenticado | Cerrar mi sesión desde el menú de usuario | Media |
| HU-10 | Consultar el estado de salud del sistema | Administrador | Consultar un endpoint de salud de la API y la base de datos | Baja |

**Trazabilidad HU → código (backend):**

| HU | Endpoints | Servicio |
|---|---|---|
| HU-01 | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `GET /users/me` | `AuthService`, `UserService` |
| HU-02 / HU-04 | `GET /planning/general-questions`, `POST /planning`, `POST /planning/{id}/answer`, `GET /planning/{id}/current-questions`, `GET /planning/{id}/tree` | `PlanningService`, `DecisionTreeManager` |
| HU-03 | `POST /planning/{id}/ready`, `POST /itineraries/generate/{planning_id}` | `ItineraryService` |
| HU-05 | `GET /itineraries`, `GET /itineraries/{id}`, `GET /itineraries/{id}/export/pdf`, gastos y equipaje | `ItineraryService`, `ExpenseService`, `PackingListService` |
| HU-06 | `PATCH /users/me` | `UserService` |
| HU-07 | Reemplazo de destino en `/itineraries/{id}/...` | `ItineraryService` |
| HU-08 | `DELETE /itineraries/{id}` | `ItineraryService` |
| HU-09 | Lado cliente: `AuthContext.logout()` borra los tokens | (frontend) |
| HU-10 | `GET /health` | `main.py` |

---

## 7. Estructura del repositorio

```
travelia-backend/
├── main.py                    # Punto de entrada FastAPI (lifespan, CORS, routers, /health)
├── app/
│   ├── api/v1/                # CONTROLADOR · rutas: auth, users, subscriptions, planning,
│   │                          #   itineraries, expenses, payments, admin, webhooks
│   ├── dependencies.py        # CONTROLADOR · inyección de dependencias + auth JWT/ADMIN
│   ├── services/              # CONTROLADOR · casos de uso / lógica de aplicación
│   ├── schemas/               # DTOs Request/Response (contrato con la Vista)
│   ├── models/                # MODELO · entidades de dominio
│   ├── ports/                 # MODELO · contratos (repositorios y servicios externos)
│   ├── repositories/          # MODELO · persistencia PostgreSQL + factory
│   │   └── mongo/             # MODELO · persistencia MongoDB
│   ├── adapters/              # Adaptadores: Wompi, OpenWeatherMap, PDF, logging
│   ├── llm/                   # Proveedores LLM, factory, router, prompts, árbol de decisión
│   ├── core/                  # Conexiones BD, fallback, seguridad, excepciones
│   ├── templates/             # Plantilla HTML del PDF del itinerario
│   └── config.py              # Configuración (pydantic-settings)
├── migrations/                # Scripts SQL de PostgreSQL
├── queries/                   # Consultas SQL de apoyo
├── docs/                      # Diagramas C4, despliegue e historias de usuario
└── .github/workflows/         # CI/CD hacia Azure App Service
```

---

## 8. Ejecución local

```bash
python -m venv venv
# Windows: venv\Scripts\activate   |   Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- Documentación interactiva: http://localhost:8000/docs (Swagger) y http://localhost:8000/redoc
- Para exportar PDF hay que tener instalado **wkhtmltopdf** (se detecta solo, o se indica con `WKHTMLTOPDF_PATH`).

Variables de entorno (archivo `.env` en la raíz; **nunca** subirlo al repositorio):

| Variable | Descripción |
|---|---|
| `DATABASE_BACKEND` | `mongo` (por defecto) o `postgres` |
| `DATABASE_FALLBACK_ENABLED` | `true` para pasar a la otra base si la principal falla |
| `MONGODB_PROD_URL` / `MONGODB_DEV_URL` | Cadena de conexión de MongoDB |
| `DATABASE_PROD_URL` / `DATABASE_DEV_URL` / `DATABASE_ENV` | Conexión de PostgreSQL y entorno (`prod` o `dev`) |
| `JWT_SECRET_KEY` | Secreto para firmar los JWT |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Claves de los proveedores de IA |
| `OPENWEATHER_API_KEY` | Clave de OpenWeatherMap |
| `WOMPI_PRIVATE_KEY`, `WOMPI_EVENTS_SECRET`, `WOMPI_INTEGRITY_SECRET` | Secretos de Wompi |
| `ADMIN_EMAILS` | Correos que se registran con rol ADMIN |
| `LOG_TARGET` | `local` (archivo `logs/travelia.log`) o `azure` |

Frontend: ver el repositorio [`travelia-frontend`](https://github.com/Cristian024/travelia-frontend) (`npm install && npm run dev`).

---

## 9. Resumen de la API

Prefijo: `/api/v1`. Todas las rutas requieren `Authorization: Bearer <access_token>`, salvo `/auth/*`, `/webhooks/wompi` y `/health`.

| Módulo | Endpoints principales |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh` |
| Usuarios | `GET /users/me`, `PATCH /users/me` |
| Suscripciones | `GET /subscriptions/plans`, `GET /subscriptions/me`, `POST /subscriptions/me` |
| Planificación | `GET /planning/general-questions`, `POST /planning`, `GET /planning/{id}`, `GET /planning/{id}/current-questions`, `POST /planning/{id}/answer`, `POST /planning/{id}/ready`, `GET /planning/{id}/tree` |
| Itinerarios | `POST /itineraries/generate/{planning_id}`, `GET /itineraries`, `GET /itineraries/public`, `GET /itineraries/{id}`, `DELETE /itineraries/{id}`, `POST /itineraries/{id}/clone`, `PATCH /itineraries/{id}/visibility`, `GET /itineraries/{id}/export/pdf`, `GET/POST/PATCH /itineraries/{id}/packing-list`, reemplazo de destino |
| Gastos | `POST/GET /itineraries/{id}/expenses`, resumen, `PATCH/DELETE /expenses/{id}` |
| Pagos | `POST /payments/checkout`, `POST /payments/transactions`, `GET /payments/{reference}` |
| Webhooks | `POST /webhooks/wompi` |
| Admin | `GET/POST/PATCH/DELETE /admin/plans`, `GET /admin/orders`, `GET /admin/payments`, `GET /admin/users`, `PATCH /admin/users/{id}/role` |
| Salud | `GET /health` |
