# gateway image. Build context is the REPO ROOT so we can copy the shared libs:
#     docker build -f services/gateway/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# Shared libs first. The gateway needs documind_contracts (LoginRequest etc.)
# and documind_common only for the shared structlog logging setup.
COPY libs/ /libs/
RUN pip install --no-cache-dir /libs/documind_contracts /libs/documind_common

COPY services/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/gateway/app ./app

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
