"""This is the main file of the Server Witch API.
It describes the endpoints of the API."""
from dataclasses import dataclass, asdict
import importlib.metadata
import secrets
import logging
import asyncio
import json
from typing import Tuple

from quart import Quart, websocket, request
from quart_schema import QuartSchema, validate_request, validate_response
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from serverwitch_api.broker import SessionBroker, SessionDoesNotExist, ClientRequest, ClientResponse, ClientError

"""Timeout waiting for a response from the client.
Currently, ChatGPT will timeout after 45 seconds if it didn't receive a response.
We want to timeout before that to provide it with more context about the reasons of the timeout."""
TIMEOUT: int = 40
"""Default log level"""
LOG_LEVEL: int = logging.DEBUG
"""Who to trust with X-Forwarded-For Headers"""
TRUSTED_HOSTS: list[str] = ["127.0.0.1"]

# Create app
app = Quart(__name__)
QuartSchema(app)
app.asgi_app = ProxyHeadersMiddleware(app.asgi_app, trusted_hosts=TRUSTED_HOSTS)

app.logger.setLevel(LOG_LEVEL)

broker = SessionBroker()

"""Run the app"""
def run() -> None:
    app.run()

"""API Status response"""
@dataclass
class Status:
    status: str
    version: str


"""Session information sent into the websocket"""
@dataclass
class Session:
    session_id: str

"""Command request"""
@dataclass
class Command:
    session_id: str
    command: str

"""Read request"""
@dataclass
class Read:
    session_id: str
    path: str

"""Write request"""
@dataclass
class Write:
    session_id: str
    path: str
    content: str

"""Response to a command request"""
@dataclass
class CommandResponse:
    return_code: int
    stdout: str
    stderr: str

"""Response to a read request"""
@dataclass
class ReadResponse:
    content: str

"""Response to a write request"""
@dataclass
class WriteResponse:
    size: int

"""Response in case of an error"""
@dataclass
class ErrorResponse:
    error: str

"""Receive the client responses through the websocket"""
async def _receive(session_id) -> None:
    while True:
        response = await websocket.receive_as(ClientResponse) # type: ignore
        app.logger.info(f"{websocket.remote_addr} - RESPONSE - {session_id} - {json.dumps(asdict(response))}")
        await broker.receive_response(session_id, response)

"""Fetch the status of the API"""
@app.get("/status") # type: ignore
@validate_response(Status)
async def status() -> Status:
    return Status(status="OK", version=importlib.metadata.version('serverwitch-api'))

"""Client requests a new session.
Calling this endpoints initiates a websocket used to send requests
to the client and receive the responses."""
@app.websocket('/session')
async def session_handler():
    session_id = secrets.token_hex()
    app.logger.info(f"{websocket.remote_addr} - SESSION - {session_id}")
    await websocket.send_as(Session(session_id=session_id), Session) # type: ignore

    task = None
    try:
        task = asyncio.ensure_future(_receive(session_id))
        async for request in broker.subscribe(session_id):
            app.logger.info(f"{websocket.remote_addr} - REQUEST - {session_id} - {json.dumps(asdict(request))}")
            await websocket.send_as(request, ClientRequest) # type: ignore
    finally:
        if task is not None:
            task.cancel()
            await task

"""Execute a command on the client"""
@app.post('/command') # type: ignore
@validate_request(Command)
@validate_response(CommandResponse, 200)
@validate_response(ErrorResponse, 500)
async def command(data: Command) -> Tuple[CommandResponse | ErrorResponse, int]:
    try:
        response = CommandResponse(**await broker.send_request(
            data.session_id,
            {'action': 'command', 'command': data.command},
            timeout=TIMEOUT))
        return response, 200
    except SessionDoesNotExist:
        app.logger.warning(f"{request.remote_addr} - INVALID SESSION ID - {repr(data.session_id)}")
        return ErrorResponse('Session does not exist.'), 500
    except ClientError as e:
        return ErrorResponse(e.message), 500
    except asyncio.TimeoutError:
        return ErrorResponse('Timeout when waiting for client.'), 500

"""Read a file from the client"""
@app.post('/read') # type: ignore
@validate_request(Read)
@validate_response(ReadResponse, 200)
@validate_response(ErrorResponse, 500)
async def read(data: Read) -> Tuple[ReadResponse | ErrorResponse, int]:
    try:
        response = ReadResponse(**await broker.send_request(
            data.session_id,
            {'action': 'read', 'path': data.path},
            timeout=TIMEOUT))
        return response, 200
    except SessionDoesNotExist:
        app.logger.warning(f"{request.remote_addr} - INVALID SESSION ID - {repr(data.session_id)}")
        return ErrorResponse('Session does not exist.'), 500
    except ClientError as e:
        return ErrorResponse(e.message), 500
    except asyncio.TimeoutError:
        return ErrorResponse('Timeout when waiting for client.'), 500

"""Write a file on the client"""
@app.post('/write') # type: ignore
@validate_request(Write)
@validate_response(WriteResponse, 200)
@validate_response(ErrorResponse, 500)
async def write(data: Write) -> Tuple[WriteResponse | ErrorResponse, int]:
    try:
        response = WriteResponse(**await broker.send_request(
            data.session_id,
            {'action': 'write', 'path': data.path, 'content': data.content},
            timeout=TIMEOUT))
        return response, 200
    except SessionDoesNotExist:
        app.logger.warning(f"{request.remote_addr} - INVALID SESSION ID - {repr(data.session_id)}")
        return ErrorResponse('Session does not exist.'), 500
    except ClientError as e:
        return ErrorResponse(e.message), 500
    except asyncio.TimeoutError:
        return ErrorResponse('Timeout when waiting for client.'), 500
