# Интеграционное тестирование. Основы автоматизации тестирования

Практический проект к курсу. Здесь есть всё, чтобы «пощупать» темы курса руками:

| Тема курса | Где в проекте |
|---|---|
| Структура HTTP-запроса и ответа | REST API на FastAPI — `app/main.py`; примеры сырых запросов ниже |
| REST | CRUD для книг: `GET / POST / PUT / DELETE /api/v1/books` |
| SOAP | Мини-сервис `POST /soap` и контракт `GET /soap?wsdl` — `app/soap.py` |
| Swagger / OpenAPI | Swagger UI на `/docs`, спецификация в `openapi/openapi.json` |
| Postman | Коллекция и окружение в `postman/`, запуск через Newman |
| Автоматизация | Тесты на `pytest` + `requests` в `tests/` |
| CI | GitHub Actions — `.github/workflows/ci.yml` |

Данные хранятся в памяти процесса: после перезапуска сервера библиотека возвращается к трём стартовым книгам. Базы данных нет — ничего ставить не нужно.

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

Нужны Python 3.12+ и Node.js 18+ (Node — только для Newman).

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

Без `make`:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8765 --reload
pytest
npx newman run postman/library.postman_collection.json -e postman/local.postman_environment.json
```

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

HTTP — текстовый протокол «запрос → ответ». Ниже реальный обмен с нашим сервером (вывод `curl -v`, сокращён только ответ на создание книги).

**Запрос:**

```http
POST /api/v1/books HTTP/1.1                      ← стартовая строка: метод, путь, версия
Host: 127.0.0.1:8765                             ← заголовки: «ключ: значение»
Authorization: Bearer secret-token
Content-Type: application/json                   ← в каком формате тело
Content-Length: 99                               ← длина тела в байтах
                                                 ← пустая строка отделяет заголовки от тела
{"title":"Мастер и Маргарита","author":"Михаил Булгаков","year":1967}
```

**Ответ:**

```http
HTTP/1.1 201 Created                             ← статусная строка: версия, код, пояснение
date: Tue, 06 Oct 2026 16:57:33 GMT
server: uvicorn
content-type: application/json
content-length: 135
location: /api/v1/books/4                        ← где теперь живёт созданный ресурс
x-request-id: dda50c91-0790-4f71-b954-22368de9729b

