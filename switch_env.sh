#!/bin/bash

# Script to switch between different Django environments

function show_current_env() {
    echo "Current environment: $DJANGO_SETTINGS_MODULE"
}

function switch_env() {
    case "$1" in
        "local")
            export DJANGO_SETTINGS_MODULE=config.settings.local
            echo "Switched to local development environment"
            ;;
        "dev")
            export DJANGO_SETTINGS_MODULE=config.settings.dev
            echo "Switched to development environment"
            ;;
        "test")
            export DJANGO_SETTINGS_MODULE=config.settings.test
            echo "Switched to test environment"
            ;;
        "staging")
            export DJANGO_SETTINGS_MODULE=config.settings.staging
            echo "Switched to staging environment"
            ;;
        "prod")
            export DJANGO_SETTINGS_MODULE=config.settings.prod
            echo "Switched to production environment"
            ;;
        *)
            echo "Usage: source switch_env.sh [local|dev|test|staging|prod]"
            echo "Current environment: $DJANGO_SETTINGS_MODULE"
            return 1
            ;;
    esac

    echo "Django will now use settings from: $DJANGO_SETTINGS_MODULE"
}

# If no arguments provided, show current environment
if [ -z "$1" ]; then
    show_current_env
else
    switch_env "$1"
fi
