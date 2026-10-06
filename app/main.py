import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status

from app import soap
from app.auth import require_token
from app.models import Book, BookIn, ErrorResponse
from app.storage import DuplicateIsbnError, storage

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Library API",
    version="1.0.0",
    description=(
        "Учебный REST API библиотеки для курса «Интеграционное тестирование».\n\n"
        "Чтение (`GET`) доступно всем. Создание, изменение и удаление требуют заголовка "
        "`Authorization: Bearer <token>` — нажмите **Authorize** и введите `secret-token`.\n\n"
        "Для сравнения с SOAP есть эндпоинт `/soap` (WSDL: `GET /soap?wsdl`)."
    ),
    openapi_tags=[
        {"name": "books", "description": "CRUD для книг"},
        {"name": "service", "description": "Служебные эндпоинты"},
    ],
)

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Книга не найдена"}}
UNAUTHORIZED = {401: {"model": ErrorResponse, "description": "Нет токена или токен неверный"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Книга с таким ISBN уже есть"}}


@app.middleware("http")
async def request_id_header(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def get_book_or_404(book_id: int) -> Book:
    book = storage.get(book_id)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@app.get("/health", tags=["service"], summary="Проверка, что сервер жив")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(f"{API_PREFIX}/books", tags=["books"], summary="Список книг")
def list_books(
    author: str | None = Query(default=None, description="Фильтр по части имени автора"),
    available: bool | None = Query(default=None, description="Фильтр по наличию"),
) -> list[Book]:
    return storage.list(author=author, available=available)


@app.get(f"{API_PREFIX}/books/{{book_id}}", tags=["books"], summary="Книга по id", responses=NOT_FOUND)
def get_book(book_id: int) -> Book:
    return get_book_or_404(book_id)


@app.post(
    f"{API_PREFIX}/books",
    tags=["books"],
    summary="Создать книгу",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_token)],
    responses={**UNAUTHORIZED, **CONFLICT},
)
def create_book(data: BookIn, response: Response) -> Book:
    try:
        book = storage.create(data)
    except DuplicateIsbnError:
        raise HTTPException(status_code=409, detail=f"Book with ISBN {data.isbn} already exists")
    response.headers["Location"] = f"{API_PREFIX}/books/{book.id}"
    return book


@app.put(
    f"{API_PREFIX}/books/{{book_id}}",
    tags=["books"],
    summary="Полностью заменить книгу",
    dependencies=[Depends(require_token)],
    responses={**UNAUTHORIZED, **NOT_FOUND, **CONFLICT},
)
def replace_book(book_id: int, data: BookIn) -> Book:
    try:
        book = storage.replace(book_id, data)
    except DuplicateIsbnError:
        raise HTTPException(status_code=409, detail=f"Book with ISBN {data.isbn} already exists")
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return book


@app.delete(
    f"{API_PREFIX}/books/{{book_id}}",
    tags=["books"],
    summary="Удалить книгу",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_token)],
    responses={**UNAUTHORIZED, **NOT_FOUND},
)
def delete_book(book_id: int) -> Response:
    if not storage.delete(book_id):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app.include_router(soap.router)