{"title":"Мастер и Маргарита","author":"Михаил Булгаков","year":1967,"isbn":null,"available":true,"id":4}
```

Запрос несуществующей книги — у `GET` тела нет, но ответ всё равно содержит описание ошибки:

```http
GET /api/v1/books/42 HTTP/1.1
Host: 127.0.0.1:8765
Accept: */*

HTTP/1.1 404 Not Found
content-type: application/json
content-length: 30

{"detail":"Book 42 not found"}
```

Невалидное тело — `422` и список всех найденных проблем, с указанием, где именно (`loc`):

```json
{"detail": [
  {"type": "string_too_short", "loc": ["body", "title"],  "msg": "String should have at least 1 character"},
  {"type": "missing",          "loc": ["body", "author"], "msg": "Field required"},
  {"type": "value_error",      "loc": ["body", "year"],   "msg": "Value error, year must not be in the future"}
]}
```

Повторить самостоятельно: `curl -v http://127.0.0.1:8765/api/v1/books/1`.

**Методы и их свойства:**

| Метод | Назначение | Безопасный | Идемпотентный | Тело запроса |
|---|---|---|---|---|
| GET | получить | да | да | нет |
| POST | создать | нет | нет — два вызова создадут две книги | да |
| PUT | заменить целиком | нет | да — повтор даёт тот же результат | да |
| PATCH | изменить частично | нет | не обязательно | да |
| DELETE | удалить | нет | да (состояние то же, хотя код второго ответа — 404) | обычно нет |

**Коды состояния**, которые встречаются в проекте:

- `2xx` — успех: `200 OK`, `201 Created` (+ `Location`), `204 No Content` (тела нет совсем).
- `4xx` — ошибка клиента: `401 Unauthorized` (+ `WWW-Authenticate`), `404 Not Found`, `405 Method Not Allowed` (+ `Allow`), `409 Conflict`, `422 Unprocessable Entity`.
- `5xx` — ошибка сервера. В SOAP 1.1 любой `Fault` приходит с `500` — даже если виноват клиент.

Что проверять в ответе при тестировании: код состояния, важные заголовки (`Content-Type`, `Location`, `WWW-Authenticate`), структуру тела (схему) и конкретные значения, а также побочные эффекты — например, что после `DELETE` ресурс действительно недоступен.

### 2. REST и SOAP

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

---

## Практические задания

Начинайте с первого уровня. После каждого изменения запускайте `make check`.

**Уровень 1. HTTP руками**

1. Выполните в терминале `curl -v` для `GET /api/v1/books/1`. Подпишите в выводе стартовую строку, заголовки запроса, статусную строку, заголовки ответа и тело.
2. Создайте книгу через `curl` с токеном и без. Сравните коды и заголовки ответов.
3. Отправьте `DELETE` одной и той же книги дважды. Какие коды пришли? Идемпотентен ли `DELETE`, если коды разные?
4. В Swagger UI найдите, какие коды ответов задокументированы для `PUT /api/v1/books/{book_id}`. Вызовите эндпоинт так, чтобы получить каждый из них.

**Уровень 2. Postman**

5. Создайте окружение *Library API — stage* с другим `baseUrl` (например, порт 9000), запустите сервер на этом порту (`PORT=9000 make run`) и прогоните коллекцию в нём.
6. Добавьте в *List books* запрос с фильтром `?available=false` и тест «у всех книг в ответе `available === false`».
7. Добавьте в *02 CRUD flow* шаг «создать вторую книгу и попытаться через `PUT` присвоить первой её ISBN» — ожидается `409`. Не забудьте удалить вторую книгу.
8. Сломайте тест (например, ожидайте `200` вместо `201`) и посмотрите, как Newman сообщает о падении и какой код возврата у команды (`echo $?`).

**Уровень 3. pytest**

9. Напишите тест: фильтр `author` без совпадений возвращает `200` и пустой массив.
10. Напишите фикстуру `two_books`, которая создаёт две книги и удаляет их после теста. Используйте её в тесте фильтра `available`.
11. Добавьте в параметризованный тест валидации ещё два случая: `author` длиннее 100 символов и `year`, равный `true`. Посмотрите на `type` ошибки во втором случае: почему это `greater_than_equal`, а не ошибка типа? (Подсказка: Pydantic по умолчанию превращает `true` в `1`; почитайте про строгий режим — `strict`.)
12. Напишите тест, что `POST` не идемпотентен: два одинаковых запроса без ISBN создают две книги с разными `id`.

**Уровень 4. Расширяем API (разработка + тесты)**

13. Реализуйте `PATCH /api/v1/books/{id}` — частичное обновление (только переданные поля). Обновите спецификацию (`make openapi`), допишите тесты в pytest и запрос в Postman.
14. Добавьте в SOAP-сервис операцию `AddBook`: элементы в WSDL, обработчик в `app/soap.py`, тесты на успех и на `Fault` при некорректных данных. Сравните, сколько кода понадобилось по сравнению с `POST` в REST.
15. Добавьте пагинацию `?limit=&offset=` в список книг с валидацией (`limit` от 1 до 100). Какие негативные тесты нужны?

**Вопросы для самопроверки**

- Чем `401` отличается от `403`? Где в проекте можно было бы применить `403`?
- Почему для невалидного тела используется `422`, а не `400`?
- Почему SOAP-ошибка «книга не найдена» приходит с кодом `500`, а REST — с `404`? Как это влияет на мониторинг и тесты?
- Что сломается в цепочке Postman, если запустить запрос *Get created book* отдельно, до *Create book*?
- Зачем фикстуре `created_book` удалять книгу после теста, если данные всё равно в памяти?
