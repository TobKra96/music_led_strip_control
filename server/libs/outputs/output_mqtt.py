from libs.output.output import Output # pylint: disable=E0611, E0401

class OutputMptt(Output):
    def __init__(self, device):

        # Call the constructor of the base class.
        super(OutputMptt, self).__init__(self, device)

    def show(self, output_array):
        print("Output mqtt..")