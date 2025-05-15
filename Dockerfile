# Dockerfile for the Meal Prep Django App

# Stage 1: Builder
FROM python:3.10-slim-buster as builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install uv so the command is available
RUN pip install --upgrade pip uv

# Copy project definition and necessary source files for the build
COPY pyproject.toml ./
COPY README.md ./
COPY manage.py ./
COPY src/ ./src/

# If you use a lock file and want to sync with it:
# COPY uv.lock ./
# RUN uv sync --system --no-cache # This would use uv.lock

# Install dependencies from pyproject.toml using uv
# The '.' tells uv to look for pyproject.toml in the current directory
# This will also build our local package mealprep_app
RUN uv pip install --system --no-cache .

# --- Diagnostic Steps --- (Removing these as pandas is not a direct dependency)
# RUN echo "--- Listing site-packages in builder stage (root) ---" && ls -l /usr/local/lib/python3.10/site-packages/
# RUN echo "--- Finding pandas module path in builder stage ---" && python -c "import pandas; print(f'Pandas module path in builder: {pandas.__file__}')"
# RUN echo "--- Attempting to import pandas and print version in builder stage ---" && python -c "import pandas; print(f'Pandas version in builder: {pandas.__version__}')"
# --- End Diagnostic Steps ---

# Stage 2: Final image
FROM python:3.10-slim-buster

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# Gunicorn will look for mealprep_project.wsgi:application
# DJANGO_SETTINGS_MODULE is also important, should be set in .env or here if not.
# We assume settings.py will correctly load .env for settings including SECRET_KEY and DATABASE_URL.

WORKDIR /home/appuser/app

# Create a non-root user and group
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup appuser

# Copy installed Python packages from the builder stage to the system site-packages
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
# Copy executables like django-admin, gunicorn from builder
COPY --from=builder /usr/local/bin /usr/local/bin

# Set PYTHONPATH to include the src directory
ENV PYTHONPATH /home/appuser/app/src

# Copy the application code
COPY manage.py . 
# Copy the entire src directory which now contains the Django project and apps
COPY src/ ./src/
# If you add a top-level static or templates dir that Gunicorn/Django needs at runtime before collectstatic:
# COPY static/ ./static/
# COPY templates/ ./templates/

# Change ownership to the appuser
RUN chown -R appuser:appgroup /home/appuser/app

USER appuser

EXPOSE 5000

# Command to run the application using Gunicorn
# The number of workers is a suggestion; adjust based on your server resources
# Ensure mealprep_project.wsgi:application correctly points to your WSGI app object.
# With PYTHONPATH set to /home/appuser/app/src, gunicorn should find mealprep_project.wsgi
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "mealprep_project.wsgi:application"] 