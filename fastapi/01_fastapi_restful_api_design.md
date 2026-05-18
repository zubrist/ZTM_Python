# Topic 1: FastAPI & RESTful API Design — 50 Interview Questions & Answers

---

## Q1. What happens under the hood when FastAPI receives a request? Walk me through the full lifecycle.

**Interview-Ready Answer:**
When a request hits a FastAPI application, it first enters the ASGI server (Uvicorn), which passes it to Starlette's middleware stack. Starlette resolcts the route via the `APIRouter` trie, then FastAPI's dependency injection system resolves all `Depends()` callables recursively before the path operation function executes. The return value is serialized through the Pydantic response model, validated, and sent back as a JSON response with appropriate status codes and headers.

**Keywords to Mention:** ASGI, Uvicorn, Starlette, dependency injection, Pydantic serialization, middleware stack, request lifecycle.

**Logic Trick:** Think of it as a **funnel**: `Uvicorn → Middleware → Router → Dependencies → Handler → Response Model → Client`. Each layer narrows responsibility.

**Code Reference:**
```python
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Order Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_db_session():
    session = AsyncSession()
    try:
        yield session  # dependency injection with cleanup
    finally:
        await session.close()

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db_session)):
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
```

---

## Q2. Explain the difference between `Depends()` with a generator function vs. a regular callable. When would you use each?

**Interview-Ready Answer:**
A regular callable dependency runs and returns a value — it's fire-and-forget. A generator dependency (using `yield`) allows setup-and-teardown semantics: code before `yield` runs before the handler, the yielded value is injected, and code after `yield` runs after the response is sent. This is critical for resource management like database sessions or file handles where cleanup is mandatory.

**Keywords to Mention:** Generator dependency, context manager pattern, teardown logic, resource lifecycle, `yield` vs `return`.

**Logic Trick:** `yield` = **"I'll lend you this resource, but I want it back."** `return` = **"Here, keep it."**

**Code Reference:**
```python
# Generator dependency — has cleanup
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()  # guaranteed cleanup even on exception

# Regular callable — no cleanup
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    return decode_jwt(token)  # simple transform, no resource to release
```

---

## Q3. How does FastAPI's dependency injection differ from Flask's approach? Why is it superior for microservices?

**Interview-Ready Answer:**
Flask relies on application context globals (`g`, `current_app`) and decorators for dependency management, which creates implicit coupling and makes testing harder. FastAPI's `Depends()` system is explicit, hierarchical, and composable — dependencies can depend on other dependencies, forming a DAG that is resolved automatically. This makes unit testing trivial because you can override any dependency with `app.dependency_overrides`, and it naturally supports async dependencies for non-blocking I/O in microservice architectures.

**Keywords to Mention:** Dependency DAG, `dependency_overrides`, explicit vs implicit coupling, composability, testability, async-first.

**Logic Trick:** Flask = **global bulletin board** (anyone can read/write). FastAPI = **personal delivery** (each handler gets exactly what it asked for).

**Code Reference:**
```python
# Composable dependency chain
async def get_settings() -> Settings:
    return Settings()

async def get_db(settings: Settings = Depends(get_settings)) -> AsyncSession:
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        yield session

async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

# Testing override — zero code change in handler
def test_create_user(client):
    app.dependency_overrides[get_db] = lambda: FakeDB()
    response = client.post("/users", json={"name": "test"})
    assert response.status_code == 201
```

---

## Q4. You have an endpoint that must accept both JSON and form data. How do you design it in FastAPI?

**Interview-Ready Answer:**
FastAPI distinguishes between `Body` (JSON) and `Form` (URL-encoded/multipart) at the parameter level, and you cannot mix them in the same endpoint signature because HTTP content types are mutually exclusive per request. The clean solution is to create two separate endpoints or use a middleware/dependency that inspects the `Content-Type` header and parses accordingly. For real-world APIs, I'd create a dependency that returns a unified Pydantic model regardless of input format.

**Keywords to Mention:** Content-Type negotiation, `Body`, `Form`, `File`, multipart, URL-encoded, single responsibility.

**Logic Trick:** Think of a **mailbox** — it accepts letters (JSON) or packages (form/multipart), but the carrier must declare which type it is on the label.

**Code Reference:**
```python
from fastapi import FastAPI, Form, Body, Request, Depends
from pydantic import BaseModel

class UserCreate(BaseModel):
    name: str
    email: str

async def parse_user(request: Request) -> UserCreate:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    elif "form" in content_type:
        form = await request.form()
        data = dict(form)
    else:
        raise HTTPException(400, "Unsupported Content-Type")
    return UserCreate(**data)

@app.post("/users", status_code=201)
async def create_user(user: UserCreate = Depends(parse_user)):
    return {"created": user.name}
```

---

## Q5. What are the practical differences between `status_code=200` and `status_code=201` in a POST endpoint, and why do interviewers care?

**Interview-Ready Answer:**
`200 OK` means the request succeeded generically, while `201 Created` semantically signals that a new resource was created and typically includes a `Location` header pointing to it. Interviewers care because proper HTTP semantics enable client-side caching, CDN behavior, and API gateway routing decisions. Using `201` also shows you understand RESTful maturity levels — a Level 2 REST API uses HTTP verbs and status codes correctly.

**Keywords to Mention:** HTTP semantics, Richardson Maturity Model, `Location` header, idempotency, REST Level 2.

**Logic Trick:** **201 = "I built something new for you."** 200 = "Done, nothing special."

**Code Reference:**
```python
from fastapi import FastAPI, Response

@app.post("/orders", status_code=201)
async def create_order(order: OrderCreate, response: Response):
    new_order = await order_service.create(order)
    response.headers["Location"] = f"/orders/{new_order.id}"
    return new_order
```

---

## Q6. How would you implement API versioning in FastAPI? Compare URL-based, header-based, and query-param approaches.

**Interview-Ready Answer:**
URL-based versioning (`/api/v1/users`) is the most common and easiest to implement with FastAPI's `APIRouter(prefix="/v1")`. Header-based versioning (`Accept: application/vnd.myapi.v2+json`) is cleaner from a REST-purist perspective but harder to test in browsers. Query-param versioning (`?version=2`) is the least desirable because it pollutes the query namespace. For microservices, I prefer URL-based because API gateways (Kong, Istio) can route based on path prefixes without custom logic.

**Keywords to Mention:** APIRouter prefix, content negotiation, API gateway routing, backward compatibility, semantic versioning.

**Logic Trick:** URL = **street address** (easy to find). Header = **secret handshake** (powerful but hidden). Query param = **sticky note on the door** (fragile).

**Code Reference:**
```python
from fastapi import APIRouter, FastAPI

app = FastAPI()

v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

@v1_router.get("/users")
async def get_users_v1():
    return {"version": 1, "users": [...]}

@v2_router.get("/users")
async def get_users_v2():
    return {"version": 2, "users": [...], "pagination": {...}}

app.include_router(v1_router)
app.include_router(v2_router)
```

---

## Q7. Explain how Pydantic V2 validators work. What's the difference between `@field_validator` and `@model_validator`?

**Interview-Ready Answer:**
`@field_validator` validates a single field in isolation — it receives the raw value and returns the cleaned value. `@model_validator` validates the entire model, useful when validation logic spans multiple fields (e.g., "end_date must be after start_date"). In Pydantic V2, `@model_validator(mode='before')` runs before field parsing (receives raw dict), while `mode='after'` runs after all fields are validated (receives the model instance). This two-phase approach lets you handle both raw-input normalization and cross-field business rules.

**Keywords to Mention:** `@field_validator`, `@model_validator`, `mode='before'`, `mode='after'`, cross-field validation, Pydantic V2.

**Logic Trick:** `field_validator` = **spell-check one word.** `model_validator` = **proofread the whole paragraph.**

**Code Reference:**
```python
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime
    label: str

    @field_validator("label")
    @classmethod
    def label_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Label cannot be blank")
        return v.strip().title()

    @model_validator(mode="after")
    def end_after_start(self) -> "DateRange":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self
```

---

## Q8. How do you handle partial updates (PATCH) with Pydantic in FastAPI? What pitfall do most developers fall into?

**Interview-Ready Answer:**
The standard approach is to make all fields `Optional` in the update schema and use `model.model_dump(exclude_unset=True)` to get only the fields the client actually sent. The common pitfall is using `exclude_none=True` instead, which makes it impossible for a client to intentionally set a field to `null`. By using `exclude_unset`, you distinguish between "client didn't send this field" and "client explicitly sent `null`".

**Keywords to Mention:** `exclude_unset`, `exclude_none`, partial update, PATCH semantics, `Optional` fields, merge strategy.

**Logic Trick:** `exclude_unset` = **"What did the client say?"** `exclude_none` = **"What isn't empty?"** — They sound similar but serve very different purposes.

**Code Reference:**
```python
from pydantic import BaseModel
from typing import Optional

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None  # client might want to SET this to None

@app.patch("/users/{user_id}")
async def update_user(user_id: int, payload: UserUpdate):
    update_data = payload.model_dump(exclude_unset=True)
    # If client sends {"bio": null} → update_data = {"bio": None} ✓
    # If client sends {"name": "Bob"} → update_data = {"name": "Bob"} ✓
    # bio is NOT in update_data — it stays unchanged in DB
    await user_repo.update(user_id, **update_data)
    return {"updated_fields": list(update_data.keys())}
```

---

## Q9. What is the purpose of `response_model_exclude_unset` in FastAPI, and when is it dangerous?

**Interview-Ready Answer:**
`response_model_exclude_unset=True` omits fields from the JSON response that were never explicitly set on the model instance. This is useful for sparse responses where you don't want to flood the client with `null` values. However, it's dangerous when clients depend on a consistent schema — frontend developers might expect every field to be present, and missing keys can cause `undefined` errors in JavaScript. In API contracts with OpenAPI specs, it can also create a mismatch between documented and actual response shapes.

