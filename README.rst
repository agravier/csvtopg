=======
csvtopg
=======


Fast utility to transform and load a CSV file in a PostgreSQL table


Description
===========

A longer description of your project goes here...

Architecture
============

At the highest level, 3 components interact to create the CLI application:

- the CLI module (``csvtopg.cli``) parses the command-line options and/or
  configuration file and creates a configuration object,
- the Config object (``csvtopg.configuration.Config``) created by the CLI module
  stores the configuration and verifies its consistency,
- the Application class (``csvtopg.application.CSVToPg``) is instantiated by the
  CLI module and configured with the Config object.

Creating the configuration object and application object independently from the
the command-line interface logic enforces the separation of concerns and eases
testing. In particular, the functional testing and performance testing of the
core application is more easily done within pytest without having to capture
the standard input and output, and independently from the particularities of
any UI.

Setting up a local Postgres instance
====================================

This is useful to local development and trying things out in general::

    docker run --name csvtopg-test-postgres \
        -v csvtopg-test-data:/var/lib/postgresql/data \
        -p 5432:5432 \
        -e POSTGRES_USER=csvtopg \
        -e POSTGRES_PASSWORD='fq5WYLL!' \
        -e POSTGRES_DB=csvtopg \
        -d postgres:latest

Don't reuse these credentials for any other purpose.

Testing
=======

The test runner is ``pytest``. The tool used to automate running various types
of tests under different environments is ``tox``.

We use ``tox`` to run all tests in different environments (a "text matrix").
For this project, we use ``tox`` to ensure that tests pass in Python 3.7 and
3.8, that the documentation is correctly generated, and to report test
coverage. These correspond to environments declared at the top of tox.ini as
``py37``, ``py38``, clean
``check``
``docs``
``report`` in the
``envlist``.

We also use the ``tox-docker`` plugin to make a real Postgres database
available as fixture for performance tests.

Tox will find pyenv-managed Python implementations and versions on its own.

Install tox the global python 3 environment. It may be installed using your
package manager or with pip::

    pip3 install tox


To run the all tests, ensure that you are not within a virtualenv and run::

    tox

tox tox-docker

Refreshing the pinned dependencies
==================================

This should result in an updated requirements.txt::

    pyenv virtualenv 3.7.4 csvtopg-clean &&
    pyenv activate csvtopg-clean &&
    pip install -r requirements-base.txt &&
    pip freeze > requirements.txt &&
    pyenv deactivate &&
    pyenv uninstall -f csvtopg-clean

Auto-ordering imports
=====================

To reorder import in all source files::

    isort --recursive src tests

Credits
=======

- The initial project structure created using `PyScaffold
  <https://pyscaffold.readthedocs.io>`_ 3.2.2.
