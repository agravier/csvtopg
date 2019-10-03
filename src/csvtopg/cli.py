"""Entry point defining the CLI of the csvtopg utility. This module does not
contain application logic. The architecture is such that a this CLI module
parses the command-line options and/or configuration file and creates a
configuration object. It then instantiated a CSVToPg object representing the
application logic, passing it the configuration object.
"""

import asyncio
import logging
import os.path
import sys
import traceback
from typing import Dict, Optional, Union

import _io
import click
import toml

from csvtopg import __version__
from csvtopg.application import CSVToPg
from csvtopg.configuration import Config, ConfigurationError, check_uvloop

log = logging.getLogger(__name__)

UVLOOP_AVAILABLE = check_uvloop()

OPTION_DEFAULTS = {
    'use_uvloop': UVLOOP_AVAILABLE,
    'log_level': 'INFO'
}


def setup_logging(loglevel: Union[int, str]):
    """Setup basic logging

    :param loglevel: minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s: %(name)s: %(message)s"
    logging.basicConfig(level=loglevel, stream=sys.stdout,
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")


def load_toml_file(conf_file: _io.TextIOWrapper) -> Dict:
    """Create a dictionary from the configuration specified in the loaded TOML
    configuration file. Note that no Config object is created, just a dict.

    :param conf_file: file data as TextIOWrapper
    :return: hierarchical configuration in a dictionary
    """
    try:
        return toml.load(conf_file)
    finally:
        conf_file.close()


def load_and_check_configuration(
        conf_file: _io.TextIOWrapper, csv_file: Optional[str],
        connection_string: Optional[str], table_name: str,
        use_uvloop: Optional[bool], log_level: Optional[str]) -> Config:
    """Load the configuration file if specified. Then load the ad-hoc options,
    which take precedence over the configuration file. Verify consistency,
    display an error message and exit in case of issue, otherwise return a
    consistent Config object.

    :param conf_file: Contents of the configuration file
    :param connection_string: PostgreSQL connection string in the libpq
        connection URI format
    :param table_name: table where the data will be inserted
    :param csv_file: Path to the CSV file to load
    :param use_uvloop: Flag to decide to use uvloop as event loop
    :param log_level: Minimum log level to be displayed in the console
    :return: Merged and verified configuration object
    """
    args_dict = Config(
        conn_uri=connection_string, input_file=csv_file,
        table_name=table_name, use_uvloop=use_uvloop,
        log_level=log_level).to_dict()
    valid_args_dict = {k: v for k, v in args_dict.items() if v is not None}
    unset_args_dict = {k: v for k, v in args_dict.items() if v is None}
    if conf_file:
        try:
            file_dict = load_toml_file(conf_file)
            file_dict.update(valid_args_dict)
            config = Config.from_dict(file_dict)
        except ConfigurationError as conf_err:
            click.echo(
                message=f'Error processing the configuration: {conf_err}',
                err=True)
            sys.exit(1)
        except Exception as e:
            error_msg = (
                f'Error while loading the configuration: {e}\n' +
                '\n'.join(traceback.format_exception(None, e, e.__traceback__)))
            click.echo(message=error_msg, err=True)
            sys.exit(1)
    else:
        for k, _ in unset_args_dict.items():
            try:
                unset_args_dict[k] = OPTION_DEFAULTS[k]
            except KeyError:
                click.echo(
                    message=f'Missing command-line option: "{k}"', err=True)
                sys.exit(1)
        config = Config.from_dict({**unset_args_dict, **valid_args_dict})
    config.input_file = os.path.expanduser(config.input_file)
    if config.configuration_issues:
        issues = '\n'.join(config.configuration_issues)
        click.echo(message=f'Invalid configuration:\n{issues}', err=True)
        sys.exit(1)
    return config


@click.command()
@click.version_option(
    version=__version__, help='Display the version and exit',
    message='%(version)s')
@click.option(
    '--conf_file', required=False, type=click.File('r'),
    help='Path to configuration file (TOML syntax). All options must be '
         'present. Redundant command-line options take precedence.')
@click.option(
    '--input_file', required=False, type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True,
        resolve_path=False, path_type=str),
    help='Path to the input CSV file')
@click.option(
    '--conn_uri', required=False, type=str,
    help='Connection string to the database, in the following format: '
         '"postgres://user:password@host:port/database?option=value"')
@click.option(
    '--table_name', required=False, type=str,
    help='Database table where the data needs to be written.')
@click.option(
    '--use_uvloop', is_flag=True, required=False,
    hidden=not UVLOOP_AVAILABLE, help='Use uvloop as event loop')
@click.option(
    '--log_level', required=False,
    help='Console logging level: DEBUG, INFO (default), WARNING, etc.')
def cli(conf_file, input_file, conn_uri, table_name, use_uvloop, log_level):
    """Entry point for console_scripts
    """
    config = load_and_check_configuration(
        conf_file, input_file, conn_uri, table_name, use_uvloop, log_level)
    if config.use_uvloop:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    setup_logging(config.log_level)
    log.info("Final configuration: %s", config)
    log.debug("Starting")
    result = CSVToPg(config).run()
    log.info(result)
    if result.errors:
        click.echo("Errors encountered:", file=sys.stderr)
        for e in result.errors:
            click.echo(f"- {e}", file=sys.stderr)
    click.echo(f'Read {result.metrics.num_rows_read} rows, wrote '
               f'{result.metrics.num_rows_written} records in '
               f'{result.metrics.wall_clock_computation_time:.3f} seconds')
    if result.errors:
        exit(2)


if __name__ == "__main__":
    cli()
