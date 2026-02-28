# PRD — Personal Intelligence Node (PIN)

## 1. Vision

**Personal Intelligence Node (PIN)** — локальный AI-ассистент как ядро персональной цифровой инфраструктуры с возможностью масштабирования в multi-user платформу и закрытую локальную сеть.

Telegram — лишь один из интерфейсов.
LLM — сменяемый компонент.
Все данные — под контролем владельца.

---

# 2. Product Scope

## 2.1 Фаза 1 — Personal OS (MVP)

### Обязательный функционал

#### 1. User Management

* Multi-user архитектура с первого дня
* Регистрация через invite-коды
* Роли: `owner`, `tester`, `user`
* Таймзона на пользователя (IANA)
* Tenant isolation (user_id обязателен в каждой таблице)

#### 2. Calendar & Events

* Создание событий из естественного языка
* Поддержка:

  * даты
  * времени
  * локации
  * тегов
* Исключения:

  * отмена одного occurrence
  * перенос одного occurrence
* Запросы:

  * события на неделю
  * события по тегам
  * события на конкретную дату

#### 3. Reminders

* Напоминания по умолчанию:

  * в день события (утром по логике времени)
  * за 15 минут
* Кастомные смещения
* Persistent scheduler
* Восстановление задач после перезапуска

#### 4. Study Tracking

* Логирование изученного материала
* Автоматическое планирование повторений:

  * +1, +3, +7, +21, +30 дней
* Список повторений на сегодня
* Отметка о выполнении

#### 5. Finance (базовый)

* Accounts
* Transactions
* Income / Expense / Transfer
* Отчёты:

  * расходы за период
  * баланс по счетам
  * средний расход

#### 6. Q&A

* Ответы на произвольные вопросы
* Ответы с учётом данных пользователя
* LLM используется только для:

  * intent detection
  * extraction
  * natural response formatting

---

# 3. Non-Goals (MVP)

* Социальная сеть
* Marketplace инструментов
* Публичная SaaS-платформа
* Enterprise SSO
* Полная автоматизация email workflow

---

# 4. System Architecture

## 4.1 High-Level Architecture

```
Interface Layer
    ├── Telegram
    ├── Web UI (future)
    ├── Local Chat (future)
    └── REST API

Core Application Layer
    ├── Auth & User Management
    ├── Domain Services
    ├── Integration Services
    ├── LLM Gateway
    ├── Scheduler
    └── API Layer

Data Layer
    ├── PostgreSQL
    ├── Redis (future)
    ├── Object Storage (future)
    └── Vector DB (future)

LLM Layer (Pluggable)
    ├── Zveno Adapter
    ├── OpenAI Adapter
    ├── Local vLLM Adapter
    └── Ollama Adapter
```

---

# 5. LLM Strategy

## 5.1 Принципы

* LLM не хранит состояние
* Вся память — в БД
* LLM — stateless reasoning engine
* Используется через unified interface

## 5.2 Pluggable Model Architecture

Интерфейс:

```
chat(messages, model, temperature, max_tokens, response_format)
health()
list_models()
```

Текущий провайдер:

* zveno.ai (google/gemini-3-flash-preview)

Будущие:

* vLLM
* TGI
* Ollama
* любой OpenAI-compatible endpoint

Замена провайдера — изменение конфигурации.

---

# 6. Data Architecture

## 6.1 Multi-Tenant Model

Каждая таблица содержит:

* `user_id`
* (future) `org_id`

Все запросы:

* scoped по user_id
* LLM получает только отфильтрованные данные

## 6.2 Основные таблицы

### users

* user_id
* role
* timezone
* default_reminders
* created_at

### invites

* code
* created_by
* used_by
* expires_at
* used_at

### events

* id
* user_id
* title
* start_at_utc
* end_at_utc
* location
* tags
* created_at

### event_exceptions

* id
* user_id
* event_id
* occurrence_date_local
* status
* moved_start_at_utc
* note

### reminders

* id
* user_id
* event_id
* occurrence_date_local
* scheduled_at_utc
* offset_minutes
* status

### study_items

* id
* user_id
* subject
* topic
* lecture_no
* created_at

### reviews

* id
* user_id
* study_item_id
* due_at
* done_at
* stage

### finance_accounts

* id
* user_id
* name
* currency
* type

### transactions

* id
* user_id
* account_id
* date
* amount
* category
* note
* type

---

# 7. Scheduler System

## Responsibilities

* Reminders
* Study repetitions
* Sync tasks
* Future cron jobs

## Requirements

* Persistent jobs
* Rehydration after restart
* Idempotency
* Graceful failure recovery

Recommended:

* APScheduler (initially)
* Redis/Celery (future scale)

---

# 8. Integration Layer

## Design Principle

Каждый внешний сервис — отдельный Connector.

## Connector Interface

```
connect()
sync()
create()
update()
delete()
```

## Planned Integrations

### iCloud

* Calendar (CalDAV)
* Contacts (CardDAV)
* Mail (IMAP/SMTP)
* Notes (если API доступен)
* Find My (ограниченно, требует изучения API)

### Yandex Mail

* IMAP (read/search)
* SMTP (send)
* OAuth / App Password

## Sync Modes

* On-demand
* Periodic
* Hybrid

---

# 9. Interface Layer

## Telegram

* Gateway
* Не содержит бизнес-логики
* Общается через API Core

## Future Interfaces

* Web UI
* Internal Social Chat
* REST API
* Mobile client (future)

---

# 10. Security

## Principles

* Zero trust between users
* Tenant isolation
* Secrets vault
* Encrypted OAuth storage
* No raw DB exposure to LLM

## LLM Restrictions

* Never access secrets
* Never mix users
* Structured JSON outputs only for actions

---

# 11. Scalability

## Stage 1

* Local machine
* PostgreSQL (docker)
* Zveno API

## Stage 2

* VPS
* Background workers
* Redis

## Stage 3

* Closed local network
* Dedicated LLM server
* GPU inference
* Vector DB
* Multi-agent workflows

---

# 12. Product Roadmap

## Phase 1 (3–6 weeks)

* Core
* Telegram interface
* Calendar + Reminders
* Multi-user
* LLM Gateway
* Scheduler

## Phase 2

* Finance
* Study repetition
* REST API
* Basic Web UI

## Phase 3

* iCloud integration
* Yandex Mail
* OAuth storage
* Sync engine

## Phase 4

* Local LLM deployment
* Vector memory
* Multi-agent orchestration
* Internal social layer

---

# 13. Key Product Differentiators

* Fully local-first architecture
* Model-agnostic
* Multi-interface
* Strong tenant isolation
* Extendable integration framework
* Personal knowledge infrastructure

---

# 14. Risks

## Technical

* Over-engineering early
* Complex integration auth flows
* LLM hallucination without strict JSON schemas
* Scheduler reliability

## Product

* Scope creep
* Feature explosion
* Premature platformization

---

# 15. Strategic Decision

Current Position:

* Personal tool with limited user group
* Built for future platform scale

Recommendation:

* Build clean Core architecture
* Avoid heavy agent frameworks initially
* Keep model abstraction from day one
* Add integrations gradually
