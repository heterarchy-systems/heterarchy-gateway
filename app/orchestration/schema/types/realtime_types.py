"""Finite ASGI message aliases for the realtime response boundary."""

from collections.abc import Awaitable, Callable, MutableMapping

type RealtimeAsgiMessageValue = str | int | bool | bytes | list[tuple[bytes, bytes]]
type RealtimeAsgiMessage = MutableMapping[str, RealtimeAsgiMessageValue]
type RealtimeAsgiSend = Callable[[RealtimeAsgiMessage], Awaitable[None]]
