"""
These tests run the full callback server and integrate with with job running code in
JobRunner, unlike the other callback server tests, which just test enqueuing and dequeuing.

As such, if you submit a job, it will run fully, so you may not want to do that.
"""

import os
import pytest
import requests
import time
from typing import Any

from JobRunner.Callback import Callback

# NOTE - the CBS is started once for this module. Don't assume it has any particular provenance
# stored.


# TODO make a test config or something
_TOKEN = os.environ["KB_AUTH_TOKEN"]


@pytest.fixture(scope="module")
def callback_ports():
    cb_good = Callback(ip="localhost", app_name="jr_good", allow_set_provenance=True)
    print("Starting cb good")
    cb_good.start_callback()

    cb_bad = Callback(ip="localhost", app_name="jr_bad", allow_set_provenance=False)
    print("Starting cb bad")
    cb_bad.start_callback()
    
    time.sleep(1)
    
    yield cb_good.port, cb_bad.port
    
    print("Stopping cb good")
    cb_good.stop()
    print("Stopping cb bad")
    cb_bad.stop()


def _post(port: int, json_body: dict[str, Any]):
    headers = {"Authorization": _TOKEN}
    return requests.post(f"http://localhost:{port}", json=json_body, headers=headers)


def test_get_set_provenance_job_input_style(callback_ports):
    port = callback_ports[0]

    resp = _post(
        port,
        {
            "method": "CallbackServer.set_provenance",
            "params": [{
                "method": "foo.bar",
                "service_ver": "beta",
                "params": ["whooe", "whoo"],
                "source_ws_objects": ["1/2/3"],
            }]
        }
    )
    j = resp.json()
    j["result"][0][0].pop("time")  # changes per test

    expected = {"result": [[{
        "service": "foo",
        "service_ver": "beta",
        "method": "bar",
        "method_params": ["whooe", "whoo"],
        "input_ws_objects": ["1/2/3"],
        "subactions": [],
        "description": "KBase SDK method run via the KBase Execution Engine"
    }]]}
    assert j == expected

    time.sleep(0.1)  # give the queues time to do their thing
    resp = _post(port, {"method":"CallbackServer.get_provenance"})
    j = resp.json()
    j["result"][0][0].pop("time")  # changes per test
    assert j == expected


def test_get_set_provenance_provenance_action_style(callback_ports):
    port = callback_ports[0]

    resp = _post(
        port,
        {
            "method": "CallbackServer.set_provenance",
            "params": [{
                "service": "myservice",
                "method": "mymethod",
                "service_ver": "release",
                "method_params": ["bing", "bang"],
                "input_ws_objects": ["4/5/6"],
                "time": "iso8601 timestamp goes here",
                "subactions": [{
                    "name": "legitmodule",
                    "ver": "1.2.3",
                    "code_url": "https://github.com/kbase/legitmodule.git",
                    "commit": "thisistaotallyalegitgithuash",
                }],
                "description": "myprov",
            }]
        }
    )
    j = resp.json()
    expected = {"result": [[{
        "service": "myservice",
        "method": "mymethod",
        "service_ver": "release",
        "method_params": ["bing", "bang"],
        "input_ws_objects": ["4/5/6"],
        "time": "iso8601 timestamp goes here",
        "subactions": [{
            "name": "legitmodule",
            "ver": "1.2.3",
            "code_url": "https://github.com/kbase/legitmodule.git",
            "commit": "thisistaotallyalegitgithuash",
        }],
        "description": "myprov",
    }]]}
    assert j == expected

    time.sleep(0.1)  # give the queues time to do their thing
    resp = _post(port, {"method":"CallbackServer.get_provenance"})
    j = resp.json()
    assert j == expected


def test_set_provenance_fail_disabled(callback_ports):
    port = callback_ports[1]

    resp = _post(
        port,
        {
            "method": "CallbackServer.set_provenance",
            "params": [{
                "method": "foo.bar",
                "service_ver": "beta",
                "params": ["whooe", "whoo"],
                "source_ws_objects": ["1/2/3"],
            }]
        }
    )
    j = resp.json()
    assert j == {
        "error": {
            "code": -32000,
            "error": "Setting provenance is not enabled",
            "message": "Setting provenance is not enabled",
        },
    }


def test_set_provenance_fail_no_params(callback_ports):
    port = callback_ports[0]
    err = "method params must be a list containing exactly one provenance action"

    resp = _post(port, {"method": "CallbackServer.set_provenance"})
    j = resp.json()
    assert j == {
        "error": {
            "code": -32000,
            "error": err,
            "message": err,
        },
    }


def test_set_provenance_fail_bad_params(callback_ports):
    port = callback_ports[0]
    err = "method params must be a list containing exactly one provenance action"

    testset = [
        None,
        {},
        "foo",
        [],
        ["foo", "bar"],
        [[]],
        ["thingy"]
    ]
    for t in testset:
        resp = _post(port, {"method": "CallbackServer.set_provenance", "params": t})
        j = resp.json()
        assert j == {
            "error": {
                "code": -32000,
                "error": err,
                "message": err,
            },
        }


def test_callback_method_fail_no_method(callback_ports):
    port = callback_ports[1]

    resp = _post(port, {"method": "CallbackServer.no_method"})
    j = resp.json()
    assert j == {
        "error": {
            "code": -32601,
            "error": "No such CallbackServer method: no_method",
            "message": "No such CallbackServer method: no_method",
        },
    }
