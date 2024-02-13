# JobRunner

The job runner is started by the batch/resource manager system and is the component that actually executes the SDK module.  It also provides the callback handler and pushes logs to the execution engine logging system.

## Callback Server Mode

It is possible to run the callback server in a standalone mode.  This can be used to speed up
testing of SDK apps (avoiding a full make test cycle) or to allow some automated operations.
The callback server can be launched in a few ways.

### Native Launch

To launch the callback server natively you can do the following. Note that
the JobRunner is currently testing against Python 3.9.

```
pip install .
# Set the DOCKER_HOST if this doesn't work out of the box
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock

# Set job dir where work output will go
export JOB_DIR=/full/path/to/work/area

# Set tokens and URL
export KB_AUTH_TOKEN="xxxxxxxxx"
export KB_ADMIN_AUTH_TOKEN="xxxxxxxxxxxx"
export KB_BASE_URL=https://ci.kbase.us/services

# Optional
export KB_REF_DATA=/path/to/local/refdata

# Launch the callback server
python -m JobRunner.Callback
```

### Container Launch

The callback server can also be launched via a container.  This may be useful
where the local python and what works with the JobRunner are incompatible.
Note that the JOB_DIR needs to be accessible by docker.  Also you must pass through
the docker socket to the container.  The path to the socket can vary depending on
the container runtime and how the container runtime is configured.

```
export JOB_DIR=/full/path/to/work/area
export KB_AUTH_TOKEN="xxxxxxxxx"
export KB_ADMIN_AUTH_TOKEN="xxxxxxxxxxxx"

docker run --name cb -d \
   -e KB_AUTH_TOKEN \
   -e KB_ADMIN_AUTH_TOKEN \
   -e KB_BASE_URL=https://ci.kbase.us/services \
   -e CALLBACK_PORT=9999 \
   -e JOB_DIR \
   -v $JOB_DIR:$JOB_DIR \
   -v /var/run/docker.sock:/run/docker.sock \
   -p 9999:9999 \
   ghcr.io/kbase/jobrunner:latest-rc

export SDK_CALLBACK_URL=http://localhost:9999
```

## Development and Testing the Job Runner

Here is a quick start guide for running test for the Job Runner code.
See the SDK guide for information about running test of SDK apps.

```
pip install -r requirements.txt -r requirements-dev.txt

# Set the DOCKER_HOST if this doesn't work out of the box
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock

# Be sure to set both tokens and the KB_BASE_URL
export KB_AUTH_TOKEN="xxxxxxxxx"
export KB_ADMIN_AUTH_TOKEN="xxxxxxxxxxxx"
export KB_BASE_URL=https://ci.kbase.us/services
export CALLBACK_IP=127.0.0.1
export CALLBACK_PORT=9999
# Set ref data to an area accessible by Docker
export KB_REF_DATA=/path/to/local/refdata

make mock
make testimage
make test
```

## Debug Mode

A debug mode can be enabled by setting the environment variable "JOBRUNNER_DEBUG_MODE" to "TRUE".
If the job runner is being used in a condor job, then this would need to be set by the runner script.
If the job runner is being used just for the callback server, then this can be set before launching
the callback server.  If using the Docker version, then this could be set using the "-e" flag.

When in debug mode, the logging level will be increased and some of the container cleanup functions
will be disabled.  This makes it possible to analyze the logs and other information for the containers.
