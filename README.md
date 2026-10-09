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



<img width="1498" height="400" alt="Лог uvicorn: запуск и остановка сервера make run" src="https://github.com/user-attachments/assets/4a3e9ec0-2e3d-4988-803e-fd318ecac517" />

*Запуск API командой `make run`: uvicorn поднялся на `http://127.0.0.1:8765` с `--reload`, затем сервер остановлен по Ctrl+C — видно штатное завершение (`Application shutdown complete`).*




<img width="480" height="71" alt="Вывод make openapi: спецификация записана в openapi/openapi.json" src="https://github.com/user-attachments/assets/28b20fc0-63c7-4479-9142-114b43016950" />



*Команда `make openapi` запускает `scripts/export_openapi.py` и записывает актуальную спецификацию в `openapi/openapi.json` — так файл в репозитории остаётся в соответствии с кодом API.*



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

Каждый ответ содержит заголовок `X-Request-ID`. 


---

## Теория на примерах из проекта

### 1. Анатомия HTTP-запроса и ответа

#### GET: список книг

<img width="1702" height="422" alt="curl -i GET /api/v1/books — 200 OK, заголовки и JSON-массив книг" src="https://github.com/user-attachments/assets/c2c9ab75-0271-43bc-b953-a60b76699058" />
*Запрос `curl -i GET /api/v1/books` → `HTTP/1.1 200 OK`. Видны все части ответа: стартовая строка, заголовки (`content-type: application/json`, `content-length`, `x-request-id`) и тело — JSON-массив книг. Список книг читается без токена.*

#### GET: одна книга

<img width="1700" height="380" alt="curl -i GET /api/v1/books/2 — 200 OK, одна книга" src="https://github.com/user-attachments/assets/11647c38-5a3d-405e-b585-b1285292853b" />
*Запрос `curl -i GET /api/v1/books/2` → `200 OK`: в теле один объект книги с `id: 2`, в заголовках — `content-type: application/json` и уникальный `x-request-id`.*

#### POST: создать книгу 

<img width="1708" height="750" alt="curl -i POST /api/v1/books с Bearer-токеном — 201 Created и заголовок Location" src="https://github.com/user-attachments/assets/508c7ee5-866e-4635-abe2-d1f78514cbed" />
*Создание книги: `POST /api/v1/books` с заголовками `Authorization: Bearer secret-token` и `Content-Type: application/json` → `201 Created`. Заголовок `location: /api/v1/books/4` указывает на новый ресурс, а в теле сервер вернул книгу с присвоенным `id: 4` и значением по умолчанию `available: true`.*


#### PUT: заменить книгу

<img width="1626" height="820" alt="curl -i PUT /api/v1/books/2 — 200 OK, книга полностью заменена" src="https://github.com/user-attachments/assets/4f2e856f-5fff-47f4-80be-ff1c33e57c89" />
*Полная замена книги: `PUT /api/v1/books/2` с токеном и новым телом → `200 OK`. В ответе обновлённая книга (`"title":"Новое название"`, `"year":2020`), `id` остался прежним — 2.*


#### DELETE: удалить книгу

<img width="1610" height="230" alt="curl -i DELETE /api/v1/books/2 — 204 No Content без тела" src="https://github.com/user-attachments/assets/25238b1f-ecab-43e7-8e53-dc60f25fce45" />
*Удаление: `DELETE /api/v1/books/2` с токеном → `204 No Content`. Тело ответа пустое и нет заголовка `content-type` — значит, удаление прошло успешно.*

#### Негативная проверка(Без токена):


<img width="1514" height="324" alt="curl -i DELETE без заголовка Authorization — 401 Unauthorized" src="https://github.com/user-attachments/assets/38f521a4-36a8-4782-b781-00192c240120" />



