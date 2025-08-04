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

from clients.baseclient import ServerError
from JobRunner.CatalogCache import CatalogCache
from .provenance import Provenance

Config.SANIC_REQUEST_TIMEOUT = 300


# may need to put these in the app.config too?
outputs = dict()
prov = []


def create_app(app_name: str = "jobrunner", shutdown_event: multiprocessing.Event = None):
    app = Sanic(app_name)

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
            return json(_error("Unexpected error", trace=stack), status=500)
    return app


def start_callback_server(
        ip,
        port,
        out_queue,
        in_queue,
        token,
        bypass_token,
        cc: CatalogCache,
        app_name: str = "jobrunner",
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
        "catcache": cc,
    }
    app = create_app(app_name=app_name, shutdown_event=shutdown_event)
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
    # We should just use the passed in token from the call
    # Would that break apps?
    if token != app.config.get("token"):
        if app.config.get("bypass_token"):
            pass
        else:
            raise SanicException(status_code=401)


def _handle_get_provenance(app):
    _check_finished(app, info="Handle get provenance")
    return {"result": [prov]}


def _handle_set_provenance(app, data):
    # strict, should be used carefully
    if os.environ.get("CALLBACK_ALLOW_SET_PROVENANCE") != "true":
        return _error("Setting provenance is not enabled")
    if (not data.get("params")
        or not isinstance(data["params"], list)
        or len(data["params"]) != 1
        or not isinstance(data["params"][0], dict)
    ):
        return _error("method params must be a list containing exactly one provenance action")
    prov = Provenance(data["params"][0])
    app.config["out_q"].put(["set_provenance", None, prov])
    return {"result": [prov.get_prov()]}


def _check_module_lookup(app, module, data):
    # check errors before submitting to the queue, otherwise the watch loop dies and the
    # server hangs. This needs to be rewritten to remove the queues and architect the server
    # to work the same way as the old Java server
    service_ver = data.get("service_ver")
    if service_ver is None:
        service_ver = data.get("context", {}).get("service_ver")
    err = f"Error looking up module {module} with version {service_ver}: "
    try:
        app.config["catcache"].get_module_info(module, service_ver)
    except ServerError as e:
        return _error(err + e.message, trace=f"{traceback.format_exc()}\n{e.data}")
    except Exception as e:  # Dunno how to test this
        return _error(err + str(e), trace=traceback.format_exc())
    return None


def _handle_submit(app, module, method, data, token):
    # Validate the module and version using the CatalogCache before submitting the job.
    # If there is an error with the module lookup, return the error response immediately.
    if err := _check_module_lookup(app, module, data):
        return err

    _check_rpc_token(app, token)
    job_id = str(uuid.uuid1())
    data["method"] = "%s.%s" % (module, method[1:-7])
    app.config["out_q"].put(["submit", job_id, data])
    return {"result": [job_id]}


def _error(errstr, trace=None, code=-32000):
    err = {"message": errstr, "code": code}
    if trace:
        err["error"] = trace
    return {"error": err}


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
    elif module == "CallbackServer":
        if method == "get_provenance":
            return _handle_get_provenance(app)
        if method == "set_provenance":
            return _handle_set_provenance(app, data)
        # https://www.jsonrpc.org/specification#error_object
        return _error(f"No such CallbackServer method: {method}", code=-32601)
    else:
        # Does this even happen any more?
        # Sync Job
        # Validate the module and version using the CatalogCache before submitting the job.
        # If there is an error with the module lookup, return the error response immediately.
        if err := _check_module_lookup(app, module, data):
            return err
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