**Keywords to Mention:** Response serialization, schema consistency, OpenAPI contract, sparse response, frontend compatibility.

**Logic Trick:** It's like a **restaurant menu** — `exclude_unset` hides dishes that aren't available today, but regular customers expect the full menu.

**Code Reference:**
```python
@app.get(
    "/users/{user_id}",
    response_model=UserResponse,
    response_model_exclude_unset=True,  # careful!
)
async def get_user(user_id: int):
    user = await repo.get(user_id)
    return user  # fields never set on this instance will be omitted from JSON
```

---

## Q10. How do you implement request/response logging middleware in FastAPI without breaking streaming responses?

**Interview-Ready Answer:**
You implement a pure ASGI middleware or use Starlette's `BaseHTTPMiddleware`, but `BaseHTTPMiddleware` has a known issue — it buffers the entire response body, which breaks `StreamingResponse` and SSE. The proper approach for production is a raw ASGI middleware that wraps the `send` callable to intercept response chunks without buffering. You log the request path, method, status code, and latency, but you must be careful not to log sensitive body content (PII, tokens).

**Keywords to Mention:** ASGI middleware, `BaseHTTPMiddleware` limitations, `StreamingResponse`, PII filtering, structured logging.

**Logic Trick:** `BaseHTTPMiddleware` = **reading the whole letter before delivering it** (slow, breaks streaming). Raw ASGI = **peeking at the envelope** (fast, non-intrusive).

**Code Reference:**
```python
import time
import logging
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("api.access")

class AccessLogMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 0

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "method=%s path=%s status=%d duration=%.2fms",
            scope["method"], scope["path"], status_code, duration_ms,
        )

app.add_middleware(AccessLogMiddleware)  # doesn't break streaming
```

---

## Q11. How would you rate-limit a FastAPI endpoint? Compare middleware-level vs dependency-level approaches.

**Interview-Ready Answer:**
Middleware-level rate limiting applies globally and is good for blanket protection (e.g., 1000 req/min per IP). Dependency-level rate limiting using `Depends()` is more granular — you can apply different limits to different endpoints or user tiers. In production microservices, I'd prefer an API gateway (Kong, Istio) for rate limiting, but if it must be in-app, a Redis-backed sliding window dependency is the most accurate approach. In-memory solutions like token bucket fail in multi-replica deployments because state isn't shared.

**Keywords to Mention:** Sliding window, token bucket, Redis-backed, API gateway offloading, per-user vs per-IP, multi-replica state.

**Logic Trick:** Rate limiting in a single pod = **putting a lock on one door of a building with 10 doors**. Redis = **central security desk** checking everyone.

**Code Reference:**
```python
import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request

redis_client = redis.from_url("redis://localhost:6379")

async def rate_limit(request: Request, limit: int = 100, window: int = 60):
    key = f"rate:{request.client.host}:{request.url.path}"
    current = await redis_client.incr(key)
    if current == 1:
        await redis_client.expire(key, window)
    if current > limit:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(window)},
        )

@app.get("/api/data", dependencies=[Depends(rate_limit)])
async def get_data():
    return {"data": "ok"}
```

---

## Q12. What's the difference between `HTTPException` and a custom exception handler? When do you choose one over the other?

**Interview-Ready Answer:**
`HTTPException` is a quick inline way to abort a request with a status code and detail message — good for simple cases. Custom exception handlers via `@app.exception_handler(MyError)` let you catch domain-specific exceptions thrown deep in your service layer and map them to HTTP responses at the boundary. This follows the principle that your business logic shouldn't know about HTTP — it raises `OrderNotFoundError`, and the handler translates it to a 404. This separation keeps service code reusable across HTTP, gRPC, and message bus consumers.

**Keywords to Mention:** Separation of concerns, domain exceptions, hexagonal architecture, error boundary, protocol-agnostic service layer.

**Logic Trick:** `HTTPException` = **yelling "STOP" in the hallway.** Custom handler = **receptionist who translates internal memos into public announcements.**

**Code Reference:**
```python
# Domain exception — knows nothing about HTTP
class OrderNotFoundError(Exception):
    def __init__(self, order_id: int):
        self.order_id = order_id

# Handler at the boundary — translates domain → HTTP
@app.exception_handler(OrderNotFoundError)
async def order_not_found_handler(request: Request, exc: OrderNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "ORDER_NOT_FOUND",
            "detail": f"Order {exc.order_id} does not exist",
            "docs": "/api/docs#orders",
        },
    )

# Service layer — clean, no HTTP knowledge
class OrderService:
    async def get_order(self, order_id: int) -> Order:
        order = await self.repo.find(order_id)
        if not order:
            raise OrderNotFoundError(order_id)  # not HTTPException!
        return order
```

---

## Q13. How do you structure a large FastAPI project? Monolithic `main.py` vs routers vs sub-applications?

**Interview-Ready Answer:**
For production microservices, I use a layered structure: `routers/` for HTTP interface, `services/` for business logic, `repositories/` for data access, and `schemas/` for Pydantic models. Each domain (orders, users, payments) gets its own `APIRouter` with a dedicated prefix and tag. Sub-applications (`app.mount`) are reserved for truly independent modules like an admin panel or a health-check service with separate middleware stacks. The key is that routers should be thin — they validate input, call a service, and format output.

**Keywords to Mention:** Layered architecture, thin controllers, separation of concerns, `APIRouter`, domain-driven structure, `app.mount`.

**Logic Trick:** **Routers are waiters** (take orders, deliver food). **Services are chefs** (do the actual cooking). Never let the waiter cook.

**Code Reference:**
```
project/
├── app/
│   ├── main.py              # FastAPI() + include_router + startup events
│   ├── config.py             # Settings with pydantic-settings
│   ├── routers/
│   │   ├── orders.py         # APIRouter(prefix="/orders", tags=["Orders"])
│   │   └── users.py
│   ├── services/
│   │   ├── order_service.py  # business logic, raises domain exceptions
│   │   └── user_service.py
│   ├── repositories/
│   │   ├── order_repo.py     # DB queries only
│   │   └── user_repo.py
│   ├── schemas/
│   │   ├── order.py          # OrderCreate, OrderResponse, OrderUpdate
│   │   └── user.py
│   ├── models/
│   │   └── order.py          # SQLAlchemy ORM models
│   └── middleware/
│       └── logging.py
├── tests/
├── Dockerfile
├── helm/
└── pyproject.toml
```

---

## Q14. Explain `BackgroundTasks` in FastAPI. What are its limitations compared to Celery?

**Interview-Ready Answer:**
`BackgroundTasks` runs functions after the response is sent, within the same process — ideal for lightweight work like sending emails or writing audit logs. However, it has critical limitations: tasks are lost if the process crashes (no persistence), they can't be distributed across workers, there's no retry mechanism, and they share the event loop so CPU-heavy tasks block other requests. For anything requiring reliability, retries, or horizontal scaling, you need Celery with a broker (Redis/RabbitMQ) or a Kafka consumer.

**Keywords to Mention:** In-process execution, no persistence, no retry, event loop blocking, task queue comparison, at-most-once delivery.

**Logic Trick:** `BackgroundTasks` = **asking your coworker "hey, do this after lunch"** (informal, might forget). Celery = **filing a work order** (tracked, retryable, assigned to available workers).

**Code Reference:**
```python
from fastapi import BackgroundTasks

async def send_welcome_email(email: str):
    # lightweight, non-critical — OK for BackgroundTasks
    await email_client.send(to=email, template="welcome")

@app.post("/users", status_code=201)
async def create_user(user: UserCreate, bg: BackgroundTasks):
    new_user = await user_service.create(user)
    bg.add_task(send_welcome_email, new_user.email)  # fire-and-forget
    return new_user  # response sent immediately
```

---

## Q15. How do you implement health checks in FastAPI for Kubernetes readiness and liveness probes?

**Interview-Ready Answer:**
Liveness probes check if the process is alive (not deadlocked) — a simple `200 OK` endpoint suffices. Readiness probes check if the service can handle traffic — this should verify downstream dependencies like database connectivity and Kafka broker availability. I separate them into `/health/live` and `/health/ready` because a service might be alive but not ready during startup or when a dependency is down. Kubernetes uses liveness to restart pods and readiness to remove them from the Service load balancer.

**Keywords to Mention:** Liveness vs readiness, downstream dependency check, pod restart vs traffic removal, graceful degradation, startup probe.

**Logic Trick:** **Liveness = "Are you breathing?"** **Readiness = "Can you work today?"** A sick person is alive but not ready for work.

**Code Reference:**
```python
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

health_router = APIRouter(prefix="/health", tags=["Health"])

@health_router.get("/live", status_code=200)
async def liveness():
    return {"status": "alive"}

@health_router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "fail"

    try:
        kafka_healthy = await kafka_producer.health_check()
        checks["kafka"] = "ok" if kafka_healthy else "fail"
    except Exception:
        checks["kafka"] = "fail"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
    )
```

---

## Q16. What is the OpenAPI schema in FastAPI, and how do you customize it for production?

**Interview-Ready Answer:**
FastAPI auto-generates an OpenAPI 3.1 schema from your route signatures, Pydantic models, and docstrings. For production, I customize it by setting `title`, `version`, `description`, and `servers` on the `FastAPI()` instance. I also hide internal endpoints from docs using `include_in_schema=False`, group endpoints with `tags_metadata`, and add security schemes for OAuth2/API key. The generated schema at `/openapi.json` drives Swagger UI, ReDoc, and can be exported for client SDK generation.

**Keywords to Mention:** OpenAPI 3.1, auto-generated schema, `include_in_schema`, tags metadata, client SDK generation, Swagger/ReDoc.

**Logic Trick:** OpenAPI = **the blueprint of your building** — anyone can read it to understand the structure without entering.

