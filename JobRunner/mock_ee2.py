"""
This is a Mock of the EE2 API.  This used when running the callback
server in standalone mode for SDK development.

It implements just the methods needed to support running the callback server.

"""

import sys


class Mock_EE2(object):
    def __init__(self):
        pass

    def add_job_logs(self, params, lines):
        for line in lines:
            if line['is_error'] == 1:
                sys.stderr.write(line['line']+'\n')
            else:
                sys.stdout.write(line['line']+'\n')

    def get_job_params(self, params):
        return None

    def list_config(self, params):
        return None

    def check_job_canceled(self, params):
        return {'finished': False}
