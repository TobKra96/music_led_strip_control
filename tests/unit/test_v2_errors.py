import gc

from mlsc.api.v2.errors import Problem
from mlsc.webserver.messages import _Message  # noqa: PLC2701


def test_problem_code_enum_includes_a_message_defined_after_the_errors_module_was_imported():
    class LateArrival(_Message):
        _code = 418
        _message = "Defined late."

    try:
        assert "LateArrival" in Problem.model_json_schema()["properties"]["code"]["enum"]
    finally:
        del LateArrival
        gc.collect()

    assert "LateArrival" not in Problem.model_json_schema()["properties"]["code"]["enum"]
