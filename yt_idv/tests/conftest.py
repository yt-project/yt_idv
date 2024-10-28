import os


def pytest_configure(config):
    # this will get run before all tests, before collection and
    # any opengl imports that happen within test files.
    os.environ["PYOPENGL_PLATFORM"] = "osmesa"
