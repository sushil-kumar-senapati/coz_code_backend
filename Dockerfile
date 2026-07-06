# Stage 1: build wheels (keeps pip/build tools out of the final image)
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: runtime
FROM python:3.12-slim
WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY . .
RUN mkdir -p uploads

EXPOSE 8000

# Do NOT use run.py in production — it sets reload=True
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
