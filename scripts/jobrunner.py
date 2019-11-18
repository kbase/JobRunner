#!/usr/bin/env python

import logging
import os
import signal
import sys
import time

from JobRunner.JobRunner import JobRunner
from clients.execution_engine2Client import execution_engine2

logging.basicConfig(level=logging.INFO)
_TOKEN_ENV = "KB_AUTH_TOKEN"
_ADMIN_TOKEN_ENV = "KB_ADMIN_AUTH_TOKEN"

jr = None # type:JobRunner
job_id = None
ee2_url = None

class TerminatedCode(Enum):
    """
    Reasons for why the job was cancelled
    """

    terminated_by_user = 0
    terminated_by_admin = 1
    terminated_by_automation = 2


def sigterm_handler(signal, frame):
    # this method defines the handler i.e. what to do
    # when you receive a SIGTERM
    # remove all containers
    logging.info("I got your signal", signal)
    logging.info("I got your frame", frame)
    token = _get_token()
    ee2 = execution_engine2(url=ee2_url, token=token)
    cjp = {'job_id': job_id, 'terminated_code': TerminatedCode.terminated_by_automation.value}
    ee2.cancel_job(cjp)
    time.sleep(1)
    jr._cancel()
    #jr.mr.cleanup_all()

signal.signal(signal.SIGTERM, sigterm_handler)


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
        except:
            print("Failed to get token.")
            sys.exit(2)
    return token


def _get_admin_token():
    if _ADMIN_TOKEN_ENV not in os.environ:
        print("Missing admin token needed for volume mounts.")
        sys.exit(2)
    admin_token = os.environ.pop('KB_ADMIN_AUTH_TOKEN')
    if _ADMIN_TOKEN_ENV in os.environ:
        print("Failed to sanitize environment")
    return admin_token


def main():
    global job_id
    global ee2_url

    # Input job id and njs_service URL
    if len(sys.argv) == 3:
        job_id = sys.argv[1]
        ee2_url = sys.argv[2]
    else:
        print("Incorrect usage")
        sys.exit(1)

    config = dict()
    config['workdir'] = os.getcwd()
    if not os.path.exists(config['workdir']):
        os.makedirs(config['workdir'])
        logging.info(f"Creating work directory at {config['workdir']}")

    config['catalog-service-url'] = ee2_url.replace('ee2', 'catalog')
    auth_ext = 'auth/api/legacy/KBase/Sessions/Login'
    config['auth-service-url'] = ee2_url.replace('ee2', auth_ext)

    #WARNING: Condor job environment may not inherit from system ENV
    if 'USE_SHIFTER' in os.environ:
        config['runtime'] = 'shifter'

    if 'JR_MAX_TASKS' in os.environ:
        config['max_tasks'] = int(os.environ['JR_MAX_TASKS'])

    token = _get_token()
    at = _get_admin_token()

    global jr
    try:
        logging.info("About to create job runner")
        jr = JobRunner(config, ee2_url, job_id, token, at)
        logging.info("About to run job")
        jr.run()
    except Exception as e:
        logging.error("An unhandled error was encountered")
        logging.error(e)
        sys.exit(2)


if __name__ == '__main__':
    main()
