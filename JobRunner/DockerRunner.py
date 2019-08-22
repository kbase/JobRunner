import atexit
from threading import Thread
from time import sleep as _sleep
from time import time as _time
from typing import List

import docker
from docker.models.containers import Container


class DockerRunner:
    """
    This class provides the container interface for Docker.

    """

    def _cleanup_docker_containers(self):
        """
        At exit, attempt to clean up all docker containers.
        Suppress errors in case they don't exist
        """
        for container in self.containers:
            self.remove(container)

    def __init__(self, logger=None):
        """
        Inputs: config dictionary, Job ID, and optional logger
        """
        self.docker = docker.from_env()
        self.logger = logger
        self.containers = []  # type: List[Container]
        self.threads = []  # type: List[Thread]
        self.log_interval = 1
        atexit.register(self._cleanup_docker_containers)

    def _sort_lines_by_time(self, sout, serr):
        """
        This is an internal function to sort and interlace output for NJS.
        This is not fully implemented yet and sould be rethought.
        """
        lines_by_time = dict()
        if len(sout) > 0:
            ierr = 0
            for line in sout.decode("utf-8").split('\n'):
                if len(line) > 0:
                    (ts, txt) = line.split(maxsplit=1)
                    if ts not in lines_by_time:
                        lines_by_time[ts] = []
                    lines_by_time[ts].append({'line': txt, 'is_error': ierr})
        if len(serr) > 0:
            ierr = 1
            for line in serr.decode("utf-8").split('\n'):
                if len(line) > 0:
                    (ts, txt) = line.split(maxsplit=1)
                    if ts not in lines_by_time:
                        lines_by_time[ts] = []
                    lines_by_time[ts].append({'line': txt, 'is_error': ierr})
        nlines = []
        for ts in sorted(lines_by_time.keys()):
            nlines.extend(lines_by_time[ts])
        return nlines

    def _shepherd(self, c, job_id, queues):
        last = 1
        try:
            dolast = False
            while True:
                now = int(_time())
                sout = c.logs(stdout=True, stderr=False, since=last, until=now,
                              timestamps=True)
                serr = c.logs(stdout=False, stderr=True, since=last, until=now,
                              timestamps=True)
                lines = self._sort_lines_by_time(sout, serr)
                if self.logger is not None:
                    self.logger.log_lines(lines)
                last = now
                if dolast:
                    break
                _sleep(self.log_interval)
                try:
                    c.reload()
                    if c.status not in ["created", "running"]:
                        dolast = True
                except Exception:
                    dolast = True
            try:
                c.remove()
            except Exception:
                # Maybe something already cleaned it up.  Move on.
                pass
            self.containers.remove(c)
            for q in queues:
                q.put(['finished', job_id, None])
        except Exception as e:
            if self.logger is not None:
                self.logger.error("Unexpected failure")
            else:
                print("Exception in docker logging for %s" % (c.id))
                raise (e)

    def get_image(self, image):
        """
        Retrieve an image by ID, and pull it if we don't already have it locally on the current
        worker node.
        :param image: The image name to pull from from dockerhub
        :return: ID of the pulled image
        :param image:
        :return:
        """

        # Pull the image from the hub if we don't have it
        pulled = False
        for im in self.docker.images.list():
            if image in im.tags:
                image_id = im.id
                pulled = True
                break

        if not pulled:
            self.logger.log("Pulling image {}".format(image))
            image_id = self.docker.images.pull(image).id
            
        return image_id

    def run(self, job_id, image, env, vols, labels, queues):
        """
        Start a docker container for the main job or subjobs
        and append it to the list of docker containers
        :param job_id: The ExecutionEngine2 Job ID
        :param image: The docker image name
        :param env: Environment for the docker container
        :param vols: Volumes for the docker container
        :param labels: Labels for the docker container
        :param queues: If there is a fin_q then whether or not to run it async
        :return:
        """

        c = self.docker.containers.run(image, 'async',
                                       environment=env,
                                       detach=True,
                                       labels=labels,
                                       volumes=vols)
        self.containers.append(c)
        # Start a thread to monitor output and handle finished containers
        t = Thread(target=self._shepherd, args=[c, job_id, queues])
        self.threads.append(t)
        t.start()
        return c

    def remove(self, c):
        """
        Wrapper to kill and remove a docker container.
        :param c: A reference to docker container object
        :return:
        """
        try:
            c.kill()
        except Exception:
            pass

        try:
            c.remove()
        except Exception:
            pass
