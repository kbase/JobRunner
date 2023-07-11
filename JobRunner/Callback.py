import os
from multiprocessing import Process
from JobRunner.config import Config
from JobRunner.JobRunner import JobRunner
import socket
from contextlib import closing
import requests
import json


class Callback():
    def __init__(self):
        workdir = os.environ.get("JOB_DIR", '/tmp/')
        if not os.path.exists(workdir):
            os.makedirs(workdir)
        self.conf = Config(workdir=workdir, use_ee2=False)
        self.ip = os.environ.get('CALLBACK_IP', get_ip())
        self.port = os.environ.get('CALLBACK_PORT')
        self.cbs = None
        self.callback_url = None

    def load_prov(self, job_params_file):
        job_params = json.load(open(job_params_file))
        for kn in ['method', 'service_ver', 'params']:
            if kn not in job_params:
                raise ValueError(f"Provenance file is missing {kn}")
        params = job_params['params']
        if not isinstance(params, list):
            raise ValueError("params in Provenenace file isn't a list")
        return job_params

    def run(self):
        os.environ['CALLBACK_IP'] = self.ip
        job_params = None
        job_params_file = os.environ.get('PROV_FILE')

        if job_params_file:
            job_params = self.load_prov(job_params_file)

        try:
            jr = JobRunner(self.conf,
                           port=self.port)
            jr.callback(job_params=job_params)
        except Exception as e:
            print("An unhandled error was encountered")
            print(e)
            raise e

    def start(self):
        if not self.port:
            self.port = find_free_port()
        self.callback_url = f"http://{self.ip}:{self.port}"
        os.environ["SDK_CALLBACK_URL"] = self.callback_url
        self.cbs = Process(target=self.run, daemon=False)
        self.cbs.start()

    def stop(self):
        self.cbs.terminate()


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
    cb.start()


if __name__ == '__main__':
    main()
