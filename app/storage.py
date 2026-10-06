from threading import Lock

from app.models import Book, BookIn

SEED_BOOKS = [
    BookIn(title="Война и мир", author="Лев Толстой", year=1869, isbn="9785171183668"),
    BookIn(title="Преступление и наказание", author="Фёдор Достоевский", year=1866, isbn="9785041047328"),
    BookIn(title="Пикник на обочине", author="Аркадий и Борис Стругацкие", year=1972, available=False),
]


class DuplicateIsbnError(Exception):
    pass


class BookStorage:
    """Хранилище в памяти. Данные живут, пока запущен процесс сервера."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._books: dict[int, Book] = {}
            self._next_id = 1
        for book in SEED_BOOKS:
            self.create(book)

    def list(self, author: str | None = None, available: bool | None = None) -> list[Book]:
        books = list(self._books.values())
        if author is not None:
            books = [b for b in books if author.lower() in b.author.lower()]
        if available is not None:
            books = [b for b in books if b.available == available]
        return books

    def get(self, book_id: int) -> Book | None:
        return self._books.get(book_id)

    def create(self, data: BookIn) -> Book:
        with self._lock:
            self._ensure_isbn_free(data.isbn)
            book = Book(id=self._next_id, **data.model_dump())
            self._books[book.id] = book
            self._next_id += 1
            return book

    def replace(self, book_id: int, data: BookIn) -> Book | None:
        with self._lock:
            if book_id not in self._books:
                return None
            self._ensure_isbn_free(data.isbn, exclude_id=book_id)
            book = Book(id=book_id, **data.model_dump())
            self._books[book_id] = book
            return book

    def delete(self, book_id: int) -> bool:
        with self._lock:
            return self._books.pop(book_id, None) is not None

    def _ensure_isbn_free(self, isbn: str | None, exclude_id: int | None = None) -> None:
        if isbn is None:
            return
        for book in self._books.values():
            if book.isbn == isbn and book.id != exclude_id:
                raise DuplicateIsbnError(isbn)


storage = BookStorage()
