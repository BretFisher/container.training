# syntax=docker/dockerfile:1
# Slide dev server (see compose.yaml and Makefile). Netlify does not use it.
#
# Build context is the repository root, because slides pull manifests from
# ../k8s with @@INCLUDE[k8s/...]. Dockerfile.dockerignore limits the context
# to slides/ and k8s/. The sources baked in here are the baseline; Compose
# watch syncs edits on top and re-runs ./build.sh once.
ARG PYTHON_VERSION=3.14-alpine
ARG PYTHON_DIGEST=sha256:2e740b2c28a426e74f11396c05e38afb3191acced75045b8d62df573c1dc8ce8

FROM python:${PYTHON_VERSION}@${PYTHON_DIGEST} AS builder

# zip: build.sh creates slides.zip when SLIDES_ZIP=1.
RUN apk add --no-cache zip

WORKDIR /repo/slides
COPY slides/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

COPY k8s /repo/k8s
COPY slides /repo/slides

EXPOSE 80
# Build the selected deck (or all decks), then serve. Compose watch execs
# ./build.sh once into this same container after each source change.
CMD ["sh", "-c", "./build.sh once && exec python -m http.server 80"]
