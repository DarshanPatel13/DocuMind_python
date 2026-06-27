# query-service image. Build context is the REPO ROOT so we can copy the shared
# libs alongside the service:
#     docker build -f services/query-service/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# 1. Shared libraries first (best caching).
COPY libs/ /libs/
RUN pip install --no-cache-dir /libs/documind_contracts /libs/documind_common

# 2. Service deps.
COPY services/query-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Service code.
COPY services/query-service/app ./app

EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
