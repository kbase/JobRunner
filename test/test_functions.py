# -*- coding: utf-8 -*-
import os
import socket
import unittest
from copy import deepcopy
from unittest.mock import patch

from JobRunner.JobRunner import JobRunner
from test.mock_data.mock_data import NJS_JOB_PARAMS


class JobRunnerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = os.environ.get('KB_AUTH_TOKEN', '')
        cls.admin_token = os.environ.get('KB_ADMIN_AUTH_TOKEN', 'bogus')
        cls.cfg = {}
        base = 'https://ci.kbase.us/services/'
        if 'TEST_URL' in os.environ:
            base = "http://%s/services/" % (os.environ['TEST_URL'])
        cls.njs_url = base + 'njs_wrapper'
        cls.jobid = '1234'
        cls.workdir = '/tmp/jr/'
        cls.cfg['token'] = cls.token
        cls.config = {
            'catalog-service-url': base + 'catalog',
            'auth-service-url': base + 'auth/api/legacy/KBase/Sessions/Login',
            'auth2-url': base + 'auth/api/V2/token',
            'workdir': '/tmp/jr'
        }
        if not os.path.exists('/tmp/jr'):
            os.mkdir('/tmp/jr')
        if 'KB_ADMIN_AUTH_TOKEN' not in os.environ:
            os.environ['KB_ADMIN_AUTH_TOKEN'] = 'bogus'

    def _cleanup(self, job):
        d = os.path.join(self.workdir, job)
        if os.path.exists(d):
            for fn in ['config.properties', 'input.json', 'output.json',
                       'token']:
                if os.path.exists(os.path.join(d, fn)):
                    os.unlink(os.path.join(d, fn))
            os.rmdir(d)

    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_config(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)

        config = jr._init_config(self.config, self.jobid, self.njs_url)
        test_config = {'catalog-service-url': 'https://ci.kbase.us/services/catalog',
                       'auth-service-url': 'https://ci.kbase.us/services/auth/api/legacy/KBase/Sessions/Login',
                       'auth2-url': 'https://ci.kbase.us/services/auth/api/V2/token',
                       'workdir': '/tmp/jr', 'hostname': socket.gethostname(),
                       'job_id': self.jobid, 'njs_url': self.njs_url,
                       'token': self.token, 'admin_token': self.admin_token}

        del config['cgroup']

        self.assertEquals(test_config, config)

    @patch('JobRunner.JobRunner.NJS', autospec=True)
    @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    def test_job_ready_to_run(self, mock_njs, mock_auth):
        self._cleanup(self.jobid)
        params = deepcopy(NJS_JOB_PARAMS)
        os.environ['KB_AUTH_TOKEN'] = 'bogus'
        jr = JobRunner(self.config, self.njs_url, self.jobid, self.token,
                       self.admin_token)

        jr.njs.check_job_canceled.return_value = {'finished': False}
        ready_to_run = jr._job_ready_to_run()
        self.assertEquals(ready_to_run, True)

        jr.njs.check_job_canceled.return_value = {'finished': True}
        ready_to_run = jr._job_ready_to_run()
        self.assertEquals(ready_to_run, False)