*Негативная проверка: `DELETE /api/v1/books/3` без заголовка `Authorization` → `401 Unauthorized`, заголовок `www-authenticate: Bearer`, тело `{"detail":"Missing Authorization header"}`. Изменяющие запросы без токена отклоняются.*


#### Негативная проверка(С неправильным токеном):

<img width="594" height="248" alt="curl -i POST с неверным токеном — 401 Unauthorized, Invalid token" src="https://github.com/user-attachments/assets/f7ee455c-75ac-403d-aea6-03fdc2c54a90" />
*Негативная проверка: `POST /api/v1/books` с `Authorization: Bearer wrong-token` → `401 Unauthorized`, тело `{"detail":"Invalid token"}`. Сервер не только требует заголовок, но и проверяет значение токена.*

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
<img width="1688" height="298" alt="image" src="https://github.com/user-attachments/assets/56c9f9a3-ae33-417e-b0a5-e45a7cfd3c69" />
*Swagger UI REST API: ресурс `books` с операциями `GET`, `POST`, `GET/PUT/DELETE /api/v1/books/{book_id}` и служебный `GET /health`. Замки отмечают изменяющие операции, которым нужен токен. REST-стиль: один ресурс, разные HTTP-методы.*

**SOAP:**
<img width="1696" height="384" alt="image" src="https://github.com/user-attachments/assets/dd66c58f-fe37-4c18-847d-5e74f1ec8c0e" />
*SOAP-контракт `GET /soap?wsdl` в браузере: в `types` описаны XSD-схемы `Book`, `GetBookRequest/Response`, `ListBooksRequest/Response`, ниже — сообщения и `portType LibraryPortType` с операциями `GetBook` и `ListBooks`. В SOAP контракт задан строго, и в нём перечислены все операции.*

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


# REST: получил книгу 1 

<img width="1658" height="392" alt="image" src="https://github.com/user-attachments/assets/619a4a19-1685-4337-b1c5-cd1123806b76" />
*REST: `GET /api/v1/books/1` → `200 OK`, `content-type: application/json`, в теле книга «Война и мир» (Лев Толстой, 1869). Операцию задают метод и URL ресурса, ответ приходит в JSON.*


<img width="1018" height="60" alt="image" src="https://github.com/user-attachments/assets/09def310-481d-431a-8450-726416ed386a" />
*Строка из лога uvicorn: сервер принял `GET /api/v1/books/1` и ответил `200 OK`.*

# Soap  получил первую книгу 

<img width="1702" height="524" alt="image" src="https://github.com/user-attachments/assets/f86d134e-fc27-4730-b48d-21dfcd545110" />
*SOAP: `POST /soap` с `GetBookRequest` (id=1) → `200 OK`, `content-type: text/xml`. В ответе XML-конверт `soap:Envelope/soap:Body/tns:GetBookResponse` с той же книгой «Война и мир». Данные те же, что в REST, но формат — XML-конверт.*

<img width="876" height="72" alt="image" src="https://github.com/user-attachments/assets/b06f1f5a-d75e-4a86-9da7-87a8d3eefde3" />
*Строка из лога uvicorn: SOAP-запрос пришёл как `POST /soap` и получил `200 OK`. Все SOAP-операции идут методом POST на один URL.*

 # REST: ошибка, книги нет

<img width="958" height="466" alt="image" src="https://github.com/user-attachments/assets/ffddad04-0ebc-4c0e-841f-e47dcc63c537" />
*REST: `GET /api/v1/books/9999` → `404 Not Found`, тело `{"detail":"Book 9999 not found"}`. В REST ошибка передаётся HTTP-кодом статуса.*


<img width="1168" height="86" alt="image" src="https://github.com/user-attachments/assets/b538db22-eb4c-4358-b97b-283712dd8b77" />
*Строка из лога uvicorn: `GET /api/v1/books/9999` → `404 Not Found`.*


# Soap ошибка,книги нет 

