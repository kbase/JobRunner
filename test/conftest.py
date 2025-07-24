import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def setup():
    print("Module setup")
    test_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = "%s/bin/" % (test_dir)
    scripts_dir = "%s/../scripts/" % (test_dir)

    os.environ["PATH"] = "%s:%s:%s" % (bin_dir, scripts_dir, os.environ["PATH"])
    
    yield

    if os.path.exists("ssh.out"):
        os.unlink("ssh.out")
