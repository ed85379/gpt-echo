import asyncio
from app.databases.memory_indexer import build_memory_index

if __name__ == "__main__":
    asyncio.run(build_memory_index(dryrun=False))