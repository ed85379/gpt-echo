from datetime import datetime
from app.core.relational_memory import RelationalMemory

if __name__ == "__main__":
    rm = RelationalMemory()
    rm.similarity_test(
        start_date=datetime(2025, 10, 1),
        end_date=datetime(2025, 10, 14)
    )