**Code Reference:**
```python
from fastapi import FastAPI

tags_metadata = [
    {"name": "Orders", "description": "CRUD operations on orders"},
    {"name": "Health", "description": "Kubernetes probes", "externalDocs": {
        "description": "K8s docs", "url": "https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/"
    }},
]

app = FastAPI(
    title="Order Service API",
    version="2.3.1",
    description="Microservice for order management",
    openapi_tags=tags_metadata,
    docs_url="/api/docs",        # custom Swagger path
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    servers=[
        {"url": "https://api.prod.example.com", "description": "Production"},
        {"url": "https://api.staging.example.com", "description": "Staging"},
    ],
)

# Internal endpoint hidden from public docs
@app.get("/internal/metrics", include_in_schema=False)
async def metrics():
    return get_prometheus_metrics()
```

---

## Q17. How does FastAPI handle query parameters with complex types like lists and enums?

**Interview-Ready Answer:**
FastAPI uses Pydantic's type coercion for query parameters. For lists, you define `Query()` with the type `list[str]` and clients send repeated keys (`?tag=python&tag=fastapi`). For enums, you define a `str, Enum` class and FastAPI validates the value against allowed members, returning a 422 if invalid. Advanced patterns include using `Annotated` types (Python 3.10+) to attach metadata like `min_length`, `regex`, and `description` directly to the type hint, keeping function signatures clean.

**Keywords to Mention:** `Query()`, `Annotated`, `Enum` validation, type coercion, 422 Validation Error, OpenAPI query parameter documentation.

**Logic Trick:** `Annotated[str, Query(min_length=1)]` = **a labeled box** — the type says what goes in, the annotation says the rules.

**Code Reference:**
```python
from enum import Enum
from typing import Annotated
from fastapi import Query

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

@app.get("/products")
async def list_products(
    tags: Annotated[list[str], Query(description="Filter by tags")] = [],
    sort: SortOrder = SortOrder.ASC,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    size: Annotated[int, Query(ge=10, le=100)] = 20,
):
    # GET /products?tags=electronics&tags=sale&sort=desc&page=2&size=50
    return await product_service.search(tags=tags, sort=sort, page=page, size=size)
```

---

## Q18. What is `Annotated` in Python 3.10+ and why does FastAPI encourage it over default parameter syntax?

**Interview-Ready Answer:**
`Annotated` from `typing` lets you attach metadata to a type hint without changing the default value semantics. Before `Annotated`, FastAPI overloaded default values (`name: str = Query(...)`) which confused linters and made the actual default unclear. With `Annotated[str, Query(min_length=1)]`, the metadata is on the type and the default value stays clean. This also enables reusability — you can define `UserId = Annotated[int, Path(gt=0)]` once and reuse it across all endpoints.

**Keywords to Mention:** PEP 593, `Annotated`, type metadata, reusable type aliases, cleaner function signatures, linter compatibility.

**Logic Trick:** Old way = **writing instructions on the gift itself.** Annotated = **attaching a tag to the gift** — cleaner, reusable.

**Code Reference:**
```python
from typing import Annotated
from fastapi import Path, Query, Header

# Reusable annotated types
UserId = Annotated[int, Path(gt=0, description="User ID")]
PageSize = Annotated[int, Query(ge=1, le=100, description="Items per page")]
AuthToken = Annotated[str, Header(alias="X-Auth-Token")]

@app.get("/users/{user_id}/orders")
async def get_user_orders(
    user_id: UserId,
    page_size: PageSize = 20,
    token: AuthToken = ...,
):
    ...  # clean, reusable, linter-friendly
```

---

## Q19. How do you implement pagination in a RESTful API? Compare offset-based vs cursor-based.

**Interview-Ready Answer:**
Offset-based pagination (`?page=3&size=20` → `OFFSET 40 LIMIT 20`) is simple but has two problems: performance degrades on large offsets because the DB must scan and discard rows, and results shift when items are inserted/deleted between pages. Cursor-based pagination (`?after=eyJpZCI6MTAwfQ`) uses an opaque token encoding the last seen item, making queries efficient (`WHERE id > 100 LIMIT 20`) and stable against insertions. For public APIs, I return pagination metadata including `next_cursor`, `has_more`, and `total_count` (optional, expensive).

**Keywords to Mention:** Offset vs cursor, keyset pagination, result stability, O(n) offset scan, opaque cursor token, `has_more`.

**Logic Trick:** Offset = **"skip to page 50 of a book"** (must flip through 49 pages). Cursor = **"bookmark where I stopped"** (instant resume).

**Code Reference:**
```python
import base64
import json
from pydantic import BaseModel

class PaginatedResponse(BaseModel):
    items: list[dict]
    next_cursor: str | None
    has_more: bool

def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"id": last_id}).encode()).decode()

def decode_cursor(cursor: str) -> int:
    return json.loads(base64.urlsafe_b64decode(cursor))["id"]

@app.get("/orders", response_model=PaginatedResponse)
async def list_orders(
    after: str | None = None,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    min_id = decode_cursor(after) if after else 0
    orders = await repo.find_after(min_id, limit=size + 1)  # fetch one extra
    has_more = len(orders) > size
    items = orders[:size]
    return PaginatedResponse(
        items=items,
        next_cursor=encode_cursor(items[-1]["id"]) if has_more else None,
        has_more=has_more,
    )
```

---

## Q20. How do you secure a FastAPI endpoint with OAuth2 + JWT? Walk through the flow.

**Interview-Ready Answer:**
The flow is: client sends credentials to `/token`, the server validates them and returns a signed JWT with claims (sub, exp, scopes). On subsequent requests, the client sends `Authorization: Bearer <token>`. FastAPI's `OAuth2PasswordBearer` extracts the token, a dependency decodes and validates it (checking signature, expiry, and audience), and returns the current user. I use `python-jose` or `PyJWT` for token operations and store secrets in environment variables, never in code. Scopes enable fine-grained permissions per endpoint.

**Keywords to Mention:** JWT, `OAuth2PasswordBearer`, token signing (HS256/RS256), claims validation, scope-based authorization, `python-jose`.

**Logic Trick:** JWT = **a stamped wristband at a concert** — it proves you paid (authentication) and shows your access level (VIP/general = scopes).

**Code Reference:**
```python
from fastapi import Depends, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import jwt, JWTError
from datetime import datetime, timedelta

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",
    scopes={"orders:read": "Read orders", "orders:write": "Create orders"},
)

SECRET_KEY = "loaded-from-env"  # in reality: os.environ["JWT_SECRET"]
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=1)):
    payload = {**data, "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_scopes = payload.get("scopes", [])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    return await user_repo.get(user_id)

@app.get("/orders", dependencies=[Security(get_current_user, scopes=["orders:read"])])
async def list_orders():
    ...
```

---

## Q21. What is idempotency in REST APIs, and how do you implement it for POST endpoints?

**Interview-Ready Answer:**
Idempotency means that making the same request multiple times produces the same result as making it once. GET, PUT, and DELETE are naturally idempotent, but POST is not — retrying a failed POST can create duplicate resources. The standard solution is an **idempotency key**: the client generates a UUID and sends it in a header (`Idempotency-Key`). The server stores the key with its response in Redis/DB; on duplicate requests, it returns the cached response instead of re-executing. This is critical in payment systems where double-charging is unacceptable.

**Keywords to Mention:** Idempotency key, `Idempotency-Key` header, duplicate prevention, at-least-once delivery, Redis cache, payment safety.

**Logic Trick:** Idempotency = **pressing an elevator button** — pressing it 5 times doesn't call 5 elevators.

**Code Reference:**
```python
import hashlib
from fastapi import Header, HTTPException

@app.post("/payments", status_code=201)
async def create_payment(
    payment: PaymentCreate,
    idempotency_key: Annotated[str, Header()],
    redis: Redis = Depends(get_redis),
):
    cache_key = f"idempotency:{idempotency_key}"

    # Check if we've seen this key before
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)  # return previous response

    # Process the payment
    result = await payment_service.charge(payment)

    # Cache the result for 24 hours
    await redis.setex(cache_key, 86400, json.dumps(result.dict()))
    return result
```

---

## Q22. What is HATEOAS, and should you implement it in a microservice API?

**Interview-Ready Answer:**
HATEOAS (Hypermedia as the Engine of Application State) means responses include links to related actions and resources, making the API self-discoverable. For example, an order response includes links to `cancel`, `pay`, and `track`. While it's the highest level of REST maturity (Level 3), most microservice APIs skip it because machine-to-machine clients already know the API contract, and it adds payload bloat. I'd implement it only for public-facing APIs consumed by third-party developers who benefit from discoverability.

**Keywords to Mention:** Richardson Maturity Model Level 3, hypermedia links, self-discoverable API, payload overhead, machine-to-machine vs public APIs.

**Logic Trick:** HATEOAS = **a "choose your adventure" book** — each page tells you where you can go next. Most backend services already have the map.

**Code Reference:**
```python
from pydantic import BaseModel

class OrderResponse(BaseModel):
    id: int
    status: str
    total: float
    links: dict[str, str]

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int):
    order = await order_service.get(order_id)
    links = {"self": f"/orders/{order_id}"}
    if order.status == "pending":
        links["cancel"] = f"/orders/{order_id}/cancel"
        links["pay"] = f"/orders/{order_id}/pay"
    if order.status == "shipped":
        links["track"] = f"/orders/{order_id}/tracking"
    return OrderResponse(**order.dict(), links=links)
```

---

## Q23. How does FastAPI handle file uploads? What's the difference between `UploadFile` and `bytes`?

**Interview-Ready Answer:**
`bytes` reads the entire file into memory — suitable only for tiny files. `UploadFile` wraps a `SpooledTemporaryFile` that stays on disk after a threshold (default 1MB), giving you an async file-like interface with `.read()`, `.seek()`, and `.filename`. For large files, you stream chunks instead of reading all at once. In production, I never store uploads on local disk — I stream them directly to object storage (S3/GCS) using presigned URLs or a chunked upload dependency.

