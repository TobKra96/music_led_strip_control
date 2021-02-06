from libs.outputs.output import Output  # pylint: disable=E0611, E0401


class OutputDummy(Output):
    def __init__(self, device):
        # Call the constructor of the base class.
        super(OutputDummy, self).__init__(device)

    def show(self, output_array):
        print("Output dummy...")
