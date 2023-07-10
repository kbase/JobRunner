#!/usr/bin/env python

import sys
import os
from JobRunner.config import Config
from JobRunner.JobRunner import JobRunner


def main():
    # Input job id and njs_service URL
    if len(sys.argv) == 2:
        catalog_url = sys.argv[1]
    else:
        print("Incorrect usage")
        sys.exit(1)
    workdir = os.environ.get("JOB_DIR", '/tmp/')
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    config = Config(workdir=workdir, job_id="test", use_ee2=False)

    try:
        jr = JobRunner(config, port=9999)
        jr.callback()
    except Exception as e:
        print("An unhandled error was encountered")
        print(e)
        raise e

if __name__ == '__main__':
    main()
