# 科创点AI Banana Slides Fork Rules

This fork is the internal PPT orchestration and rendering engine for 科创点AI.

## Platform provider boundary

- Production model calls must use `KCD_PLATFORM`; never read provider API keys from settings, environment variables, requests, or the database.
- Each generation request must include `platform_execution` with a platform project ID, PPT job ID, idempotency key, gateway URL, and short-lived execution token.
- The execution token is request context only. Never persist it, log it, include it in task snapshots, or echo it in API responses.
- Text and image calls go through the platform model-invocation API. Poll boundedly and preserve the platform's retryable/error classification.
- Do not cache execution context globally. Concurrent projects and jobs must remain isolated.

## Product surface

- Keep Banana responsible for outline/page orchestration, visual composition, rendering, and export.
- The built-in frontend and user-editable provider settings are disabled in the product image.
- Only health, project actions, task status, and file/export endpoints are part of the product API.
- Preserve compatibility with the platform OpenAPI contract and fixtures in the main repository.

## Supply chain and testing

- Base changes on a recorded upstream commit. Upstream syncs require review and a new immutable image digest.
- Production images must contain a complete, locked Python environment. Entrypoints must never run `uv sync`, `pip install`, or otherwise download/build dependencies.
- Database migrations run as an explicit one-shot deployment step. The API process must not fall back to `create_all` when a migration fails.
- Never commit `.env`, user projects, generated decks, provider responses containing secrets, registry credentials, or local databases.
- Tests must cover token redaction, concurrent job isolation, text/image invocation polling, platform errors, and operation without provider API keys.

## Durable task rules

- Every platform project creation and stage submission has a persisted idempotency receipt with a request hash. Reusing a key with different input is a conflict.
- Receipts may store project/job/stage identifiers and task state, but never request bodies, execution tokens, credentials, or raw provider responses.
- Process restarts must convert orphaned processing tasks to a retryable interrupted state. Re-driving the same stage must reuse completed page artifacts.
- Model invocation keys are derived from stable stage, page, operation, and content identities. Thread scheduling order must not affect idempotency.
- Background work is bounded. Capacity exhaustion returns a retryable busy response instead of creating an unbounded queue.
