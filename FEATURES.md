# Find-Doc Backend — Feature Bank

> **Purpose:** Resume ammunition. Each feature entry has enough technical and contextual detail to generate tailored bullets for different job types.
> Filter by `Tags` to pull relevant features per application, then ask Claude to synthesize into polished bullets.
>
> **Job type tags:** `[backend]` `[data-modeling]` `[systems]` `[devops]` `[fullstack]` `[security]` `[database]`

---

## 1. Authentication & Security

---

### JWT-Based Authentication System

Implements a stateless auth flow across registration, login, and protected routes. On registration and login, a signed JWT is generated with a `user_id` payload and a 1-hour expiry. Tokens are verified on every protected route via a reusable `@jwt_required` decorator that extracts the Bearer token from the `Authorization` header, decodes it with `PyJWT`, and injects the payload into Flask's `g` context for downstream handlers.

**Key files:** [src/user-service/auth_module/auth_routes.py](src/user-service/auth_module/auth_routes.py), [src/user-service/auth_module/middleware/jwt_validation.py](src/user-service/auth_module/middleware/jwt_validation.py)
**Tech:** Python, Flask, PyJWT (`HS256`), `bcrypt` (password hashing with `gensalt`), `flask.g` for request-scoped user context
**Tags:** `[backend]` `[security]`

---

### Bcrypt Password Hashing

Plain-text passwords are never stored. On account creation, the password is popped from the incoming request payload, hashed with `bcrypt.hashpw` + `bcrypt.gensalt()`, and the hash is stored in MongoDB. On login, `bcrypt.checkpw` compares the submitted password against the stored hash. Email uniqueness is enforced at the application layer before insertion.

**Key files:** [src/user-service/booking_module/routes/users.py](src/user-service/booking_module/routes/users.py), [src/user-service/auth_module/auth_routes.py](src/user-service/auth_module/auth_routes.py)
**Tech:** Python, `bcrypt`, MongoDB uniqueness check via `find_one` before insert
**Tags:** `[backend]` `[security]`

---

## 2. Appointment Booking

---

### Transactional Appointment Booking with Slot Locking

Books a healthcare appointment inside a MongoDB multi-document transaction to prevent double-booking. Within a single session, the handler: (1) verifies the user exists, (2) fetches the provider's `Schedule` document, (3) calls `is_slot_available` to confirm the target slot is unbooked, (4) uses a MongoDB `array_filters` positional update to flip `is_booked: True` on the matching slot, and (5) `$push`es the new `Appointment` subdocument onto the user's record. Any failure triggers `abort_transaction`, rolling back both writes atomically.

**Key files:** [src/user-service/booking_module/routes/users.py](src/user-service/booking_module/routes/users.py) (`book_appointment`, lines 86–161), [src/user-service/booking_module/models/schedule.py](src/user-service/booking_module/models/schedule.py)
**Tech:** Python, Flask, MongoDB multi-document transactions (`start_session`, `start_transaction`, `commit_transaction`, `abort_transaction`), `array_filters` for nested array updates, Pydantic model validation
**Tags:** `[backend]` `[database]` `[systems]`

---

### Transactional Appointment Cancellation

Mirrors the booking flow in reverse. Cancellation resolves the target appointment by `apt_id` within a session transaction, removes it from the user document via `$pull`, and reinstates the corresponding provider slot by flipping `is_booked: False` using an `array_filters` update — all atomically. Handles the edge case where `start_datetime` may arrive as a `datetime` object rather than a string before passing it to the slot filter.

**Key files:** [src/user-service/booking_module/routes/users.py](src/user-service/booking_module/routes/users.py) (`cancel_appointment`, lines 164–211)
**Tech:** Python, Flask, MongoDB transactions, `$pull` operator, `array_filters`
**Tags:** `[backend]` `[database]`

---

## 3. Data Modeling

---

### Pydantic Schema Layer for MongoDB Documents

All domain objects are defined as Pydantic `BaseModel` subclasses, providing runtime validation and type coercion before any data touches MongoDB. `User` enforces `EmailStr`, nested `FullName`, `datetime` for date of birth, and an `AccountStatus` enum with a default of `ACTIVE`. `Appointment` uses a custom `ObjectId` field type with a `_id` alias. `Schedule` nests a `Slot` list and exposes `is_slot_available` as a domain method. `model_dump()` serializes validated objects to plain dicts for MongoDB insertion.

