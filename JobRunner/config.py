import logging
import os
from socket import gethostname


_TOKEN_ENV = "KB_AUTH_TOKEN"
_ADMIN_TOKEN_ENV = "KB_ADMIN_AUTH_TOKEN"
_DEBUG = "DEBUG_MODE"


def _get_token():
    # Get the token from the environment or a file.
    # Set the KB_AUTH_TOKEN if not set.
    token = None
    if _TOKEN_ENV in os.environ:
        token = os.environ[_TOKEN_ENV]
    elif os.path.exists("token"):
        with open("token") as f:
            token = f.read().rstrip()
        os.environ[_TOKEN_ENV] = token
    return token


def _get_admin_token():
    if _ADMIN_TOKEN_ENV not in os.environ:
        return None
    # We pop the token so it isn't exposed later
    admin_token = os.environ.pop("KB_ADMIN_AUTH_TOKEN")
    if _ADMIN_TOKEN_ENV in os.environ:
        logging.error("Failed to sanitize environment")
    return admin_token


class Config():
    job_id = None
    workdir = None
    base_url = "https://ci.kbase.us/services/"
    ee2_url = None
    token = None
    admin_token = None
    runtime = None
    hostname = None
    debug = False
    cgroup = None
    user = None

    def __init__(self, workdir=None, base_url=None, job_id=None, use_ee2=True):
        if workdir:
            self.workdir = workdir
        else:
            self.workdir = os.getcwd()
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)
            logging.info(f"Creating work directory at {self.workdir}")
        if base_url:
            self.base_url = base_url
        _auth_ext = "auth/api/legacy/KBase/Sessions/Login"
        if use_ee2:
            self.ee2_url = f"{self.base_url}ee2"
        else:
            self.ee2_url = None
        self.catalog_url = f"{self.base_url}catalog"
        self.auth_url = f"{self.base_url}{_auth_ext}"
        self.auth2_url = f"{self.base_url}auth/api/V2/token"

        self.runtime = os.environ.get("RUNTIME", "docker")
        self.max_tasks = int(os.environ.get("JR_MAX_TASKS", "10"))
        self.token = _get_token()
        self.admin_token = _get_admin_token()
        if _DEBUG in os.environ and os.environ[_DEBUG].lower() == "true":
            self.debug = True
        if job_id:
            self.job_id = job_id
        self.hostname = gethostname()
