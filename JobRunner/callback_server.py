import asyncio
import uuid
import os
from queue import Empty
import logging
from typing import Annotated, Union
from fastapi import FastAPI, Header
from pydantic import BaseModel
import uvicorn


app = FastAPI()

outputs = dict()
prov = []
token = None
bypass_token = False
in_q = None
out_q = None


def abort():
    print("TODO")


def config(conf):
    global token
    global out_q
    global in_q
    token = conf["token"]
    out_q = conf["out_q"]
    in_q = conf["in_q"]


def start_callback_server(ip, port, out_queue, in_queue, token, bypass_token):
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
    #app.config.update(conf)
    config(conf)
    if os.environ.get("IN_CONTAINER"):
        ip = "0.0.0.0"
    #app.run(host=ip, port=port, debug=False, access_log=False)
    uvconfig = uvicorn.Config("JobRunner.callback_server:app", host=ip, port=port, log_level="info")
    server = uvicorn.Server(uvconfig)
    server.run()



class RPC(BaseModel):
    method: str


@app.post("/")
async def root(data: dict, Authorization: Annotated[Union[str, None], Header()] = None):
#    data = request.json
    if data is not None and "method" in data:
        token = Authorization
        response = await _process_rpc(data, token)
        status = 500 if "error" in response else 200
        # return json(response, status=status)
        return response
    return {}


def _check_finished(info=None):
    global prov
    global in_q
    logging.debug(info)
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


def _check_rpc_token(req_token):
    global token
    if req_token != token:
        if bypass_token:
            pass
        else:
            abort(401)


def _handle_provenance():
    _check_finished(info="Handle Provenance")
    return {"result": [prov]}


def _handle_submit(module, method, data, token):
    global out_q
    _check_rpc_token(token)
    job_id = str(uuid.uuid1())
    data["method"] = "%s.%s" % (module, method[1:-7])
    out_q.put(["submit", job_id, data])
    return {"result": [job_id]}


def _handle_checkjob(data):
    if "params" not in data:
        abort(404)
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
            logging.debug(e)

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
        _check_rpc_token(token)
        job_id = str(uuid.uuid1())
        data["method"] = "%s.%s" % (module, method)
        out_q.put(["submit", job_id, data])
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
            logging.error(exception_message)
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
