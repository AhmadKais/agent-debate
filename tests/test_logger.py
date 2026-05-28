import json
import tempfile
from pathlib import Path

from src.core.logger import FIFOLogger


def test_creates_log_file():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=5, max_lines=100)
        logger.info("test", "hello world")
        files = list(Path(tmp).glob("debate_*.log"))
        assert len(files) == 1


def test_rotates_at_max_lines():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=5, max_lines=3)
        for i in range(4):
            logger.info("test", f"line {i}")
        files = sorted(Path(tmp).glob("debate_*.log"))
        assert len(files) == 2
        with open(files[-1]) as f:
            assert len(f.readlines()) == 1


def test_fifo_deletes_oldest_file():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=3, max_lines=1)
        for i in range(4):
            logger.info("test", f"msg {i}")
        files = sorted(Path(tmp).glob("debate_*.log"))
        assert len(files) <= 3


def test_log_is_valid_json():
    with tempfile.TemporaryDirectory() as tmp:
        logger = FIFOLogger(log_dir=tmp, max_files=5, max_lines=100)
        logger.info("src", "test message")
        files = list(Path(tmp).glob("debate_*.log"))
        with open(files[0]) as f:
            entry = json.loads(f.readline())
        assert entry["level"] == "INFO"
        assert entry["source"] == "src"
        assert "test message" in entry["msg"]