<img width="1674" height="740" alt="image" src="https://github.com/user-attachments/assets/a1d50363-7df0-46e1-8b3d-5eed2bdfee59" />
*SOAP: `GetBookRequest` с несуществующим id=9999 → `HTTP/1.1 500 Internal Server Error`, в теле `soap:Fault` с `faultcode` `soap:Client` и `faultstring` «Book 9999 not found». По стандарту SOAP 1.1 ошибка передаётся элементом Fault в конверте и статусом 500.*

<img width="1148" height="68" alt="image" src="https://github.com/user-attachments/assets/38d117ff-1343-4725-9443-dfc07901be7a" />
*Строка из лога uvicorn: `POST /soap` → `500 Internal Server Error`. Это ожидаемый ответ на SOAP Fault, а не падение сервера.*


# WSDL-контракт SOAP

<img width="1652" height="920" alt="image" src="https://github.com/user-attachments/assets/17656bf3-094f-4492-b929-47ca88af3ea2" />
*Фрагмент WSDL из терминала: XSD-описания `GetBookRequest` (`id` типа `xsd:int`), `GetBookResponse` (`book` типа `tns:Book`), `ListBooksRequest` и `ListBooksResponse` (список книг, `maxOccurs="unbounded"`). Контракт задаёт типы входных и выходных сообщений.*

<img width="1108" height="74" alt="image" src="https://github.com/user-attachments/assets/0a152cfb-e318-47a8-8f93-766ed63aa9f0" />
*Строка из лога uvicorn: контракт отдан по `GET /soap?wsdl` со статусом `200 OK`.*


### 3. Swagger и OpenAPI

**Swagger**

<img width="1544" height="728" alt="Снимок экрана — 2026-10-09 в 18 33 24" src="https://github.com/user-attachments/assets/0925e658-93ce-4cae-a3e1-2472b086453c" />
*Swagger UI по адресу `/docs`: Library API версии 1.0.0 по спецификации OAS 3.1, ссылка на `/openapi.json`, описание авторизации (`Authorization: Bearer <token>`, кнопка Authorize) и список операций ресурса `books`. Документация генерируется прямо из кода.*


**В спецификации заранее описаны тело запроса и все возможные ответы**

<img width="1451" height="708" alt="Снимок экрана — 2026-10-09 в 18 41 33" src="https://github.com/user-attachments/assets/7c6989c7-b2df-4090-a20c-8af12ec6c105" />
*Операция `POST /api/v1/books` в Swagger: тело запроса обязательно (`required`), тип `application/json`, подставлен пример книги (Булгаков, «Мастер и Маргарита»). Пример и формат тела берутся из спецификации.*

<img width="1422" height="927" alt="Снимок экрана — 2026-10-09 в 18 41 53" src="https://github.com/user-attachments/assets/fb1e0a99-129d-4d4e-9654-802c76717211" />
*Результат Execute: Swagger сформировал `curl` с заголовком `Authorization: Bearer secret-token`, сервер ответил `201`, в теле созданная книга с `id: 4`, в заголовках — `location: /api/v1/books/4` и `x-request-id`. Ниже начинается список ответов из спецификации (`201 Successful Response`).*

<img width="1413" height="941" alt="Снимок экрана — 2026-10-09 в 20 29 08" src="https://github.com/user-attachments/assets/611da254-8f49-4ff7-9adc-ae7f38f8a876" />
*Раздел Schemas: модели `Book`, `BookIn`, `ErrorResponse`, `HTTPValidationError` и `ValidationError`. Все структуры запросов, ответов и ошибок описаны в спецификации.*

**Схема описывает поля, типы и обязательность**

<img width="2958" height="798" alt="image" src="https://github.com/user-attachments/assets/695e87c1-901b-448e-a09b-8ca1b8b8f2fe" />
*Схема `BookIn` (тело POST и PUT): обязательные поля отмечены `*` — `title` (1–200 символов), `author` (1–100), `year` (≥ 1450); `isbn` (string или null) и `available` (boolean) необязательны; `Additional properties: forbidden`. Те же правила проверяет сервер, при нарушении он отвечает 422.*

