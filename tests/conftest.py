import os
import random
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parent.parent
HOST = os.getenv("HOST", "127.0.0.1")
PORT = os.getenv("PORT", "8765")
BASE_URL = os.getenv("BASE_URL", f"http://{HOST}:{PORT}")
API_TOKEN = os.getenv("API_TOKEN", "secret-token")


class ApiClient(requests.Session):
    """requests.Session, который подставляет базовый URL к относительным путям."""

    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.headers["Accept"] = "application/json"

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", 5)
        return super().request(method, f"{self.base_url}{url}", *args, **kwargs)


def _is_up(url: str) -> bool:
    try:
        return requests.get(f"{url}/health", timeout=0.5).status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def base_url():
    """Использует уже запущенный сервер или поднимает свой на время сессии тестов."""
    if _is_up(BASE_URL):
        yield BASE_URL
        return

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", HOST, "--port", PORT],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(50):
            if _is_up(BASE_URL):
                break
            if proc.poll() is not None:
                pytest.exit(f"Server process exited with code {proc.returncode}", returncode=1)
            time.sleep(0.2)
        else:
            pytest.exit(f"Server did not start at {BASE_URL}", returncode=1)
        yield BASE_URL
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture
def api(base_url):
    with ApiClient(base_url) as client:
        yield client


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {API_TOKEN}"}


def random_isbn() -> str:
    return "978" + "".join(random.choices("0123456789", k=10))


@pytest.fixture
def book_payload():
    return {
        "title": "Тестирование API",
        "author": "Иван Тестировщиков",
        "year": 2020,
        "isbn": random_isbn(),
        "available": True,
    }


@pytest.fixture
def created_book(api, auth_headers, book_payload):
    """Создаёт книгу перед тестом и удаляет её после (setup / teardown)."""
    response = api.post("/api/v1/books", json=book_payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    book = response.json()
    yield book
    api.delete(f"/api/v1/books/{book['id']}", headers=auth_headers)
