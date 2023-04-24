# Import the Sanic app, usually created with Sanic(__name__)
from JobRunner.callback_server import create_app
import json
from queue import Queue
from unittest.mock import patch
from pprint import pprint

_TOKEN = "bogus"

conf = {"TOKEN": _TOKEN, "BYPASS_TOKEN": 1, "MOTD": False}
app = create_app(conf)
sa_args = {"motd": False, "access_log": False}


def _post(data):
    # Returns -> httpx.Response:
    header = {"Authorization": _TOKEN}
    return app.test_client.post("/", server_kwargs=sa_args,
                                headers=header, data=data)[1]


def test_cb_returns_200():
    response = app.test_client.get("/", server_kwargs=sa_args)[1]
    assert response.status == 200


def test_cb_post_empty():
    response = _post(None)
    print(response.json)
    assert response.json == [{}]


def test_cb_post():
    out_q = Queue()
    in_q = Queue()
    conf = {"TOKEN": _TOKEN, "OUT_Q": out_q, "IN_Q": in_q}
    app.config.update(conf)
    data = json.dumps({"method": "bogus._test_submit"})
    response = _post(data)
    assert "result" in response.json
    job_id = response.json["result"][0]
    mess = out_q.get()
    assert "submit" in mess
    data = json.dumps({"method": "bogus._check_job", "params": [job_id]})
    response = _post(data)
    pprint(response)

    assert "result" in response.json
    assert response.json["result"][0]["finished"] == 0
    data = json.dumps({"method": "bogus.get_provenance", "params": [job_id]})
    response = _post(data)
    assert "result" in response.json
    assert response.json["result"][0] in [None, []]
    in_q.put(["prov", job_id, "bogus"])
    response = _post(data)
    assert "result" in response.json
    assert response.json["result"][0] == "bogus"
    in_q.put(["output", job_id, {"foo": "bar"}])
    data = json.dumps({"method": "bogus._check_job", "params": [job_id]})
    response = _post(data)
    assert "result" in response.json
    assert response.json["result"][0]["finished"] == 1
    assert "foo" in response.json["result"][0]


@patch("JobRunner.callback_server.uuid", autospec=True)
def test_cb_submit_sync(mock_uuid):
    out_q = Queue()
    in_q = Queue()
    conf = {"TOKEN": _TOKEN, "OUT_Q": out_q, "IN_Q": in_q}
    app.config.update(conf)
    mock_uuid.uuid1.return_value = "bogus"
    data = json.dumps({"method": "bogus.test"})
    in_q.put(["output", "bogus", {"foo": "bar"}])
    response = _post(data)
    assert "finished" in response.json
    assert "foo" in response.json
