# Makefile for Plex Radio Player Docker operations

# Variables
IMAGE_NAME := plex-radio-client
CONTAINER_NAME := plex-radio-client
REGISTRY := ghcr.io/kernelkaribou/plex-radio-client
TAG := latest

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  build       - Build Docker image locally"
	@echo "  run         - Run container with default settings"
	@echo "  run-dev     - Run container for development (interactive)"
	@echo "  stop        - Stop running container"
	@echo "  clean       - Remove container and image"
	@echo "  logs        - Show container logs"
	@echo "  shell       - Open shell in running container"
	@echo "  pull        - Pull latest image from registry"
	@echo "  push        - Push image to registry (requires auth)"
	@echo "  compose-up  - Start with docker-compose"
	@echo "  compose-down - Stop docker-compose services"

# Build image locally
.PHONY: build
build:
	docker build -t $(IMAGE_NAME):$(TAG) .

# Run container with standard settings
.PHONY: run
run:
	docker run -d \
		--name $(CONTAINER_NAME) \
		--privileged \
		--network host \
		--restart unless-stopped \
		-v $(PWD)/last_channel.txt:/app/last_channel.txt \
		-v /run/user/$(shell id -u)/pulse:/run/user/1000/pulse:rw \
		-e PLEX_RADIO_API_URL=http://localhost:5000 \
		$(IMAGE_NAME):$(TAG)

# Run container for development (interactive)
.PHONY: run-dev
run-dev:
	docker run -it --rm \
		--name $(CONTAINER_NAME)-dev \
		--privileged \
		--network host \
		-v $(PWD):/app \
		-v /run/user/$(shell id -u)/pulse:/run/user/1000/pulse:rw \
		-e PLEX_RADIO_API_URL=http://localhost:5000 \
		--entrypoint bash \
		$(IMAGE_NAME):$(TAG)

# Stop container
.PHONY: stop
stop:
	-docker stop $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)

# Clean up container and image
.PHONY: clean
clean: stop
	-docker rmi $(IMAGE_NAME):$(TAG)

# Show container logs
.PHONY: logs
logs:
	docker logs -f $(CONTAINER_NAME)

# Open shell in running container
.PHONY: shell
shell:
	docker exec -it $(CONTAINER_NAME) bash

# Pull latest image from registry
.PHONY: pull
pull:
	docker pull $(REGISTRY):$(TAG)

# Push image to registry
.PHONY: push
push:
	docker tag $(IMAGE_NAME):$(TAG) $(REGISTRY):$(TAG)
	docker push $(REGISTRY):$(TAG)

# Docker compose operations
.PHONY: compose-up
compose-up:
	export UID=$(shell id -u) && export GID=$(shell id -g) && docker-compose up -d

.PHONY: compose-down
compose-down:
	docker-compose down

# Test build (multi-stage if we had one)
.PHONY: test
test: build
	docker run --rm $(IMAGE_NAME):$(TAG) python -c "import radio_client; print('Import successful')"

# Health check
.PHONY: health
health:
	docker inspect --format='{{.State.Health.Status}}' $(CONTAINER_NAME)
