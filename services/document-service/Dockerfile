# document-service image. Build context is the REPO ROOT so we can copy the
# shared libs alongside the service:
#     docker build -f services/document-service/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# 1. Install the shared libraries first (changes least often -> best caching).
COPY libs/ /libs/
RUN pip install --no-cache-dir /libs/documind_contracts /libs/documind_common

# 2. Service deps.
COPY services/document-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Service code.
COPY services/document-service/app ./app

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
