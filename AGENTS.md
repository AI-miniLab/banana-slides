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
- Never commit `.env`, user projects, generated decks, provider responses containing secrets, registry credentials, or local databases.
- Tests must cover token redaction, concurrent job isolation, text/image invocation polling, platform errors, and operation without provider API keys.