**Keywords to Mention:** `SpooledTemporaryFile`, streaming upload, memory pressure, presigned URLs, object storage, chunk size.

**Logic Trick:** `bytes` = **drinking the whole glass at once** (small glass only). `UploadFile` = **sipping through a straw** (works for any size).

**Code Reference:**
```python
from fastapi import UploadFile, File
import aiofiles

@app.post("/uploads")
async def upload_file(file: UploadFile = File(..., max_size=50_000_000)):  # 50MB
    # Stream to S3 in chunks instead of reading all into memory
    s3_key = f"uploads/{file.filename}"
    async with s3_client.create_multipart_upload(Bucket="my-bucket", Key=s3_key) as mpu:
        chunk_num = 1
        while chunk := await file.read(5 * 1024 * 1024):  # 5MB chunks
            await mpu.upload_part(Body=chunk, PartNumber=chunk_num)
            chunk_num += 1

    return {"filename": file.filename, "s3_key": s3_key, "content_type": file.content_type}
```

---

## Q24. How do you implement WebSocket endpoints in FastAPI? What are the gotchas?

**Interview-Ready Answer:**
FastAPI supports WebSockets via `@app.websocket("/ws")` using Starlette's WebSocket class. The gotchas are: (1) WebSocket connections don't go through the normal middleware stack, so auth must be handled in the handshake or first message; (2) each connection holds a long-lived coroutine, so you need to manage connection lifecycle carefully; (3) Kubernetes ingress and load balancers need sticky sessions or proper upgrade header forwarding; (4) `Depends()` works differently — generator dependencies run teardown when the connection closes, not per-message.

**Keywords to Mention:** WebSocket handshake, connection manager pattern, sticky sessions, upgrade header, heartbeat/ping-pong, graceful disconnection.

**Logic Trick:** HTTP = **sending letters** (one question, one answer). WebSocket = **phone call** (ongoing conversation, must handle hangups).

**Code Reference:**
```python
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field

@dataclass
class ConnectionManager:
    active: dict[int, WebSocket] = field(default_factory=dict)

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws

    def disconnect(self, user_id: int):
        self.active.pop(user_id, None)

    async def send_to(self, user_id: int, message: dict):
        if ws := self.active.get(user_id):
            await ws.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await process_message(user_id, data)
    except WebSocketDisconnect:
        manager.disconnect(user_id)
```

---

## Q25. What are FastAPI's `startup` and `shutdown` lifespan events? How have they changed in recent versions?

**Interview-Ready Answer:**
Previously, FastAPI used `@app.on_event("startup")` and `@app.on_event("shutdown")` decorators, but these are deprecated in favor of the `lifespan` context manager pattern. The new approach uses an async generator passed to `FastAPI(lifespan=lifespan)` where code before `yield` runs on startup and code after runs on shutdown. This is better because it guarantees cleanup (via the generator protocol) and allows sharing state (like a DB pool) between startup and shutdown via the yielded value, avoiding global variables.

**Keywords to Mention:** Lifespan context manager, `@asynccontextmanager`, deprecated `on_event`, resource cleanup guarantee, shared state.

**Logic Trick:** Old events = **two separate alarm clocks** (wake up, go to bed) — disconnected. Lifespan = **your whole daily routine** in one place — open the office, work, close the office.

**Code Reference:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize resources
    app.state.db_pool = await create_pool(settings.database_url)
    app.state.kafka_producer = await create_kafka_producer()
    print("🚀 Service started")

    yield  # Application runs here

    # Shutdown: cleanup resources
    await app.state.kafka_producer.flush()
    await app.state.db_pool.close()
    print("🛑 Service stopped")

app = FastAPI(lifespan=lifespan)
```

---

## Q26. How do you implement request validation beyond Pydantic — for example, checking that a referenced foreign key exists?

**Interview-Ready Answer:**
Pydantic validates data shape and types, but business validation (like "does this user_id exist in the database?") belongs in the service layer or in a FastAPI dependency. I create a dependency that takes the path/body parameter, queries the database, and either returns the validated entity or raises an `HTTPException(404)`. This avoids polluting Pydantic models with database logic and keeps validation composable and testable.

**Keywords to Mention:** Business validation vs schema validation, dependency-based validation, separation of concerns, database lookup dependency, composable validators.

**Logic Trick:** Pydantic = **customs checking your passport format is valid.** Dependency = **immigration checking if you're actually allowed in the country.**

**Code Reference:**
```python
async def valid_order(
    order_id: Annotated[int, Path(gt=0)],
    db: AsyncSession = Depends(get_db),
) -> Order:
    """Dependency that validates order exists and returns it."""
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(404, f"Order {order_id} not found")
    return order

@app.put("/orders/{order_id}/cancel")
async def cancel_order(order: Order = Depends(valid_order)):
    # `order` is guaranteed to exist — no need to check again
    await order_service.cancel(order)
    return {"status": "cancelled"}
```

---

## Q27. How do you return different response models based on the outcome (e.g., success vs error)?

**Interview-Ready Answer:**
FastAPI's `response_model` defines the success shape, but for error cases you use the `responses` parameter to document alternative schemas in OpenAPI. The actual error responses come from exception handlers returning `JSONResponse`. I define a standard `ErrorResponse` model used across all services for consistency. The `responses` parameter is documentation-only — it doesn't enforce validation on error responses, so you must ensure your exception handlers conform to the schema manually or through tests.

**Keywords to Mention:** `responses` parameter, multi-schema documentation, `JSONResponse`, standard error envelope, OpenAPI documentation, consistent error format.

**Logic Trick:** `response_model` = **the happy path receipt.** `responses` = **the "what could go wrong" section of the manual.**

**Code Reference:**
```python
class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None

@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Order not found"},
        403: {"model": ErrorResponse, "description": "Access denied"},
        500: {"model": ErrorResponse, "description": "Internal error"},
    },
)
async def get_order(order_id: int):
    ...
```

---

## Q28. What is the `Depends` cache behavior, and how do you share a dependency result within a single request?

**Interview-Ready Answer:**
By default, FastAPI caches dependency results per request — if multiple parameters depend on the same function, it's called only once and the result is shared. This is crucial for things like database sessions, where you want a single session per request, not multiple. You can disable caching with `Depends(get_db, use_cache=False)` if you need fresh results. Understanding this prevents bugs like accidentally creating multiple DB transactions per request.

**Keywords to Mention:** Dependency caching, per-request scope, `use_cache=False`, shared session, dependency DAG resolution.

**Logic Trick:** Default `Depends` = **one shared pizza for the table** (everyone gets from the same one). `use_cache=False` = **everyone orders their own pizza.**

**Code Reference:**
```python
async def get_db():
    session = AsyncSession()
    try:
        yield session
    finally:
        await session.close()

# Both user_repo and order_repo get the SAME session (cached)
async def get_user_repo(db: AsyncSession = Depends(get_db)):
    return UserRepository(db)

async def get_order_repo(db: AsyncSession = Depends(get_db)):
    return OrderRepository(db)

@app.post("/checkout")
async def checkout(
    user_repo: UserRepository = Depends(get_user_repo),
    order_repo: OrderRepository = Depends(get_order_repo),
):
    # user_repo.db is order_repo.db — same session, same transaction
    ...
```

---

## Q29. How do you serve static files or a single-page application (SPA) alongside a FastAPI backend?

**Interview-Ready Answer:**
FastAPI inherits Starlette's `StaticFiles` mount for serving CSS/JS/images. For an SPA, you mount static files at a path and add a catch-all route that serves `index.html` for unmatched paths, enabling client-side routing. However, in production microservices, static assets should be served by a CDN or Nginx reverse proxy — the Python ASGI server should focus on API requests. Mixing static serving with API handling wastes Uvicorn workers on I/O that Nginx handles orders of magnitude better.

**Keywords to Mention:** `StaticFiles`, CDN offloading, Nginx reverse proxy, SPA catch-all route, separation of concerns.

**Logic Trick:** **Don't use a chef to deliver pizzas** — let Nginx/CDN handle static files, let FastAPI handle logic.

**Code Reference:**
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="static"), name="static")

# SPA catch-all — must be LAST route
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("static/index.html")
```

---

## Q30. How do you implement request/response compression in FastAPI?

**Interview-Ready Answer:**
FastAPI supports GZip compression via `GZipMiddleware` from Starlette. You set a `minimum_size` threshold (e.g., 500 bytes) so small responses aren't compressed (the overhead would make them larger). The middleware checks the `Accept-Encoding` header and compresses only if the client supports gzip. In production, compression is typically handled by the reverse proxy (Nginx, Envoy, API gateway) to offload CPU from the application server, but the middleware is useful for direct-to-client setups.

**Keywords to Mention:** `GZipMiddleware`, `Accept-Encoding`, minimum size threshold, reverse proxy offloading, CPU tradeoff.

**Logic Trick:** Compression = **vacuum-sealing your luggage** — saves space but takes effort. Don't vacuum-seal a single sock.

**Code Reference:**
```python
from starlette.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=500)  # bytes

# Responses larger than 500 bytes will be gzipped
# if client sends Accept-Encoding: gzip
```

---

## Q31. How do you handle CORS in FastAPI, and what's the security risk of `allow_origins=["*"]`?

**Interview-Ready Answer:**
CORS middleware (`CORSMiddleware`) adds the appropriate `Access-Control-Allow-*` headers to responses. Using `allow_origins=["*"]` means any website can make authenticated requests to your API, which is a security risk if you're using cookies or ambient credentials — an attacker's site could make API calls on behalf of a logged-in user. In production, I whitelist specific origins and never use `allow_credentials=True` with `allow_origins=["*"]` (Starlette actually blocks this combination). For microservice-to-microservice calls, CORS is irrelevant — it's a browser-only security mechanism.

**Keywords to Mention:** Same-origin policy, preflight OPTIONS request, `Access-Control-Allow-Origin`, CSRF risk, credential-bearing requests, browser-only mechanism.

