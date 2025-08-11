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
import socket

# NOTE - the CBS is started once for this module. Don't assume it has any particular provenance
# stored.


# TODO make a test config or something
_TOKEN = os.environ["KB_AUTH_TOKEN"]

def _set_env_true(envvar):
    envold = os.environ.get(envvar)
    os.environ[envvar] = "true"
    return envold


def _restore_env(envvar, old_val):
    if old_val is None:
        os.environ.pop(envvar)
    else:
        os.environ[envvar] = old_val


@pytest.fixture(scope="module")
def callback_ports():
    # This setup is a mess. The running containers need the url of the callback server,
    # where the host cannot be 0.0.0.0 or localhost because they're containers.
    # However, the callback server needs to bind to one of those addresses.
    # Unfortunately, the current code assumes the bind address for the server and the
    # host address to supply to the containers is the same.
    # As such we get the host address to use for the sdk url for the containers and
    # set the IN_CONTAINER env var to force the server to bind to 0.0.0.0, even though
    # it's not running in a container.
    # If we don't set the ip address explicitly it calls an external service to get
    # the ip, which doesn't work if you're behind a NAT.
    # All of this needs a rethink / refactor
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com", 80))
    ip = s.getsockname()[0]
    s.close()

    db_old = _set_env_true("DEBUG_RUNNER")
    # make the server bind to 0.0.0.0 but keep the provided ip for the SDK_CALLBACK_URl
    ic_old = _set_env_true("IN_CONTAINER")

    cb_good = Callback(ip=ip, app_name="jr_good", allow_set_provenance=True, max_tasks=3)
    print("Starting cb good")
    cb_good.start_callback()

    cb_bad = Callback(ip=ip, app_name="jr_bad", allow_set_provenance=False)
    print("Starting cb bad")
    cb_bad.start_callback()

    time.sleep(1)

    yield cb_good.port, cb_bad.port

    _restore_env("DEBUG_RUNNER", db_old)
    _restore_env("IN_CONTAINER", ic_old)

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
                    "commit": "thisistotallyalegitgithash",
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
            "commit": "thisistotallyalegitgithash",
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
            "name": "CallbackServerError",
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
            "name": "CallbackServerError",
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
                "name": "CallbackServerError",
                "message": err,
            },
        }


def test_callback_method_fail_no_method(callback_ports):
    port = callback_ports[0]

    resp = _post(port, {"method": "CallbackServer.no_method"})
    j = resp.json()
    assert j == {
        "error": {
            "code": -32601,
            "name": "CallbackServerError",
            "message": "No such CallbackServer method: no_method",
        },
    }


def test_submit_job_sync(callback_ports):
    port = callback_ports[0]

    resp = _post(port, {
        "method": "njs_sdk_test_1.run",
        "params": [{"id": "whee"}],
        "context": {"service_ver": "dev"}
    })
    j = resp.json()
    assert j == {
        "result": [{
            "hash": "366eb8cead445aa3e842cbc619082a075b0da322",
            "id": "whee",
            "name": "njs_sdk_test_1"
        }],
        "finished": 1,
        "id": "callback",
        "version": "1.1"
    }


def test_submit_job_async(callback_ports):
    port = callback_ports[0]

    resp = _post(port, {
        "method": "njs_sdk_test_2._run_submit",
        "params": [{"id": "godiloveasynchrony"}],
        "service_ver": "beta",
    })
    j = resp.json()
    job_id = j["result"][0]
    res = {"result": [{"finished": 0}]}
    while not res["result"][0]["finished"]:
        time.sleep(.5)
        resp = _post(port, {
            "method": "CallbackServer._check_job",
            "params": [job_id]
        })
        res = resp.json()
    assert res == {"result": [{
        "result": [{
            "hash": "9d6b868bc0bfdb61c79cf2569ff7b9abffd4c67f",
            "id": "godiloveasynchrony",
            "name": "njs_sdk_test_2"
        }],
        "finished": 1,
        "id": "callback",
        "version": "1.1"
    }]}


def test_submit_fail_bad_method_names(callback_ports):
    port = callback_ports[0]

    badnames = ["DataFileUtilws_name_to_id", "DataFileUtil.ws_name_to_id.run"]

    for bn in badnames:
        resp = _post(port, {
            "method": bn,
            "params": ["JobRunner_test_public_ws"],
        })
        j = resp.json()
        assert j == {"error": {
            "code": -32000,
            "name": "CallbackServerError",
            "message": f"Illegal method name: {bn}",
        }}


