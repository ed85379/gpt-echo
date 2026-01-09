# test_recall.py
import sys
from datetime import datetime, time, timezone
from app.core.relational_memory import RelationalMemory

rm = RelationalMemory()

def parse_date_as_day_bounds(date_str: str):
    """
    '2025-11-01' -> (2025-11-01T00:00:00Z, 2025-11-01T23:59:59.999999Z)

    We treat the CLI args as *dates* and expand them to full-day
    UTC bounds. That way, if you say:

        2025-11-01 2025-11-15

    you get everything from the start of the 1st through the end of the 15th.
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise SystemExit(f"Invalid date '{date_str}'. Expected YYYY-MM-DD.") from e

    start = datetime.combine(d, time.min).replace(tzinfo=timezone.utc)
    end = datetime.combine(d, time.max).replace(tzinfo=timezone.utc)
    return start, end


def main():
    if len(sys.argv) != 4:
        print("Usage: python test_recall.py <message_id> <start_date> <end_date>")
        print("Example:")
        print("  python test_recall.py 679123abc 2025-11-01 2025-11-15")
        sys.exit(1)

    message_id = sys.argv[1]
    start_date_str = sys.argv[2]  # e.g. '2025-11-01'
    end_date_str = sys.argv[3]    # e.g. '2025-11-15'

    # Expand dates to full-day UTC bounds
    start_ts, _ = parse_date_as_day_bounds(start_date_str)
    _, end_ts = parse_date_as_day_bounds(end_date_str)

    # Hand everything off to the harness
    rm.test_recall_vs_qdrant_for_message(
        message_id=message_id,
        start_ts=start_ts,
        end_ts=end_ts,
    )


if __name__ == "__main__":
    main()