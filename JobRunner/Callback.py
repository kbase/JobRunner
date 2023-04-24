import os
from multiprocessing import Process
from JobRunner.JobRunner import JobRunner
import socket
from contextlib import closing
import requests
import logging

_TOKEN_ENV = "KB_AUTH_TOKEN"
_ADMIN_TOKEN_ENV = "KB_ADMIN_AUTH_TOKEN"
_BASE_URL = "KB_BASE_URL"
_DEFAULT_BASE_URL = "https://kbase.us/services/"


class Config():
    def __init__(self):
        self.token = _get_token()
        self.admin_token = _get_admin_token()
        self.base = os.environ.get(_BASE_URL, _DEFAULT_BASE_URL).rstrip("/")
        self.catalog_url = f"{self.base}/catalog"
        self.workdir = os.environ.get("JOB_DIR", '/tmp/')
        logging.info(f"job_dir: {self.workdir}")
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)
        auth_ext = 'auth/api/legacy/KBase/Sessions/Login'
        self.auth_service_url = f"{self.base}/{auth_ext}"
        # Input job id and njs_service URL
        self.runtime = "docker"
        if 'USE_SHIFTER' in os.environ:
            self.runtime = "shifter"
        self.max_tasks = int(os.environ.get('JR_MAX_TASKS', '10'))

    def get_conf(self):
        config = {}
        config['workdir'] = self.workdir
        config['catalog-service-url'] = self.catalog_url
        config['auth-service-url'] = self.auth_service_url
        config['runtime'] = self.runtime
        config['max_tasks'] = self.max_tasks
        return config


class Callback():
    def __init__(self):
        self.conf = Config()
        print("Config")
        self.ip = os.environ.get('CALLBACK_IP', get_ip())
        self.port = None
        self.cbs = None
        self.callback_url = None

    def run(self):
        os.environ['CALLBACK_IP'] = self.ip

        try:
            jr = JobRunner(self.conf.get_conf(),
                           None,
                           'test',
                           self.conf.token,
                           self.conf.admin_token,
                           port=self.port)
            jr.callback()
        except Exception as e:
            print("An unhandled error was encountered")
            print(e)
            raise e

    def start(self):
        self.port = find_free_port()
        self.callback_url = f"http://{self.ip}:{self.port}"
        os.environ["SDK_CALLBACK_URL"] = self.callback_url
        self.cbs = Process(target=self.run, daemon=False)
        self.cbs.start()

    def stop(self):
        self.cbs.terminate()


def _get_token():
    # Get the token from the environment or a file.
    # Set the KB_AUTH_TOKEN if not set.
    if _TOKEN_ENV in os.environ:
        token = os.environ[_TOKEN_ENV]
    else:
        try:
            with open('token') as f:
                token = f.read().rstrip()
            os.environ[_TOKEN_ENV] = token
        except Exception:
            raise OSError("No token found")
    return token


def _get_admin_token():
    if _ADMIN_TOKEN_ENV not in os.environ:
        print("Warning: Missing admin token needed for volume mounts.")
        return None
    admin_token = os.environ.pop(_ADMIN_TOKEN_ENV)
    if _ADMIN_TOKEN_ENV in os.environ:
        raise OSError("Failed to sanitize environment")
    return admin_token


def get_ip():
    ip = requests.get('https://ipv4.jsonip.com').json()['ip']
    return ip


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def main():
    print("Todo")


if __name__ == '__main__':
    main()
