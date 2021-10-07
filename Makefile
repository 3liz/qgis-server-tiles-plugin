SHELL:=bash
.ONESHELL:

#
# tiles server plugin makefile
#

COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/

# Qgis version flavor
FLAVOR:=release

BECOME_USER:=$(shell id -u)

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

LOCAL_HOME ?= $(shell pwd)

# Check setup.cfg for flake8 configuration
lint:
	@flake8

test: lint
	mkdir -p $$(pwd)/.local $(LOCAL_HOME)/.cache
	docker run --rm --name qgis-py-server-test-$(COMMITID) -w /src \
		-u $(BECOME_USER) \
		-v $$(pwd):/src \
		-v $$(pwd)/.local:/.local \
		-v $(LOCAL_HOME)/.cache:/.cache \
		-e PIP_CACHE_DIR=/.cache \
		-e PYTEST_ADDOPTS="$(TEST_OPTS)" \
		$(QGIS_IMAGE) ./tests/run-tests.sh

BECOME_USER:=$(shell id -u)
BECOME_GROUP:=$(shell id -g)
CACHEDIR:=.wmts_cache

PROJECT_NAME:=qgis_server_tiles

run: env
	cd tests && docker-compose -p $(PROJECT_NAME) up -V --force-recreate

stop:
	cd tests && docker-compose -p $(PROJECT_NAME) down -v --remove-orphans

.PHONY: env

env:
	@echo "Creating environment file for docker-compose"
	@mkdir tests/$(CACHEDIR)
	@cat <<-EOF > tests/.env
		WORKDIR=$(shell pwd)
		CACHEDIR=$(CACHEDIR)
		QGIS_VERSION=$(FLAVOR)
		QGIS_USER_ID=$(BECOME_USER)
		QGIS_USER_GID=$(BECOME_GROUP)
		SERVER_HTTP_PORT=127.0.0.1:8888
		SERVER_MANAGEMENT_PORT=127.0.0.1:19876
		EOF

