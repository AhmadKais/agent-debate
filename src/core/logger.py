import os
from datetime import datetime
from pathlib import Path


class FIFOLogger:
    """Rotating logger: max N files, max M lines each. Deletes oldest on overflow."""

    def __init__(self, log_dir: str = "logs", max_files: int = 20, max_lines: int = 500):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_files = max_files
        self.max_lines = max_lines
        self._current_file: Path | None = None
        self._current_lines = 0
        self._open_current()

    def _log_files(self) -> list[Path]:
        return sorted(self.log_dir.glob("debate_*.log"))

    def _open_current(self) -> None:
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
        files = self._log_files()
        while len(files) >= self.max_files:
            os.remove(files[0])
            files = files[1:]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self._current_file = self.log_dir / f"debate_{ts}.log"
        self._current_lines = 0

    def log(self, level: str, source: str, message: str) -> None:
        if self._current_lines >= self.max_lines:
            self._rotate()
        ts = datetime.now().isoformat()
        entry = f'{{"ts": "{ts}", "level": "{level}", "source": "{source}", "msg": {json_escape(message)}}}\n'
        with open(self._current_file, "a") as f:
            f.write(entry)
        self._current_lines += 1

    def info(self, source: str, message: str) -> None:
        self.log("INFO", source, message)

    def error(self, source: str, message: str) -> None:
        self.log("ERROR", source, message)

    def warning(self, source: str, message: str) -> None:
        self.log("WARNING", source, message)


def json_escape(s: str) -> str:
    import json
    return json.dumps(s)
