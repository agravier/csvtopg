import logging
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List

import dacite

log = logging.getLogger(__name__)


class ConfigurationError(Exception):
    pass


@dataclass
class Config:
    conn_uri: str
    file_path: str
    use_uvloop: Optional[bool]
    log_level: str

    @property
    def configuration_issues(self) -> List[str]:
        issues = []
        if self.use_uvloop and not check_uvloop():
            issues.append(
                'Could not import uvloop. Try installing it or removing the '
                'use_uvloop configuration flag.')
        if not self.conn_uri:
            issues.append('Missing database connection string.')
        if not self.file_path:
            issues.append('Missing input CSV file path.')
        if self.log_level is not None and self.log_level not in {
                'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'}:
            issues.append(f'Unknown log level: "{self.log_level}".')
        return issues

    @classmethod
    def from_dict(cls, conf_dict: Dict) -> 'Config':
        """Create a Config instance from the specification in a dictionary. All
        members must be present in the dictionary. No implicit consistency
        verification is performed; checking config.configuration_issues remains
        the caller's responsibility.

        :param conf_dict configuration data in a Dict-like object
        :return: instantiated Config object
        """
        try:
            conf: cls = dacite.from_dict(data_class=cls, data=conf_dict,
                                         config=dacite.Config(strict=True))
            return conf
        except (dacite.exceptions.MissingValueError, KeyError) as e:
            missing = e.args[0] if isinstance(e, KeyError) else e.field_path
            message = f'Missing configuration key: {missing}'
            raise ConfigurationError(message) from e
        except dacite.UnexpectedDataError as e:
            message = f'Unexpected configuration keys: {e.keys}'
            raise ConfigurationError(message) from e

    def to_dict(self) -> Dict:
        return asdict(self)


def check_uvloop():
    try:
        import uvloop
        return True
    except ImportError:
        return False