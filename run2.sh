podman run --name cb2 -d \
   -e KB_* \
   -e CALLBACK_PORT=9999 \
   -e JOB_DIR \
   -e IN_CONTAINER=1 \
   -v $JOB_DIR:$JOB_DIR \
   -p 9999:9999 \
   -v /var/run/user/16907/podman/podman.sock:/run/docker.sock \
   kbase/callback

