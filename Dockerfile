# Stage 1: Сборка зависимостей
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка системных зависимостей ТОЛЬКО если нужны для компиляции (раскомментировать при ошибках сборки)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# Кэшируем зависимости отдельно для ускорения пересборки
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Финальный образ
FROM python:3.11-slim-bookworm

WORKDIR /app
ENV PATH="/home/appuser/.local/bin:$PATH"

# Создаём непривилегированного пользователя (требование безопасности Railway)
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && chown appuser:appuser /app
USER appuser

# Копируем установленные зависимости из builder-стадии
COPY --from=builder --chown=appuser:appuser /home/appuser/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

# Порт приложения (обязательно для Railway)
EXPOSE 8000

# HEALTHCHECK для мониторинга (опционально, но рекомендуется)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]