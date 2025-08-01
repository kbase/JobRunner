from contextlib import closing
import json
import os
import requests
import socket

from JobRunner.config import Config
from JobRunner.JobRunner import JobRunner


class Callback():
    def __init__(
        self,
        *,
        ip: str = None,
        app_name: str = None,
        allow_set_provenance: bool = None
    ):
        workdir = os.environ.get("JOB_DIR", '/tmp/')
        self.conf = Config(job_id="callback", workdir=workdir, use_ee2=False)
        self.ip = ip or os.environ.get('CALLBACK_IP') or get_ip()
        self.port = os.environ.get('CALLBACK_PORT')
        self._allow_set_provenance = allow_set_provenance
        self._app_name = app_name
        self.callback_url = None

    def load_prov(self, job_params_file):
        job_params = json.load(open(job_params_file))
        for kn in ['method', 'service_ver', 'params']:
            if kn not in job_params:
                raise ValueError(f"Provenance file is missing {kn}")
        params = job_params['params']
        if not isinstance(params, list):
            raise ValueError("params in Provenance file isn't a list")
        return job_params

    def start_callback(self):
        if not self.port:
            self.port = find_free_port()
        self.callback_url = f"http://{self.ip}:{self.port}"
        os.environ["SDK_CALLBACK_URL"] = self.callback_url
        if self._allow_set_provenance is not None:
            # if running in container mode, don't force an env var
            os.environ["CALLBACK_ALLOW_SET_PROVENANCE"] = (
                "true" if self._allow_set_provenance else "false"
            )
        os.environ['CALLBACK_IP'] = self.ip
        job_params = None
        job_params_file = os.environ.get('PROV_FILE')

        if job_params_file:
            job_params = self.load_prov(job_params_file)

        try:
            self.jr = JobRunner(self.conf, port=self.port)
            self.jr.callback(job_params=job_params, app_name=self._app_name)
        except Exception as e:
            print("An unhandled error was encountered")
            print(e)
            raise e

    def stop(self):
        self.jr.stop()

    def wait_for_stop(self):
        self.jr.wait_for_stop()

def get_ip():
    ip = requests.get('https://ipv4.jsonip.com').json()['ip']
    return ip


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def main():
    cb = Callback()
    cb.start_callback()
    cb.wait_for_stop()  # block forever


if __name__ == '__main__':
    main()
