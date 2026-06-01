"""FIFO rotating structured JSONL logger.

Writes one JSON line per event to timestamped log files.
Rotates to a new file at max_lines. Deletes the oldest file
when max_files is exceeded — strict FIFO ordering.
All parameters come from config/config.json, never hardcoded.
"""

import json
import os
from datetime import datetime
from pathlib import Path


class FIFOLogger:
    """Rotating JSONL logger with configurable file and line limits.

    Each log entry is one JSON line: {"ts", "level", "source", "msg"}.
    A single corrupt line never breaks the entire file (JSONL advantage).
    """

    def __init__(self, log_dir: str = "logs", max_files: int = 20, max_lines: int = 500):
        """Create or resume a rotating log session in log_dir."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_files = max_files
        self.max_lines = max_lines
        self._current_file: Path | None = None
        self._current_lines = 0
        self._open_current()

    def _log_files(self) -> list[Path]:
        """Return sorted list of all existing debate log files."""
        return sorted(self.log_dir.glob("debate_*.log"))

    def _open_current(self) -> None:
        """Open the most recent log file if it has capacity; otherwise rotate."""
        files = self._log_files()
        if files:
            last = files[-1]
            with open(last) as f:
                lines = f.readlines()
            if len(lines) < self.max_lines:
                self._current_file = last
                self._current_lines = len(lines)
                return
        self._rotate()

    def _rotate(self) -> None:
        """Create a new log file, deleting the oldest if at max_files limit."""
        files = self._log_files()
        while len(files) >= self.max_files:
            os.remove(files[0])
            files = files[1:]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self._current_file = self.log_dir / f"debate_{ts}.log"
        self._current_lines = 0

    def log(self, level: str, source: str, message: str) -> None:
        """Write one JSONL entry. Rotates automatically at max_lines."""
        if self._current_lines >= self.max_lines:
            self._rotate()
        ts = datetime.now().isoformat()
        entry = f'{{"ts": "{ts}", "level": "{level}", "source": "{source}", "msg": {json.dumps(message)}}}\n'
        with open(self._current_file, "a") as f:
            f.write(entry)
        self._current_lines += 1

    def info(self, source: str, message: str) -> None:
        """Log an informational event."""
        self.log("INFO", source, message)

    def error(self, source: str, message: str) -> None:
        """Log an error event."""
        self.log("ERROR", source, message)

    def warning(self, source: str, message: str) -> None:
        """Log a warning event."""
        self.log("WARNING", source, message)
