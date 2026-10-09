VENV   ?= .venv
PYTHON ?= $(VENV)/bin/python
HOST   ?= 127.0.0.1
PORT   ?= 8765

export HOST PORT PYTHON

COLLECTION  = postman/library.postman_collection.json
ENVIRONMENT = postman/local.postman_environment.json
NEWMAN      = npx --yes newman@6.2.1 run $(COLLECTION) -e $(ENVIRONMENT) \
              --env-var baseUrl=http://$(HOST):$(PORT) \
              --reporters cli,junit --reporter-junit-export reports/newman.xml

.PHONY: help install run test newman check openapi clean

$(VENV)/bin/python:
	python3 -m venv $(VENV)

install: $(VENV)/bin/python
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.main:app --host $(HOST) --port $(PORT) --reload

test:
	$(PYTHON) -m pytest

newman:
	@mkdir -p reports
	scripts/with_server.sh $(NEWMAN)

check:
	@mkdir -p reports
	scripts/with_server.sh sh -c '$(PYTHON) -m pytest && $(NEWMAN)'

openapi:
	$(PYTHON) scripts/export_openapi.py

clean:
	rm -rf reports server.log .pytest_cache
