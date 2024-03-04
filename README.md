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


## Live editing
* The JobRunner is deployed in ee2 in the /condor_shared directory
* You can download files from github using this script https://github.com/kbase/execution_engine2/blob/main/scripts/download_runner.sh
* You can edit files in place without going through the entire development cycle and without pushing to github. For example, if you want to edit the DockerRunner.py you can extract it like so
```
tar -zxvf JobRunner.tgz JobRunner/JobRunner/DockerRunner.py
```
* Then you can edit it, and place it back into the tgz file
```
vi JobRunner/JobRunner/DockerRunner.py
tar -rvf JobRunner.tar JobRunner/JobRunner/DockerRunner.py
gzip -c JobRunner.tar > JobRunner.tgz
```
