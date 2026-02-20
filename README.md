# Peroxia Technology Backend Assignment

## Build a Real-Time Backend Service

This repository contains the backend service for a simplified Team Collaboration / Notification System.
It is built using **FastAPI** (Python), **SQLite** (Database), **SQLAlchemy** (ORM), and **WebSockets** for real-time capabilities.

### Installation and Setup

1. **Activate Virtual Environment and Install Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the Application:**
   ```bash
   uvicorn app.main:app --port 8080 --reload
   ```
   The API will be available at `http://localhost:8080`.

3. **Run the Integration Tests:**
   A test script has been provided to verify both REST and WebSockets functionalities.
   ```bash
   python test_flow.py
   ```

---

## Architecture Design

The backend uses a layered architecture, which favors Separation of Concerns:
- **`app/main.py`**: Entry point of the FastAPI application. Registers all API and WebSocket routers.
- **`app/core/`**: Configuration, JWT, Security, and the WebSocket ConnectionManager.
- **`app/db/`**: Handles the Database connection strategy using SQLAlchemy's declarative base.
- **`app/models/`**: SQLAlchemy models representing the tables in the database.
- **`app/schemas/`**: Pydantic models for validation and serialization.
- **`app/api/endpoints/`**: Holds specific business domain routes (`auth`, `projects`, `tasks`, and `websockets`).
- **`app/api/dependencies.py`**: FastAPI dependency injector, specifically useful for resolving the active user through JWT.

### Tradeoffs
- **SQLite over PostgreSQL**: SQLite is perfectly fine for basic constraints and simplifying testing. However, a production setup would migrate easily to PostgreSQL via `databases` / `asyncpg` bindings without modifying core logic.
- **Synchronous vs Asynchronous Database**: I utilized `autocommit=False` via SQLAlchemy's default Sync engine. For higher I/O capacity, utilizing `SQLAlchemy[asyncio]` + `asyncpg` is the optimal choice for FastAPI.
- **Memory-based WebSocket Rooms**: The current `ConnectionManager` stores WebSocket clients in Python memory (`dict`). While very fast, this limits horizontal scalability (server instances). For production, leveraging WebSockets with a **Redis Pub/Sub** broker would allow broadcasting messages across multiple backend instances.

---

## Event-Driven Design Explanation

A core feature of this platform is its asynchronous, event-driven pattern designed around real-time broadcasting and deferred processing.

1. **Fire-and-Forget Architecture (WebSockets)**:
   - When users construct states modifying events via standard REST API calls (`POST /tasks`, `PATCH /status`, `PUT /tasks/{id}`), the server successfully mutates the SQL state locally.
   - Crucially, it does **not** block returning the HTTP response waiting for client delivery confirmation. Instead, it fires an asynchronous broadcast: `await manager.broadcast(event)`.
   - The WebSocket Manager independently handles serialization and multiplexing the specific payload out to dozens or hundreds of connected clients residing in the `project_id` bucket. This decouples our write-path from our notification-path.

2. **Background Jobs (FastAPI BackgroundTasks)**:
   - We incorporated FastAPI's `BackgroundTasks` feature to further minimize client blocking latency.
   - Example implementation: When a task is updated with an `assignee_id`, checking if the assignee changed forces the `tasks.py` router to trigger a dummy email notification (`simulate_send_email_notification()`).
   - This function enters an asynchronous event loop yielding execution time until "sent" successfully (simulated via `asyncio.sleep()`). Crucially, the frontend user who triggered the update instantly gets a `200 OK` response.

By avoiding heavy synchronous integrations (like synchronous SMPT email rendering) on the hot-path and isolating cross-client WebSocket propagation, the backend achieves extremely low round-trip latency.

---

## Data Model Design

The database encompasses relational entities required by the system:
- **`User`**: Tracks `email`, `username`, and `hashed_password` (using Bcrypt).
- **`Project`**: Has an `owner_id` explicitly attached to the User.
- **`ProjectMember`**: An association/join table. It tracks which `user_id` is joined to which `project_id`.
- **`Task`**: Associated with a specific `project_id`. Includes `title`, `status` (Enum: `todo`, `in_progress`, `done`), and an optional `assignee_id`.

Relationship `cascade="all, delete-orphan"` rules are maintained on dependencies for clean data deletion.

---

## WebSocket Design

The real-time notification capability leverages a *Room/Channel Concept* implemented via the `ConnectionManager` in `app/core/websocket.py`:

1. **Connection Logic**:
   - Clients connect via `/ws/projects/{project_id}?token={jwt_token}`.
   - The server validates the token and confirms the user is a `ProjectMember` for the requested room.
   - If granted, the WebSocket is registered iteratively to `active_connections[project_id]`.

2. **Event Broadcasting**:
   - WebSockets are unidirectional in this specific feature scope (`Server -> Client flow`).  
   - Users mutate task states via regular REST API calls (e.g., `PATCH /tasks/{id}/status`).
   - The REST endpoint persists the change in SQLite, and independently invokes `await manager.broadcast(event_data, project_id)`.
   - The Manager pushes an identical JSON payload to all connected clients listening inside that specific `project_id` bucket.

---

## API Documentation

FastAPI guarantees Swagger out of the box. Once the server is running on `uvicorn app.main:app`:
1. **Swagger UI**: Visit `http://localhost:8080/docs`
2. **ReDoc UI**: Visit `http://localhost:8080/redoc`
3. **OpenAPI JSON export**: Included inside the repository as `openapi.json` for importing into **Postman** or **Bruno**.
