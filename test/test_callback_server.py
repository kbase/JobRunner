# Import the Sanic app, usually created with Sanic(__name__)

import json
import pytest
from queue import Queue
from unittest.mock import patch, create_autospec

from JobRunner.callback_server import create_app
from JobRunner.CatalogCache import CatalogCache

_TOKEN = "bogus"


@pytest.fixture(scope="module")
def app():
    yield create_app()


def _post(app, data):
    # Returns -> httpx.Response:
    header = {"Authorization": _TOKEN}
    sa = {"access_log": False}
    return app.test_client.post("/", server_kwargs=sa, headers=header, data=data)[1]


def test_index_returns_200(app):
    response = app.test_client.get("/")[1]
    assert response.status == 200


def test_index_post_empty(app):
    response = _post(app, None)
    print(response.json)
    assert response.json == [{}]


def test_index_post(app):
    out_q = Queue()
    in_q = Queue()
    # just make the cache do nothing when called so the submit call works
    cc = create_autospec(CatalogCache, spec_set=True, instance=True)
    conf = {"token": _TOKEN, "out_q": out_q, "in_q": in_q, "catcache": cc}
    app.config.update(conf)
    data = json.dumps({"method": "bogus._test_submit"})
    response = _post(app, data)
    assert "result" in response.json
    job_id = response.json["result"][0]
    mess = out_q.get()
    assert "submit" in mess
    data = json.dumps({"method": "bogus._check_job", "params": [job_id]})
    response = _post(app, data)

    assert "result" in response.json
    assert response.json["result"][0]["finished"] is 0
    data = json.dumps({"method": "CallbackServer.get_provenance"})
    response = _post(app, data)
    assert "result" in response.json
    assert response.json["result"][0] in [None,[]]
    in_q.put(["prov", job_id, "bogus"])
    response = _post(app, data)
    assert "result" in response.json
    assert response.json["result"][0] == "bogus"
    in_q.put(["output", job_id, {"foo": "bar"}])
    data = json.dumps({"method": "bogus._check_job", "params": [job_id]})
    response = _post(app, data)
    assert "result" in response.json
    assert response.json["result"][0]["finished"] is 1
    assert "foo" in response.json["result"][0]


@patch("JobRunner.callback_server.uuid", autospec=True)
def test_index_submit_sync(mock_uuid, app):
    out_q = Queue()
    in_q = Queue()
    conf = {"token": _TOKEN, "out_q": out_q, "in_q": in_q}
    app.config.update(conf)
    mock_uuid.uuid1.return_value = "bogus"
    data = json.dumps({"method": "bogus.test"})
    in_q.put(["output", "bogus", {"foo": "bar"}])
    response = _post(app, data)
    assert "finished" in response.json
    assert "foo" in response.json

