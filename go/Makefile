.PHONY: help build run test clean tidy install dev

help: ## Display this help screen
	@grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	@echo "📦 Installing Go dependencies..."
	@go mod download
	@go mod tidy

build: ## Build the application
	@echo "🔨 Building application..."
	@go build -o bin/server ./cmd/server

run: ## Run the application
	@echo "🚀 Running application..."
	@go run ./cmd/server/main.go

dev: ## Run in development mode with auto-reload
	@echo "🔄 Running in development mode..."
	@which air > /dev/null || go install github.com/cosmtrek/air@latest
	@air

test: ## Run tests
	@echo "🧪 Running tests..."
	@go test -v ./...

test-coverage: ## Run tests with coverage
	@echo "📊 Running tests with coverage..."
	@go test -v -coverprofile=coverage.out ./...
	@go tool cover -html=coverage.out -o coverage.html

clean: ## Clean build artifacts
	@echo "🧹 Cleaning..."
	@rm -rf bin/
	@rm -f coverage.out coverage.html
	@rm -f saving_advisor.db

tidy: ## Tidy and verify dependencies
	@echo "📦 Tidying dependencies..."
	@go mod tidy
	@go mod verify

fmt: ## Format code
	@echo "✨ Formatting code..."
	@go fmt ./...

lint: ## Run linter
	@echo "🔍 Running linter..."
	@which golangci-lint > /dev/null || go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest
	@golangci-lint run

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	@docker build -t saving-advisor-go:latest -f ../Dockerfile.go ..

docker-run: ## Run Docker container
	@echo "🐳 Running Docker container..."
	@docker run -p 8080:8080 --env-file ../.env saving-advisor-go:latest
