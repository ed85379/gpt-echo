import asyncio
from typing import Dict, Any, Callable, Awaitable
from app.core import utils

broadcast_queue = asyncio.Queue()
log_queue = asyncio.Queue()
index_queue = asyncio.Queue()
index_memory_queue = asyncio.Queue()

# Typing: adjust as needed for your actual message structure
Message = Dict[str, Any]

async def run_broadcast_queue(
    queue: asyncio.Queue,
    broadcast_message: Callable[..., Awaitable[None]],
    *,
    logger=None
):
    while True:
        msg = await queue.get()
        try:
            # Adjust keys as needed for your message dict!
            await broadcast_message(
                message=msg["message"],
                timestamp=msg.get("timestamp"),
                to=msg.get("to", "frontend"),
                project_id=msg.get("project_id", "")
            )
        except Exception as e:
            utils.write_system_log(
                level="error",
                module="api",
                component="queues",
                function="run_broadcast_queue",
                action="broadcast_failed",
                error=str(e),
                message=str(msg)
            )
            # Optionally: re-queue or alert
        finally:
            queue.task_done()

async def run_log_queue(
    queue: asyncio.Queue,
    log_message: Callable[..., Awaitable[None]],
    *,
    logger=None
):
    while True:
        msg = await queue.get()
        try:
            await log_message(
                role=msg.get("role", "muse"),
                message=msg["message"],
                timestamp=msg.get("timestamp"),
                project_id=msg.get("project_id"),
                source=msg.get("source"),
                skip_index=msg.get("skip_index", False)
                # Add any other fields your log_message expects
            )
        except Exception as e:
            utils.write_system_log(
                level="error",
                module="api",
                component="queues",
                function="run_log_queue",
                action="log_failed",
                error=str(e),
                message=str(msg)
            )
            # Optionally: re-queue or alert
        finally:
            queue.task_done()

async def run_index_queue(
    queue: asyncio.Queue,
    build_index: Callable[..., Awaitable[None]],
    *,
    logger=None
):
    while True:
        message_id = await queue.get()
        try:
            await build_index(
                message_id=message_id,
            )
        except Exception as e:
            utils.write_system_log(
                level="error",
                module="api",
                component="queues",
                function="run_index_queue",
                action="index_failed",
                error=str(e),
                message_id=str(message_id)
            )
            # Optionally: re-queue or alert
        finally:
            queue.task_done()

async def run_memory_index_queue(
    queue: asyncio.Queue,
    build_memory_index: Callable[..., Awaitable[None]],
    *,
    logger=None
):
    while True:
        entry_id = await queue.get()
        try:
            await build_memory_index(
                entry_id=entry_id,
            )
        except Exception as e:
            utils.write_system_log(
                level="error",
                module="api",
                component="queues",
                function="run_memory_index_queue",
                action="index_failed",
                error=str(e),
                entry_id=str(entry_id)
            )
            # Optionally: re-queue or alert
        finally:
            queue.task_done()