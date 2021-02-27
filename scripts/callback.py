#!/usr/bin/env python

import sys
import os
from JobRunner.JobRunner import JobRunner

_TOKEN_ENV = "KB_AUTH_TOKEN"
_ADMIN_TOKEN_ENV = "KB_ADMIN_AUTH_TOKEN"


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
        return None
    admin_token = os.environ.pop(_ADMIN_TOKEN_ENV)
    if _ADMIN_TOKEN_ENV in os.environ:
        print("Failed to sanitize environment")
    return admin_token


def main():
    # Input job id and njs_service URL
    if len(sys.argv) == 2:
        catalog_url = sys.argv[1]
    else:
        print("Incorrect usage")
        sys.exit(1)
    config = {}
    config['workdir'] = os.environ.get("JOB_DIR", '/tmp/')
    if not os.path.exists(config['workdir']):
        os.makedirs(config['workdir'])
    config['catalog-service-url'] = catalog_url
    auth_ext = 'auth/api/legacy/KBase/Sessions/Login'
    config['auth-service-url'] = catalog_url.replace('catalog', auth_ext)
    if 'USE_SHIFTER' in os.environ:
        config['runtime'] = 'shifter'

    if 'JR_MAX_TASKS' in os.environ:
        config['max_tasks'] = int(os.environ['JR_MAX_TASKS'])

    token = _get_token()
    at = _get_admin_token()
    if not os.path.exists(config['workdir']):
        os.makedirs(config['workdir'])

    try:
        jr = JobRunner(config, None, 'test', token, at, port=9999)
        jr.callback()
    except Exception as e:
        print("An unhandled error was encountered")
        print(e)
        raise e

if __name__ == '__main__':
    main()