**Logic Trick:** CORS = **a nightclub bouncer checking your invitation** — `*` means no bouncer (anyone gets in with your VIP badge).

**Code Reference:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com", "https://admin.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["X-Request-Id", "X-RateLimit-Remaining"],
    max_age=3600,  # preflight cache duration
)
```

---

## Q32. How do you inject configuration/settings into FastAPI using `pydantic-settings`?

**Interview-Ready Answer:**
`pydantic-settings` (formerly part of Pydantic V1) provides a `BaseSettings` class that reads from environment variables, `.env` files, and secrets directories. I create a `Settings` class with typed fields and use `@lru_cache` to ensure it's instantiated only once. This is injected as a dependency via `Depends(get_settings)`. The `model_config` attribute lets you set the `.env` file path, prefix for env vars (e.g., `APP_`), and case sensitivity. This is the 12-Factor App way of handling configuration.

**Keywords to Mention:** 12-Factor App, `BaseSettings`, environment variables, `.env` file, `@lru_cache` singleton, secrets directory, `model_config`.

**Logic Trick:** `BaseSettings` = **a smart form that auto-fills from your environment** — you define what you need, it finds the values.

**Code Reference:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        case_sensitive=False,
    )

    database_url: str
    kafka_brokers: str = "localhost:9092"
    jwt_secret: str
    debug: bool = False
    log_level: str = "INFO"
    max_connections: int = 20

@lru_cache
def get_settings() -> Settings:
    return Settings()

@app.get("/debug/config")
async def show_config(settings: Settings = Depends(get_settings)):
    return {"debug": settings.debug, "log_level": settings.log_level}
```

---

## Q33. What is the difference between `Path`, `Query`, `Body`, `Header`, `Cookie`, and `Form` in FastAPI?

**Interview-Ready Answer:**
Each corresponds to a different part of an HTTP request: `Path` extracts from URL path segments (`/users/{id}`), `Query` from the query string (`?page=2`), `Header` from HTTP headers, `Cookie` from cookies, `Body` from the JSON request body, and `Form` from URL-encoded or multipart form data. FastAPI infers the source automatically: path params from the route, Pydantic models from the body, and simple types from query parameters. Explicit declarations (`Query()`, `Header()`) let you add validation, aliases, and descriptions. Understanding this mapping is essential for correct OpenAPI documentation.

**Keywords to Mention:** HTTP request anatomy, automatic source inference, explicit declaration, validation metadata, OpenAPI parameter location (`in: query`, `in: header`).

**Logic Trick:** Think of an HTTP request as a **letter**: `Path` = address on envelope, `Query` = sticky note on envelope, `Header` = postal metadata, `Cookie` = return address sticker, `Body` = the letter content, `Form` = a filled-out form enclosed.

**Code Reference:**
```python
from fastapi import Path, Query, Body, Header, Cookie

@app.put("/users/{user_id}")
async def update_user(
    user_id: Annotated[int, Path(gt=0)],                    # from URL
    include_orders: Annotated[bool, Query()] = False,        # from ?include_orders=true
    user_data: UserUpdate = Body(...),                       # from JSON body
    x_request_id: Annotated[str, Header()],                  # from X-Request-Id header
    session_token: Annotated[str | None, Cookie()] = None,   # from cookie
):
    ...
```

---

## Q34. How do you implement API key authentication in FastAPI?

**Interview-Ready Answer:**
For simple machine-to-machine auth, I use an API key dependency that checks a header (`X-API-Key`) against stored keys. FastAPI's `APIKeyHeader` security scheme integrates with OpenAPI docs, showing the auth requirement in Swagger UI. In production, keys are stored hashed in a database (not plaintext), rotated periodically, and scoped to specific endpoints or rate limits. For multi-tenant systems, the API key maps to a tenant ID that's injected into every downstream query.

**Keywords to Mention:** `APIKeyHeader`, hashed key storage, key rotation, tenant isolation, OpenAPI security scheme, machine-to-machine auth.

**Logic Trick:** API key = **building access card** — simple, effective, but if someone copies it, they get full access. JWT = **fingerprint scanner** — harder to forge.

**Code Reference:**
```python
from fastapi.security import APIKeyHeader
from fastapi import Security, HTTPException

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    hashed = hashlib.sha256(api_key.encode()).hexdigest()
    tenant = await db.execute(
        select(Tenant).where(Tenant.api_key_hash == hashed, Tenant.active == True)
    )
    tenant = tenant.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return tenant

@app.get("/data", dependencies=[Security(verify_api_key)])
async def get_data():
    ...
```

---

## Q35. What is structured logging, and how do you implement it in FastAPI?

**Interview-Ready Answer:**
Structured logging outputs log entries as JSON objects instead of flat strings, making them queryable by log aggregation tools (ELK, Loki, Datadog). Each log entry includes standard fields like `timestamp`, `level`, `request_id`, `service_name`, and contextual fields like `user_id` and `order_id`. In FastAPI, I use `structlog` or `python-json-logger` with middleware that sets a correlation ID (from `X-Request-Id` or auto-generated UUID) in contextvars, making it available to all log calls within that request's scope.

**Keywords to Mention:** `structlog`, JSON logging, correlation ID, `contextvars`, log aggregation, ELK/Loki, request tracing.

**Logic Trick:** Flat logs = **a pile of sticky notes.** Structured logs = **a spreadsheet** — searchable, filterable, sortable.

**Code Reference:**
```python
import structlog
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
)
logger = structlog.get_logger()

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    req_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    request_id_var.set(req_id)
    structlog.contextvars.bind_contextvars(request_id=req_id)
    response = await call_next(request)
    response.headers["X-Request-Id"] = req_id
    return response

# Anywhere in code:
logger.info("order_created", order_id=123, total=99.99)
# Output: {"event":"order_created","order_id":123,"total":99.99,"request_id":"abc-123","timestamp":"...","level":"info"}
```

---

## Q36. How do you test FastAPI endpoints? Explain `TestClient` vs `httpx.AsyncClient`.

**Interview-Ready Answer:**
`TestClient` (from Starlette) is synchronous — it wraps the ASGI app and runs requests in a thread, which is fine for simple tests. `httpx.AsyncClient` with `ASGITransport` is truly async, which is required when your tests involve async fixtures, async database setup, or when you need to test WebSocket and streaming behavior accurately. I prefer `httpx.AsyncClient` in pytest with `pytest-asyncio` because it tests the actual async code path, catching issues that `TestClient`'s thread-wrapping might mask.

**Keywords to Mention:** `TestClient`, `httpx.AsyncClient`, `ASGITransport`, `pytest-asyncio`, async test path, `dependency_overrides`.

**Logic Trick:** `TestClient` = **driving a car simulator** (close to real but not identical). `AsyncClient` = **driving the actual car on a test track** (real engine, controlled environment).

**Code Reference:**
```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    app.dependency_overrides[get_db] = lambda: FakeDB()
    response = await client.post(
        "/orders",
        json={"product_id": 1, "quantity": 3},
    )
    assert response.status_code == 201
    assert response.json()["quantity"] == 3
    app.dependency_overrides.clear()
```

---

## Q37. What are FastAPI "sub-dependencies" and how deep can the dependency tree go?

**Interview-Ready Answer:**
Sub-dependencies are dependencies that themselves have dependencies — forming a directed acyclic graph (DAG). For example, `get_order_service` depends on `get_order_repo`, which depends on `get_db`, which depends on `get_settings`. FastAPI resolves this DAG automatically, handling caching and teardown in the correct order (LIFO for generators). There's no hard limit on depth, but deep chains (>4-5 levels) often indicate over-engineering. The DAG must be acyclic — circular dependencies will cause a `RecursionError`.

**Keywords to Mention:** Dependency DAG, recursive resolution, LIFO teardown, circular dependency detection, composability, depth trade-offs.

**Logic Trick:** Dependencies are like **Russian nesting dolls** — each one opens to reveal the next, and you close them in reverse order.

**Code Reference:**
```python
# Level 0: Configuration
def get_settings() -> Settings:
    return Settings()

# Level 1: Infrastructure
async def get_db(settings: Settings = Depends(get_settings)):
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as session:
        yield session

# Level 2: Repository
async def get_order_repo(db: AsyncSession = Depends(get_db)):
    return OrderRepository(db)

# Level 3: Service
async def get_order_service(
    repo: OrderRepository = Depends(get_order_repo),
    kafka: KafkaProducer = Depends(get_kafka_producer),
):
    return OrderService(repo, kafka)

# Level 4: Handler — receives fully constructed service
@app.post("/orders")
async def create_order(
    order: OrderCreate,
    service: OrderService = Depends(get_order_service),
):
    return await service.create(order)
```

---

## Q38. How do you handle long-running requests in FastAPI without timing out?

**Interview-Ready Answer:**
For truly long-running operations, never hold the HTTP connection open — return a `202 Accepted` with a task ID immediately, process async (via Celery, Kafka, or BackgroundTasks), and let the client poll a status endpoint. For moderately long requests, increase Uvicorn's `--timeout-keep-alive` and configure your reverse proxy/load balancer timeout. If the client needs real-time progress, use WebSockets or Server-Sent Events (SSE) via `StreamingResponse`. The key principle is that HTTP request handlers should return fast — under 30 seconds as a rule.

**Keywords to Mention:** `202 Accepted`, async task pattern, polling endpoint, SSE, `StreamingResponse`, timeout configuration, task queue.

**Logic Trick:** Long-running request = **ordering furniture** — the store says "we'll deliver it, here's your tracking number" (202 + polling), they don't make you stand in the store waiting.

