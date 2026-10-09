# Интеграционное тестирование. Основы автоматизации тестирования

| Тема курса | Где в проекте |
|---|---|
| Структура HTTP-запроса и ответа | REST API на FastAPI — `app/main.py`; примеры сырых запросов ниже |
| REST | CRUD для книг: `GET / POST / PUT / DELETE /api/v1/books` |
| SOAP | Мини-сервис `POST /soap` и контракт `GET /soap?wsdl` — `app/soap.py` |
| Swagger / OpenAPI | Swagger UI на `/docs`, спецификация в `openapi/openapi.json` |
| Postman | Коллекция и окружение в `postman/`, запуск через Newman |
| Автоматизация | Тесты на `pytest` + `requests` в `tests/` |
| CI | GitHub Actions — `.github/workflows/ci.yml` |

Данные хранятся в памяти процесса: после перезапуска сервера библиотека возвращается к трём стартовым книгам.

## Структура

```
app/
  main.py        REST-эндпоинты, middleware X-Request-ID
  models.py      Pydantic-модели: правила валидации полей (→ ошибки 422)
  auth.py        Проверка заголовка Authorization: Bearer <token>
  storage.py     Хранилище в памяти + стартовые данные
  soap.py        SOAP 1.1 сервис и WSDL, написан вручную на xml.etree
tests/
  conftest.py    Фикстуры: клиент API, токен, создание/удаление книги
  test_*.py      Позитивные и негативные проверки REST и SOAP
postman/
  library.postman_collection.json   Коллекция с pm.test-проверками
  local.postman_environment.json    Окружение: baseUrl и token
openapi/openapi.json                Выгруженная спецификация OpenAPI 3.1
scripts/
  export_openapi.py                 Пересоздать openapi/openapi.json
  with_server.sh                    Поднять сервер, выполнить команду, остановить
Makefile                            Короткие команды для всего вышеперечисленного
```

## Быстрый старт

Python 3.12+ и Node.js 18+ (Node — только для Newman)

```bash
make install     # создаст .venv и установит зависимости из requirements.txt
make run         # API на http://127.0.0.1:8765, Swagger UI — http://127.0.0.1:8765/docs
```

В другом терминале:

```bash
make test        # pytest; если сервер не запущен, тесты поднимут его сами
make newman      # Postman-коллекция через Newman (сервер тоже поднимется сам)
make check       # pytest + newman одной командой
make openapi     # обновить openapi/openapi.json после изменения API
```



<img width="1498" height="400" alt="image" src="https://github.com/user-attachments/assets/4a3e9ec0-2e3d-4988-803e-fd318ecac517" />


<img width="1650" height="920" alt="image" src="https://github.com/user-attachments/assets/ca0f7783-65b6-45a7-b6a0-1eea0b7834a2" />


<img width="1246" height="752" alt="image" src="https://github.com/user-attachments/assets/234578ca-37e8-44eb-bc71-b236bcd6affd" />



<img width="480" height="71" alt="Снимок экрана — 2026-10-09 в 17 12 05" src="https://github.com/user-attachments/assets/28b20fc0-63c7-4479-9142-114b43016950" />



Отчёты в формате JUnit складываются в `reports/` (`pytest.xml`, `newman.xml`).

Порт и токен меняются переменными окружения: `PORT=9000 make run`, `API_TOKEN=my-token make run`. Тестам нужно передать те же значения (`PORT`, `API_TOKEN` или `BASE_URL`).

## API

Базовый адрес: `http://127.0.0.1:8765`. Изменяющие запросы требуют заголовок `Authorization: Bearer secret-token`.

| Метод | Путь | Токен | Успех | Ошибки |
|---|---|---|---|---|
| GET | `/health` | — | 200 | — |
| GET | `/api/v1/books?author=&available=` | — | 200 | 422 — неверный параметр |
| GET | `/api/v1/books/{id}` | — | 200 | 404, 422 — id не число |
| POST | `/api/v1/books` | да | 201 + `Location` | 401, 409 — ISBN занят, 422 |
| PUT | `/api/v1/books/{id}` | да | 200 | 401, 404, 409, 422 |
| DELETE | `/api/v1/books/{id}` | да | 204, пустое тело | 401, 404 |
| GET | `/soap?wsdl` | — | 200, WSDL | — |
| POST | `/soap` | — | 200, SOAP-ответ | 500 + `soap:Fault` |

Книга:

```json
{
  "id": 1,
  "title": "Война и мир",
  "author": "Лев Толстой",
  "year": 1869,
  "isbn": "9785171183668",
  "available": true
}
```

