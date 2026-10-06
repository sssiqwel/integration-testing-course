"""Минимальный SOAP 1.1 сервис (document/literal) поверх того же хранилища.

Написан вручную на xml.etree, чтобы было видно, из чего состоит SOAP-сообщение.
Описание контракта — в WSDL: GET /soap?wsdl
"""

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request, Response

from app.models import Book
from app.storage import storage

SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
TNS = "http://example.com/library"
SOAP_CONTENT_TYPE = "text/xml; charset=utf-8"

router = APIRouter(include_in_schema=False)


def _wsdl(location: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions name="LibraryService"
    targetNamespace="{TNS}"
    xmlns="http://schemas.xmlsoap.org/wsdl/"
    xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"
    xmlns:tns="{TNS}"
    xmlns:xsd="http://www.w3.org/2001/XMLSchema">

  <types>
    <xsd:schema targetNamespace="{TNS}" elementFormDefault="qualified">
      <xsd:complexType name="Book">
        <xsd:sequence>
          <xsd:element name="id" type="xsd:int"/>
          <xsd:element name="title" type="xsd:string"/>
          <xsd:element name="author" type="xsd:string"/>
          <xsd:element name="year" type="xsd:int"/>
          <xsd:element name="isbn" type="xsd:string" minOccurs="0"/>
          <xsd:element name="available" type="xsd:boolean"/>
        </xsd:sequence>
      </xsd:complexType>
      <xsd:element name="GetBookRequest">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="id" type="xsd:int"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="GetBookResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="book" type="tns:Book"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="ListBooksRequest">
        <xsd:complexType>
          <xsd:sequence/>
        </xsd:complexType>
      </xsd:element>
      <xsd:element name="ListBooksResponse">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="book" type="tns:Book" minOccurs="0" maxOccurs="unbounded"/>
          </xsd:sequence>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>

  <message name="GetBookInput"><part name="parameters" element="tns:GetBookRequest"/></message>
  <message name="GetBookOutput"><part name="parameters" element="tns:GetBookResponse"/></message>
  <message name="ListBooksInput"><part name="parameters" element="tns:ListBooksRequest"/></message>
  <message name="ListBooksOutput"><part name="parameters" element="tns:ListBooksResponse"/></message>

  <portType name="LibraryPortType">
    <operation name="GetBook">
      <input message="tns:GetBookInput"/>
      <output message="tns:GetBookOutput"/>
    </operation>
    <operation name="ListBooks">
      <input message="tns:ListBooksInput"/>
      <output message="tns:ListBooksOutput"/>
    </operation>
  </portType>

  <binding name="LibraryBinding" type="tns:LibraryPortType">
    <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="GetBook">
      <soap:operation soapAction="{TNS}/GetBook"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
    <operation name="ListBooks">
      <soap:operation soapAction="{TNS}/ListBooks"/>
      <input><soap:body use="literal"/></input>
      <output><soap:body use="literal"/></output>
    </operation>
  </binding>

  <service name="LibraryService">
    <port name="LibraryPort" binding="tns:LibraryBinding">
      <soap:address location="{escape(location)}"/>
    </port>
  </service>
</definitions>
"""


def _envelope(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<soap:Envelope xmlns:soap="{SOAP_ENV_NS}" xmlns:tns="{TNS}">'
        f"<soap:Body>{body}</soap:Body>"
        "</soap:Envelope>"
    )


def _fault(code: str, message: str) -> Response:
    body = f"<soap:Fault><faultcode>soap:{code}</faultcode><faultstring>{escape(message)}</faultstring></soap:Fault>"
    # SOAP 1.1 требует HTTP 500 для любого Fault, даже если виноват клиент.
    return Response(content=_envelope(body), status_code=500, media_type=SOAP_CONTENT_TYPE)


def _book_xml(tag: str, book: Book) -> str:
    isbn = f"<tns:isbn>{escape(book.isbn)}</tns:isbn>" if book.isbn else ""
    return (
        f"<tns:{tag}>"
        f"<tns:id>{book.id}</tns:id>"
        f"<tns:title>{escape(book.title)}</tns:title>"
        f"<tns:author>{escape(book.author)}</tns:author>"
        f"<tns:year>{book.year}</tns:year>"
        f"{isbn}"
        f"<tns:available>{str(book.available).lower()}</tns:available>"
        f"</tns:{tag}>"
    )


def _get_book(request_el: ET.Element) -> Response:
    id_el = request_el.find(f"{{{TNS}}}id")
    if id_el is None or not (id_el.text or "").strip().lstrip("-").isdigit():
        return _fault("Client", "GetBookRequest/id must be an integer")
    book = storage.get(int(id_el.text))
    if book is None:
        return _fault("Client", f"Book {id_el.text.strip()} not found")
    body = f"<tns:GetBookResponse>{_book_xml('book', book)}</tns:GetBookResponse>"
    return Response(content=_envelope(body), media_type=SOAP_CONTENT_TYPE)


def _list_books(_: ET.Element) -> Response:
    books = "".join(_book_xml("book", b) for b in storage.list())
    body = f"<tns:ListBooksResponse>{books}</tns:ListBooksResponse>"
    return Response(content=_envelope(body), media_type=SOAP_CONTENT_TYPE)


OPERATIONS = {
    f"{{{TNS}}}GetBookRequest": _get_book,
    f"{{{TNS}}}ListBooksRequest": _list_books,
}


@router.get("/soap")
def wsdl(request: Request) -> Response:
    if "wsdl" not in request.query_params:
        return Response("Use GET /soap?wsdl for the contract or POST a SOAP envelope.", media_type="text/plain")
    location = str(request.url_for("soap_endpoint"))
    return Response(content=_wsdl(location), media_type="text/xml; charset=utf-8")


@router.post("/soap", name="soap_endpoint")
async def soap_endpoint(request: Request) -> Response:
    raw = await request.body()
    try:
        envelope = ET.fromstring(raw)
    except ET.ParseError as exc:
        return _fault("Client", f"Malformed XML: {exc}")

    if envelope.tag != f"{{{SOAP_ENV_NS}}}Envelope":
        return _fault("Client", "Root element must be soap:Envelope")
    body = envelope.find(f"{{{SOAP_ENV_NS}}}Body")
    if body is None or len(body) == 0:
        return _fault("Client", "soap:Body is missing or empty")

    operation_el = body[0]
    handler = OPERATIONS.get(operation_el.tag)
    if handler is None:
        return _fault("Client", f"Unknown operation {operation_el.tag}")
    return handler(operation_el)
