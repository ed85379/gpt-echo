from fastapi import FastAPI, APIRouter
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.interfaces.websocket_server import router as websocket_router
from app.interfaces.websocket_server import broadcast_message
from app.core.memory_core import log_message, purge_message_job
from app.core.muse_initiator import run_thread_summarization
from app.databases.memory_indexer import build_index, build_memory_index
from app.api.routers.system_api import config_router, uipolling_router, states_router, time_skip_router
from app.api.routers.muse_presence_api import profile_router, muse_router
from app.api.routers.messages_api import router as messages_router
from app.api.routers.cortex_api import router as cortex_router
from app.api.routers.memory_api import memory_router
from app.api.routers.import_api import router as import_router
from app.api.routers.projects_api import router as projects_router
from app.api.routers.files_api import router as files_router
from app.api.routers.threads_api import router as threads_router
from .queues import run_broadcast_queue, run_log_queue, run_index_queue, run_memory_index_queue, run_purge_queue, \
    broadcast_queue, log_queue, index_queue, index_memory_queue, purge_queue, summarization_queue, \
    run_summarization_queue
from app.commands.registry import command_registry
from app.addons.config import ENABLED_ADDONS
from app.addons.loader import load_addons
from app.commands.core_commands import register_core_commands
from app.commands.registry import command_registry

print("MODULE REGISTRY ID:", id(command_registry))



app = FastAPI(debug=True)
router = APIRouter()
app.include_router(config_router)
app.include_router(messages_router)
app.include_router(cortex_router)
app.include_router(memory_router)
app.include_router(import_router)
app.include_router(projects_router)
app.include_router(files_router)
app.include_router(states_router)
app.include_router(uipolling_router)
app.include_router(profile_router)
app.include_router(muse_router)
app.include_router(time_skip_router)
app.include_router(threads_router)

app.state.command_registry = command_registry
print("APP STATE REGISTRY ID:", id(app.state.command_registry))
register_core_commands(command_registry)
load_addons(app, ENABLED_ADDONS)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Accept requests from any origin (you can restrict later if needed)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket_router)

# --- Utility Functions ---

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_broadcast_queue(broadcast_queue, broadcast_message))
    asyncio.create_task(run_log_queue(log_queue, log_message))
    asyncio.create_task(run_index_queue(index_queue, build_index))
    asyncio.create_task(run_memory_index_queue(index_memory_queue, build_memory_index))
    asyncio.create_task(run_purge_queue(purge_queue, purge_message_job))
    asyncio.create_task(run_summarization_queue(summarization_queue, run_thread_summarization))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_main:app", host="0.0.0.0", port=5000, reload=True)

