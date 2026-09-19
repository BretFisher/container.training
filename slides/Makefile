# Slide build and local dev server. Run from the slides/ directory.
SLIDES_PORT ?= 8080

.PHONY: help build serve down clean

help: ## Show this help
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

build: ## Build every deck once, without Docker (needs Python 3 + requirements.txt)
	./build.sh once

# Git facts for the slide footer. The builder container has no .git, so
# markmaker.py reads these from the environment instead.
export REPOSITORY_URL ?= $(shell git config remote.origin.url)
export BRANCH         ?= $(shell git rev-parse --abbrev-ref HEAD)
export COMMIT         ?= $(shell git rev-parse --short HEAD)

serve: ## Build the image, serve slides on http://localhost:$(SLIDES_PORT), rebuild on change
	@echo "Slides: http://localhost:$(SLIDES_PORT)/  (Ctrl-C to stop)"
	SLIDES_PORT=$(SLIDES_PORT) docker compose up --build --watch

down: ## Stop and remove the dev container
	docker compose down

clean: down ## Also remove generated files from a local (non-Docker) build
	rm -f *.yml.html *.yml.html.tmp index.html past.html slides.zip
	rm -rf fragments
