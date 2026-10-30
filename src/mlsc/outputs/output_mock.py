from loguru import logger

from mlsc.diagnosis import Diagnosis
from mlsc.outputs.output import Output


class OutputMock(Output):
    def __init__(self, device) -> None:
        # Call the constructor of the base class.
        super().__init__(device)

    @staticmethod
    def show(output_array) -> None:
        logger.debug(f"Output dummy... {output_array}")

    @classmethod
    def diagnose(cls, device_config: dict, host=None) -> Diagnosis:
        return Diagnosis.ok("Mock Output: no hardware is driven.")
