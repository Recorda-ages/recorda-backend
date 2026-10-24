# Account privacy settings implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. No commit before the user's approval of the real API evidence.

**Goal:** Implement authenticated account settings and atomic acceptance of pending follows when making an account public.

**Architecture:** Keep routes thin, put transaction ownership in services, and reuse the existing individual acceptance logic. Queries stay in repositories. Existing readers already resolve privacy dynamically.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, SQLAlchemy, pytest, Ruff.

**Spec:** https://github.com/Recorda-ages/recorda-backend/issues/111 and CONTRIBUTING.md.

## Global constraints

- GET returns `is_private` and the stored `language`; PATCH changes privacy. After rebasing onto dev on 23/10, it also preserves the language update contract introduced by #112.
- Making an account private preserves accepted followers.
- Making it public accepts pending incoming requests and updates notifications in one transaction.
- Repeated values are a no-op with HTTP 200.
- Minimum coverage 80%; Ruff lint and format must pass.
- Branch from `origin/dev`; publish only after screenshot approval; never merge.

## Review focus

- Missing/invalid tokens and disabled accounts cannot read or change settings.
- Empty/null updates must not clear privacy or change language.
- Incoming pending requests must be isolated from outgoing requests and other accounts.
- A failure after the first acceptance must roll back privacy, follow status, and notifications.
- Old Recordas must immediately follow the new privacy; accepted followers retain access.

## Task 1: Account privacy API and regression coverage

**Files:** `app/schemas/settings.py`, `app/services/settings_service.py`, `app/api/routes/user.py`, existing follow request and notification services/repositories, `tests/test_settings_routes.py`, API documentation/evidence.

**Interfaces:** `UserSettings(is_private, language)`, `UserSettingsUpdate(is_private: bool | None = None)`, PATCH result extends settings with `accepted_requests: int`; `follow_request_service._accept(db, follow)` performs acceptance without authorization or commit.

- [x] Add failing authenticated endpoint tests for GET, private/public transitions, no-op, notification conversion and rollback.
- [x] Run `.venv/Scripts/python.exe -m pytest tests/test_settings_routes.py --no-cov -q`; verify failures identify missing endpoints.
- [x] Extract the shared acceptance helper and make the service own its transaction; implement settings schemas, repository queries, service and routes.
- [x] Run settings and existing acceptance/notification tests; resolve failures.
- [x] Test old Recordas across privacy toggles through detail, general feed, grid, visible listing and followers/following routes. The user approved adding the minimal missing grid route.
- [x] Run full pytest coverage, Ruff check and Ruff format check. Initial run: 748 passed, 7 PostgreSQL-dependent skips. On 22/10, disposable PostgreSQL 16.15 validation: 755 passed, zero skips, 98.46% coverage.
- [x] Review the diff, fix the concurrent follow/privacy race, and capture real API and coverage evidence using the authorized isolated preview database. The real PostgreSQL concurrency test passed on 22/10.
- [x] Present screenshots and demonstrate the three manual scenarios in visible Swagger at the user's request. The user authorized including the results in the PR.
- [x] Commit, rebase onto updated dev, push, open PR #135 with evidence, and verify successful CI. No merge.