Правила валидации (`app/models.py`): `title` 1–200 символов и не из одних пробелов, `author` 1–100, `year` от 1450 до текущего года, `isbn` — 13 цифр, начинается с 978/979, необязателен и уникален, `available` — boolean (по умолчанию `true`). Неизвестные поля запрещены. `id` назначает сервер.

Каждый ответ содержит заголовок `X-Request-ID`. Если клиент прислал свой `X-Request-ID`, сервер вернёт его же — так запрос удобно искать в логах.


---

## Теория на примерах из проекта

### 1. Анатомия HTTP-запроса и ответа

# GET: список книг

<img width="1702" height="422" alt="image" src="https://github.com/user-attachments/assets/c2c9ab75-0271-43bc-b953-a60b76699058" />

# GET: одна книга

<img width="1700" height="380" alt="image" src="https://github.com/user-attachments/assets/11647c38-5a3d-405e-b585-b1285292853b" />

# POST: создать книгу 

<img width="1708" height="750" alt="image" src="https://github.com/user-attachments/assets/508c7ee5-866e-4635-abe2-d1f78514cbed" />


# PUT: заменить книгу

<img width="1626" height="820" alt="image" src="https://github.com/user-attachments/assets/4f2e856f-5fff-47f4-80be-ff1c33e57c89" />


# DELETE: удалить книгу

<img width="1610" height="230" alt="image" src="https://github.com/user-attachments/assets/25238b1f-ecab-43e7-8e53-dc60f25fce45" />

# Негативная проверка(Без токена):

<img width="1514" height="324" alt="image" src="https://github.com/user-attachments/assets/38f521a4-36a8-4782-b781-00192c240120" />


# Негативная проверка(С токеном):

<img width="594" height="248" alt="Снимок экрана — 2026-10-09 в 17 23 41" src="https://github.com/user-attachments/assets/f7ee455c-75ac-403d-aea6-03fdc2c54a90" />

Невалидное тело — `422` и список всех найденных проблем, с указанием, где именно (`loc`):

```json
{"detail": [
  {"type": "string_too_short", "loc": ["body", "title"],  "msg": "String should have at least 1 character"},
  {"type": "missing",          "loc": ["body", "author"], "msg": "Field required"},
  {"type": "value_error",      "loc": ["body", "year"],   "msg": "Value error, year must not be in the future"}
]}
```
### 2. REST и SOAP

**REST:**
<img width="2998" height="1208" alt="image" src="https://github.com/user-attachments/assets/42d29d63-dfb9-4dfc-b16e-6b8ea30cf9f9" />

**SOAP:**
<img width="3282" height="1976" alt="image" src="https://github.com/user-attachments/assets/339254b0-23f9-45c7-a9f8-73a9cd1e13e8" />


В проекте одни и те же данные отдаются двумя способами. Получить книгу № 1:

**REST:**

```http
GET /api/v1/books/1 HTTP/1.1
Host: 127.0.0.1:8765
Accept: application/json
```

**SOAP:**

```http
POST /soap HTTP/1.1
Host: 127.0.0.1:8765
Content-Type: text/xml; charset=utf-8
SOAPAction: "http://example.com/library/GetBook"

<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="http://example.com/library">
  <soap:Body>
    <tns:GetBookRequest><tns:id>1</tns:id></tns:GetBookRequest>
  </soap:Body>
</soap:Envelope>
```

Ответ SOAP — тоже конверт:

```xml
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tns="http://example.com/library">
  <soap:Body>
    <tns:GetBookResponse>
      <tns:book>
        <tns:id>1</tns:id><tns:title>Война и мир</tns:title><tns:author>Лев Толстой</tns:author>
        <tns:year>1869</tns:year><tns:isbn>9785171183668</tns:isbn><tns:available>true</tns:available>
      </tns:book>
    </tns:GetBookResponse>
  </soap:Body>
</soap:Envelope>
```

| | REST | SOAP |
|---|---|---|
| Что это | Архитектурный стиль | Протокол со строгим стандартом |
| Формат | Любой, чаще JSON | Только XML, обязательно `Envelope` / `Body` |
| Операция определяется | Методом HTTP + URL ресурса (`GET /books/1`) | Элементом в теле и `SOAPAction` (`GetBookRequest`); почти всегда `POST` на один URL |
| Контракт | Необязателен; обычно OpenAPI (`/openapi.json`) | WSDL (`/soap?wsdl`) — часть стандарта |
| Ошибки | Коды HTTP: 404, 422… | `soap:Fault` с `faultcode`/`faultstring`, HTTP 500 |
| Кеширование | Работает для `GET` из коробки | Практически нет — всё через `POST` |
| Где встречается | Веб и мобильные API, микросервисы | Банки, госсистемы, интеграции «enterprise» |

