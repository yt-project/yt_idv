# Contributing

Contributions are welcome, and they are greatly appreciated! Every little bit
helps, and credit will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at https://github.com/yt-project/yt_idv/issues.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

interactive volume rendering for yt could always use more documentation, whether as part of the
official interactive volume rendering for yt docs, in docstrings, or even on the web in blog posts,
articles, and such.

### Submit Feedback

The best way to send feedback is to file an issue at https://github.com/yt-project/yt_idv/issues.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

## Get Started!

Ready to contribute? Here's how to set up `yt_idv` for local development.

### Development environment setup

To set up your local development environment:

1. Fork the `yt_idv` repo on GitHub.

2. Clone your fork locally

   ```
   $ git clone git@github.com:your_name_here/yt_idv.git
   ```

3. Install your local copy into a virtualenv. Assuming you have virtualenvwrapper installed, this is how you set up your fork for local development

   ```
   $ mkvirtualenv yt_idv
   $ cd yt_idv/
   $ python -m pip install -e .[dev]
   ```

4. (optional) Initialize pre-commit if you want to catch linting errors throughout development. When you submit a pull request, the pre-commit.ci bot will run a number of checks so it can be easier to catch errors along the way.

   ```
   $ pre-commit install
   ```

### Developing

Once your environment is setup, you are ready to make changes!

1. Create a branch for local development

   ```
   $ git checkout -b name-of-your-bugfix-or-feature
   ```

   Now you can make your changes locally.

2. When you're done making changes,

3. Commit your changes and push your branch to GitHub

   ```
   $ git add .
   $ git commit -m "Your detailed description of your changes."
   $ git push origin name-of-your-bugfix-or-feature
   ```

4. Submit a pull request through the GitHub website.

### Running and writing tests

The test suite is run with `pytest` using headless `osmesa` tests, so you need
an environment with `osmesa` available. To run the tests:

    ```
    $ pytest yt_idv
    ```

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in README.rst.
3. The pull request should work for Python 3.5, 3.6, 3.7 and 3.8, and for PyPy. Check
   https://travis-ci.com/yt-project/yt_idv/pull_requests
   and make sure that the tests pass for all supported Python versions.

## Tips

To run a subset of tests

```
$ pytest tests.test_yt_idv
```

## Releasing

To create a release, follow these steps:

1. [prep for release](#prep-for-release)
2. [create and push a new version tag](#create-and-push-a-new-version-tag)
3. [cleanup from release](#cleanup-from-release)

### prep for release

First make sure the version specified in `setup.cfg` and `yt_idv/__init__.py`
match the upcoming release and that there is an entry in `HISTORY.md`. Push up
any updates to the version or history and then move on to the next step.

Next, double check that your local main branch matches https://github.com/yt-project/yt_idv/:

```shell
git fetch --all
git checkout main
git rebase upstream/main
```

### create and push a new version tag

Now create and push a new version tag. For example, for version 1.2.3:

```shell
git tag v1.2.3
git push upstream v1.2.3
```

When a new tag is pushed, a GitHub action is triggered that will:

1. build a new source release and push up to PyPI
2. create a draft release on GitHub with auto-generated release notes

After the action runs, go open up the draft release (which should be visible on the
[releases page](https://github.com/yt-project/yt_idv/releases)), edit the notes to
match the release notes in `HISTORY.md` for this version.

### cleanup from release

While not strictly necessary, it helps to bump the active development version
in `setup.cfg` and `yt_idv/__init__.py` and add a blank entry in `HISTORY.md`.
