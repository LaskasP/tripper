FROM node:22-alpine AS ui-build

WORKDIR /build
COPY tripper_ui/package.json tripper_ui/package-lock.json ./
RUN npm ci
COPY tripper_ui/ ./
RUN npm run build


FROM python:3.12-slim AS api

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --locked --no-dev
COPY alembic.ini ./
COPY migrations/ migrations/
COPY tripper_api/ tripper_api/
COPY run.py ./

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "tripper_api.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM nginx:1.27-alpine AS ui

COPY --from=ui-build /build/dist/ /usr/share/nginx/html/tripper/
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80