Что это значит для тестировщика: в REST проверяем код состояния и JSON; в SOAP код почти всегда 200 или 500, а суть ответа — внутри XML (успешный элемент или `Fault`). Посмотрите `tests/test_soap.py` и папку *04 SOAP* в Postman-коллекции.

### 3. Swagger и OpenAPI

**OpenAPI** — формат описания REST API (эндпоинты, параметры, схемы тел, коды ответов, авторизация). **Swagger UI** — интерактивная страница, построенная по этому описанию.

FastAPI генерирует спецификацию из кода: типы параметров и Pydantic-модели превращаются в схемы, `responses=` в декораторах — в описания ошибок.

- `http://127.0.0.1:8765/docs` — Swagger UI. Нажмите **Authorize**, введите `secret-token`, затем на любом эндпоинте **Try it out → Execute**. Swagger покажет и `curl`-команду, и полный ответ с заголовками.
- `http://127.0.0.1:8765/redoc` — та же спецификация в виде документации.
- `http://127.0.0.1:8765/openapi.json` — сама спецификация. Копия лежит в `openapi/openapi.json`; тест `test_exported_openapi_spec_is_up_to_date` и CI падают, если её забыли обновить (`make openapi`).

Спецификацию можно импортировать в Postman: *Import → openapi/openapi.json* — получится коллекция-заготовка со всеми запросами.

SOAP-эндпоинт намеренно скрыт из OpenAPI: его контракт описывает WSDL.

### 4. Postman и Newman

Откройте Postman → *Import* → выберите оба файла из `postman/`, справа вверху выберите окружение **Library API — local**.

Что посмотреть в коллекции:

- **Переменные окружения** `{{baseUrl}}` и `{{token}}` — один и тот же набор запросов можно направить на другой стенд, просто сменив окружение.
- **Авторизация на уровне коллекции** — Bearer `{{token}}` наследуется всеми запросами. В негативных запросах она переопределена: *No Auth* или неверный токен.
- **Скрипт коллекции (Tests)** выполняется после каждого запроса: проверяет `X-Request-ID` и время ответа.
- **Pre-request Script** в *Create book* генерирует уникальный ISBN и кладёт его в переменную `isbn`.
- **Цепочка** в папке *02 CRUD flow*: *Create* сохраняет `id` из ответа (`pm.collectionVariables.set("bookId", ...)`), следующие запросы используют `{{bookId}}`: прочитать → обновить → удалить → убедиться, что 404.
- **Проверки** `pm.test(...)`: код (`pm.response.to.have.status`), заголовки (`to.have.header`), схема тела (`to.have.jsonSchema`), значения (`pm.expect(...)`).

Запуск всей коллекции: в Postman — *Run collection*; из консоли — Newman:

```bash
make newman
# или напрямую, при запущенном сервере:
npx newman run postman/library.postman_collection.json -e postman/local.postman_environment.json
```

Запросы цепочки зависят друг от друга, поэтому папку *02* нужно запускать целиком и по порядку.

### 5. Автотесты на pytest

`tests/conftest.py` — общие фикстуры:

- `base_url` (на всю сессию) — проверяет `/health`; если сервер не запущен, стартует `uvicorn` в подпроцессе и гасит его в конце.
- `api` — `requests.Session` с базовым URL: в тестах пишем просто `api.get("/api/v1/books")`.
- `auth_headers`, `book_payload` — токен и валидное тело с уникальным ISBN.
- `created_book` — **setup/teardown**: до `yield` создаёт книгу, после теста удаляет. Тест получает готовые данные и не оставляет мусора.

Тест строится по схеме *Arrange — Act — Assert*:

```python
def test_get_book_by_id(api, created_book):          # Arrange: книга создана фикстурой
    response = api.get(f"/api/v1/books/{created_book['id']}")   # Act

    assert response.status_code == 200               # Assert
    assert response.json() == created_book
```

`@pytest.mark.parametrize` позволяет одной функцией проверить много негативных случаев — см. `test_create_book_validation_errors_return_422` (12 вариантов невалидного тела).

Полезные запуски:

```bash
pytest -k soap                 # только тесты, в имени которых есть «soap»
pytest tests/test_books_write.py::test_full_crud_flow
pytest -x                      # остановиться на первом падении
BASE_URL=http://stage:8765 pytest   # прогнать тесты против другого стенда
```

### 6. CI

`.github/workflows/ci.yml` на каждый push в `main` и каждый pull request: ставит зависимости, проверяет актуальность `openapi/openapi.json`, поднимает сервер, запускает pytest и Newman, прикладывает отчёты JUnit и лог сервера к запуску.

<img width="3254" height="936" alt="image" src="https://github.com/user-attachments/assets/d379b3a4-258c-4578-8595-fc1ee88d79a7" />