**Code Reference:**
```python
import uuid
from fastapi import BackgroundTasks
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

task_store: dict[str, dict] = {}

async def generate_report(task_id: str, params: dict):
    task_store[task_id]["status"] = TaskStatus.PROCESSING
    try:
        result = await heavy_computation(params)  # takes 5 minutes
        task_store[task_id] = {"status": TaskStatus.COMPLETED, "result_url": result}
    except Exception as e:
        task_store[task_id] = {"status": TaskStatus.FAILED, "error": str(e)}

@app.post("/reports", status_code=202)
async def request_report(params: ReportParams, bg: BackgroundTasks):
    task_id = str(uuid.uuid4())
    task_store[task_id] = {"status": TaskStatus.PENDING}
    bg.add_task(generate_report, task_id, params.dict())
    return {"task_id": task_id, "status_url": f"/reports/status/{task_id}"}

@app.get("/reports/status/{task_id}")
async def check_status(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task
```

---

## Q39. How do you implement request throttling per authenticated user (not just per IP)?

**Interview-Ready Answer:**
Per-user throttling requires identifying the user first (via JWT/API key), then using their user ID as the rate limit key instead of IP. I implement this as a composable dependency chain: `get_current_user` → `check_user_rate_limit`. The rate limit configuration can be tier-based (free users: 100/min, pro: 1000/min) stored in a `plans` table. Redis sorted sets with timestamp scores implement a precise sliding window, and the dependency injects remaining quota info into response headers (`X-RateLimit-Remaining`).

**Keywords to Mention:** User-based key, tiered rate limits, sliding window (sorted set), `X-RateLimit-*` headers, composable dependencies, Redis ZRANGEBYSCORE.

**Logic Trick:** IP-based = **counting how many letters come from one post office.** User-based = **counting how many letters one person sends** (regardless of which post office).

**Code Reference:**
```python
import time
from fastapi import Depends, HTTPException, Response

async def check_user_rate_limit(
    user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    response: Response = ...,
):
    now = time.time()
    window = 60  # seconds
    limit = user.plan.rate_limit  # e.g., 100 for free, 1000 for pro
    key = f"ratelimit:user:{user.id}"

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)  # remove old entries
    pipe.zadd(key, {str(now): now})               # add current request
    pipe.zcard(key)                                 # count in window
    pipe.expire(key, window)
    _, _, count, _ = await pipe.execute()

    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))

    if count > limit:
        raise HTTPException(429, "Rate limit exceeded")
```

---

## Q40. What are `APIRoute` classes, and when would you create a custom one?

**Interview-Ready Answer:**
`APIRoute` is the class FastAPI uses internally to wrap each endpoint. You can subclass it to intercept request/response processing at the route level (more granular than middleware). Common use cases include: adding request body logging for specific routes, implementing route-level timing metrics, or transforming request/response formats. Unlike middleware which applies globally, custom `APIRoute` applies only to routers that use it, giving you targeted control.

**Keywords to Mention:** `APIRoute` subclass, route-level interception, granular middleware, `get_route_handler`, targeted processing.

**Logic Trick:** Middleware = **TSA security for the whole airport.** Custom `APIRoute` = **VIP security for one gate** — same idea, targeted scope.

**Code Reference:**
```python
from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute
import time

class TimedRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def timed_handler(request: Request) -> Response:
            start = time.perf_counter()
            response = await original(request)
            duration = time.perf_counter() - start
            response.headers["X-Response-Time"] = f"{duration:.4f}s"
            return response

        return timed_handler

# Only this router gets timing headers
timed_router = APIRouter(route_class=TimedRoute)

@timed_router.get("/heavy-endpoint")
async def heavy():
    await asyncio.sleep(1)
    return {"status": "done"}
```

---

## Q41. What are the implications of running FastAPI with multiple Uvicorn workers?

**Interview-Ready Answer:**
Multiple Uvicorn workers (`--workers 4`) spawn separate processes, each with its own memory space. This means in-memory caches, global variables, and connection pools are NOT shared between workers. WebSocket connection managers that store connections in a dict will only work within one worker — clients might reconnect to a different worker and lose state. Solutions include external state stores (Redis for cache, Redis Pub/Sub for WebSocket fan-out) and sticky sessions at the load balancer. The number of workers should typically match CPU cores for CPU-bound work, but for async I/O-bound FastAPI apps, fewer workers with more async concurrency is often better.

**Keywords to Mention:** Process isolation, shared-nothing architecture, Redis for shared state, sticky sessions, worker count sizing, pre-fork model.

**Logic Trick:** Multiple workers = **separate kitchens in the same restaurant** — each chef has their own ingredients (memory). They need a shared fridge (Redis) to coordinate.

**Code Reference:**
```python
# ❌ BROKEN with multiple workers — state is per-process
connections: dict[int, WebSocket] = {}  # only visible in one worker

# ✅ CORRECT — use Redis Pub/Sub for cross-worker communication
import redis.asyncio as redis

async def broadcast(channel: str, message: str):
    r = redis.from_url("redis://localhost")
    await r.publish(channel, message)

# Uvicorn command:
# uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
# Or use Gunicorn with Uvicorn workers:
# gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## Q42. How do you implement content negotiation (returning JSON vs XML vs CSV)?

**Interview-Ready Answer:**
Content negotiation uses the `Accept` header — the client specifies what formats it can handle, and the server picks the best match. In FastAPI, I implement this with a dependency that reads the `Accept` header and a custom response factory. For JSON it's default, for CSV I use `StreamingResponse` with `text/csv`, for XML I use `lxml` serialization. The `Vary: Accept` response header tells caches that the response changes based on this header. Most microservice APIs only support JSON, but data export endpoints often need CSV.

**Keywords to Mention:** `Accept` header, `Vary` header, `StreamingResponse`, content type, cache variation, MIME types.

**Logic Trick:** Content negotiation = **a multilingual menu** — the customer says "I speak French" (Accept header), the waiter brings the French menu.

**Code Reference:**
```python
import csv
import io
from fastapi import Header
from fastapi.responses import StreamingResponse, JSONResponse

@app.get("/orders/export")
async def export_orders(
    accept: Annotated[str, Header()] = "application/json",
):
    orders = await order_repo.get_all()

    match accept:
        case "text/csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=["id", "total", "status"])
            writer.writeheader()
            writer.writerows([o.dict() for o in orders])
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=orders.csv"},
            )
        case "application/json" | _:
            return JSONResponse([o.dict() for o in orders])
```

---

## Q43. How do you implement circuit breaker pattern for downstream API calls in FastAPI?

**Interview-Ready Answer:**
A circuit breaker prevents cascading failures by stopping requests to a failing downstream service. It has three states: **Closed** (normal), **Open** (all requests fail fast without calling downstream), and **Half-Open** (allows a few test requests to check recovery). I implement it using `aiobreaker` or `tenacity` with state tracking in Redis (for multi-pod consistency). The breaker trips after N consecutive failures, stays open for a cooldown period, then transitions to half-open. This protects your service from hanging on timeouts to a dead dependency.

**Keywords to Mention:** Circuit breaker states (closed/open/half-open), cascading failure prevention, fail-fast, cooldown period, `aiobreaker`, bulkhead pattern.

**Logic Trick:** Circuit breaker = **an electrical fuse** — when too much current flows (errors), it trips to prevent a fire (cascading failure). You manually reset it (half-open) to test if the problem is fixed.

**Code Reference:**
```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class BreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: int = 30
    state: BreakerState = BreakerState.CLOSED
    failure_count: int = 0
    last_failure: datetime | None = None

    async def call(self, func, *args, **kwargs):
        match self.state:
            case BreakerState.OPEN:
                if datetime.utcnow() - self.last_failure > timedelta(seconds=self.recovery_timeout):
                    self.state = BreakerState.HALF_OPEN
                else:
                    raise HTTPException(503, "Service unavailable (circuit open)")
            case BreakerState.HALF_OPEN | BreakerState.CLOSED:
                pass

        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0
            self.state = BreakerState.CLOSED
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure = datetime.utcnow()
            if self.failure_count >= self.failure_threshold:
                self.state = BreakerState.OPEN
            raise

payment_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

@app.post("/checkout")
async def checkout(order: OrderCreate):
    return await payment_breaker.call(payment_client.charge, order)
```

---

## Q44. What's the difference between synchronous and asynchronous route handlers in FastAPI?

**Interview-Ready Answer:**
When you define `async def`, FastAPI runs the function directly on the asyncio event loop — ideal for I/O-bound operations with `await`. When you define `def` (non-async), FastAPI runs it in a thread pool (`anyio.to_thread.run_sync`) to prevent blocking the event loop. The gotcha is that a `def` handler holds a thread, and the default thread pool size is limited (40 threads in anyio). Using `async def` but calling blocking code (like synchronous database drivers) without `await` is the worst of both worlds — it blocks the event loop for ALL concurrent requests.

**Keywords to Mention:** Event loop, thread pool executor, `anyio.to_thread`, blocking vs non-blocking, thread pool exhaustion, sync driver pitfall.

**Logic Trick:** `async def` = **you're a juggler** (keep multiple balls in the air). `def` = **you're a worker in a booth** (one task at a time, booth is limited). `async def` with blocking calls = **a juggler who freezes** (drops all balls).

**Code Reference:**
```python
# ✅ Async handler — runs on event loop, uses async DB driver
@app.get("/orders")
async def get_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order))  # non-blocking
    return result.scalars().all()

# ✅ Sync handler — runs in thread pool, safe for blocking I/O
@app.get("/legacy-report")
def get_report():
    # Uses synchronous library — FastAPI puts this in a thread
    data = requests.get("https://legacy-api.example.com/data")
    return data.json()

# ❌ BROKEN — blocks the event loop!
@app.get("/bad")
async def bad_handler():
    data = requests.get("https://slow-api.com")  # BLOCKING in async context!
    return data.json()
