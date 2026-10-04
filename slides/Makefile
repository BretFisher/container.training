# Slide build and local dev server. Run from the slides/ directory.
SLIDES_PORT ?= 8080

.PHONY: help build build-dev serve down clean labtest-plan labtest labtest-watch labtest-stop

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

build: ## Build every deck once, without Docker (needs Python 3 + requirements.txt)
	./build.sh once

build-dev: ## Like build, but footers show each slide's file and #anchor
	SLIDES_DEV=1 ./build.sh once

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

# Lab tests (see labtest/README.md). Examples:
#   make labtest-plan DECK=kube-sec-twodays.yml
#   make labtest DECK=kube-sec-twodays.yml TAG=bret ONLY="k8s/daemonset.md k8s/rollout.md"
#   make labtest DECK=kube-sec-twodays.yml TAG=bret FROM=k8s/daemonset.md TO=k8s/rollout.md
DECK    ?= kube-sec-twodays.yml
TAG     ?=
ONLY    ?=
FROM    ?=
TO      ?=
LABTEST_SELECT = $(foreach f,$(ONLY),--only $(f)) $(if $(FROM),--from $(FROM)) $(if $(TO),--to $(TO))

labtest-plan: ## List the lab commands of DECK and the ones that probably hang (no lab needed)
	python3 labtest/labtest.py plan $(DECK) $(LABTEST_SELECT)

labtest: ## Run the labs of DECK on lab TAG (ONLY=, FROM=, TO= select files)
	@test -n "$(TAG)" || { echo "Set TAG=<lab tag>, see prepare-labs/tags/"; exit 1; }
	python3 labtest/labtest.py run $(DECK) --tag $(TAG) $(LABTEST_SELECT)

labtest-watch: ## Watch the test terminal on lab TAG live (read-only)
	python3 labtest/labtest.py watch --tag $(TAG)

labtest-stop: ## Stop a lab test that runs on lab TAG
	python3 labtest/labtest.py stop --tag $(TAG)
