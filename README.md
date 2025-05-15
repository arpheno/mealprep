# Meal Prep App

A web application for planning batch cooking and meal preparation, aiming to hit Recommended Dietary Allowances (RDAs) for two people. Built with Django, Django REST Framework (DRF) for the backend, and Vue.js for the frontend.

## Project Goals

*   Design and manage meal components and full meal plans.
*   Integrate with USDA FoodData Central (FDC) for comprehensive nutritional information.
*   Track nutritional intake against RDAs and Tolerable Upper Intake Levels (ULs).
*   Provide a user-friendly interface for creating and adjusting meal components and plans.
*   Visualize nutritional breakdowns, including macronutrients and micronutrients.

## Tech Stack

*   **Backend:** Python, Django, Django REST Framework (DRF)
*   **Frontend:** Vue.js
*   **Database:** PostgreSQL
*   **Package Management:** `uv` (for Python), `npm`/`yarn` (for Node.js/Vue.js)
*   **Testing:** `pytest`, `pytest-django`
*   **Containerization:** Docker, Docker Compose
*   **Linting/Formatting:** (Assumed: tools like Black, Flake8 for Python; ESLint, Prettier for Vue.js)

## Project Evolution Summary

*   Initially started with Flask, then restarted with Django and DRF for a more robust API.
*   Uses `uv` for Python package management.
*   Docker Compose orchestrates the Django/Gunicorn application and PostgreSQL database.
*   Domain models (Nutrient, Ingredient, MealComponent, etc.) translated into Django models.
*   Integrated with USDA FoodData Central (FDC) by importing foundational food data via a Django management command.
*   Refactored the Django project structure to a `src/` layout to resolve packaging issues.
*   Frontend developed with Vue.js, including components for meal component creation and nutritional breakdown visualization.
*   Addressed various frontend and backend issues, including static file serving, CSRF, API request/response handling, and database migrations.

## Setup and Running

This project uses `uv` for Python package management and Docker for containerization. The frontend uses Node.js and npm (or yarn).

### Prerequisites

*   Python (version as specified in `pyproject.toml`, e.g., 3.10+)
*   `uv` (`pip install uv`)
*   Node.js and npm (or yarn)
*   Docker Desktop (or Docker Engine + Docker Compose)

### Backend Development Setup (Django/DRF)

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <project-directory>
    ```

2.  **Set up Python virtual environment and install dependencies:**
    ```bash
    uv venv .venv --seed  # Or your preferred venv creation method
    source .venv/bin/activate  # On Windows use .venv\Scripts\activate
    uv pip install -e ".[dev]" # Assuming a [dev] extra in pyproject.toml for dev tools
    ```
    Alternatively, if you prefer to install directly from `pyproject.toml` without editable mode for dependencies:
    ```bash
    uv pip install -r requirements.txt # If you generate one, or directly from pyproject.toml if supported
    # For development, it's common to have dev dependencies in pyproject.toml
    uv pip install Django djangorestframework psycopg2-binary django-environ gunicorn pytest pytest-django pandas openpyxl django-cors-headers
    ```


3.  **Set up environment variables:**
    Create a `.env` file in the project root (where `manage.py` resides, which is top-level, not inside `src/`).
    You can copy from a `.env.example` if one is provided.
    ```env
    SECRET_KEY='your_very_strong_and_long_secret_key_here'
    DEBUG=True
    ALLOWED_HOSTS=localhost,127.0.0.1
    # For Docker Compose
    DATABASE_URL=postgresql://meal_user:supersecretpassword@db:5432/mealprep_db
    # For local development against a locally running Postgres instance
    # DATABASE_URL=postgresql://your_local_user:your_local_password@localhost:5432/your_local_db
    VITE_API_BASE_URL=http://localhost:8000/api # Example, used by frontend if proxied through Django dev server or directly
    VUE_APP_API_BASE_URL=http://localhost:8000/api # Ensure this matches your frontend setup
    PYTHONPATH=./src # Important for src layout
    CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000
    ```
    **Note:** `PYTHONPATH=./src` might be more reliably set in `docker-compose.yml` for the `web` service and in your shell/IDE for local `manage.py` commands if not using Docker for those.

4.  **Build Docker images and run services:**
    ```bash
    docker-compose up --build -d
    ```

5.  **Run database migrations (inside Docker container):**
    ```bash
    docker-compose exec web python manage.py migrate
    ```

6.  **Create a superuser (optional, for Django Admin):**
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

7.  **Load initial data (e.g., FDC, DRVs):**
    ```bash
    docker-compose exec web python manage.py import_fdc_foundational --delete-before-import data/fdc_json/FoundationalFoods.json
    docker-compose exec web python manage.py import_custom_drvs data/drv_data/UK_DRV_summary_transposed.xlsx
    # Add other import commands as necessary
    ```

8.  The Django backend should be available at `http://localhost:8000` (or the port mapped in `docker-compose.yml`).
    The Django admin will be at `http://localhost:8000/admin/`.

