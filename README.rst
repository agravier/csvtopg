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
core application is more easily done within pytest without having to capture the
standard input and output, and independently from the particularities of any UI.

Credits
=======

- The initial project structure created using `PyScaffold
  <https://pyscaffold.readthedocs.io>`_ 3.2.2.
