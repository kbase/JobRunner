import unittest
from unittest.mock import patch

from JobRunner.Callback import Callback


def setup_mock_environ(mock_environ_get,
                       callback_ip="127.0.0.1",
                       callback_port="8080"):
    # Helper function to mock environment variables
    mock_environ_get.side_effect = lambda x, default=None: {
        "JOB_DIR": "/tmp/",
        "CALLBACK_IP": callback_ip,
        "CALLBACK_PORT": callback_port,
    }.get(x, default)


def assert_callback_attributes(callback,
                               job_id="callback",
                               workdir="/tmp/",
                               ip="127.0.0.1",
                               port="8080",
                               cbs=None,
                               callback_url=None):
    # Helper function to assert Callback attributes
    assert callback.conf.job_id == job_id
    assert callback.conf.workdir == workdir
    assert callback.ip == ip
    assert callback.port == port
    assert callback.cbs == cbs
    assert callback.callback_url == callback_url


class TestCallback(unittest.TestCase):

    @patch('JobRunner.Callback.os.environ.get')
    def test_init_with_environment_variables(self, mock_environ_get):
        # test the __init__ method of the Callback class when the environment variables including CALLBACK_IP are all set

        setup_mock_environ(mock_environ_get)
        callback = Callback()

        assert_callback_attributes(callback)

    @patch('JobRunner.Callback.os.environ.get')
    @patch('JobRunner.Callback.get_ip')
    def test_init_without_callback_ip_environment_variables(self, mock_get_ip, mock_environ_get):
        # test the __init__ method of the Callback class when the CALLBACK_IP environment variable is missing

        setup_mock_environ(mock_environ_get, callback_ip=None)
        mock_get_ip.return_value = "192.168.1.1"

        callback = Callback()
        assert_callback_attributes(callback, ip="192.168.1.1")

    @patch('JobRunner.Callback.os.environ.get')
    @patch('JobRunner.Callback.get_ip')
    def test_init_get_ip_error(self, mock_get_ip, mock_environ_get):
        # test the __init__ method of the Callback class when the get_ip function raises an error but the CALLBACK_IP is set

        setup_mock_environ(mock_environ_get)
        # Mock get_ip function to raise an error
        mock_get_ip.side_effect = RuntimeError("Failed to get IP")

        callback = Callback()
        assert_callback_attributes(callback)