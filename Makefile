VENV ?= .venv
ALEMBIC := $(VENV)/bin/alembic
UVICORN := $(VENV)/bin/uvicorn
PY := $(VENV)/bin/python

m ?= "autogen"

.PHONY: help local-db-upgrade alembic-upgrade alembic-rev migrate alembic-stamp run shell

help:
	@echo "Makefile targets:"
	@echo "  make local-db-upgrade        # Alias for running Alembic upgrade head against local DB"
	@echo "  make alembic-rev m=\"msg\"   # Create alembic autogenerate revision with message"
	@echo "  make alembic-upgrade         # Run alembic upgrade head"
	@echo "  make alembic-stamp          # Stamp head (mark migrations as applied)"
	@echo "  make migrate m=\"msg\"     # Create revision then upgrade head"
	@echo "  make run                    # Start uvicorn on 0.0.0.0:8000 (dev)"
	@echo "  make shell                  # Open python shell using venv"


# load .env into environment when present, then run the command
ENV_LOAD := set -a; [ -f .env ] && . .env; set +a;

alembic-rev:
	$(ENV_LOAD) $(ALEMBIC) -c alembic.ini revision --autogenerate -m $(m)

alembic-upgrade:
	$(ENV_LOAD) $(ALEMBIC) -c alembic.ini upgrade head

alembic-stamp:
	$(ENV_LOAD) $(ALEMBIC) -c alembic.ini stamp head

migrate: alembic-rev alembic-upgrade

local-db-upgrade: alembic-upgrade


run:
	$(ENV_LOAD) $(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

shell:
	$(ENV_LOAD) $(PY)
