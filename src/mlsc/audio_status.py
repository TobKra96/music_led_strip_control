"""Status of the audio stream, shared between the audio process and the webserver process."""
import json
import multiprocessing

STATUS_BYTES = 4096
# Keeps a long backend error from overflowing the shared buffer; device names are short.
MAX_MESSAGE = 1000


class AudioStatus:
    """The latest `MicSupervisor` status as JSON in shared memory.

    The audio process calls `write`, the webserver process calls `read`.
    The object is created before the processes start and passed to both as an argument.
    """

    def __init__(self) -> None:
        self._data = multiprocessing.Array("c", STATUS_BYTES)

    def write(self, status: dict) -> None:
        if status.get("message"):
            status = {**status, "message": status["message"][:MAX_MESSAGE]}
        data = json.dumps(status).encode()
        with self._data.get_lock():
            self._data.value = data

    def read(self) -> dict:
        """Return the status, or an empty dict before the audio process wrote one."""
        with self._data.get_lock():
            data = self._data.value
        return json.loads(data) if data else {}
