# The MIT License (MIT)
#
# Copyright (C) 2021 Simon Meins
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# HTTP request library to send send and receive data over the HTTP protocol.


# Import modules
# socket    : network communication
# json      : JSON manipulation
# namedtuple: special tuple object types

from socket import socket, AF_INET, SOCK_STREAM
from json import dumps
from collections import namedtuple

# Create namedtuple instances

url         = namedtuple("url", "scheme netloc path")
status_line = namedtuple("status_line", "http_version status_code reason_phrase")

# Define constants

HTTP_VERSION = "HTTP/1.1"
HTTP_POST    = "POST"
HTTP_GET     = "GET"


class HTTPResponse:
    
    """
    HTTPResponse class to parse an HTTP response.

    Constructor (__init__):
        parameter raw_http_response [string]: raw HTTP response string
    """

    def __init__(self, raw_http_response: str) -> None:
        self.raw_http_response = raw_http_response

    def __repr__(self) -> str:
        return f"<Response [{self.status_code}]>"

    @property
    def _status_line(self) -> status_line:

        """
        Parse the status line of the HTTP response (private method).
        returns: HTTP status line [namedtuple]
        """

        status_line_end_idx = self.raw_http_response.index("\r\n")
        status_line_raw     = self.raw_http_response[:status_line_end_idx].split()

        return status_line(
            http_version=status_line_raw[0], 
            status_code=status_line_raw[1], 
            reason_phrase=status_line_raw[2]
        )

    @property
    def status_code(self) -> int:

        """
        Return the status code of the HTTP response.
        returns: HTTP response status code [integer]
        """

        return int(self._status_line.status_code)

    @property
    def text(self) -> str:

        """
        Parse the HTTP response text (body data).
        returns: HTTP response text [string]
        """

        text_start_idx     = self.raw_http_response.index("\r\n\r\n")
        http_response_text = self.raw_http_response[text_start_idx + 4:]

        return http_response_text

    @property
    def headers(self) -> dict:

        """
        Parse the HTTP response headers.
        returns: HTTP response headers [dictionary]
        """
        
        header_start_idx = self.raw_http_response.index("\r\n")
        header_end_idx   = self.raw_http_response.index("\r\n\r\n")
        http_headers     = self.raw_http_response[header_start_idx + 2:header_end_idx].replace(" ", "")

        return {key_value[0]: key_value[1] for header in http_headers.split("\r\n") if (key_value := header.split(":", 1))}


