podman run --name cb -d \
   --net host \
   -e KB_* \
   -e CALLBACK_PORT=9999 \
   -e JOB_DIR \
   -v $JOB_DIR:$JOB_DIR \
   -v /var/run/user/16907/podman/podman.sock:/run/docker.sock \
   jr

