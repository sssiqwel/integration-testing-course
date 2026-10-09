from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookIn(BaseModel):


    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "title": "Мастер и Маргарита",
                    "author": "Михаил Булгаков",
                    "year": 1967,
                    "isbn": "9785170902765",
                    "available": True,
                }
            ]
        },
    )

    title: str = Field(min_length=1, max_length=200, description="Название книги")
    author: str = Field(min_length=1, max_length=100, description="Автор")
    year: int = Field(ge=1450, description="Год издания (не позже текущего)")
    isbn: str | None = Field(
        default=None,
        pattern=r"^97[89]\d{10}$",
        description="ISBN-13 без дефисов, уникален в рамках библиотеки",
    )
    available: bool = Field(default=True, description="Есть ли книга в наличии")

    @field_validator("title", "author")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("year")
    @classmethod
    def not_in_future(cls, value: int) -> int:
        if value > date.today().year:
            raise ValueError("year must not be in the future")
        return value


class Book(BookIn):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(description="Идентификатор, назначается сервером")


class ErrorResponse(BaseModel):
    detail: str
