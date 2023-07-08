from JobRunner.callback_server import app, config
from fastapi.testclient import TestClient
import json
from queue import Queue
from unittest.mock import patch
from pprint import  pprint

_TOKEN = "bogus"

client = TestClient(app)


def _post(data):
    # Returns -> httpx.Response:
    header = {"Authorization": _TOKEN}
    sa = {"access_log": False}
    return client.post("/", headers=header, json=data)


def xtest_cb_returns_200():
    response = client.get("/")[1]
    assert response.status == 200


def test_cb_post_empty():
    response = _post({})
    assert response.json() == {}


def test_cb_post():
    out_q = Queue()
    in_q = Queue()
    conf = {"token": _TOKEN, "out_q": out_q, "in_q": in_q}
    config(conf)
    data = {"method": "bogus._test_submit"}
    response = _post(data)
    assert "result" in response.json()
    job_id = response.json()["result"][0]
    mess = out_q.get()
    assert "submit" in mess
    data = {"method": "bogus._check_job", "params": [job_id]}
    response = _post(data)
    pprint(response.json())

    assert "result" in response.json()
    assert response.json()["result"][0]["finished"]==0
    data = {"method": "bogus.get_provenance", "params": [job_id]}
    response = _post(data)
    assert "result" in response.json()
    assert response.json()["result"][0] in [None,[]]
    in_q.put(["prov", job_id, "bogus"])
    response = _post(data)
    assert "result" in response.json()
    assert response.json()["result"][0] == "bogus"
    in_q.put(["output", job_id, {"foo": "bar"}])
    data = {"method": "bogus._check_job", "params": [job_id]}
    response = _post(data)
    assert "result" in response.json()
    assert response.json()["result"][0]["finished"]==1
    assert "foo" in response.json()["result"][0]


@patch("JobRunner.callback_server.uuid", autospec=True)
def test_cb_submit_sync(mock_uuid):
    out_q = Queue()
    in_q = Queue()
    conf = {"token": _TOKEN, "out_q": out_q, "in_q": in_q}
    #app.config.update(conf)
    config(conf)
    mock_uuid.uuid1.return_value = "bogus"
    data = {"method": "bogus.test"}
    in_q.put(["output", "bogus", {"foo": "bar"}])
    response = _post(data)
    assert "finished" in response.json()
    assert "foo" in response.json()

