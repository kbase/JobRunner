import logging
from multiprocessing import Process, Queue, Event
import os
from queue import Empty
import requests
import signal
import socket
import threading
from time import sleep as _sleep, time as _time

from clients.authclient import KBaseAuth
from clients.CatalogClient import Catalog
from clients.execution_engine2Client import execution_engine2 as EE2

from .CatalogCache import CatalogCache
from .MethodRunner import MethodRunner
from .SpecialRunner import SpecialRunner
from .config import Config
from .callback_server import start_callback_server
from .exceptions import CantRestartJob
from .logger import Logger
from .provenance import Provenance

logging.basicConfig(format="%(created)s %(levelname)s: %(message)s",
                    level=logging.INFO)


# TODO CODE this whole system seems much too complex and is trying to serve too many purposes
#           Likely needs a large rethink / refactor


class JobRunner(object):
    """
    This class provides the mechanisms to launch a KBase job
    on a container runtime.  It handles starting the callback service
    to support subjobs and provenenace calls.
    """

    def __init__(self, config: Config, port=None):
        """
        inputs: config dictionary, EE2 URL, Job id, Token, Admin Token
        """

        self.ee2 = None
        if config.ee2_url:
            self.ee2 = EE2(url=config.ee2_url, timeout=60)
        self.logger = Logger(config.job_id, ee2=self.ee2)
        self.token = config.token
        self.client_group = os.environ.get("CLIENTGROUP", "None")
        self.bypass_token = os.environ.get("BYPASS_TOKEN", True)
        self.admin_token = config.admin_token
        self.config = config
        # self.config = self._init_config(config, job_id, ee2_url)

        self.hostname = config.hostname
        self.auth = KBaseAuth(config.auth_url)
        self.job_id = config.job_id
        self.workdir = config.workdir
        self.jr_queue = Queue()
        self.callback_queue = Queue()
        self.prov = None
        self._init_callback_url(port=port)
        self.debug = config.debug
        self.mr = MethodRunner(self.config, logger=self.logger, debug=self.debug)
        self.sr = SpecialRunner(self.config, self.job_id, logger=self.logger)
        catalog = Catalog(config.catalog_url, token=self.admin_token)
        self.cc = CatalogCache(catalog, self.admin_token)
        self._shutdown_event = Event()
        self._stop = False
        self.cbs = None
        self._watch_thread = None

        signal.signal(signal.SIGINT, self.shutdown)

    def _check_job_status(self) -> bool:
        """
        returns True if the job is still okay to run.
        """
        status = {'finished': False}
        try:
            if self.ee2:
                status = self.ee2.check_job_canceled({"job_id": self.job_id})
        except Exception as e:
            self.logger.error(
                f"Warning: Job cancel check failed due to {e}. However, the job will continue to run."
            )
            return True
        if status.get("finished", False):
            return False
        return True

    def _init_workdir(self):
        """
        Check to see for existence of scratch dir:
        e.g. /mnt/awe/condor or /cdr/
        """
        if not os.path.exists(self.workdir):
            self.logger.error("Missing workdir")
            raise OSError("Missing Working Directory")

    def _get_cgroup(self) -> str:
        """ Examine /proc/PID/cgroup to get the cgroup the runner is using """
        if os.environ.get("NO_CGROUP"):
            return None
        pid = os.getpid()
        cfile = "/proc/{}/cgroup".format(pid)
        # TODO REMOVE THIS OR FIGURE OUT FOR TESTING WHAT TO DO ABOUT THIS
        if not os.path.exists(cfile):
            raise Exception(f"Couldn't find cgroup {cfile}")
        else:
            with open(cfile) as f:
                for line in f:
                    if line.find("htcondor") > 0:
                        items = line.split(":")
                        if len(items) == 3:
                            return items[2].strip()

        raise Exception(f"Couldn't parse out cgroup from {cfile}")

    def _submit_special(self, config: dict, job_id: str, job_params: dict):
        """
        Handler for methods such as CWL, WDL and HPC
        """
        (module, method) = job_params["method"].split(".")
        self.logger.log(f"Submit {job_id} as a {module}:{method} job")

        self.sr.run(
            config,
            job_params,
            job_id,
            callback=self.callback_url,
            fin_q=[self.jr_queue],
        )

    def _submit(self, config: dict, job_id: str, job_params: dict, subjob=True):
        (module, method) = job_params["method"].split(".")
        service_ver = job_params.get("service_ver")
        if service_ver is None:
            service_ver = job_params.get("context", {}).get("service_ver")

        # TODO Fail gracefully if this step fails. For example, setting service_ver='fake'
        module_info = self.cc.get_module_info(module, service_ver)

        git_url = module_info["git_url"]
        git_commit = module_info["git_commit_hash"]
        if not module_info["cached"]:
            fstr = "Running module {}: url: {} commit: {}"
            self.logger.log(fstr.format(module, git_url, git_commit))
        else:
            version = module_info["version"]
            f = "WARNING: Module {} was already used once for this job. "
            f += "Using cached version: url: {} "
            f += "commit: {} version: {} release: release"
            self.logger.error(f.format(module, git_url, git_commit, version))

        vm = self.cc.get_volume_mounts(module, method, self.client_group)
        config["volume_mounts"] = vm

        action = self.mr.run(
            config,
            module_info,
            job_params,
            job_id,
            callback=self.callback_url,
            subjob=subjob,
            fin_q=self.jr_queue,
        )
        self._update_prov(action)

    def _cancel(self):
        self.mr.cleanup_all(debug=self.debug)

    def shutdown(self, sig, bt):
        logging.warning("Recieved an interrupt")
        # Send a cancel to the queue
        self.jr_queue.put(["cancel", None, None])

    def _watch(self, config: dict) -> dict:
        # Run a thread to check for expired token
        # Run a thread for 7 day max job runtime
        # TODO in callback server mode (e.g. Sanic) if this loop exits the server
        # hangs forever. Needs to be reworked so that doesn't happen, which seems like a big lift
        ct = 1
        exp_time = self._get_token_lifetime() - 600
        while not self._stop:
            try:
                req = self.jr_queue.get(timeout=1)
                if _time() > exp_time:
                    err = "Token has expired"
                    self.logger.error(err)
                    self._cancel()
                    return {"error": err}
                if req[0] == "submit":
                    if ct > self.config.max_tasks:
                        self.logger.error("Too many subtasks")
                        self._cancel()
                        return {"error": "Canceled or unexpected error"}
                    if req[2].get("method").startswith("special."):
                        self._submit_special(
                            config=config, job_id=req[1], job_params=req[2]
                        )
                    else:
                        self._submit(config=config, job_id=req[1], job_params=req[2])
                    ct += 1
                elif req[0] == "set_provenance":
                    # Ok, we're syncing provenance in 2 different places by sending messages
                    # on 2 different queues. I think there may be design issues here
                    self.prov = req[2]
                    self.callback_queue.put(["prov", None, self.prov.get_prov()])
                elif req[0] == "finished_special":
                    job_id = req[1]
                    self.callback_queue.put(["output", job_id, req[2]])
                    ct -= 1
                elif req[0] == "finished":
                    subjob = True
                    job_id = req[1]
                    if job_id == self.job_id:
                        subjob = False
                    output = self.mr.get_output(job_id, subjob=subjob)
                    self.callback_queue.put(["output", job_id, output])
                    ct -= 1
                    if not subjob:
                        if ct > 0:
                            err = "Orphaned containers may be present"
                            self.logger.error(err)
                        return output
                elif req[0] == "cancel":
                    self._cancel()
                    return {}
            except Empty:
                pass
            if ct == 0:
                logging.error("Count got to 0 without finish")
                # This shouldn't happen
                return
            # Run cancellation / finish job checker
            if not self._check_job_status():
                self.logger.error("Job canceled or unexpected error")
                self._cancel()
                _sleep(5)
                return {"error": "Canceled or unexpected error"}

    def _init_callback_url(self, port=None):
        # Find a free port and Start up callback server
        if os.environ.get("CALLBACK_IP") is not None:
            self.ip = os.environ.get("CALLBACK_IP")
            self.logger.log("Callback IP provided ({})".format(self.ip))
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("gmail.com", 80))
            self.ip = s.getsockname()[0]
            s.close()
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", 0))
        if port:
            self.port = port
        else:
            self.port = sock.getsockname()[1]
        sock.close()
        url = "http://{}:{}/".format(self.ip, self.port)
        self.logger.log("Job runner received Callback URL {}".format(url))
        self.callback_url = url

    def _update_prov(self, action: dict):
        self.prov.add_subaction(action)
        self.callback_queue.put(["prov", None, self.prov.get_prov()])

    def _validate_token(self):
        # Validate token and get user name
        try:
            user = self.auth.get_user(self.token)
        except Exception as e:
            self.logger.error("Token validation failed")
            raise Exception(e)

        return user

    def _get_token_lifetime(self):
        try:
            url = self.config.auth2_url
            logging.info(f"About to get token lifetime from {url} for user token")
            header = {"Authorization": self.token}
            resp = requests.get(url, headers=header).json()
            return resp["expires"]
        except Exception as e:
            self.logger.error("Failed to get token lifetime")
            raise e

    def _retry_finish(self, finish_job_params: dict, success: bool):
        """
        In case of failure to finish, retry once
        """
        if success:
            if (
                "job_output" not in finish_job_params
                or finish_job_params["job_output"] is None
            ):
                finish_job_params["job_output"] = {}

        try:
            if self.ee2:
                self.ee2.finish_job(finish_job_params)
        except Exception:
            _sleep(30)
            if self.ee2:
                self.ee2.finish_job(finish_job_params)

    def run(self):
        """
        This method starts the actual run.  This is a blocking operation and
        will not return until the job finishes or encounters and error.
        This method also handles starting up the callback server.
        """
        running_msg = f"Running job {self.job_id} ({os.environ.get('CONDOR_ID')}) on {self.hostname} ({self.ip}) in {self.workdir}"

        self.logger.log(running_msg)
        logging.info(running_msg)

        cg_msg = "Client group: {}".format(self.client_group)
        self.logger.log(cg_msg)
        logging.info(cg_msg)

        # Check to see if the job was run before or canceled already.
        # If so, log it
        logging.info("About to check job status")
        if not self._check_job_status():
            error_msg = "Job already run or terminated"
            self.logger.error(error_msg)
            logging.error(error_msg)
            raise CantRestartJob(error_msg)

        # Get job inputs from ee2 db
        # Config is not stored in job anymore, its a server wide config
        # I don't think this matters for reproducibility

        logging.info("About to get job params and config")
        try:
            job_params = self.ee2.get_job_params({"job_id": self.job_id})

        except Exception as e:
            self.logger.error("Failed to get job parameters. Exiting.")
            raise e

        try:
            config = self.ee2.list_config()
        except Exception as e:
            self.logger.error("Failed to config . Exiting.")
            raise e

        # config["job_id"] = self.job_id
        self.logger.log(
            f"Server version of Execution Engine: {config.get('ee.server.version')}"
        )

        # Update job as started and log it
        logging.info("About to start job")
        try:
            self.ee2.start_job({"job_id": self.job_id})
        except Exception as e:
            self.logger.error(
                "Job already started once. Job restarts are not currently supported"
            )
            raise e

        logging.info("Initing work dir")
        self._init_workdir()
        self.config.user = self._validate_token()
        self.config.cgroup = self._get_cgroup()

        logging.info("Setting provenance")
        self.prov = Provenance(job_params)

        # Start the callback server
        logging.info("Starting callback server")
        cb_args = [
            self.ip,
            self.port,
            self.jr_queue,
            self.callback_queue,
            self.token,
            self.bypass_token,
        ]
        self.cbs = Process(target=start_callback_server, args=cb_args)
        self.cbs.start()

        # Submit the main job
        self.logger.log(f"Job is about to run {job_params.get('app_id')}")

        # TODO Try except for when submit or watch failure happens and correct finishjob call
        self._submit(
            config=config, job_id=self.job_id, job_params=job_params, subjob=False
        )
        output = self._watch(config)
        self.cbs.terminate()
        self.logger.log("Job is done")

        error = output.get("error")
        if error:
            error_message = "Job output contains an error"
            self.logger.error(f"{error_message} {error}")
            self._retry_finish(
                {"job_id": self.job_id, "error_message": error_message, "error": error},
                success=False,
            )
        else:
            self._retry_finish(
                {"job_id": self.job_id, "job_output": output}, success=True
            )

        # TODO: Attempt to clean up any running docker containers
        #       (if something crashed, for example)
        return output

        # Run docker or shifter	and keep a record of container id and
        #  subjob container ids
        # Run a job shutdown hook

    def callback(self, job_params=None, app_name=None):
        """
        This method just does the minimal steps to run the call back server.
        """
        running_msg = f"Running job {self.job_id} on {self.hostname} ({self.ip}) in {self.workdir}"

        self.logger.log(running_msg)

        base = self.config.base_url
        # TODO: Some of this should come from some config file that may live
        #       in the module being tested.
        config = {
            'kbase-endpoint': base,
            'external-url': f"{base}ee2",
            'shock-url': f"{base}shock-api",
            'handle-url': f"{base}handle_service",
            'srv-wiz-url': f"{base}service_wizard",
            'auth-service-url': f"{base}auth/api/legacy/KBase/Sessions/Login",
            'auth-service-url-v2': f"{base}auth/api/V2/token",
            'auth-service-url-allow-insecure': False,
            'scratch': '/kb/module/work/tmp',
            'workspace-url': f"{base}ws",
            'ref_data_base': '/tmp/db'
        }
        # config["job_id"] = self.job_id

        if not job_params:
            job_params = {
                'method': 'sdk.sdk',
                'service_ver': '1.0',
                'params': [{}]
            }

        self.prov = Provenance(job_params)
        self._init_workdir()
        job_dir = os.path.join(self.workdir, "workdir")  # TODO should handle this in mr
        # TODO: This is calling a private method.
        self.mr._init_workdir(config, job_dir, job_params)
        self.config.user = self._validate_token()

        # Start the callback server
        logging.info("Starting callback server")
        cb_args = [
            self.ip,
            self.port,
            self.jr_queue,
            self.callback_queue,
            self.token,
            self.bypass_token,
            self.cc,
        ]
        kwargs = {"shutdown_event": self._shutdown_event, "max_tasks": self.config.max_tasks}
        if app_name:
            kwargs["app_name"] = app_name  # don't add if None
        self.cbs = Process(target=start_callback_server, args=cb_args, kwargs=kwargs)
        self.cbs.start()
        self._watch_thread = threading.Thread(target=self._watch, args=[config])
        self._watch_thread.start()

    def stop(self):
        """
        Stop any running callback server and stop the job runner event loop.
        
        After calling this method this instance of the job runner is no longer usable.
        """
        self._shutdown_event.set()
        self._stop = True
        self.wait_for_stop()

    def wait_for_stop(self):
        if self._watch_thread:
            self._watch_thread.join()
        if self.cbs:
            self.cbs.join()
