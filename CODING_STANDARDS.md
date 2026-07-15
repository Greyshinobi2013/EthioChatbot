# Coding Standards

## Python Standards

Use Python 3.11+

Follow PEP8.

Use type hints.

Use docstrings.

Use pathlib.

---

## Architecture Rules

Business logic must never exist inside Streamlit pages.

Services must be reusable.

Configuration driven design required.

No hard-coded paths.

No hard-coded configuration values.

---

## Logging

Log:

- Startup
- Errors
- Warnings
- State transitions
- Recognition events
- Playback events

---

## Error Handling

All external resources must use exception handling.

Avoid application crashes.

Recover safely whenever possible.

---

## Reusability

Do not duplicate functionality.

Create reusable modules.

Follow SOLID principles.

---

## Code Quality

No TODO comments.

No placeholder functions.

No pseudocode.

Every generated function must work.