### Frontend Development Setup (Vue.js)

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```

2.  **Install Node.js dependencies:**
    ```bash
    npm install  # or yarn install
    ```

3.  **Run the Vue.js development server:**
    ```bash
    npm run dev # or yarn dev
    ```
    The frontend should be available at `http://localhost:5173` (or the port specified by Vite/Vue CLI). It will make API calls to the Django backend.

### Running Tests (Backend)

Ensure your Docker services are running if tests require the database.
```bash
docker-compose exec web pytest
```
Or, if running locally with a configured test database and active venv:
```bash
pytest
```

## Project Structure

```
.
├── .env                   # Local environment variables (IMPORTANT: add to .gitignore)
├── .gitignore             # Specifies intentionally untracked files
├── Dockerfile             # Defines the Docker image for the Django application
├── docker-compose.yml     # Defines services for Docker (Django app, PostgreSQL DB)
├── manage.py              # Django's command-line utility (adjusted for src layout)
├── pyproject.toml         # Project metadata and Python dependencies (for uv)
├── README.md              # This file
├── data/                  # Directory for raw data files (e.g., FDC JSON, DRV Excel)
├── frontend/              # Vue.js frontend application
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── components/
│   │   ├── services/      # (Optional) For API call logic
│   │   ├── store/         # (Optional) For Vuex/Pinia state management
│   │   ├── views/         # (Optional) For page-level components
│   │   ├── App.vue
│   │   ├── main.js
│   │   └── router.js      # (Optional) If using Vue Router
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js     # (Or vue.config.js if using Vue CLI)
│   └── ... (other frontend files like .eslintrc.js, .prettierrc.js)
├── src/                   # Main source code directory for the Django project
│   ├── api/               # Django app for the REST API
│   │   ├── migrations/
│   │   ├── management/    # Custom Django management commands
│   │   │   └── commands/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   └── tests.py       # (Or a separate tests/ directory within api/)
│   └── mealprep_project/  # Django project configuration
│       ├── __init__.py
│       ├── asgi.py
│       ├── settings.py
│       ├── urls.py
│       └── wsgi.py
├── staticfiles/           # Collected static files (generated by collectstatic)
├── tests/                 # Project-level or integration tests (alternative to app-specific tests/)
└── ... (other config files like .editorconfig, .prettierignore)

```

## Key Management Commands

*   `python manage.py import_fdc_foundational <path_to_json_file>`: Imports foundational food data from FDC JSON.
*   `python manage.py import_custom_drvs <path_to_excel_file>`: Imports Dietary Reference Values.

## API Endpoints

(To be detailed further, but generally provided by DRF ViewSets under `/api/`)

*   `/api/nutrients/`
*   `/api/ingredients/`
*   `/api/ingredients/search/?name=<term>`
*   `/api/mealcomponents/`
*   `/api/foodportions/`
*   `/api/dietaryreferencevalues/`

*(More details will be added as the project progresses, including specific API documentation and frontend component interactions.)* 