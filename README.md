# JobRunner

The job runner is started by the batch/resource manager system and is the component that actually executes the SDK module.  It also provides the callback handler and pushes logs to the execution engine logging system.

# Debugging 
* Log into the ee2 container for the environment you want, e.g. CI
```
cd /condor_shared
cp JobRunner.tgz JobRunner.backup.date.tgz
cd /runner/JobRunner
```
