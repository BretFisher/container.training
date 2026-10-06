FROM python:alpine AS base
WORKDIR /app
RUN pip install redis
RUN pip install requests
COPY worker.py .
CMD ["python", "worker.py"]

# worker:v0.2 for the rollout demo: same code, slower loop
FROM base AS slow
ENV WORKER_SLEEP=1.1

# default target (last stage) for Compose, Tilt, and docker build
FROM base
