import asyncio
import uuid
from typing import AsyncGenerator, Dict, Tuple, Any
from dataclasses import dataclass

"""Error when a requesting a session id that doesn't exist"""
class SessionDoesNotExist(Exception):
    pass

"""Error when creating a session with a session id that already exists"""
class SessionAlreadyExists(Exception):
    pass

"""Error when the client returned an error"""
class ClientError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message

"""Request sent to the client"""
@dataclass
class ClientRequest:
    request_id: str
    data: Any 

"""Response received from the client"""
@dataclass
class ClientResponse:
    request_id: str
    error: bool
    data: Any

"""This broker routes the requests to the clients and waits for the responses"""
class SessionBroker:
    def __init__(self):
        """Dictionary of session id -> queue of messages waiting to be sent to the client"""
        self.sessions: Dict[str, asyncio.Queue] = {}
        """Dictionary of (session id, request id) -> future of a client response to that particular request"""
        self.pending_responses: Dict[Tuple[str, str], asyncio.Future] = {}

    """Send a request to the client with the session id"""
    async def send_request(self, session_id: str, data: Any, timeout: int = 60) -> Any:
        if session_id not in self.sessions:
            raise SessionDoesNotExist()

        # Generate an id for the request that will be sent back by the client alongside the response
        request_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.pending_responses[(session_id, request_id)] = future

        # Send the request along with its UUID
        await self.sessions[session_id].put(ClientRequest(request_id=request_id, data=data))

        try:
            # Wait for a response or timeout
            return await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError:
            raise
        finally:
            # Cleanup regardless of whether a response was received or not
            if (session_id, request_id) in self.pending_responses:
                del self.pending_responses[(session_id, request_id)]
            
    """Receive client responses from a particular session.
    This resolves the response future."""
    async def receive_response(self, session_id: str, response: ClientResponse) -> None:
        if (session_id, response.request_id) in self.pending_responses:
            future = self.pending_responses.pop((session_id, response.request_id))
            if not future.done():
                if response.error:
                    future.set_exception(ClientError(message=response.data))
                else:
                    future.set_result(response.data)

    """Add a new client with a session id and yield the requests to send"""
    async def subscribe(self, session_id: str) -> AsyncGenerator[ClientRequest, None]:
        if session_id in self.sessions:
            raise SessionAlreadyExists()

        queue = asyncio.Queue()
        self.sessions[session_id] = queue

        try:
            while True:
                yield await queue.get()
        finally:
            # Clean up the session and any pending responses when the session ends
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.pending_responses = {k: v for k, v in self.pending_responses.items() if k[0] != session_id}
