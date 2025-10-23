from datetime import datetime
from app.core.relational_memory import RelationalMemory

if __name__ == "__main__":
    rm = RelationalMemory()
    rm.index_messages_by_date(
        start_date=datetime(2025, 10, 5),
        end_date=datetime(2025, 10, 15)
    )