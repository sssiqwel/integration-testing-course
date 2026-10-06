from datetime import date

import pytest

from conftest import random_isbn

BOOKS = "/api/v1/books"


# ---------- POST ----------

def test_create_book(api, auth_headers, book_payload):
    response = api.post(BOOKS, json=book_payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.headers["Content-Type"] == "application/json"
    body = response.json()
    assert isinstance(body["id"], int)
    assert {k: v for k, v in body.items() if k != "id"} == book_payload
    assert response.headers["Location"] == f"{BOOKS}/{body['id']}"

    api.delete(f"{BOOKS}/{body['id']}", headers=auth_headers)


def test_create_book_applies_defaults(api, auth_headers):
    response = api.post(BOOKS, json={"title": "Без ISBN", "author": "Аноним", "year": 2001}, headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["isbn"] is None
    assert body["available"] is True

    api.delete(f"{BOOKS}/{body['id']}", headers=auth_headers)


def test_create_book_trims_whitespace(api, auth_headers, book_payload):
    book_payload["title"] = "  Пробелы вокруг  "
    response = api.post(BOOKS, json=book_payload, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["title"] == "Пробелы вокруг"

    api.delete(f"{BOOKS}/{response.json()['id']}", headers=auth_headers)


@pytest.mark.parametrize(
    "headers, expected_detail",
    [
        ({}, "Missing Authorization header"),
        ({"Authorization": "Bearer wrong-token"}, "Invalid token"),
    ],
    ids=["no-header", "wrong-token"],
)
def test_create_book_without_valid_token_returns_401(api, book_payload, headers, expected_detail):
    response = api.post(BOOKS, json=book_payload, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {"detail": expected_detail}


def test_create_book_with_wrong_auth_scheme_returns_401(api, book_payload):
    response = api.post(BOOKS, json=book_payload, headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "patch, field",
    [
        ({"title": None}, "title"),
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"author": 123}, "author"),
        ({"year": "сто"}, "year"),
        ({"year": 1000}, "year"),
        ({"year": date.today().year + 1}, "year"),
        ({"isbn": "123"}, "isbn"),
        ({"isbn": "978-5-17-090276-5"}, "isbn"),
        ({"available": "maybe"}, "available"),
        ({"rating": 5}, "rating"),
    ],
    ids=[
        "title-null", "title-empty", "title-blank", "title-too-long", "author-not-string",
        "year-not-int", "year-too-old", "year-in-future", "isbn-short", "isbn-with-dashes",
        "available-not-bool", "unknown-field",
    ],
)
def test_create_book_validation_errors_return_422(api, auth_headers, book_payload, patch, field):
    response = api.post(BOOKS, json={**book_payload, **patch}, headers=auth_headers)

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == field for err in errors), errors


def test_create_book_missing_required_field_returns_422(api, auth_headers, book_payload):
    del book_payload["author"]
    response = api.post(BOOKS, json=book_payload, headers=auth_headers)

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body", "author"]


def test_create_book_with_invalid_json_returns_422(api, auth_headers):
    response = api.post(
        BOOKS,
        data="{not json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "json_invalid"


def test_create_book_with_duplicate_isbn_returns_409(api, auth_headers, created_book, book_payload):
    response = api.post(BOOKS, json={**book_payload, "title": "Дубликат"}, headers=auth_headers)

    assert response.status_code == 409
    assert created_book["isbn"] in response.json()["detail"]


# ---------- PUT ----------

def test_replace_book(api, auth_headers, created_book):
    new_data = {"title": "Новое название", "author": "Новый автор", "year": 1999, "isbn": None, "available": False}
    response = api.put(f"{BOOKS}/{created_book['id']}", json=new_data, headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == {"id": created_book["id"], **new_data}
    assert api.get(f"{BOOKS}/{created_book['id']}").json() == response.json()


def test_replace_book_keeps_own_isbn(api, auth_headers, created_book):
    data = {k: v for k, v in created_book.items() if k != "id"} | {"year": 2021}
    response = api.put(f"{BOOKS}/{created_book['id']}", json=data, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["year"] == 2021


def test_replace_book_requires_full_body(api, auth_headers, created_book):
    response = api.put(f"{BOOKS}/{created_book['id']}", json={"title": "Только название"}, headers=auth_headers)

    assert response.status_code == 422
    missing = {err["loc"][-1] for err in response.json()["detail"]}
    assert missing == {"author", "year"}


def test_replace_missing_book_returns_404(api, auth_headers, book_payload):
    response = api.put(f"{BOOKS}/999999", json=book_payload, headers=auth_headers)

    assert response.status_code == 404


def test_replace_book_without_token_returns_401(api, created_book, book_payload):
    response = api.put(f"{BOOKS}/{created_book['id']}", json=book_payload)

    assert response.status_code == 401
    assert api.get(f"{BOOKS}/{created_book['id']}").json() == created_book


def test_replace_book_with_taken_isbn_returns_409(api, auth_headers, created_book, book_payload):
    other = api.post(BOOKS, json={**book_payload, "isbn": random_isbn()}, headers=auth_headers).json()
    try:
        response = api.put(f"{BOOKS}/{other['id']}", json=book_payload, headers=auth_headers)
        assert response.status_code == 409
    finally:
        api.delete(f"{BOOKS}/{other['id']}", headers=auth_headers)


# ---------- DELETE ----------

def test_delete_book(api, auth_headers, created_book):
    response = api.delete(f"{BOOKS}/{created_book['id']}", headers=auth_headers)

    assert response.status_code == 204
    assert response.content == b""
    assert api.get(f"{BOOKS}/{created_book['id']}").status_code == 404


def test_delete_is_not_repeatable(api, auth_headers, created_book):
    assert api.delete(f"{BOOKS}/{created_book['id']}", headers=auth_headers).status_code == 204
    assert api.delete(f"{BOOKS}/{created_book['id']}", headers=auth_headers).status_code == 404


def test_delete_book_without_token_returns_401(api, created_book):
    response = api.delete(f"{BOOKS}/{created_book['id']}")

    assert response.status_code == 401
    assert api.get(f"{BOOKS}/{created_book['id']}").status_code == 200


# ---------- Сценарий целиком ----------

def test_full_crud_flow(api, auth_headers, book_payload):
    created = api.post(BOOKS, json=book_payload, headers=auth_headers)
    assert created.status_code == 201
    book_id = created.json()["id"]

    assert api.get(f"{BOOKS}/{book_id}").json()["title"] == book_payload["title"]

    updated = api.put(f"{BOOKS}/{book_id}", json={**book_payload, "available": False}, headers=auth_headers)
    assert updated.status_code == 200
    assert api.get(f"{BOOKS}/{book_id}").json()["available"] is False

    assert api.delete(f"{BOOKS}/{book_id}", headers=auth_headers).status_code == 204
    assert api.get(f"{BOOKS}/{book_id}").status_code == 404
