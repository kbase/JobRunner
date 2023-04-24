import os


def setup():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    bin_dir = "%s/bin/" % (test_dir)
    scripts_dir = "%s/../scripts/" % (test_dir)

    path = os.environ["PATH"]
    os.environ["PATH"] = f"{bin_dir}:{scripts_dir}:{path}"


def teardown():
    if os.path.exists("ssh.out"):
        os.unlink("ssh.out")
