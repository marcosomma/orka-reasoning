import pytest
import json
from orka.orchestrator.simplified_prompt_rendering import SimplifiedPromptRenderer

@pytest.mark.parametrize("input_obj, field, expected", [
    ({"foo": "bar", "num": 42}, "foo", "bar"),
    ({"foo": "bar", "num": 42}, "num", 42),
    ({"foo": "bar"}, "missing", None),
    ("notadict", "foo", None),
])
def test_get_input_field(input_obj, field, expected):
    assert SimplifiedPromptRenderer.get_input_field(input_obj, field) == expected


def test_jinja2_template_with_json_input():
    from jinja2 import Environment
    env = Environment()
    env.globals['get_input_field'] = SimplifiedPromptRenderer.get_input_field
    template = env.from_string("Field: {{ get_input_field(input, 'foo') }}")
    rendered = template.render(input={"foo": "bar"})
    assert "Field: bar" in rendered


def test_jinja2_template_with_nested_json():
    from jinja2 import Environment
    env = Environment()
    env.globals['get_input_field'] = SimplifiedPromptRenderer.get_input_field
    template = env.from_string("Num: {{ get_input_field(input, 'num') }}")
    rendered = template.render(input={"num": 123})
    assert "Num: 123" in rendered


def test_jinja2_template_with_missing_field():
    from jinja2 import Environment
    env = Environment()
    env.globals['get_input_field'] = SimplifiedPromptRenderer.get_input_field
    template = env.from_string("Missing: {{ get_input_field(input, 'notfound', 'default') }}")
    rendered = template.render(input={"foo": "bar"})
    assert "Missing: default" in rendered
