# AD Editor

Минимальный каркас сервиса для совместной работы над Architecture Document (AD):

- хранение параметров архитектуры в YAML (Git-backed),
- API для редактирования сущностей,
- API для git-операций (branch/checkout/commit/push),
- запуск существующего рендера `tools/adtool.py` для генерации AD.

## Быстрый старт

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

## Конфигурация

Через переменные окружения:

- `AD_EDITOR_REPO_ROOT` — корень git-репозитория.
- `AD_EDITOR_SPECS_DIR` — каталог с архитектурами (по умолчанию `examples/`).
- `AD_EDITOR_OUTPUT_DIR` — куда сохранять сгенерированные документы (по умолчанию `generated/`).
- `AD_EDITOR_ADTOOL` — путь до `tools/adtool.py`.

## Основные endpoint'ы

- `GET /architectures`
- `GET /architectures/{id}/spec/{entity}`
- `PUT /architectures/{id}/spec/{entity}`
- `POST /architectures/{id}/build`
- `GET /git/branches`
- `POST /git/checkout`
- `POST /git/branch`
- `DELETE /git/branch/{name}`
- `POST /git/commit`
- `POST /git/push`

## Какие вводные нужны для production-версии

1. **Модель данных AD**: окончательный список YAML-файлов, обязательные поля, справочники, правила ссылочной целостности.
2. **Git workflow**: naming для веток, политика commit message, кто имеет право push в какие ветки.
3. **Роли и доступы**: минимум роли (architect/reviewer/admin), интеграция с SSO/LDAP.
4. **Требования к аудиту**: какие действия логируем и как долго храним.
5. **Требования к генерации документа**: какие шаблоны/секции обязательны (ISO 42010/MODAF mapping), формат (MD/HTML/PDF).
6. **Операционные требования**: где деплоить (on-prem/k8s), резервное копирование, SLA.
7. **Интеграции**: GitLab/GitHub/Bitbucket, ticketing (Jira), ссылки на диаграммы (draw.io, Miro, EA).
