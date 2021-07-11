from libs.outputs.output import Output  # pylint: disable=E0611, E0401

import logging


class OutputDummy(Output):
    def __init__(self, device):
        # Call the constructor of the base class.
        super(OutputDummy, self).__init__(device)
        self.logger = logging.getLogger(__name__)

    def show(self, output_array):
        logging.debug("Output dummy...")
