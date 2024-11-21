#!/bin/bash

# Accept environment parameter (default to development)
ENV=${1:-development}
echo "Environment set to: $ENV"

# Store the project root directory
export PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Project root: $PROJECT_ROOT"

# Activate virtual environment (using full path)
source "${PROJECT_ROOT}/.venv/bin/activate"

# Project-specific settings
export PYTHONPATH="${PROJECT_ROOT}"
export DJANGO_ENV="$ENV"

# Set the correct settings module based on environment
if [ "$ENV" = "production" ]; then
    export DJANGO_SETTINGS_MODULE="config.settings.prod"
    echo "Setting production environment"
else
    export DJANGO_SETTINGS_MODULE="config.settings.dev"
    echo "Setting development environment"
fi

# Load environment variables from .env
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

echo "Django $ENV environment activated!"
echo "Project: $(basename ${PROJECT_ROOT})"
echo "Path: ${PROJECT_ROOT}"
echo "Settings module set to: ${DJANGO_SETTINGS_MODULE}"