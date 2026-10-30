import multiprocessing
import time

from mlsc.device import Device


def test_the_device_given_to_a_process_does_not_carry_the_processes_of_its_services():
    # A started Process cannot be pickled, and spawn (Windows) pickles the Device when it starts each service process.
    device = Device({}, {"device_name": "test"}, None, "device_0")
    started = multiprocessing.Process(target=time.sleep, args=(0.1,))
    started.start()
    try:
        device._Device__output_process = started  # ruff: ignore[private-member-access]

        state = device.__getstate__()

        assert not any(isinstance(value, multiprocessing.process.BaseProcess) for value in state.values())
    finally:
        started.join()
