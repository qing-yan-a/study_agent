import threading
import time

try:
    import msvcrt
except ImportError:  # pragma: no cover - Windows console only
    msvcrt = None


class SoftStopController:
    def __init__(self) -> None:
        self._stop_requested = threading.Event()
        self._shutdown_requested = threading.Event()
        self._suspended = threading.Event()
        self._thread: threading.Thread | None = None
        self._buffer = ""

    def start(self) -> None:
        if msvcrt is None or self._thread is not None:
            return

        self._thread = threading.Thread(
            target=self._watch_console,
            name="soft-stop-listener",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        self._shutdown_requested.set()

        if self._thread is not None:
            self._thread.join(timeout=0.5)
            self._thread = None

        self._buffer = ""

    def suspend(self) -> None:
        self._buffer = ""
        self._suspended.set()

    def resume(self) -> None:
        self._buffer = ""
        self._suspended.clear()

    def stop_requested(self) -> bool:
        return self._stop_requested.is_set()

    def _watch_console(self) -> None:
        while not self._shutdown_requested.is_set():
            if self._suspended.is_set():
                time.sleep(0.05)
                continue

            if not msvcrt.kbhit():
                time.sleep(0.05)
                continue

            char = msvcrt.getwch()

            if char in {"\x00", "\xe0"}:
                if msvcrt.kbhit():
                    msvcrt.getwch()
                continue

            if char in {"\r", "\n"}:
                command = self._buffer.strip().lower()
                self._buffer = ""

                if command == "stop":
                    self._stop_requested.set()
                    print("\n[stop] 已收到停止请求，将在当前步骤结束后停止。")

                continue

            if char == "\b":
                self._buffer = self._buffer[:-1]
                continue

            if char.isprintable():
                self._buffer += char