<img width="2844" height="576" alt="image" src="https://github.com/user-attachments/assets/9361eaa1-a25c-4a9a-bc92-cc4b9424d23f" />


**Авторизация**

<img width="1256" height="566" alt="image" src="https://github.com/user-attachments/assets/80070f3c-2a65-4bcc-90db-0168544e68c5" />
*Окно Authorize: схема `HTTPBearer (http, Bearer)`, подсказка про токен `secret-token` (переменная окружения `API_TOKEN`). После ввода Swagger добавляет заголовок `Authorization` ко всем защищённым запросам.*


**Выполнение запроса из Swagger**

<img width="2882" height="1418" alt="image" src="https://github.com/user-attachments/assets/c1306d4f-a621-4888-b38c-04ffa607b5ad" />
*Запрос из Swagger: `DELETE /api/v1/books/1` с токеном → код `204`. Показаны сгенерированный `curl`, Request URL и заголовки ответа (`date`, `server`, `x-request-id`), тела нет.*

**OpenAPI**
В браузере -- http://127.0.0.1:8765/openapi.json

<img width="3244" height="1928" alt="image" src="https://github.com/user-attachments/assets/00051b46-f8ae-4190-b796-512664b2e31d" />
*Спецификация `/openapi.json`: `"openapi": "3.1.0"`, блок `info` (название, описание, версия 1.0.0) и начало `paths` — `/health` и `GET /api/v1/books` с query-параметрами `author` и `available`. По этому файлу строится Swagger UI, и его можно импортировать в Postman.*

### 4. Postman и Newman

**Postman**

**Запросы сгруппированы по сценариям: сервис, CRUD-цепочка, негативные проверки, SOAP**

<img width="301" height="139" alt="Снимок экрана — 2026-10-09 в 18 57 02" src="https://github.com/user-attachments/assets/253b56fe-5377-4245-a640-6713cab4db1e" />
*Коллекция Postman «Library API — интеграционное тестирование» разбита на папки: `01 Service`, `02 CRUD flow (create -> read -> update -> delete)`, `03 Negative cases`, `04 SOAP`.*


<img width="2052" height="1228" alt="image" src="https://github.com/user-attachments/assets/21f88b7e-e17c-4473-837f-5055612b060c" />
*Запрос `Create book` из папки CRUD flow: `POST {{baseUrl}}/api/v1/books` → `201 Created`, в теле созданная книга с `id: 5`. Адрес берётся из переменной окружения `{{baseUrl}}`. В сайдбаре видна вся цепочка, включая проверки `-> 409` и `-> 404`.*


<img width="2040" height="1270" alt="image" src="https://github.com/user-attachments/assets/c4f578da-8fee-47cd-aa11-41196cef3c01" />
*Запрос `Get updated book`: `GET {{baseUrl}}/api/v1/books/{{bookId}}` → `200 OK`. `id` созданной книги передаётся между запросами через переменную `{{bookId}}`.*


<img width="1424" height="1370" alt="image" src="https://github.com/user-attachments/assets/522480fb-9b8a-4293-a533-7f10c196759e" />
*Запрос `Delete book`: `DELETE {{baseUrl}}/api/v1/books/{{bookId}}` → `204 No Content`, тело пустое. Выбрано окружение «Library API — local».*


<img width="1440" height="1442" alt="image" src="https://github.com/user-attachments/assets/c5951940-53e0-4fbc-85ab-5bbfaeab2d5a" />
*Запрос `Get deleted book -> 404`: после удаления `GET` той же книги возвращает `404 Not Found` и `{"detail": "Book 5 not found"}` — книга действительно удалена.*


