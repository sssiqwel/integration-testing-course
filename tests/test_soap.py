import xml.etree.ElementTree as ET

import pytest

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://example.com/library"
NS = {"soap": SOAP_NS, "tns": TNS, "wsdl": "http://schemas.xmlsoap.org/wsdl/"}


def envelope(body: str) -> str:
    return (
        f'<soap:Envelope xmlns:soap="{SOAP_NS}" xmlns:tns="{TNS}">'
        f"<soap:Body>{body}</soap:Body></soap:Envelope>"
    )


@pytest.fixture
def soap_call(api):
    def call(body: str, action: str):
        return api.post(
            "/soap",
            data=envelope(body).encode("utf-8"),
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{TNS}/{action}"',
                "Accept": "text/xml",
            },
        )

    return call


def fault_string(response) -> str:
    root = ET.fromstring(response.content)
    return root.find("soap:Body/soap:Fault/faultstring", NS).text


def test_wsdl_describes_operations(api):
    response = api.get("/soap?wsdl")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/xml")
    root = ET.fromstring(response.content)
    operations = {op.get("name") for op in root.findall("wsdl:portType/wsdl:operation", NS)}
    assert operations == {"GetBook", "ListBooks"}


def test_get_book(soap_call, created_book):
    response = soap_call(f"<tns:GetBookRequest><tns:id>{created_book['id']}</tns:id></tns:GetBookRequest>", "GetBook")

    assert response.status_code == 200
    book = ET.fromstring(response.content).find("soap:Body/tns:GetBookResponse/tns:book", NS)
    assert book.find("tns:title", NS).text == created_book["title"]
    assert book.find("tns:isbn", NS).text == created_book["isbn"]
    assert book.find("tns:available", NS).text == "true"


def test_list_books(api, soap_call):
    response = soap_call("<tns:ListBooksRequest/>", "ListBooks")

    assert response.status_code == 200
    books = ET.fromstring(response.content).findall("soap:Body/tns:ListBooksResponse/tns:book", NS)
    assert len(books) == len(api.get("/api/v1/books").json())


def test_get_missing_book_returns_fault(soap_call):
    response = soap_call("<tns:GetBookRequest><tns:id>999999</tns:id></tns:GetBookRequest>", "GetBook")

    assert response.status_code == 500
    assert fault_string(response) == "Book 999999 not found"


@pytest.mark.parametrize(
    "body, expected",
    [
        ("<tns:GetBookRequest><tns:id>abc</tns:id></tns:GetBookRequest>", "must be an integer"),
        ("<tns:GetBookRequest/>", "must be an integer"),
        ("<tns:DeleteBookRequest/>", "Unknown operation"),
        ("", "missing or empty"),
    ],
    ids=["id-not-int", "id-missing", "unknown-operation", "empty-body"],
)
def test_invalid_requests_return_client_fault(soap_call, body, expected):
    response = soap_call(body, "GetBook")

    assert response.status_code == 500
    root = ET.fromstring(response.content)
    assert root.find("soap:Body/soap:Fault/faultcode", NS).text == "soap:Client"
    assert expected in fault_string(response)


def test_malformed_xml_returns_fault(api):
    response = api.post("/soap", data=b"<not-closed>", headers={"Content-Type": "text/xml"})

    assert response.status_code == 500
    assert "Malformed XML" in fault_string(response)
