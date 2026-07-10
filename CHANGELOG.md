# Changelog

All notable changes to the **FIFA 2026 CrowdFlow Assist** project will be documented in this file.

## [1.0.0] - 2026-07-10

### Added
- Restated operational pain point, user personas, success metrics, and core theme selection.
- Architectural design with system components, data flows, and GenAI justification.
- Project boilerplate: `.env`, `.env.example`, `requirements.txt`.
- Backend config (`config.py`) and schema validations (`schemas.py`).
- Security utilities (`utils/security.py`) for rate-limiting, injection detection, and sanitization.
- In-memory cache manager (`services/cache_service.py`) for optimizing latency and LLM costs.
- Stadium structural graph and live simulation service (`services/crowd_sensor.py`).
- Dijkstra accessibility-aware routing algorithm (`services/route_service.py`).
- Multilingual instruction generation service (`services/llm_service.py`) supporting Google Gemini API with robust fallbacks.
- Single-page frontend dashboard with WCAG 2.1 AA compliance (dark mode, keyboard focus, low bandwidth warning, high contrast).
- Fully mocked unit and integration test suite (`tests/`).
- Setup, run, and test instructions (`README.md`).