def test_submit_fail_module_lookup_async(callback_ports):
    port = callback_ports[0]
    resp = _post(port, {
        "method": "DataFileUtilFake._ws_name_to_id_submit",
        "params": ["JobRunner_test_public_ws"],
    })
    j = resp.json()
    # ensure the catalog service trace is included.
    assert "biokbase/catalog/controller.py" in j["error"]["error"]
    assert "JobRunner/callback_server.py" in j["error"]["error"]
    del j["error"]["error"]
    assert j == {"error": {
        "code": -32000,
        "name": "CallbackServerError",
        "message": "Error looking up module DataFileUtilFake with version None: "
            + "'Module cannot be found based on module_name or git_url parameters.'",
    }}


def test_submit_fail_module_lookup_service_ver_sync(callback_ports):
    port = callback_ports[0]
    resp = _post(port, {
        "method": "KBaseReport.create",
        "params": ["JobRunner_test_public_ws"],
        "service_ver": "fake"
    })
    j = resp.json()
    # ensure the catalog service trace is included.
    assert "biokbase/catalog/Impl.py" in j["error"]["error"]
    assert "JobRunner/callback_server.py" in j["error"]["error"]
    del j["error"]["error"]
    assert j == {"error": {
        "code": -32000,
        "name": "CallbackServerError",
        "message": "Error looking up module KBaseReport with version fake: "
            + "'No module version found that matches your criteria!'",
    }}


def test_submit_job_fail_too_old_image(callback_ports):
    # This image was built such a long time ago modern versions of docker refuse to run it.
    # The error message thrown by the MethodRunner doesn't actually reflect this. The image
    # exists but docker refuses to pull it
    port = callback_ports[0]

    resp = _post(port, {
        "method": "HelloService.say_hello",
        "params": ["I'm not your buddy, pal"],
    })
    j = resp.json()
    assert "JobRunner/JobRunner/DockerRunner.py" in j["error"]["error"]
    del j["error"]["error"]
    assert j ==  {
        "error": {
            "code": -32601,
            "message": "Couldn't find image for "
                + "dockerhub-ci.kbase.us/kbase:helloservice.25528a3b917ab4f40bc7aba45b08e581e33d985a",
            "name": "CallbackServerError"
        },
        "finished": 1,
    }


def test_submit_fail_max_jobs_limit(callback_ports):
    port = callback_ports[0]

    jobs = [
        {
            "method": "njs_sdk_test_1.run",
            "ver": "dev",
            "params": [{"id": "child1", "cli_async": True, "wait": 3}]
        },
        {
            "method": "njs_sdk_test_1.run",
            "ver": "dev",
            "params": [{"id": "child2", "wait": 3}]
        },
    ]

    resp = _post(port, {
        "method": "njs_sdk_test_1.run",
        "params": [{"id": "parent", "wait": 1, "run_jobs_async": True, "jobs": jobs}]
    })
    j = resp.json()
    assert j == {"finished": 1,
       "id": "callback",
       "result": [{
            "hash": "366eb8cead445aa3e842cbc619082a075b0da322",
            "id": "parent",
            "name": "njs_sdk_test_1",
            "wait": 1,
            "jobs": [
                [{
                    "hash": "366eb8cead445aa3e842cbc619082a075b0da322",
                    "id": "child1",
                    "name": "njs_sdk_test_1",
                    "wait": 3
                }],
                [{
                    "hash": "366eb8cead445aa3e842cbc619082a075b0da322",
                    "id": "child2",
                    "name": "njs_sdk_test_1",
                    "wait": 3
                }],
            ],
        }],
       "version": "1.1"
    }

    jobs.append({
        "method": "njs_sdk_test_1.run",
        "ver": "dev",
        "params": [{"id": "child3", "cli_async": True, "wait": 3}]
    })
    resp = _post(port, {
        "method": "njs_sdk_test_1.run",
        "params": [{"id": "parent", "wait": 1, "run_jobs_async": True, "jobs": jobs}]
    })
    j = resp.json()
    # Ensure error from SDK module is picked up
    assert "lib/njs_sdk_test_1/njs_sdk_test_1Server.py" in j["error"]["error"]
    del j["error"]["error"]
    assert j == {
        "error": {
            "code": -32000,
            "message": "'No more than 3 concurrently running methods are allowed'",
            "name": "Server error"
        },
       "finished": 1,
       "id": "callback",
       "version": "1.1"
    }
