# SchoolHub School Service

Асинхронный FastAPI-микросервис для классов, участников, предметов, расписания,
домашних заданий и школьных событий.

## Архитектура

```text
API -> Service -> Repository -> PostgreSQL
              -> Redis cache
              -> outbox_events (same transaction)
Outbox relay -> Kafka
```

- API отвечает за HTTP-контракты, dependency injection и преобразование ошибок.
- Service проверяет роли и membership, управляет транзакциями и бизнес-правилами.
- Repository содержит только SQLAlchemy 2 запросы и не выполняет `commit()`.
- Изменяющие операции сохраняют бизнес-данные и `DomainEvent` атомарно в PostgreSQL.
- Outbox relay публикует сохранённые события в Kafka с retry/backoff.

## Запуск

Скопируй `.env.example` в `.env`, затем выполни:

```bash
docker compose -f docker-compose.dev.yaml up --build
```

Миграции выполняются отдельным сервисом `migrate`. Приложение не вызывает
`Base.metadata.create_all()` при запуске.

После запуска доступны:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

Проверки состояния:

- `/health` и `/health/live` — liveness без внешних зависимостей;
- `/health/ready` — PostgreSQL, Kafka и outbox relay; недоступный Redis отмечается
  как деградация, но не выключает сервис.

## Авторизация

School Service не валидирует JWT или Telegram initData. Он должен быть доступен за
API Gateway и принимает уже проверенную identity через заголовки:

```text
X-User-ID: <uuid>
X-Telegram-ID: <integer>
X-Global-Role: admin | user
X-Correlation-ID: <optional string>
```

Нельзя публиковать сервис напрямую в недоверенную сеть, пока API Gateway не удаляет
входящие identity-заголовки клиента и не устанавливает собственные проверенные значения.

## API

Все бизнес-маршруты используют prefix `/v1`:

- `/classes` и `/classes/{class_id}`
- `/classes/{class_id}/members`
- `/classes/{class_id}/subjects`
- `/classes/{class_id}/schedule`
- `/classes/{class_id}/schedule/overrides`
- `/classes/{class_id}/homeworks` и `.../history`
- `/classes/{class_id}/events`
- `/classes/{class_id}/days/{date}`

Точный контракт доступен в OpenAPI/Swagger.

## Тесты

```bash
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/e2e -q
```

Unit-тесты используют mock session/repositories/services. Integration и E2E запускают
настоящий PostgreSQL через Testcontainers, поэтому им нужен работающий Docker daemon.

Текущий набор содержит 142 теста:

- 125 unit: repository, services, API, cache, Kafka, outbox relay и readiness;
- 14 integration: repository, service, transactional outbox и API с PostgreSQL;
- 3 E2E flow: class-to-day, замена урока и история домашнего задания.

## Kafka

При запуске через Compose поднимается single-node Kafka в KRaft-режиме. Контейнер
School Service подключается к `kafka:29092`, а с хоста broker доступен через
`localhost:9092`.

Изменяющие API-операции сохраняют подготовленные `DomainEvent` в таблицу
`outbox_events` внутри той же транзакции, что и бизнес-изменения. Затем фоновый relay
читает доступные записи через `FOR UPDATE SKIP LOCKED` и публикует их в topic,
сохранённый вместе с событием. `aggregate_id` используется как message key, поэтому
события одного aggregate попадают в одну partition и сохраняют порядок внутри неё.

Producer и relay создаются один раз в lifespan приложения. Настройки находятся в
секциях `APP_CONFIG__KAFKA__*` и `APP_CONFIG__OUTBOX__*` файла `.env`.

Неуспешная отправка планируется повторно с exponential backoff. После исчерпания
`MAX_ATTEMPTS` запись получает статус `failed` и сохраняет последнюю ошибку. Relay
поддерживает несколько экземпляров сервиса, но семантика доставки остаётся
at-least-once: consumers должны дедуплицировать события по `event_id`.

Заголовок `X-Correlation-ID` переносится во все Kafka-события изменяющих операций.

## Redis

Redis используется как необязательный cache-aside слой:

- расписание на день и неделю;
- список, отдельное домашнее задание и история изменений;
- централизованные версионированные ключи с prefix `school-service:v1`;
- TTL настраивается через `APP_CONFIG__REDIS__DEFAULT_TTL_SECONDS`;
- изменения расписания, предметов и домашних заданий инвалидируют связанные ключи.

Ошибки чтения и записи кэша логируются, после чего сервис продолжает работу через
PostgreSQL. Если Redis недоступен при прямом запуске приложения, startup также
продолжается без кэша. `app/services/events.py` намеренно оставлен без read-through
кэширования как понятный пример для самостоятельного упражнения.

## Логирование

Базовая конфигурация пишет логи в stdout. Сервисы логируют вход и успешный выход
публичных операций, обращения к БД, cache hit/miss, бизнес-валидации, отказы доступа
и неожиданные исключения. Секреты и содержимое домашних заданий в логи не выводятся.

## Observability

В `infrastructure/` находятся:

- Prometheus scrape configuration;
- Grafana provisioning и базовый dashboard;
- Loki с локальным filesystem storage;
- Grafana Alloy для чтения Docker stdout/stderr и label `service`.

Application-level `/metrics` и counters/histograms намеренно не реализованы. До
добавления `/metrics` Prometheus targets приложения будут показываться как недоступные.

## Намеренно оставлено для самостоятельной реализации

- JWT и Telegram auth internals — в Auth Service/API Gateway;
- Kafka consumers в Analytics и Notification Service;
- RabbitMQ publisher/consumer для Telegram-команд;
- расширенное structured/JSON logging, если оно понадобится;
- Prometheus middleware, `/metrics` и business metrics;
- S3/MinIO upload flow для `HomeworkAttachmentORM`.
