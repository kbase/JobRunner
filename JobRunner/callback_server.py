import asyncio
import multiprocessing
import os
from queue import Empty
import traceback
import uuid

from sanic import Sanic
from sanic.config import Config
from sanic.exceptions import SanicException
from sanic.log import logger
from sanic.response import json


Config.SANIC_REQUEST_TIMEOUT = 300


# may need to put these in the app.config too?
outputs = dict()
prov = []


def create_app(shutdown_event: multiprocessing.Event = None):
    app = Sanic("jobrunner")

    if shutdown_event:
        @app.after_server_start
        async def shutdown_listener(app, _):
            while not shutdown_event.is_set():
                await asyncio.sleep(0.1)
            app.stop()

    @app.route("/", methods=["GET", "POST"])
    async def root(request):
        data = request.json
        try:
            if request.method == "POST" and data is not None and "method" in data:
                token = request.headers.get("Authorization")
                response = await _process_rpc(request.app, data, token)
                status = 500 if "error" in response else 200
                return json(response, status=status)
            return json([{}])
        except Exception as e:
            stack = traceback.format_exc()
            print(f"Exception when processing jsonrpc: {e}\n: {stack}")
            return json(_error("Unexpected error"), status=500)
    return app


def start_callback_server(
        ip,
        port,
        out_queue,
        in_queue,
        token,
        bypass_token,
        shutdown_event: multiprocessing.Event = None
    ):
    timeout = 3600
    max_size_bytes = 100000000000
    conf = {
        "token": token,
        "out_q": out_queue,
        "in_q": in_queue,
        "bypass_token": bypass_token,
        "RESPONSE_TIMEOUT": timeout,
        "REQUEST_TIMEOUT": timeout,
        "KEEP_ALIVE_TIMEOUT": timeout,
        "REQUEST_MAX_SIZE": max_size_bytes,
    }
    app = create_app(shutdown_event=shutdown_event)
    app.config.update(conf)
    if os.environ.get("IN_CONTAINER"):
        ip = "0.0.0.0"
    app.run(host=ip, port=port, debug=False, access_log=False, motd=False)


def _check_finished(app, info=None):
    global prov
    logger.debug(info)
    in_q = app.config["in_q"]
    try:
        # Flush the queue
        while True:
            [mtype, fjob_id, output] = in_q.get(block=False)
            if mtype == "output":
                outputs[fjob_id] = output
            elif mtype == "prov":
                prov = output
    except Empty:
        pass


def _check_rpc_token(app, token):
    if token != app.config.get("token"):
        if app.config.get("bypass_token"):
            pass
        else:
            raise SanicException(status_code=401)


def _handle_get_provenance(app):
    _check_finished(app, info="Handle get provenance")
    return {"result": [prov]}


def _handle_submit(app, module, method, data, token):
    _check_rpc_token(app, token)
    job_id = str(uuid.uuid1())
    data["method"] = "%s.%s" % (module, method[1:-7])
    app.config["out_q"].put(["submit", job_id, data])
    return {"result": [job_id]}


def _error(errstr, code=-32000):
    return {"error": {"error": errstr, "message": errstr, "code": code}}


def _handle_checkjob(app, data):
    if "params" not in data:
        raise SanicException(status_code=404)
    job_id = data["params"][0]
    _check_finished(app, f"Checkjob for {job_id}")
    resp = {"finished": 0}

    if job_id in outputs:
        resp = outputs[job_id]
        resp["finished"] = 1
        try:
            if "error" in resp:
                return resp
        except Exception as e:
            logger.debug(e)

    return {"result": [resp]}


async def _process_rpc(app, data, token):
    """
    Handle KBase SDK App Client Requests
    """

    (module, method) = data["method"].split(".")
    # async submit job
    if method.startswith("_") and method.endswith("_submit"):
        return _handle_submit(app, module, method, data, token)
    # check job
    elif method.startswith("_check_job"):
        return _handle_checkjob(app, data=data)
    # Provenance
    elif method.startswith("get_provenance"):
        return _handle_get_provenance(app)
    else:
        # Sync Job
        _check_rpc_token(app, token)
        job_id = str(uuid.uuid1())
        data["method"] = "%s.%s" % (module, method)
        app.config["out_q"].put(["submit", job_id, data])
        try:
            while True:
                _check_finished(app, f'synk check for {data["method"]} for {job_id}')
                if job_id in outputs:
                    resp = outputs[job_id]
                    resp["finished"] = 1
                    return resp
                await asyncio.sleep(1)
        except Exception as e:
            # Attempt to log error, but this is not very effective..
            exception_message = f"Timeout or exception: {e} {type(e)}"
            logger.error(exception_message)
            error_obj = {
                "error": exception_message,
                "code": "123",
                "message": exception_message,
            }
            outputs[job_id] = {
                "result": exception_message,
                "error": error_obj,
                "finished": 1,
            }
            return outputs[job_id]
