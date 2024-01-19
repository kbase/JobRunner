# -*- coding: utf-8 -*-
import os
import unittest
from copy import deepcopy
from queue import Queue
from pathlib import Path

from JobRunner.MethodRunner import MethodRunner
from JobRunner.config import Config
from .mock_data import (
    EE2_JOB_PARAMS,
    CATALOG_GET_MODULE_VERSION,
    CATALOG_GET_SECURE_CONFIG_PARAMS,
)


class MockLogger(object):
    def __init__(self):
        self.lines = []
        self.errors = []

    def log_lines(self, lines):
        self.lines.append(lines)

    def log(self, line):
        self.lines.append(line)

    def error(self, line):
        self.errors.append(line)


class MockRunner(object):
    def __init__(self):
        self.env = None

    def fake_container(self):
        class FakeContainer:
            id = 'Fake'
        return FakeContainer()

    def get_image(self, image):
        return "1234"

    def run(self, job_id, image, env, vols, labels, qs, cgroup):
        self.env = env
        return self.fake_container()


class MethodRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = os.environ.get("KB_AUTH_TOKEN", "")
        # WARNING: don't call any logging metholsds on the context object,
        # it'll result in a NoneType error
        cls.workdir = os.environ.get("JOB_DIR", "/tmp")
        os.makedirs("/tmp/mr/", exist_ok=True)
        cls.job_id = "1234"
        cls.cfg = Config(workdir=cls.workdir, job_id=cls.job_id)
        # cls.cfg = {
        #     "catalog-service-url": "http://localhost",
        #     "token": cls.token,
        #     "admin_token": os.environ.get("KB_ADMIN_AUTH_TOKEN"),
        #     "workdir": cls.workdir
        # }
        cls.logger = MockLogger()
        cls.mr = MethodRunner(cls.cfg, logger=cls.logger)
        base = "https://ci.kbase.us/services/"
        refdata = os.environ.get("KB_REF_DATA", "/kb/data")
        cls.conf = {
            "kbase-endpoint": base,
            "workspace-url": base,
            "shock-url": base,
            "handle-url": base,
            "auth-service-url": base,
            "auth-service-url-v2": base,
            "external-url": base,
            "srv-wiz-url": base,
            "ref_data_base":  refdata,
            "auth-service-url-allow-insecure": True,
            "scratch": "/kb/module/work/tmp",
            "user": "mrbogus",
        }

    def test_run(self):
        mr = MethodRunner(self.cfg, logger=MockLogger())
        module_info = deepcopy(CATALOG_GET_MODULE_VERSION)
        module_info["docker_img_name"] = "mock_app:latest"
        q = Queue()
        action = mr.run(self.conf, module_info, EE2_JOB_PARAMS, self.job_id, fin_q=q)
        self.assertIn("name", action)
        out = q.get(timeout=10)
        self.assertEqual(out[0], "finished")
        self.assertEqual(self.job_id, out[1])

    def test_no_output(self):
        mr = MethodRunner(self.cfg, logger=MockLogger())
        module_info = deepcopy(CATALOG_GET_MODULE_VERSION)
        module_info["docker_img_name"] = "mock_app:latest"
        Path(f"{self.workdir}/workdir/output.json").unlink(missing_ok=True)
        q = Queue()
        params = deepcopy(EE2_JOB_PARAMS)
        params["method"] = "echo_test.noout"
        action = mr.run(self.conf, module_info, params, self.job_id, fin_q=q)
        self.assertIn("name", action)
        out = q.get(timeout=10)
        self.assertEqual(out[0], "finished")
        self.assertEqual(self.job_id, out[1])
        result = mr.get_output(self.job_id, subjob=False)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["name"], "Output not found")

    def test_too_much_output(self):
        mr = MethodRunner(self.cfg, logger=MockLogger())
        module_info = deepcopy(CATALOG_GET_MODULE_VERSION)
        module_info["docker_img_name"] = "mock_app:latest"
        Path(f"{self.workdir}/workdir/output.json").unlink(missing_ok=True)
        q = Queue()
        params = deepcopy(EE2_JOB_PARAMS)
        params["method"] = "echo_test.bogus"
        action = mr.run(self.conf, module_info, params, self.job_id, fin_q=q)
        self.assertIn("name", action)
        out = q.get(timeout=10)
        self.assertEqual(out[0], "finished")
        self.assertEqual(self.job_id, out[1])
        result = mr.get_output(self.job_id, subjob=False, max_size=10)
        self.assertIn("error", result)
        err = "Too much output from a method"
        self.assertEqual(result["error"]["name"], err)

    def test_secure_params(self):
        mr = MethodRunner(self.cfg, logger=MockLogger())
        module_info = deepcopy(CATALOG_GET_MODULE_VERSION)
        module_info["docker_img_name"] = "mock_app:latest"
        module_info["secure_config_params"] = CATALOG_GET_SECURE_CONFIG_PARAMS
        Path(f"{self.workdir}/workdir/output.json").unlink(missing_ok=True)
        q = Queue()
        params = deepcopy(EE2_JOB_PARAMS)
        params["method"] = "echo_test.bogus"
        mockrunner = MockRunner()
        mr.runner = mockrunner
        mr.run(self.conf, module_info, params, self.job_id, fin_q=q)
        self.assertIn("KBASE_SECURE_CONFIG_PARAM_param1", mockrunner.env)

    def test_bad_method(self):
        mr = MethodRunner(self.cfg, logger=MockLogger())
        module_info = deepcopy(CATALOG_GET_MODULE_VERSION)
        module_info["docker_img_name"] = "mock_app:latest"
        Path(f"{self.workdir}/workdir/output.json").unlink(missing_ok=True)
        q = Queue()
        params = deepcopy(EE2_JOB_PARAMS)
        params["method"] = "echo_test.badmethod"
        action = mr.run(self.conf, module_info, params, self.job_id, fin_q=q)
        self.assertIn("name", action)
        out = q.get(timeout=10)
        self.assertEqual(out[0], "finished")
        self.assertEqual(self.job_id, out[1])
        result = mr.get_output(self.job_id, subjob=False)
        self.assertIn("error", result)
        self.assertEqual(result["error"]["name"], "Method not found")

    def test_bad_runtime(self):
        cfg = deepcopy(self.cfg)
        cfg.runtime = "bogus"
        with self.assertRaises(OSError):
            MethodRunner(cfg, logger=MockLogger())