class HTTPRequest:

    """
    HTTPRequest class to construct and send an HTTP request.
    This HTTPRequest class implements a subset of the HTTP protocol version 1.1 which is defined in RFC2616.

    Constructor (__init__):
        parameter method      [string]: HTTP request method (e.g. GET, POST, etc.)
        parameter url         [string]: Destination URL for the HTTP request
        parameter data    [dictionary]: HTTP request parameters
        parameter json    [dictionary]: HTTP request JSON data (POST request only)
        parameter headers [dictionary]: HTTP request headers
        parameter timeout    [integer]: socket timeout
    """

    def __init__(self, method: str, url: str, data: dict = {}, json: dict = {}, headers: dict = {}, timeout: float = 3.0) -> None:
        self.method  = method
        self.url     = url
        self.data    = data
        self.json    = json
        self.headers = headers
        self.timeout = timeout

        self.json_body: bool = True if self.json else False

        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.settimeout(timeout)

        dest_host = self._parse_url.netloc[1]
        dest_port = self._parse_url.netloc[2]

        self.socket.connect((dest_host, int(dest_port)))

    def content_length(self, json: bool = True) -> int:

        """
        Calculate the content length of the HTTP request data.
        returns: content length [integer]
        """
        
        if not json:
            return len(self._parse_http_data())

        return len(self._parse_http_json())

    def _parse_http_headers(self) -> str:

        """
        Parse the HTTP request headers. Include 'Host' and 'Content-Length' header by default.
        returns: formatted HTTP request headers [string]
        """
        
        http_headers: str = ""

        dest_host = self._parse_url.netloc[0]
        http_headers += f"Host: {dest_host}\r\n"

        if self.method == HTTP_POST:
            http_headers += f"Content-Length: {self.content_length(self.json_body)}\r\n"

        for header_key, header_value in self.headers.items():
            http_headers += f"{header_key}: {header_value}\r\n"

        return http_headers
        
    @property
    def _parse_url(self) -> url:

        """
        Parse the destination URL.
        returns: destination URL components [namedtuple]
        """
        
        if not self.url.startswith("http"):
            raise ValueError("Invalid URL")

        delimiter = "/"
        url_parts = self.url.split(delimiter)

        scheme       = url_parts[0].replace(":", "")
        netloc_abs   = url_parts[2]

        netloc_host: str = ""
        netloc_port: str = ""

        if ":" in url_parts[2]:
            netloc_parts = netloc_abs.split(":")
            netloc_host, netloc_port = netloc_parts[0], netloc_parts[1]
        else:
            netloc_host, netloc_port = url_parts[2], 80

        path = ''.join([f"/{path}" for path in url_parts[3:]])

        return url(
            scheme=scheme, 
            netloc=(netloc_abs, netloc_host, netloc_port), 
            path=path
        )

    def _parse_http_json(self) -> str:

        """
        Convert JSON data to string.
        returns: JSON data [string]
        """

        return dumps(self.json)

    def _parse_http_data(self) -> str:

        """
        Parse the HTTP request parameters.
        returns: formatted HTTP request parameters [string]
        """

        request_data: str = ""

        for i, (key, data) in enumerate(self.data.items()):
            fmt = f"{key}={data}"
            if i != len(self.data) - 1: fmt += "&"
            request_data += fmt

        return request_data
        
    def construct_http_request(self) -> str:

        """
        Construct the final HTTP request string.
        returns: constructed HTTP request string [string]        
        """

        parsed_url     = self._parse_url
        http_headers   = self._parse_http_headers()

        body_data = self._parse_http_json()

        if not self.json:
            body_data = self._parse_http_data()

        if self.method == HTTP_GET:
            return f"{self.method} {parsed_url.path}{f'?{body_data}' if self.data and not self.json else ''} {HTTP_VERSION}\r\n{http_headers}\r\n"

        return f"{self.method} {parsed_url.path} {HTTP_VERSION}\r\n{http_headers}\r\n{body_data}"
        
    def send_http_request(self) -> None:

        """
        Construct and send a new HTTP request.
        """

        http_request = str.encode(self.construct_http_request())
        self.socket.send(http_request)

    def get_http_response(self) -> HTTPResponse:

        """
        Receive and parse the HTTP response.
        returns: parsed HTTP response [HTTPResponse]
        """
        
        response_buffer = b""

        while True:
            data = self.socket.recv(1024)
            if not data:
                break
            response_buffer += data

        self.socket.close()

        return HTTPResponse(response_buffer.decode("utf-8"))


def get(url: str, data: dict = {}, headers: dict = {}, timeout: float = 3.0) -> HTTPResponse:

    """
    Wrapper function to make a new HTTP GET request.
    returns: HTTP response [HTTPResponse]
    """

    http_request_instance = HTTPRequest(method="GET", url=url, data=data, headers=headers, timeout=timeout)
    http_request_instance.send_http_request()

    return http_request_instance.get_http_response()

def post(url: str, data: dict = {}, json: dict = {}, headers: dict = {}, timeout: float = 3.0) -> HTTPResponse:

    """
    Wrapper function to make a new HTTP POST request.
    returns: HTTP response [HTTPResponse]
    """

    http_request_instance = HTTPRequest("POST", url=url, data=data, json=json, headers=headers, timeout=timeout)
    http_request_instance.send_http_request()

    return http_request_instance.get_http_response()