```

---

## Q45. How do you implement Server-Sent Events (SSE) in FastAPI?

**Interview-Ready Answer:**
SSE uses `StreamingResponse` with `text/event-stream` media type. The handler yields formatted events (`data: ...\n\n`) through an async generator. Unlike WebSockets, SSE is unidirectional (server→client), uses regular HTTP (no upgrade), and auto-reconnects via the browser's `EventSource` API. SSE is ideal for live dashboards, log tailing, and progress updates. The gotcha is that each SSE connection holds an open coroutine, so you need to handle client disconnection (`asyncio.CancelledError`) to avoid resource leaks.

**Keywords to Mention:** `StreamingResponse`, `text/event-stream`, unidirectional, auto-reconnect, `EventSource`, `Last-Event-ID`, resource cleanup.

**Logic Trick:** WebSocket = **phone call** (two-way). SSE = **radio broadcast** (one-way, listener tunes in/out freely).

**Code Reference:**
```python
import asyncio
from fastapi.responses import StreamingResponse

async def event_generator(order_id: int):
    try:
        while True:
            status = await order_repo.get_status(order_id)
            yield f"event: status_update\ndata: {json.dumps({'status': status})}\n\n"
            if status in ("delivered", "cancelled"):
                yield f"event: done\ndata: {json.dumps({'final': True})}\n\n"
                break
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        # Client disconnected — clean up
        pass

