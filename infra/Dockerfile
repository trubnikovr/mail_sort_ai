FROM python:3.12-slim

ARG SERVICE=migrations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY infra/run_mail_services.py ./infra/run_mail_services.py

COPY packages/contracts ./packages/contracts
COPY packages/database ./packages/database
COPY packages/logging ./packages/logging
COPY packages/alerts ./packages/alerts
COPY apps/mail-collector ./apps/mail-collector
COPY apps/mail-decision ./apps/mail-decision
COPY apps/mail-router ./apps/mail-router
COPY apps/mail-alerts ./apps/mail-alerts
COPY apps/mail-health ./apps/mail-health

RUN pip install --no-cache-dir \
      ./packages/contracts \
      ./packages/database \
      ./packages/logging \
      ./packages/alerts \
    && if [ "$SERVICE" = "mail-app" ]; then \
         pip install --no-cache-dir \
           ./apps/mail-collector \
           ./apps/mail-decision \
           ./apps/mail-router; \
       elif [ "$SERVICE" != "migrations" ]; then \
         pip install --no-cache-dir "./apps/$SERVICE"; \
       fi

CMD ["python", "-m", "alembic", "-c", "packages/database/alembic.ini", "upgrade", "head"]
