# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app
COPY . /app
# One dependency/build layer avoids duplicating the full PyTorch tree at every
# COPY/RUN under the managed environment's vfs Docker storage driver.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export SSL_CERT_FILE=/run/secrets/proxy_ca PIP_CERT=/run/secrets/proxy_ca GIT_SSL_CAINFO=/run/secrets/proxy_ca; fi; \
    apt-get update && apt-get install -y --no-install-recommends build-essential git ca-certificates && \
    pip install --no-cache-dir -r requirements.lock --extra-index-url https://download.pytorch.org/whl/cpu && \
    sh scripts/install_diffvg.sh && \
    pip install --no-deps --no-build-isolation -e . && \
    rm -rf /tmp/hachi-diffvg /root/.cache/pip /var/lib/apt/lists/*
CMD ["python", "-m", "pytest", "-q"]
