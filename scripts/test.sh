#!/bin/bash

# Test runner script that sets up the proper Python path

set -e

# Add the app directory to PYTHONPATH
export PYTHONPATH="${PWD}/app:${PYTHONPATH}"

# Set Django settings module
export DJANGO_SETTINGS_MODULE="config.settings"

# Change to the app directory for Django commands
cd app

echo "Setting up test environment..."

# Run migrations for testing
python manage.py migrate --noinput

echo "Running tests..."

# Run the tests
python -m pytest ../tests/ -v

echo "Tests completed."
