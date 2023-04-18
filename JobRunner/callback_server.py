import asyncio
import os
import uuid
from queue import Empty

from sanic import Sanic
from sanic.config import Config
from sanic.exceptions import SanicException
from sanic.log import logger
from sanic.response import json

Config.SANIC_REQUEST_TIMEOUT = 300

# app = Sanic.get_app(name="myApp", force_create=True)
outputs = dict()
prov = []

def start_callback_server(ip, port, out_queue, in_queue, token, bypass_token):
    app = Sanic.get_app(name="myApp", force_create=True)
    timeout = 3600
    max_size_bytes = 100000000000
    conf = {
        "TOKEN": token,
        "OUT_Q": out_queue,
        "IN_Q": in_queue,
        "BYPASS_TOKEN": bypass_token,
        "RESPONSE_TIMEOUT": timeout,
        "REQUEST_TIMEOUT": timeout,
        "KEEP_ALIVE_TIMEOUT": timeout,
        "REQUEST_MAX_SIZE": max_size_bytes,
    }

    app.ctx.TOKEN = token
    app.ctx.OUT_Q = out_queue
    app.ctx.IN_Q = in_queue
    app.ctx.BYPASS_TOKEN = bypass_token
    app.ctx.RESPONSE_TIMEOUT = timeout
    app.ctx.REQUEST_TIMEOUT = timeout
    app.ctx.KEEP_ALIVE_TIMEOUT = timeout
    app.ctx.REQUEST_MAX_SIZE = max_size_bytes

    print("before update: ", conf)
    print("In scs app.ctx: ", app.ctx)

    app.config["TOKEN"] = token
    app.config["OUT_Q"] = out_queue
    app.config["IN_Q"] = in_queue
    app.config["BYPASS_TOKEN"] = bypass_token
    app.config["RESPONSE_TIMEOUT"] = timeout
    app.config["REQUEST_TIMEOUT"] = timeout
    app.config["KEEP_ALIVE_TIMEOUT"] = timeout
    app.config["REQUEST_MAX_SIZE"] = max_size_bytes

    print("after update: ", app.config)

    #app.add_route(root, '/', methods=["GET", "POST"])

    #app.run(host=ip, port=port, debug=False, access_log=False)
    app.run(host=ip, port=port, debug=True, access_log=False)


@app.route("/", methods=["GET", "POST"])
async def root(request):
    data = request.json
    print("data is: ", data)
    print("request header is: ", request.headers)
    if request.method == "POST" and data is not None and "method" in data:
        token = request.headers.get("Authorization")
        response = await _process_rpc(data, token)
        status = 500 if "error" in response else 200
        return json(response, status=status)
    return json([{}])


def _check_finished(info=None):
    app = Sanic.get_app(name="myApp")
    global prov
    logger.debug(info)
    in_q = app.config["IN_Q"]
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


def _check_rpc_token(token):
    app = Sanic.get_app(name="myApp")
    print("token checking")
    print("app.config is: ", app.config)
    print("app.ctx is: ", app.ctx)
    if token != app.config.get("TOKEN"):
        print("token passed in is: ", token)
        print("token in app.config is: ", app.config.get("TOKEN"))
        print("token is not right")
        if app.config.get("BYPASS_TOKEN"):
            print("Bypass token")
            pass
        else:
            # abort(401)
            print("raise Exception")
            raise SanicException(status_code=401)


def _handle_provenance():
    _check_finished(info="Handle Provenance")
    return {"result": [prov]}


def _handle_submit(module, method, data, token):
    app = Sanic.get_app(name="myApp")
    _check_rpc_token(token)
    job_id = str(uuid.uuid1())
    data["method"] = "%s.%s" % (module, method[1:-7])
    app.config["OUT_Q"].put(["submit", job_id, data])
    return {"result": [job_id]}


def _handle_checkjob(data):
    if "params" not in data:
        # abort(404)
        raise SanicException(status_code=404)
    job_id = data["params"][0]
    _check_finished(f"Checkjob for {job_id}")
    resp = {"finished": 0}

    if job_id in outputs:
        resp = outputs[job_id]
        resp["finished"] = 1
        try:
            if "error" in resp:
                return {"result": [resp], "error": resp["error"]}
        except Exception as e:
            logger.debug(e)

    return {"result": [resp]}


async def _process_rpc(data, token):
    """
    Handle KBase SDK App Client Requests
    """
    
    (module, method) = data["method"].split(".")
    # async submit job
    if method.startswith("_") and method.endswith("_submit"):
        return _handle_submit(module, method, data, token)
    # check job
    elif method.startswith("_check_job"):
        return _handle_checkjob(data=data)
    # Provenance
    elif method.startswith("get_provenance"):
        return _handle_provenance()
    else:
        # Sync Job
        app = Sanic.get_app(name="myApp")
        _check_rpc_token(token)
        job_id = str(uuid.uuid1())
        data["method"] = "%s.%s" % (module, method)
        app.config["OUT_Q"].put(["submit", job_id, data])
        try:
            while True:
                _check_finished(f'synk check for {data["method"]} for {job_id}')
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
