# JobRunner

The job runner is started by the batch/resource manager system and is the component that actually executes the SDK module.  It also provides the callback handler and pushes logs to the execution engine logging system.


## Debug Mode

A debug mode can be enabled by setting the environment variable "JOBRUNNER_DEBUG_MODE" to "TRUE".
If the job runner is being used in a condor job, then this would need to be set by the runner script.
If the job runner is being used just for the callback server, then this can be set before launching
the callback server.  If using the Docker version, then this could be set using the "-e" flag.

When in debug mode, the logging level will be increased and some of the container cleanup functions
will be disabled.  This makes it possible to analyze the logs and other information for the containers.
