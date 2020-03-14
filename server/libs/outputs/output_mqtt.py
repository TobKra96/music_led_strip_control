from libs.outputs.output import Output # pylint: disable=E0611, E0401
from time import sleep

class OutputMptt(Output):
    def __init__(self, device):

        # Call the constructor of the base class.
        super(OutputMptt, self).__init__(device)

    def show(self, output_array):
        sleep(0.05)