<img width="1422" height="1374" alt="image" src="https://github.com/user-attachments/assets/b96e72bc-4ab7-4496-a06c-2bf851085940" />
*Негативный запрос `Create with wrong token -> 401`: `POST {{baseUrl}}/api/v1/books` с неверным токеном → `401 Unauthorized`, `{"detail": "Invalid token"}`.*


<img width="686" height="698" alt="Снимок экрана — 2026-10-09 в 20 03 31" src="https://github.com/user-attachments/assets/25a0038d-b893-422f-939f-fbd34b6dccc4" />
*Прогон всей коллекции в Collection Runner с окружением «Library API — local»: 1 итерация за 577 ms, All tests 88, Passed 88, Failed 0, Errors 0. Видны проверки по каждому запросу: статус, заголовок `X-Request-ID`, время ответа, JSON Schema тела.*


**Newman**

<img width="1262" height="904" alt="image" src="https://github.com/user-attachments/assets/58530f6c-c5b3-426d-9361-728cb42cccea" />
*Запуск коллекции из командной строки через Newman: папки `01 Service` и `02 CRUD flow`, у каждого запроса статус ответа и пройденные проверки (✓), включая `Location header points to the new book` и `Body matches Book schema`.*


<img width="1118" height="800" alt="image" src="https://github.com/user-attachments/assets/c6012f8c-9159-456f-a0ff-f472eaa37c20" />
*Конец прогона Newman: последний запрос `GetBook not found -> Fault` (`500`, проверка `soap:Fault with Client code`) и итоговая таблица — 21 запрос, 42 test-scripts, 88 assertions, в колонке failed везде 0. Коллекция полностью проходит из CLI, так же как в CI.*


### 5. Автотесты на pytest


<img width="840" height="460" alt="Снимок экрана — 2026-10-09 в 19 54 59" src="https://github.com/user-attachments/assets/1cd94e82-1190-4762-a715-e1e6546cd5cb" />
*Запуск `make test`: pytest 8.3.4, конфигурация `pytest.ini`, `testpaths: tests`, собрано 57 тестов. Первые тесты из `test_books_read.py` и `test_books_write.py` (список, фильтры, 404, 422, 401 без токена) — PASSED.*

<img width="844" height="458" alt="Снимок экрана — 2026-10-09 в 19 54 31" src="https://github.com/user-attachments/assets/86d57eca-6287-4be4-bb43-dbff6ab763e4" />
*Продолжение прогона: параметризованный тест `test_create_book_validation_errors_return_422[...]` для каждого правила валидации (пустой и слишком длинный `title`, неверный `year`, `isbn`, лишнее поле и т. д.), а также `duplicate_isbn_returns_409` и тесты PUT — все PASSED.*

<img width="852" height="461" alt="Снимок экрана — 2026-10-09 в 19 54 15" src="https://github.com/user-attachments/assets/a7ee3b73-5c5c-41ac-9814-eb06036a91d3" />
*Окончание прогона: тесты DELETE, полный CRUD-сценарий, служебные проверки (`X-Request-ID`, 404/405, Swagger, актуальность `openapi.json`) и SOAP (WSDL, GetBook, ListBooks, Fault). Итог — `57 passed in 0.12s`, JUnit-отчёт записан в `reports/pytest.xml`.*

### 6. CI

`.github/workflows/ci.yml` на каждый push в `main` и каждый pull request: ставит зависимости, проверяет актуальность `openapi/openapi.json`, поднимает сервер, запускает pytest и Newman, прикладывает отчёты JUnit и лог сервера к запуску.

<img width="1302" height="370" alt="Снимок экрана — 2026-10-09 в 20 05 29" src="https://github.com/user-attachments/assets/1cb83740-95bb-4a0f-a345-3cf717f4ee15" />
*Запуск GitHub Actions по push в `main`: workflow `ci.yml`, job `test` завершился успешно за 22 s (общее время 25 s), Status Success, сохранён 1 артефакт с отчётами.*
