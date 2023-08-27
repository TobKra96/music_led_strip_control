import logging

from libs.outputs.output import Output  # pylint: disable=E0611, E0401


class OutputDummy(Output):
    def __init__(self, device) -> None:
        # Call the constructor of the base class.
        super().__init__(device)
        self.logger = logging.getLogger(__name__)

    def show(self, output_array):
        logging.debug("Output dummy...")
