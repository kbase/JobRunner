# JobRunner

The job runner is started by the batch/resource manager system and is the component that actually executes the SDK module.  It also provides the callback handler and pushes logs to the execution engine logging system.

## Updating dependencies

After updating the project's dependencies with `uv`, be sure to run

```
make updatereqs
```

to regenerate the `requirements.txt` file. Other repositories are dependent on this file
to properly integrate the job runner.

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
# Note the location of the socket file may vary based on
# your container runtime installation.
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock

# Set job dir where work output will go
# Note you may need to set the permissions to world writeable
# depending on your container runtime installation.
export JOB_DIR=/full/path/to/work/area

# Set tokens and URL
export KB_AUTH_TOKEN="xxxxxxxxx"
export KB_ADMIN_AUTH_TOKEN="xxxxxxxxxxxx"
export KB_BASE_URL=https://ci.kbase.us/services/

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
   -e KB_BASE_URL=https://ci.kbase.us/services/ \
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

Requirements:
* Java 8+
* The
  [cromwell-44.jar](https://github.com/broadinstitute/cromwell/releases/download/44/cromwell-44.jar)
  must exist in `$HOME`
* `cromwell.conf` must exist in `$HOME`. It may be an empty file.
* The env vars below must be set.
    * Required:
        * The 2 auth token env vars (although they don't have to be a valid token
        * KB_BASE_URL must start with http but otherwise can be anything
    * Required for MacOS:
        * JOB_DIR, since otherwise the tests attempt to mount /tmp
    * Optional:
        * Everything else, although you may need to set DOCKER_HOST depending on your
          system setup.

```
uv sync --dev  # only the first time or when uv.lock changes

# Set the DOCKER_HOST if this doesn't work out of the box
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock

# Be sure to set both tokens and the KB_BASE_URL. Other variables are optional.
export KB_AUTH_TOKEN="xxxxxxxxx"
export KB_ADMIN_AUTH_TOKEN="xxxxxxxxxxxx"
export KB_BASE_URL=https://ci.kbase.us/services/
# Set ref data and job dir to areas accessible by Docker
export KB_REF_DATA=/path/to/local/refdata
export JOB_DIR=/path/to/job/dir

make mock
make testimage
make test
```

There is a scripot at [run_tests.sh](./run_tests.sh) that can help make this process simpler.

## Using the CallBack Server 
* Install a kb-sdk module such as DataFileUtil using `kb-sdk install` or copying from an existing apps `lib/installed_clients` directory
* Point that client to the callback server's IP and PORT
* The follow example points the DataFileUtil client to the callback server to launch a DataFileUtil container and download a specific object 

```
from DataFileUtilClient import DataFileUtil
callback_url = 'http://127.0.0.1:9999'
token='<redacted>'
dfu = DataFileUtil(callback_url, service_ver='dev', token=token)

ref = '68940/2/1'
data = dfu.get_objects({
            'object_refs': [ref]
        })['data'][0]
print(data)
```

## Debug Mode

A debug mode can be enabled by setting the environment variable "JOBRUNNER_DEBUG_MODE" to "TRUE".
If the job runner is being used in a condor job, then this would need to be set by the runner script.
If the job runner is being used just for the callback server, then this can be set before launching
the callback server.  If using the Docker version, then this could be set using the "-e" flag.

When in debug mode, the logging level will be increased and some of the container cleanup functions
will be disabled.  This makes it possible to analyze the logs and other information for the containers.
