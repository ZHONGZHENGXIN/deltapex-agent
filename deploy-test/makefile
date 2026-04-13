# Variables
DOCKER_REGISTRY=v2ai
API_IMAGE=$(DOCKER_REGISTRY)/bait-api-test
WEB_IMAGE=$(DOCKER_REGISTRY)/bait-web-test
DOCS_IMAGE=$(DOCKER_REGISTRY)/bait-docs-test
VERSION=latest

# 包含 .env 文件（如果存在）
-include .env
export

# Build Docker images
build-api:
	@echo "Building API Docker image: $(API_IMAGE):$(VERSION)..."
	docker build -t $(API_IMAGE):$(VERSION) ../api
	@echo "API Docker image built successfully: $(API_IMAGE):$(VERSION)"

build-web:
	@echo "Building web Docker image: $(WEB_IMAGE):$(VERSION)..."
	@echo "Using NEXT_PUBLIC_DOCS_URL: $(or $(NEXT_PUBLIC_DOCS_URL),http://localhost:8082)"
	@echo "Using NEXT_PUBLIC_API_URL: $(or $(NEXT_PUBLIC_API_URL),http://localhost:8081)"
	docker build \
		--build-arg NEXT_PUBLIC_DOCS_URL=$(or $(NEXT_PUBLIC_DOCS_URL),http://localhost:8082) \
		--build-arg NEXT_PUBLIC_API_URL=$(or $(NEXT_PUBLIC_API_URL),http://localhost:8081) \
		-t $(WEB_IMAGE):$(VERSION) ../web
	@echo "Web Docker image built successfully: $(WEB_IMAGE):$(VERSION)"

build-docs:
	@echo "Building docs Docker image: $(DOCS_IMAGE):$(VERSION)..."
	@echo "Using NEXT_PUBLIC_APP_URL: $(or $(NEXT_PUBLIC_APP_URL),http://localhost:8081)"
	docker build \
		--build-arg NEXT_PUBLIC_APP_URL=$(or $(NEXT_PUBLIC_APP_URL),http://localhost:8081) \
	    -t $(DOCS_IMAGE):$(VERSION) ../docs
	@echo "Docs Docker image built successfully: $(DOCS_IMAGE):$(VERSION)"

# Push Docker images
push-api:
	@echo "Pushing API Docker image: $(API_IMAGE):$(VERSION)..."
	docker push $(API_IMAGE):$(VERSION)
	@echo "API Docker image pushed successfully: $(API_IMAGE):$(VERSION)"

push-web:
	@echo "Pushing web Docker image: $(WEB_IMAGE):$(VERSION)..."
	docker push $(WEB_IMAGE):$(VERSION)
	@echo "Web Docker image pushed successfully: $(WEB_IMAGE):$(VERSION)"

push-docs:
	@echo "Pushing docs Docker image: $(DOCS_IMAGE):$(VERSION)..."
	docker push $(DOCS_IMAGE):$(VERSION)
	@echo "Docs Docker image pushed successfully: $(DOCS_IMAGE):$(VERSION)"

# Run Docker images
run-api:
	@echo "Running API Docker image: $(API_IMAGE):$(VERSION)..."
	docker rm -f bait-api-test
	docker run -d -p 8000:8000 --name bait-api-test -v $(PWD)/../api/.env:/app/api/.env $(API_IMAGE):$(VERSION)
	@echo "API Docker image running successfully: $(API_IMAGE):$(VERSION)"

run-web:
	@echo "Running web Docker image: $(WEB_IMAGE):$(VERSION)..."
	docker rm -f bait-web-test
	docker run -d -p 3000:3000 --name bait-web-test -v $(PWD)/../web/.env:/app/web/.env $(WEB_IMAGE):$(VERSION)
	@echo "Web Docker image running successfully: $(WEB_IMAGE):$(VERSION)"

run-docs:
	@echo "Running docs Docker image: $(DOCS_IMAGE):$(VERSION)..."
	docker rm -f bait-docs-test
	docker run -d -p 4000:4000 --name bait-docs-test -v $(PWD)/../docs/.env:/app/docs/.env $(DOCS_IMAGE):$(VERSION)
	@echo "Docs Docker image running successfully: $(DOCS_IMAGE):$(VERSION)"

deploy:
# Build all images
build-all: build-api build-web build-docs

# Push all images
push-all: push-api push-web push-docs

# Run all images
run-all: run-api run-web run-docs

# Build all images
build-all: build-api build-web build-docs

# Push all images
push-all: push-api push-web push-docs

# Run all images
run-all: run-api run-web run-docs

# Build and push all images
build-push-all: build-all push-all
	@echo "All Docker images have been built and pushed."

# Build and push images
build-push-api: build-api push-api
build-push-web: build-web push-web
build-push-docs: build-docs push-docs
	@echo "All Docker images have been built and pushed."

# Build and push images
build-push-api: build-api push-api
build-push-web: build-web push-web
build-push-docs: build-docs push-docs

start:
	@echo "Running all Docker images: $(API_IMAGE):$(VERSION), $(WEB_IMAGE):$(VERSION), $(DOCS_IMAGE):$(VERSION)..."
	docker compose up -d
	@echo "All Docker images running successfully: $(API_IMAGE):$(VERSION), $(WEB_IMAGE):$(VERSION), $(DOCS_IMAGE):$(VERSION)"

stop:
	@echo "Stopping all Docker images: $(API_IMAGE):$(VERSION), $(WEB_IMAGE):$(VERSION), $(DOCS_IMAGE):$(VERSION)..."
	docker compose down
	@echo "All Docker images stopped successfully: $(API_IMAGE):$(VERSION), $(WEB_IMAGE):$(VERSION), $(DOCS_IMAGE):$(VERSION)"

logs:
	@echo "Viewing logs for all Docker images: $(API_IMAGE):$(VERSION), $(WEB_IMAGE):$(VERSION), $(DOCS_IMAGE):$(VERSION)..."
	docker compose logs -f

restart: stop start logs

deploy: build-all restart

# Phony targets
.PHONY: build-web build-api build-docs push-web push-api push-docs build-all push-all build-push-all build-push-web build-push-docs start stop logs restart deploy
