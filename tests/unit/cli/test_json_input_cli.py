import pytest
import json
import subprocess
import sys
import os


ORKA_CLI = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../orka/orka_cli.py'))
DUMMY_YML = os.path.abspath(os.path.join(os.path.dirname(__file__), 'dummy.yml'))

def setup_module(module):
    # Crea un file YAML minimale valido per la CLI
    with open(DUMMY_YML, 'w') as f:
        f.write('orchestrator:\n  id: dummy\n  strategy: sequential\n  agents: []\n')

def teardown_module(module):
    if os.path.exists(DUMMY_YML):
        os.remove(DUMMY_YML)

def run_orka_cli(input_str, extra_args=None):
    cmd = [sys.executable, ORKA_CLI, '--json-input', 'run', DUMMY_YML, input_str]
    if extra_args:
        cmd.extend(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def test_json_input_oneline():
    input_json = '{"foo": "bar", "num": 1}'
    result = run_orka_cli(input_json)
    assert 'Error' not in result.stderr

def test_json_input_multiline():
    input_json = '{\n  "foo": "bar",\n  "num": 1\n}'
    result = run_orka_cli(input_json)
    assert 'Error' not in result.stderr

def test_json_input_with_spaces():
    input_json = '{    "foo"  :   "bar"   ,   "num"  : 1   }'
    result = run_orka_cli(input_json)
    assert 'Error' not in result.stderr

def test_json_input_invalid():
    input_json = '{foo: bar}'
    result = run_orka_cli(input_json)
    # Accetta sia stderr che stdout, e exit code diverso da 0
    # Accetta anche messaggi più dettagliati
    assert (
        'Could not parse input' in result.stderr
        or 'Could not parse input' in result.stdout
    )
    assert result.returncode != 0