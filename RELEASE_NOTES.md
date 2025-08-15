# Job runner release notes

## 0.1.0

* Fixed a bug that could cause Java client failures when a result key was returned in an HTTP 500
  response.
* Fixed a bug that caused job files to be incorrectly written to the root job directory when
  running in callback server only mode.
* The docker image was updated to use `tini` for launching the executable
* Updated dependency management to `uv`
* Updated test running to `pytest`
* Unused `setup.py` and `travis.yml` files were deleted.
* Added the `set_provenance` API method to the callback server.
* Fixed a number of issues around the callback server hanging forever when an error
  occurred when running a subjob.
* Fixed a bug where an illegal module name would cause the callback server to throw a
  non-specific error.
* Made the callback server attempt to run the `release` version of an SDK app when
  no service version is provided rather than running whatever the catalog service returns.
* Restored the format of the provenance subaction `ver` field to
  `<module version>-<release version>`, e.g. `0.1.3-beta`.
* Fixed a bug where an illegal job ID would cause a non-specific error to be thrown.
* Fixed a bug where a non-existent job ID would be treated as a still running job.
* Added special casing for running jobs at NERSC that rewrites unreachable URLs.

## Earlier release notes

... have been lost.
