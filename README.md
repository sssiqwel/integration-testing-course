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

Каждый ответ содержит заголовок `X-Request-ID`. 


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

# REST: получил книгу 1 

<img width="1658" height="392" alt="image" src="https://github.com/user-attachments/assets/619a4a19-1685-4337-b1c5-cd1123806b76" />

<img width="1018" height="60" alt="image" src="https://github.com/user-attachments/assets/09def310-481d-431a-8450-726416ed386a" />


# Soap  получил первую книгу 

<img width="1702" height="524" alt="image" src="https://github.com/user-attachments/assets/f86d134e-fc27-4730-b48d-21dfcd545110" />

<img width="876" height="72" alt="image" src="https://github.com/user-attachments/assets/b06f1f5a-d75e-4a86-9da7-87a8d3eefde3" />

 # REST: ошибка, книги нет

<img width="958" height="466" alt="image" src="https://github.com/user-attachments/assets/ffddad04-0ebc-4c0e-841f-e47dcc63c537" />

<img width="1168" height="86" alt="image" src="https://github.com/user-attachments/assets/b538db22-eb4c-4358-b97b-283712dd8b77" />

# Soap ошибка,книги нет 

<img width="1674" height="740" alt="image" src="https://github.com/user-attachments/assets/a1d50363-7df0-46e1-8b3d-5eed2bdfee59" />

<img width="1148" height="68" alt="image" src="https://github.com/user-attachments/assets/38d117ff-1343-4725-9443-dfc07901be7a" />

# WSDL-контракт SOAP

<img width="1652" height="920" alt="image" src="https://github.com/user-attachments/assets/17656bf3-094f-4492-b929-47ca88af3ea2" />


<img width="1108" height="74" alt="image" src="https://github.com/user-attachments/assets/0a152cfb-e318-47a8-8f93-766ed63aa9f0" />

### 3. Swagger и OpenAPI

**Swagger**

<img width="1544" height="728" alt="Снимок экрана — 2026-10-09 в 18 33 24" src="https://github.com/user-attachments/assets/0925e658-93ce-4cae-a3e1-2472b086453c" />

**В спецификации заранее описаны тело запроса и все возможные ответы**

<img width="1451" height="708" alt="Снимок экрана — 2026-10-09 в 18 41 33" src="https://github.com/user-attachments/assets/7c6989c7-b2df-4090-a20c-8af12ec6c105" />


<img width="1422" height="927" alt="Снимок экрана — 2026-10-09 в 18 41 53" src="https://github.com/user-attachments/assets/fb1e0a99-129d-4d4e-9654-802c76717211" />


**Схема описывает поля, типы и обязательность**

<img width="2958" height="798" alt="image" src="https://github.com/user-attachments/assets/695e87c1-901b-448e-a09b-8ca1b8b8f2fe" />

<img width="2844" height="576" alt="image" src="https://github.com/user-attachments/assets/9361eaa1-a25c-4a9a-bc92-cc4b9424d23f" />

**Авторизация**
<img width="1256" height="566" alt="image" src="https://github.com/user-attachments/assets/80070f3c-2a65-4bcc-90db-0168544e68c5" />

**Выполнение запроса из Swagger**

<img width="2882" height="1418" alt="image" src="https://github.com/user-attachments/assets/c1306d4f-a621-4888-b38c-04ffa607b5ad" />

**OpenAPI**
В браузере -- http://127.0.0.1:8765/openapi.json

<img width="3244" height="1928" alt="image" src="https://github.com/user-attachments/assets/00051b46-f8ae-4190-b796-512664b2e31d" />

### 4. Postman и Newman

**Postman**

**Запросы сгруппированы по сценариям: сервис, CRUD-цепочка, негативные проверки, SOAP**

<img width="301" height="139" alt="Снимок экрана — 2026-10-09 в 18 57 02" src="https://github.com/user-attachments/assets/253b56fe-5377-4245-a640-6713cab4db1e" />


<img width="2052" height="1228" alt="image" src="https://github.com/user-attachments/assets/21f88b7e-e17c-4473-837f-5055612b060c" />



<img width="2040" height="1270" alt="image" src="https://github.com/user-attachments/assets/c4f578da-8fee-47cd-aa11-41196cef3c01" />



<img width="1424" height="1370" alt="image" src="https://github.com/user-attachments/assets/522480fb-9b8a-4293-a533-7f10c196759e" />



<img width="1440" height="1442" alt="image" src="https://github.com/user-attachments/assets/c5951940-53e0-4fbc-85ab-5bbfaeab2d5a" />



<img width="1422" height="1374" alt="image" src="https://github.com/user-attachments/assets/b96e72bc-4ab7-4496-a06c-2bf851085940" />



<img width="1434" height="1366" alt="image" src="https://github.com/user-attachments/assets/ad040dd5-ee6c-473b-a233-e16575563375" />


**Newman**

<img width="1262" height="904" alt="image" src="https://github.com/user-attachments/assets/58530f6c-c5b3-426d-9361-728cb42cccea" />



<img width="1118" height="800" alt="image" src="https://github.com/user-attachments/assets/c6012f8c-9159-456f-a0ff-f472eaa37c20" />

### 5. Автотесты на pytest


<img width="840" height="460" alt="Снимок экрана — 2026-10-09 в 19 54 59" src="https://github.com/user-attachments/assets/1cd94e82-1190-4762-a715-e1e6546cd5cb" />


<img width="844" height="458" alt="Снимок экрана — 2026-10-09 в 19 54 31" src="https://github.com/user-attachments/assets/86d57eca-6287-4be4-bb43-dbff6ab763e4" />


<img width="852" height="461" alt="Снимок экрана — 2026-10-09 в 19 54 15" src="https://github.com/user-attachments/assets/a7ee3b73-5c5c-41ac-9814-eb06036a91d3" />


### 6. CI

`.github/workflows/ci.yml` на каждый push в `main` и каждый pull request: ставит зависимости, проверяет актуальность `openapi/openapi.json`, поднимает сервер, запускает pytest и Newman, прикладывает отчёты JUnit и лог сервера к запуску.

<img width="3254" height="936" alt="image" src="https://github.com/user-attachments/assets/d379b3a4-258c-4578-8595-fc1ee88d79a7" />
