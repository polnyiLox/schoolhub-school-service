# SchoolHub School Service

Асинхронный FastAPI-микросервис для классов, участников, предметов, расписания,
домашних заданий и школьных событий.

## Архитектура

```text
API -> Service -> Repository -> PostgreSQL
```

- API отвечает за HTTP-контракты, dependency injection и преобразование ошибок.
- Service проверяет роли и membership, управляет транзакциями и бизнес-правилами.
- Repository содержит только SQLAlchemy 2 запросы и не выполняет `commit()`.
- Изменяющие операции формируют `DomainEvent` в `pending_events`, но не публикуют его.

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
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/e2e -q
```

Unit-тесты используют mock session/repositories/services. Integration и E2E запускают
настоящий PostgreSQL через Testcontainers, поэтому им нужен работающий Docker daemon.

## Observability

В `infrastructure/` находятся:

- Prometheus scrape configuration;
- Grafana provisioning и базовый dashboard;
- Loki с локальным filesystem storage;
- Grafana Alloy для чтения Docker stdout/stderr и label `service`.

Application-level `/metrics`, counters/histograms и настройка Python logging намеренно
не реализованы. До добавления `/metrics` Prometheus targets приложения будут показываться
как недоступные.

## Намеренно оставлено для самостоятельной реализации

- JWT и Telegram auth internals — в Auth Service/API Gateway;
- Kafka producer/consumer и публикация `service.drain_events()`;
- RabbitMQ publisher/consumer для Telegram-команд;
- Redis cache, в первую очередь для расписания класса на дату;
- `configure_logging()` и structured logging;
- Prometheus middleware, `/metrics` и business metrics;
- S3/MinIO upload flow для `HomeworkAttachmentORM`.
