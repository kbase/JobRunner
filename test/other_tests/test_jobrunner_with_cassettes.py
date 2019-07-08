# -*- coding: utf-8 -*-
import logging

import vcr
from dotenv import load_dotenv
from job import j1

from clients.NarrativeJobServiceClient import NarrativeJobService
from clients.authclient import KBaseAuth

logging.basicConfig(level=logging.INFO)

load_dotenv("test.env")
load_dotenv("test/other_tests/test.env")
import os
import unittest

from JobRunner.JobRunner import JobRunner


class JobRunnerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = os.environ.get('KB_AUTH_TOKEN', None)
        cls.admin_token = os.environ.get('KB_ADMIN_AUTH_TOKEN', None)
        cls.job_id = os.environ.get('JOB_ID', None)
        endpoint = os.environ.get('ENDPOINT', None)

        cls.config = {
            'catalog-service-url': endpoint + '/catalog',
            'auth-service-url': endpoint + '/auth/api/legacy/KBase/Sessions/Login',
            'auth2-url': endpoint + '/auth/api/V2/token',
            'workdir': '/tmp/jr',
            'ee2': endpoint + "/ee2",
            'njs': endpoint + "/njs_wrapper"
        }

        cls.config['token'] = cls.token

    @unittest.skip(" skipping")
    def test_vcr(self):
        njs = NarrativeJobService(url=self.config['njs'])
        with vcr.use_cassette('cassettes/version.yaml'):
            assert (njs.ver() == '0.2.11')

    @unittest.skip(" skipping")
    def test_getJobParams(self):
        njs = NarrativeJobService(url=self.config['njs'], token=self.config['token'])
        with vcr.use_cassette('cassettes/get_job_params.yaml'):
            params = njs.get_job_params(job_id=self.job_id)
            assert (params == j1.job_params)

    @unittest.skip(" skipping")
    def test_auth(self):
        auth = KBaseAuth(auth_url=self.config.get('auth-service-url'))

    @unittest.skip(" skipping")
    def test_completed_job(self):
        jr = JobRunner(self.config, self.config['njs'], self.job_id, self.token,
                       self.admin_token)

        output = jr.run()
        error = "Job already run or canceled"
        assert (output == {'error': error})

    @unittest.skip(" skipping")
    #CANNOT RERUN COMPLETED JOBS
    def test_completed_job_with_rerun(self):
        jr = JobRunner(self.config, self.config['njs'], self.job_id, self.token,
                       self.admin_token)

        output = jr.run(rerun=True)
        error = "Job already run or canceled"
        assert (output == {'error': error})

    @unittest.skip(" skipping")
    def test_job_canceled(self):
        njs = NarrativeJobService(url=self.config['njs'], token=self.config['token'])
        with vcr.use_cassette('cassettes/check_job_canceled.yaml'):
            canceled = njs.check_job_canceled({'job_id': self.job_id})
            canceled_response = {'job_id': '5c6c8aa9e4b0f2ea4c0bac74', 'finished': 1, 'canceled': 0,
                                 'ujs_url': 'https://ci.kbase.us/services/userandjobstate/'}
            assert (canceled == canceled_response)

    # @attr('offline')
    # @patch('JobRunner.JobRunner.KBaseAuth', autospec=True)
    # @patch('JobRunner.JobRunner.NJS', autospec=True)
    # def test_run(self, mock_njs, mock_auth):
