# Antkeeping.info

Antkeeping.info is a web platform for ant keepers worldwide. It provides:

- Detailed species information (size, food, distribution, nuptial flight periods, etc.)
- Species, genus and subfamily lists filterable by country/state
- Nuptial flight calendar showing flight months per species
- Top charts and other statistics

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 5.2 |
| REST API | Django REST Framework + drf-spectacular |
| Database | PostgreSQL |
| Cache | Redis (production) / dummycache (development) |
| Frontend | Bootstrap 5, TinyMCE |
| Runtime | Python 3.12+ |

## Requirements

- Python 3.12+
- PostgreSQL
- Redis (production only — not required for local development)
- [uv](https://docs.astral.sh/uv/) (dependency manager)

> **Windows users:** Development under WSL2 is highly recommended.

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Create a PostgreSQL database and user with appropriate permissions
4. Copy the example environment file and edit it:
   ```bash
   cp .env.example .env
   ```
5. Run database migrations:
   ```bash
   uv run python manage.py migrate
   ```
6. Start the development server:
   ```bash
   uv run python manage.py runserver
   ```

## API

The REST API is available at `/api/`. Interactive documentation (Swagger UI) is served at `/api/doc`.

Key endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /api/ants/` | List all ant species |
| `GET /api/ants/<species>/` | Species detail |
| `GET /api/genera/` | List genera |
| `GET /api/regions/` | List regions |
| `GET /api/regions/<region>/ants/` | Species in a region |
| `GET /api/flights/` | Nuptial flight records |
| `GET /api/schema` | OpenAPI schema |

## Development

This project uses [pre-commit](https://pre-commit.com/) hooks for code quality (Ruff, DJLint, Gitlint).

Install hooks after cloning:
```bash
uv run pre-commit install
```

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/).

## License

See [LICENSE](LICENSE).
