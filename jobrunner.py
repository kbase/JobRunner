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
            with open("token") as f:
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
    admin_token = os.environ.pop("KB_ADMIN_AUTH_TOKEN")
    if _ADMIN_TOKEN_ENV in os.environ:
        print("Failed to sanitize environment")
    return admin_token


def main():
    # Input job id and njs_service URL
    if len(sys.argv) == 3:
        job_id = sys.argv[1]
        njs_url = sys.argv[2]
    else:
        print("Incorrect usage")
        sys.exit(1)
    config = {}
    config["workdir"] = os.environ.get("WORKDIR", "/tmp/")
    config["catalog-service-url"] = njs_url.replace("njs_wrapper", "catalog")
    token = _get_token()
    at = _get_admin_token()

    try:
        jr = JobRunner(config, njs_url, job_id, token, at)
        jr.run()
    except Exception as e:
        print("An unhandled error was encountered")
        print(e)
        sys.exit(2)


if __name__ == "__main__":
    main()
