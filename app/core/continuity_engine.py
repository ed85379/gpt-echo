import asyncio
import random
from app.core.muse_initiator import run_whispergate, run_discoveryfeeds_lookup, run_check_reminders
from app.core.time_location_utils import seconds_until
from app.api.queues import run_broadcast_queue, run_log_queue, run_index_queue, run_memory_index_queue, broadcast_queue, log_queue, index_queue, index_memory_queue
from app.interfaces.websocket_server import broadcast_message
from app.core.memory_core import log_message
from app.databases.memory_indexer import build_index

# --- Scheduled Tasks ---
scheduled_tasks = [
    {"name": "whispergate", "interval": 3600, "function": run_whispergate},
#    {"name": "check_dropped_threads", "interval": 3600, "function": muse_initiator.run_dropped_threads_check},
    {"name": "discovery_feed", "interval": 3600, "function": run_discoveryfeeds_lookup},
    {"name": "reminder_checker", "interval": 60, "function": run_check_reminders},
#    {"name": "inactivity_checker", "interval": 1800, "function": muse_initiator.run_inactivity_check},
#    {"name": "dreamtime", "interval": 86400, "function": muse_initiator.run_dream_gate},
#    {"name": "introspection_engine", "interval": 86400, "function": muse_initiator.run_introspection_engine},
]

# --- Individual Loop for Each Task ---
async def task_runner(task):
    name = task["name"]
    fn = task["function"]

    if name in ("dreamtime", "introspection_engine"):
        hour = 3 if name == "dreamtime" else 4
        delay = seconds_until(hour)
        print(f"[ContinuityEngine] {name} will run in {delay} seconds (scheduled for {hour}:00)")
        await asyncio.sleep(delay)
        while True:
            try:
                print(f"[ContinuityEngine] Running task: {name}")
                fn()
            except Exception as e:
                print(f"[ContinuityEngine] Error in task '{name}': {e}")
            await asyncio.sleep(86400)  # Every 24 hours after
    else:
        interval = task["interval"]
        # Apply jitter
        jitter = random.randint(1, max(90, interval // 4)) if interval >= 300 else random.randint(1, 15)
        print(f"[ContinuityEngine] Initial delay for {name}: {jitter} seconds")
        await asyncio.sleep(jitter)
        while True:
            try:
                print(f"[ContinuityEngine] Running task: {name}")
                fn()
            except Exception as e:
                print(f"[ContinuityEngine] Error in task '{name}': {e}")
            await asyncio.sleep(interval)



# --- Main Event Loop ---
async def main():
    # launch queue consumers
    asyncio.create_task(run_log_queue(log_queue, log_message))
    asyncio.create_task(run_index_queue(index_queue, build_index))

    # launch your scheduled tasks
    await asyncio.gather(
        *(task_runner(task) for task in scheduled_tasks),
    )

# --- Entrypoint ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[ContinuityEngine] Stopped.")
