# Static check: downloads and renders charts, but does not install releases.
FALCO_CHART_VERSION ?= 9.2.0
TALON_CHART_VERSION ?= 0.5.0
RENDER_DIR ?= /tmp/falco-demo-render

.PHONY: render
render: # Download the selected charts and render candidate manifests; no cluster writes.
	@test -n "$(FALCO_CHART_VERSION)" || { echo "Set FALCO_CHART_VERSION to a verified packaged version"; exit 1; }
	@test -n "$(TALON_CHART_VERSION)" || { echo "Set TALON_CHART_VERSION to a verified packaged version"; exit 1; }
	mkdir -p "$(RENDER_DIR)"
	helm template falco-talon falco-talon --repo https://falcosecurity.github.io/charts --version "$(TALON_CHART_VERSION)" --namespace falco -f talon-values.yaml --set-file config.rulesOverride=talon-rules.yaml > "$(RENDER_DIR)/talon.yaml"
	helm template falco falco --repo https://falcosecurity.github.io/charts --version "$(FALCO_CHART_VERSION)" --namespace falco -f falco-values.yaml > "$(RENDER_DIR)/falco.yaml"