@app.get("/orders/{order_id}/stream")
async def stream_order_status(order_id: int):
    return StreamingResponse(
        event_generator(order_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

---

## Q46. How do you handle database migrations with Alembic in a FastAPI project?

**Interview-Ready Answer:**
Alembic manages incremental schema migrations using versioned Python scripts. I configure it to use the same `DATABASE_URL` from `pydantic-settings` and auto-generate migrations by comparing SQLAlchemy models against the current DB state (`alembic revision --autogenerate`). In CI/CD, migrations run as an init container in Kubernetes before the application starts, ensuring the schema is ready. Critical practices include: always reviewing auto-generated migrations (they miss some changes), running migrations in transactions, and having a rollback plan (`alembic downgrade -1`).

**Keywords to Mention:** Alembic, auto-generate, version chain, init container, transactional DDL, rollback, `env.py` configuration.

**Logic Trick:** Alembic = **a Git for your database schema** — each migration is a commit, you can revert, and everyone stays in sync.

**Code Reference:**
```python
# alembic/env.py — using pydantic-settings for config
from app.config import get_settings
from app.models import Base

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata

# In Kubernetes — init container runs migration
# Dockerfile:
# CMD ["alembic", "upgrade", "head"]

# helm/templates/deployment.yaml:
# initContainers:
#   - name: migrate
#     image: {{ .Values.image.repository }}
#     command: ["alembic", "upgrade", "head"]
#     envFrom:
#       - secretRef:
#           name: {{ .Values.secretName }}
```

---

## Q47. What is the `Request` object in FastAPI, and when do you access it directly?

**Interview-Ready Answer:**
The `Request` object (from Starlette) gives you raw access to everything: headers, cookies, client IP, URL, path params, query string, and the raw body stream. You access it directly when FastAPI's parameter extraction isn't sufficient — for example, reading the raw body for webhook signature verification (where you need the exact bytes before any parsing), accessing unusual headers, or implementing custom authentication schemes. For normal endpoints, you should prefer FastAPI's typed parameters over raw `Request` access because you lose automatic validation and documentation.

**Keywords to Mention:** `starlette.requests.Request`, raw body access, webhook signatures, client IP, `request.state`, escape hatch.

**Logic Trick:** Typed parameters = **reading a pre-sorted mailbox** (organized, labeled). `Request` = **digging through the mail bag yourself** (full control, but you sort it).

**Code Reference:**
```python
from fastapi import Request
import hmac, hashlib

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    # Must read raw body for signature verification
    raw_body = await request.body()
    signature = request.headers.get("Stripe-Signature")

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(400, "Invalid signature")

    event = json.loads(raw_body)
    await process_stripe_event(event)
    return {"received": True}
```

---

## Q48. How do you implement multi-tenancy in a FastAPI microservice?

**Interview-Ready Answer:**
Multi-tenancy can be implemented at three levels: **database-level** (separate DB per tenant — strongest isolation), **schema-level** (same DB, separate schemas — good balance), or **row-level** (same tables, filtered by `tenant_id` — most efficient). In FastAPI, I inject the tenant context through a dependency that extracts the tenant from the JWT or API key, then passes it to the repository layer which automatically adds `WHERE tenant_id = :tid` to all queries. This uses SQLAlchemy's `execution_options` or a custom session that scopes queries automatically.

**Keywords to Mention:** Row-level security, tenant isolation, `execution_options`, automatic query scoping, data leakage prevention, tenant context dependency.

**Logic Trick:** Row-level = **shared office with locked filing cabinets.** Schema-level = **separate floors.** Database-level = **separate buildings.**

**Code Reference:**
```python
from contextvars import ContextVar

tenant_ctx: ContextVar[int] = ContextVar("tenant_id")

async def get_tenant(
    user: User = Depends(get_current_user),
) -> int:
    tenant_ctx.set(user.tenant_id)
    return user.tenant_id

class TenantScopedRepository:
    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    async def get_all(self) -> list[Order]:
        result = await self.db.execute(
            select(Order).where(Order.tenant_id == self.tenant_id)
        )
        return result.scalars().all()

    async def create(self, data: OrderCreate) -> Order:
        order = Order(**data.dict(), tenant_id=self.tenant_id)  # auto-scope
        self.db.add(order)
        await self.db.commit()
        return order

@app.get("/orders")
async def list_orders(
    tenant_id: int = Depends(get_tenant),
    db: AsyncSession = Depends(get_db),
):
    repo = TenantScopedRepository(db, tenant_id)
    return await repo.get_all()  # guaranteed tenant-isolated
```

---

## Q49. What are `response_class` options in FastAPI, and when do you customize them?

**Interview-Ready Answer:**
FastAPI defaults to `JSONResponse`, but you can override per-endpoint with `response_class`. Options include `HTMLResponse` for template rendering, `PlainTextResponse` for raw text, `RedirectResponse` for 3xx redirects, `StreamingResponse` for large files or SSE, `FileResponse` for serving files, and `ORJSONResponse`/`UJSONResponse` for faster JSON serialization. `ORJSONResponse` is a common production optimization — `orjson` serializes 2-10x faster than the stdlib `json` module, which matters at high throughput.

**Keywords to Mention:** `ORJSONResponse`, `StreamingResponse`, `FileResponse`, serialization performance, `response_class`, `orjson`, content type.

**Logic Trick:** `response_class` = **choosing the envelope type** — regular letter (JSON), package (FileResponse), postcard (PlainText), or redirect slip (RedirectResponse).

**Code Reference:**
```python
from fastapi.responses import ORJSONResponse, StreamingResponse, RedirectResponse

# Global default — faster JSON for all endpoints
app = FastAPI(default_response_class=ORJSONResponse)

# Per-endpoint override
@app.get("/large-dataset", response_class=ORJSONResponse)
async def get_large_dataset():
    data = await repo.get_million_rows()  # orjson handles this 5x faster
    return data

@app.get("/go-to-docs")
async def redirect_to_docs():
    return RedirectResponse(url="/api/docs")

@app.get("/download/{file_id}")
async def download_file(file_id: str):
    file_path = f"/storage/{file_id}"
    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=f"{file_id}.pdf",
    )
```

---

## Q50. You're designing a new microservice from scratch with FastAPI. Walk me through your architectural decisions.

**Interview-Ready Answer:**
First, I define the API contract (OpenAPI spec) before writing code — contract-first design ensures frontend and other services can develop in parallel. I use **layered architecture**: routers (thin HTTP layer), services (business logic), repositories (data access), and schemas (Pydantic models). Configuration uses `pydantic-settings` for 12-Factor compliance. I choose async SQLAlchemy + asyncpg for PostgreSQL, and `confluent-kafka` for event publishing. The health endpoints are ready for Kubernetes probes from day one. Structured logging with correlation IDs is non-negotiable. I containerize with a multi-stage Dockerfile, deploy with Helm, and set up Prometheus metrics and GitLab CI from the first commit. The key principle is: **production readiness is not an afterthought — it's built in from the start.**

**Keywords to Mention:** Contract-first design, layered architecture, 12-Factor App, async drivers, health probes, structured logging, multi-stage Docker, Helm chart, Prometheus, CI/CD from day one.

**Logic Trick:** Building a microservice = **building a house**: foundation (config, logging, health checks) → structure (layers, DI) → plumbing (DB, Kafka) → electricity (metrics, CI/CD) → furnishing (business logic). Never start with the furniture.

**Code Reference:**
```python
# The skeleton — everything production-ready from commit #1
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import get_settings
from app.routers import orders, health
from app.middleware.logging import AccessLogMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.db = await init_db(settings.database_url)
    app.state.kafka = await init_kafka(settings.kafka_brokers)
    yield
    await app.state.kafka.flush()
    await app.state.db.dispose()

app = FastAPI(
    title="Order Service",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

# Middleware
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=get_settings().allowed_origins)

# Metrics
Instrumentator().instrument(app).expose(app, include_in_schema=False)

# Routes
app.include_router(health.router)
app.include_router(orders.router, prefix="/api/v1")
```

---

> **End of Topic 1: FastAPI & RESTful API Design — 50/50 Questions Complete**
>
> Say **"Continue"** for **Topic 2: Asynchronous Programming (asyncio & tenacity)**.


## Q51. The Role of Starlette in FastAPI

**Interview-Ready Answer:**
FastAPI is built **on top of Starlette**, a lightweight ASGI framework. Starlette handles the HTTP protocol, routing, middleware stack, request/response objects, and exception handling. FastAPI adds OpenAPI/Swagger schema generation, automatic request validation via Pydantic, dependency injection, and convenience decorators. In short: **Starlette = the transport layer (ASGI, HTTP, routing), FastAPI = developer ergonomics and API documentation.** You can call Starlette's components directly (e.g., `Request`, `Response` objects) and add Starlette middleware. Most of FastAPI's core — `@app.get()`, `@app.post()`, `@app.middleware()` — is inherited from or delegated to Starlette. This is why FastAPI is so lightweight; it doesn't reinvent the wheel, it just makes Starlette easier to use for building APIs.

**Keywords to Mention:** Starlette, ASGI, transport layer, middleware stack, `Request`/`Response`, HTTP routing, built-on-top-of, Pydantic validation, OpenAPI schema generation.

**Logic Trick:** **FastAPI : Starlette = Express : Node.js**. Node.js is the runtime; Express adds convenience. Starlette is the ASGI framework; FastAPI adds OpenAPI + validation sugar.

**Code Reference:**
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

app = FastAPI()

# Access Starlette's Request object directly
@app.get("/raw-request")
async def get_raw_request(request: Request):
    # Starlette's Request object — raw ASGI power
    return {
        "method": request.method,
        "headers": dict(request.headers),
        "scope": request.scope,  # Raw ASGI scope dict
    }

# Use Starlette's exception handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "path": request.url.path},
    )

# Add Starlette middleware directly
class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time
        start = time.time()
        response = await call_next(request)
        response.headers["X-Process-Time"] = str(time.time() - start)
        return response

app.add_middleware(TimingMiddleware)

# **Interview Answer:** FastAPI is built ON TOP of Starlette (ASGI framework).
# Starlette handles: routing, middleware, Request/Response objects, HTTP protocol.
# FastAPI adds: Pydantic validation, OpenAPI schema generation, dependency injection.
# You can access Starlette's components directly (Request, custom middleware, exception handlers).
# In short: Starlette = transport layer; FastAPI = developer ergonomics + documentation magic.
# FastAPI leverages Starlette's battle-tested foundation and adds a thin convenience layer
# for rapid, production-ready API development. FastAPI == Starlette + Pydantic + OpenAPI.
```

---

## **PUT vs PATCH: The Critical Difference**

### **Interview-Ready Answer:**

**PUT** replaces the **entire resource** — you send the complete updated object, and the server replaces the old one completely. Missing fields are either set to `null` or cause a 400 error. **PATCH** updates **specific fields only** — you send only the fields you want to change, and the server merges them with the existing resource. Missing fields are left untouched.

**Idempotency:** PUT is idempotent — calling it 10 times with the same body produces the same result as calling it once. PATCH is NOT idempotent unless explicitly designed that way — because partial updates can have side effects.

**Real-world analogy:** 
- **PUT** = "Replace my entire profile. Here's the complete new version."
- **PATCH** = "Just change my email address. Leave everything else alone."

**Keywords to Mention:** Full replacement vs partial update, idempotency, missing fields semantics, 400 vs merge behavior, HTTP semantics.

**Logic Trick:** PUT = **replacing a whole LEGO set with a new one.** PATCH = **replacing 3 bricks in the existing set.**

### **Code Comparison**

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

app = FastAPI()

class UserUpdate(BaseModel):
    """For PUT — all fields required (or use defaults)"""
    name: str
    email: str
    age: int
    bio: Optional[str] = None
    created_at: datetime

class UserPatch(BaseModel):
    """For PATCH — all fields optional"""
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    bio: Optional[str] = None

# Current user in database
users = {
    1: {
        "id": 1,
        "name": "Alice",
        "email": "alice@example.com",
        "age": 30,
        "bio": "Software engineer",
        "created_at": "2023-01-01T00:00:00"
    }
}

# ============ PUT ENDPOINT ============
@app.put("/users/{user_id}", status_code=200)
async def update_user_put(user_id: int, payload: UserUpdate):
    """
    PUT: FULL REPLACEMENT
    
    Client must send the ENTIRE resource:
    {
        "name": "Alice",
        "email": "alice@example.com",
        "age": 30,
        "bio": "Software engineer",
        "created_at": "2023-01-01T00:00:00"
    }
    
    ✅ Replaces the entire user — all fields
    ❌ If client forgets a field, it's either set to None or 400 error
    
    Idempotent: Calling this 5 times with same data = same result
    """
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Replace the entire user object
    users[user_id] = {**payload.dict(), "id": user_id}
    return users[user_id]

# ============ PATCH ENDPOINT ============
@app.patch("/users/{user_id}", status_code=200)
async def update_user_patch(user_id: int, payload: UserPatch):
    """
    PATCH: PARTIAL UPDATE
    
    Client sends only the fields to change:
    {
        "email": "alice.new@example.com"
    }
    
    ✅ Updates only the email, leaves name/age/bio unchanged
    ✅ All fields optional — client sends what they want to change
    
    NOT necessarily idempotent (depends on the side effects)
    """
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Merge only the provided fields
    update_data = payload.model_dump(exclude_unset=True)  # ← KEY: only fields client sent
    for field, value in update_data.items():
        user[field] = value
    
    return user

# ============ COMPARISON EXAMPLE ============

# Initial state:
# users[1] = {
#     "id": 1,
#     "name": "Alice",
#     "email": "alice@example.com",
#     "age": 30,
#     "bio": "Software engineer"
# }

# PUT /users/1
# Request body: {"name": "Bob", "email": "bob@ex.com", "age": 25, "bio": null, "created_at": "..."}
# Result: user[1] = entire dict replaced — name=Bob, email=bob@ex.com, age=25, bio=null
# ✅ All fields replaced

# PATCH /users/1
# Request body: {"email": "alice.new@ex.com"}
# Result: user[1] = {
#     "id": 1,
#     "name": "Alice",  ← UNCHANGED (was in original, not in PATCH request)
#     "email": "alice.new@ex.com",  ← CHANGED
#     "age": 30,  ← UNCHANGED
#     "bio": "Software engineer"  ← UNCHANGED
# }
# ✅ Only email changed

# ============ CRITICAL: exclude_unset in PATCH ============

@app.patch("/users/{user_id}", status_code=200)
async def safe_patch(user_id: int, payload: UserPatch):
    """
    GOTCHA: You MUST use exclude_unset=True in PATCH!
    
    Without it:
    payload.model_dump() returns {"name": None, "email": None, "age": None, "bio": None}
    This would SET all fields to None! (Turns PATCH into PUT with nulls)
    
    With it:
    payload.model_dump(exclude_unset=True) returns only {"email": "new@ex.com"}
    Client can intentionally set a field to null, and it will be set to null
    """
    user = users.get(user_id)
    if not user:
        raise HTTPException(404, detail="User not found")
    
    # ✅ CORRECT: Only merge fields the client actually sent
    update_data = payload.model_dump(exclude_unset=True)
    user.update(update_data)
    return user

# ============ INTERVIEW GOTCHAS ============

# GOTCHA 1: Can client set a field to null in PATCH?
# ANSWER: Only if you distinguish between "not sent" (exclude_unset=True) and "sent as null"

# Test: Can user intentionally clear their bio?
# PATCH /users/1
# {"bio": null}
# 
# With exclude_unset=True: YES, bio becomes null (client explicitly sent it)
# Without exclude_unset=True: bio becomes null (but you can't tell if client meant it)

# GOTCHA 2: Is PATCH idempotent?
# ANSWER: No, not always. If you have server-side logic like "increment version on PATCH",
# then calling it twice = different results. PUT is always idempotent.

# GOTCHA 3: How to handle nested updates in PATCH?
# ANSWER: Deep merge is complex. Simple rule: don't support nested PATCH updates.
# For complex objects, use PUT (full replacement) or separate endpoints for each field.

# ============ BEST PRACTICES ============

"""
1. Use PUT for full resource replacement (client sends complete object)
2. Use PATCH for selective updates (client sends only changed fields)
3. In PATCH, ALWAYS use exclude_unset=True to distinguish "not sent" from "sent as None"
4. Make all fields Optional in PATCH schemas
5. Document whether null means "clear the field" or "leave unchanged"
6. For side-effect endpoints (e.g., publish_user), use POST, not PATCH
7. If you can't distinguish "not sent" from "sent as null", use PUT instead
"""

# ============ SQL EXAMPLES ============

# PUT: Replace entire row
# UPDATE users SET name=?, email=?, age=?, bio=? WHERE id=?

# PATCH: Update only provided columns
# UPDATE users SET email=? WHERE id=?  (only email changes)

# PATCH with null: Explicitly set to null
# UPDATE users SET bio=null WHERE id=?  (clears bio)
```

### **Interview Summary Table**

| Aspect | PUT | PATCH |
|--------|-----|-------|
| **Semantics** | Full replacement | Partial update |
| **Request Body** | Complete resource | Only changed fields |
| **Missing Fields** | Error or null | Left unchanged |
| **Idempotent?** | YES | NO (by default) |
| **Schema Fields** | All required | All optional |
| **`exclude_unset`** | Not needed | CRITICAL |
| **Side Effects** | Usually safe | Depends on logic |
| **Example** | `PUT /users/1` (whole profile) | `PATCH /users/1` (one field) |

### **Interview Answer (Memorize This)**

> "PUT replaces the entire resource — you send the complete updated object, server replaces everything. Missing fields are lost or set to null. PATCH updates specific fields only — server merges provided fields with existing data, untouched fields stay the same. PUT is idempotent — calling it 10 times = same result. PATCH is not idempotent unless designed for it. In Pydantic PATCH handlers, ALWAYS use `exclude_unset=True` to only merge fields the client actually sent; otherwise, all Optional fields default to None and wipe the resource."

---

## Why fastAPi is fast to Run

> 1. uvicorn Webserver , which is a ASGI Asynchronous Server gateway interface . 
> 2. SGI : uses starlette ASGI python library , which is very lightweight
> 3. Supports async and await python functions which allows to handle concurrent request 

## How fastapi first to code
> 1. Automatic input validation with pydantic
> 2. Auto-generated OpenAPI/Swagger documentation which is also interactive
> 3. Seamless integration with Modern Ecosystem(ML/ DL libraries , OAuth , JWT, SQLALchemy , Tortoise, Docker , kubernetes etc.)