**Key files:** [src/user-service/booking_module/models/user.py](src/user-service/booking_module/models/user.py), [src/user-service/booking_module/models/appointment.py](src/user-service/booking_module/models/appointment.py), [src/user-service/booking_module/models/schedule.py](src/user-service/booking_module/models/schedule.py)
**Tech:** Python, Pydantic v2 (`BaseModel`, `EmailStr`, `Field`, `model_dump`), `enum.Enum`, `bson.ObjectId`
**Tags:** `[data-modeling]` `[backend]`

---

## 4. Background Jobs

---

### Cron-Based Appointment Status Updater

Runs a nightly background job (midnight via cron) that sweeps every user document in MongoDB and recalculates each appointment's `status` field — setting it to `"passed"` if `start_time` is before the current time, or `"upcoming"` otherwise. The job is registered at app startup using APScheduler's `BackgroundScheduler` and runs in-process without blocking the Flask request loop.

**Key files:** [src/user-service/scheduler.py](src/user-service/scheduler.py), [src/user-service/app.py](src/user-service/app.py)
**Tech:** Python, APScheduler (`BackgroundScheduler`, `add_job` with `cron` trigger), MongoDB `update_one` with `$set`, `datetime.fromisoformat`
**Tags:** `[backend]` `[systems]` `[devops]`

---

## 5. Provider Schedules

---

### Filtered Provider Availability Endpoint

Serves a provider's schedule with booked slots stripped out before the response is returned. The handler fetches the full `Schedule` document by `provider_id`, iterates `availability`, and builds a new list containing only slots where `is_booked is False`. This keeps booking state server-side and prevents clients from ever seeing or attempting to book occupied slots.

**Key files:** [src/user-service/booking_module/routes/provider_schedules.py](src/user-service/booking_module/routes/provider_schedules.py)
**Tech:** Python, Flask, MongoDB `find_one`, response filtering via list comprehension
**Tags:** `[backend]`

---

### Bulk Mock Schedule Generator

Seed script that programmatically generates realistic provider schedules for a configurable date range. For each provider ID, it randomly selects working days and shift lengths (4–6 hours), then creates 15-minute `Slot` objects across every working day in the range. Schedules are inserted in batches of 1,000 using `insert_many` for throughput efficiency. Used to populate the `provider_schedules` collection for demos.

**Key files:** [src/user-service/scripts/generate_mock_schedules.py](src/user-service/scripts/generate_mock_schedules.py)
**Tech:** Python, PyMongo `insert_many` (bulk writes), `datetime` / `timedelta` arithmetic, `random.sample`, JSON provider ID manifest
**Tags:** `[backend]` `[database]` `[devops]`

---

## 6. Infrastructure & Architecture

---

### Microservices Architecture with API Gateway

Designed as a four-service microservices system: `user-service` (auth + booking), `provider-service` (profiles + reviews), `healthbot-service` (symptom-based provider discovery chatbot), and `api-gateway-service` (centralized routing + access control). Each service is independently deployable. The gateway layer enforces JWT validation via a shared `@jwt_required` decorator before forwarding to internal services.

**Key files:** [src/gateway_service/routes/gateways.py](src/gateway_service/routes/gateways.py), [src/user-service/app.py](src/user-service/app.py)
**Tech:** Python, Flask Blueprints, Flask-CORS, Heroku (`heroku.yml`), Docker (`Dockerfile`)
**Tags:** `[systems]` `[devops]` `[backend]` `[fullstack]`

---

### MongoDB Atlas Connection with TLS

Establishes a TLS-secured connection to MongoDB Atlas at startup using `certifi` as the CA bundle. Validates that `MONGODB_URI` and `DB_NAME` env vars are present before attempting to connect, raising a `RuntimeError` with a descriptive message if either is missing. Exposes `users_collection` and `provider_schedules_collection` as module-level singletons consumed across all route handlers.

**Key files:** [src/user-service/mongodb_connection.py](src/user-service/mongodb_connection.py)
**Tech:** Python, PyMongo `MongoClient`, `certifi`, `python-dotenv`, connection ping health check (`client.admin.command("ping")`)
**Tags:** `[backend]` `[database]` `[devops]`
