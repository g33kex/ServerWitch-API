from dataclasses import dataclass
import importlib.metadata
import secrets
import asyncio
import logging
from typing import Tuple

from quart import Quart, websocket, request
from quart_schema import QuartSchema, validate_request, validate_response
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from serverwitch_api.broker import SessionBroker, SessionDoesNotExist, ClientRequest, ClientResponse, ClientError

TIMEOUT: int = 40
TRUSTED_HOSTS: list[str] = ["127.0.0.1"]
LOG_LEVEL: int = logging.INFO

app = Quart(__name__)
QuartSchema(app)
app.asgi_app = ProxyHeadersMiddleware(app.asgi_app, trusted_hosts=TRUSTED_HOSTS)

app.logger.setLevel(LOG_LEVEL)

broker = SessionBroker()

def run() -> None:
    app.run()

@dataclass
class Status:
    status: str
    version: str

@dataclass
class Session:
    session_id: str

@dataclass
class Command:
    session_id: str
    command: str

@dataclass
class Read:
    session_id: str
    path: str

@dataclass
class Write:
    session_id: str
    path: str
    content: str

@dataclass
class CommandResponse:
    return_code: int
    stdout: str
    stderr: str

@dataclass
class ReadResponse:
    content: str

@dataclass
class WriteResponse:
    size: int

@dataclass
class ErrorResponse:
    error: str

@app.get("/status") # type: ignore
@validate_response(Status)
async def status() -> Status:
    return Status(status="OK", version=importlib.metadata.version('serverwitch-api'))

async def _receive(session_id) -> None:
    while True:
        response = await websocket.receive_as(ClientResponse) # type: ignore
        await broker.receive_response(session_id, response)

@app.websocket('/session')
async def session_handler():
    session_id = secrets.token_hex()
    app.logger.info(f"Creating new session for {websocket.remote_addr}")
    await websocket.send_as(Session(session_id=session_id), Session) # type: ignore

    task = None
    try:
        task = asyncio.ensure_future(_receive(session_id))
        async for request in broker.subscribe(session_id):
            app.logger.info(f"Sending request: {request}")
            await websocket.send_as(request, ClientRequest) # type: ignore
    finally:
        if task is not None:
            task.cancel()
            await task

@app.post('/command') # type: ignore
@validate_request(Command)
@validate_response(CommandResponse, 200)
@validate_response(ErrorResponse, 500)
async def command(data: Command) -> Tuple[CommandResponse | ErrorResponse, int]:
    app.logger.info(f"Receiving command from {request.remote_addr}")
    try:
        response = CommandResponse(**await broker.send_request(
            data.session_id,
            {'action': 'command', 'command': data.command},
            timeout=TIMEOUT))
        return response, 200
    except SessionDoesNotExist:
        return ErrorResponse('Session does not exist.'), 500
    except ClientError as e:
        return ErrorResponse(e.message), 500
    except asyncio.TimeoutError:
        return ErrorResponse('Timeout when waiting for client.'), 500

@app.post('/read') # type: ignore
@validate_request(Read)
@validate_response(ReadResponse, 200)
@validate_response(ErrorResponse, 500)
async def read(data: Read) -> Tuple[ReadResponse | ErrorResponse, int]:
    app.logger.info(f"Received read from {request.remote_addr}")
    try:
        response = ReadResponse(**await broker.send_request(
            data.session_id,
            {'action': 'read', 'path': data.path},
            timeout=TIMEOUT))
        return response, 200
    except SessionDoesNotExist:
        return ErrorResponse('Session does not exist.'), 500
    except ClientError as e:
        return ErrorResponse(e.message), 500
    except asyncio.TimeoutError:
        return ErrorResponse('Timeout when waiting for client.'), 500

@app.post('/write') # type: ignore
@validate_request(Write)
@validate_response(WriteResponse, 200)
@validate_response(ErrorResponse, 500)
async def write(data: Write) -> Tuple[WriteResponse | ErrorResponse, int]:
    app.logger.info(f"Received write from {request.remote_addr}")
    try:
        response = WriteResponse(**await broker.send_request(
            data.session_id,
            {'action': 'write', 'path': data.path, 'content': data.content},
            timeout=TIMEOUT))
        return response, 200
    except SessionDoesNotExist:
        return ErrorResponse('Session does not exist.'), 500
    except ClientError as e:
        return ErrorResponse(e.message), 500
    except asyncio.TimeoutError:
        return ErrorResponse('Timeout when waiting for client.'), 500

