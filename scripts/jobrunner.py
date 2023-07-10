#!/usr/bin/env python
# import sentry_sdk
import logging
import os
import sys
import time
from typing import Dict

from JobRunner.config import Config
from JobRunner.JobRunner import JobRunner
from JobRunner.exceptions import CantRestartJob


def get_jr_logger():
    logger = logging.getLogger("jr")
    logger.propagate = False
    logger.setLevel(0)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    log_level = os.environ.get("LOGLEVEL", "INFO").upper()
    if log_level:
        ch.setLevel(log_level)
        logger.setLevel(log_level)

    fmt = "%(created)f:%(levelname)s:%(name)s:%(message)s"
    formatter = logging.Formatter(fmt)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


jr_logger = get_jr_logger()


def _terminate_job_in_ee2(jr: JobRunner, params: Dict):
    finished_job_in_ee2 = False
    attempts = 5

    while not finished_job_in_ee2:
        if attempts == 0:
            break
        try:
            jr.ee2.finish_job(params=params)
            finished_job_in_ee2 = True
        except Exception:
            try:
                jr.ee2.cancel_job(params=params)
                finished_job_in_ee2 = True
            except Exception:
                pass
        attempts -= 1
        if not finished_job_in_ee2:
            time.sleep(30)


def terminate_job(jr: JobRunner, debug=False):
    """
    Unexpected Job Error, so attempt to finish the job, and if that fails, attempt to cancel the job
    """
    params = {
        "job_id": jr.job_id,
        "error_message": "Unexpected Job Error",
        "error_code": 2,
        "terminated_code": 2,
    }

    _terminate_job_in_ee2(jr=jr, params=params)

    # Attempt to clean up Docker and Special Runner Containers
    # Kill Callback Server
    try:
        jr.mr.cleanup_all(debug=debug)
    except Exception as e:
        jr_logger.info(e)

    try:
        jr.cbs.kill()
    except Exception as e2:
        jr_logger.info(e2)

    jr.logger.error(
        f"An unhandled exception resulted in a premature exit of the app. Job id is {jr.job_id}"
    )


def main():
    # Input job id and njs_service URL
    if len(sys.argv) == 3:
        job_id = sys.argv[1]
        ee2_url = sys.argv[2]
    else:
        jr_logger.error("Incorrect usage")
        sys.exit(1)
    ee2_suffix = ee2_url.split("/")[-1]
    base_url = ee2_url.rstrip(ee2_suffix)

    config = Config(workdir=os.getcwd(), job_id=job_id, base_url=base_url)
    if not os.path.exists(config.workdir):
        os.makedirs(config.workdir)
        jr_logger.info(f"Creating work directory at {config.workdir}")

    jr = None
    try:
        jr_logger.info("About to create job runner")
        jr = JobRunner(config)
    except Exception as e:
        jr_logger.error(
            f"An unhandled error was encountered setting up job runner {e}",
            exc_info=True,
        )

        if jr:
            terminate_job(jr, debug=config.debug)
        sys.exit(3)

    try:
        jr_logger.info("About to run job with job runner")
        if config.debug:
            jr.logger.log(
                line="Debug mode enabled. Containers will not be deleted after job run."
            )
        jr.run()
    except CantRestartJob:
        # Exit, but don't mark the job as failed
        sys.exit(1)
    except Exception as e:
        jr_logger.error(f"Error: An unhandled error was encountered {e}", exc_info=True)
        jr.logger.error(line=f"{e}")
        terminate_job(jr, debug=config.debug)
        sys.exit(4)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        sys.exit(e)
