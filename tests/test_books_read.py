BOOK_FIELDS = {"id", "title", "author", "year", "isbn", "available"}


def test_list_books_returns_array_of_books(api):
    response = api.get("/api/v1/books")

    assert response.status_code == 200
    books = response.json()
    assert isinstance(books, list)
    assert len(books) >= 1
    for book in books:
        assert set(book) == BOOK_FIELDS
        assert isinstance(book["id"], int)


def test_list_contains_created_book(api, created_book):
    ids = [b["id"] for b in api.get("/api/v1/books").json()]

    assert created_book["id"] in ids


def test_filter_by_author_is_case_insensitive(api, created_book):
    response = api.get("/api/v1/books", params={"author": "тестировщиков"})

    assert response.status_code == 200
    books = response.json()
    assert created_book["id"] in [b["id"] for b in books]
    assert all("тестировщиков" in b["author"].lower() for b in books)


def test_filter_by_availability(api):
    books = api.get("/api/v1/books", params={"available": "false"}).json()

    assert books
    assert all(b["available"] is False for b in books)


def test_invalid_query_param_returns_422(api):
    response = api.get("/api/v1/books", params={"available": "maybe"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "available"]


def test_get_book_by_id(api, created_book):
    response = api.get(f"/api/v1/books/{created_book['id']}")

    assert response.status_code == 200
    assert response.json() == created_book


def test_get_missing_book_returns_404(api):
    response = api.get("/api/v1/books/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Book 999999 not found"}


def test_get_book_with_non_integer_id_returns_422(api):
    response = api.get("/api/v1/books/abc")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "book_id"]


def test_read_does_not_require_auth(api):
    response = api.get("/api/v1/books", headers={"Authorization": "Bearer wrong"})

    assert response.status_code == 200
