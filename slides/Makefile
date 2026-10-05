# Slide build and local dev server. Run from the slides/ directory.
SLIDES_PORT ?= 8080
PYTHON ?= python3
export SLIDES_DECK ?=

.PHONY: help build build-dev serve zip down clean labtest-plan labtest labtest-watch labtest-stop

help: ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

build: ## Build slides once; SLIDES_DECK=filename.yml selects one deck (needs requirements.txt)
	./build.sh once

build-dev: ## Like build, but footers show each slide's file and #anchor
	SLIDES_DEV=1 ./build.sh once

.PHONY: test-markmaker
test-markmaker: ## Test compiler, build selection, and navigation (needs requirements.txt)
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

# Git facts for the slide footer. The builder container has no .git, so
# markmaker.py reads these from the environment instead.
export REPOSITORY_URL ?= $(shell git config remote.origin.url)
export BRANCH         ?= $(shell git rev-parse --abbrev-ref HEAD)
export COMMIT         ?= $(shell git rev-parse --short HEAD)

serve: ## Serve with foreground Compose watch; SLIDES_DECK=filename.yml selects one deck
	@./build.sh check
	@if [ -n "$$SLIDES_DECK" ]; then printf 'Serving deck: %s\n' "$$SLIDES_DECK"; else printf 'Serving all decks.\n'; fi
	SLIDES_PORT=$(SLIDES_PORT) docker compose up --build --watch

# Same build as Netlify (no dev footers), in the dev image, so the host
# needs no Python packages. Only slides.zip comes back to this directory.
zip: ## Build every deck and slides.zip in Docker, like Netlify; copy slides.zip here
	docker compose build
	docker compose run --rm -e SLIDES_ZIP=1 -e SLIDES_DEV=0 -e SLIDES_DECK= -v "$(CURDIR):/out" slides \
		sh -c './build.sh once && cp slides.zip /out/'
	@echo "Created $(CURDIR)/slides.zip"

down: ## Stop and remove the dev container
	docker compose down

clean: down ## Also remove generated files from a local (non-Docker) build
	rm -f *.yml.html *.yml.html.tmp index.html past.html slides.zip
	rm -rf fragments

# Lab tests (see labtest/README.md). Examples:
#   make labtest-plan SLIDES_DECK=kube-sec-twodays.yml
#   make labtest SLIDES_DECK=kube-sec-twodays.yml TAG=bret ONLY="k8s/daemonset.md k8s/rollout.md"
#   make labtest SLIDES_DECK=kube-sec-twodays.yml TAG=bret FROM=k8s/daemonset.md TO=k8s/rollout.md
#   make labtest TAG=bret LOCAL=1 ONLY=k8s/kyverno-colors.md   (test changes that are not pushed)
TAG     ?=
ONLY    ?=
FROM    ?=
TO      ?=
LABTEST_SELECT = $(foreach f,$(ONLY),--only $(f)) $(if $(FROM),--from $(FROM)) $(if $(TO),--to $(TO))

labtest-plan: ## List the lab commands of SLIDES_DECK and the ones that probably hang (no lab needed)
	python3 labtest/labtest.py plan "$${SLIDES_DECK:-kube-sec-twodays.yml}" $(LABTEST_SELECT)

labtest: ## Run the labs of SLIDES_DECK on lab TAG (ONLY=, FROM=, TO= select files; LOCAL=1 uses this checkout)
	@test -n "$(TAG)" || { echo "Set TAG=<lab tag>, see prepare-labs/tags/"; exit 1; }
	python3 labtest/labtest.py run "$${SLIDES_DECK:-kube-sec-twodays.yml}" --tag $(TAG) $(LABTEST_SELECT) $(if $(LOCAL),--local-repo)

labtest-watch: ## Watch the test terminal on lab TAG live (read-only)
	python3 labtest/labtest.py watch --tag $(TAG)

labtest-stop: ## Stop a lab test that runs on lab TAG
	python3 labtest/labtest.py stop --tag $(TAG)

# Validate the checked-in Helm examples without a Kubernetes cluster.
.PHONY: helm-labs-check
helm-labs-check: ## Build dependencies and lint/render the Helm lab charts (needs Helm 4.3.0)
	helm dependency build ../k8s/helm-labs/dockercoins-deps
	@set -e; for chart in schema-check redis dockercoins-deps; do \
		helm lint ../k8s/helm-labs/$$chart; \
		helm template check ../k8s/helm-labs/$$chart > /dev/null; \
	done
