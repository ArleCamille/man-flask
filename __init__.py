import json
import os
from subprocess import run
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session
from typing import Optional
from os import DirEntry
from sys import stderr
from pathlib import Path

import defaults
from db import BaseEntry, ManEntry

DEFAULT_CONFIG_PATH = '/etc/man-flask-conf.json'

def _get_manpaths() -> list[str]:
    proc = run(['manpath'], capture_output=True)
    paths = proc.stdout.decode()
    return list(map(lambda x: x.strip(), paths.split(':')))

class ManFlaskConfig:
    template_path: str = defaults.DEFAULT_TEMPLATE_PATH
    static_path: str   = defaults.DEFAULT_STATIC_PATH

    potential_compressions: list[str] = defaults.DEFAULT_POTENTIAL_COMPRESSIONS

    manpaths: list[str]

    db_path: str = defaults.DEFAULT_DB_PATH
    db_engine: Engine

    def _parse_man_entry(self, path_section: str, entry: DirEntry[str]):
        print(f'Parsing {entry.path}...', file=stderr)
        filename                   = entry.name
        compression: Optional[str] = None
        for c in self.potential_compressions:
            if filename.endswith(f'.{c}'):
                compression = c
                filename = filename[:-len(c)-1]

        manual, section = filename.rsplit('.', 1)
        ManEntry.create_section(self.db_engine, section, manual,
                                path_section=path_section,
                                man_extension=compression)

    def populate_man_entries(self):
        # scan all the directories
        for mandir in self.manpaths:
            with os.scandir(mandir) as dir:
                for entry in dir:
                    if not entry.is_dir() or not entry.name.startswith('man'):
                        # ignore; not a canonical man section
                        continue
                    path_section = entry.name[3:]
                    with os.scandir(entry.path) as subdir:
                        for man_entry in subdir:
                            self._parse_man_entry(path_section, man_entry)

    def _post_init(self, echo_db: bool):
        Path(self.db_path).mkdir(parents=True, exist_ok=True)
        self.manpaths  = _get_manpaths()
        self.db_engine = create_engine(f'sqlite:///{self.db_path}/man.db',
                                       echo=echo_db)
        BaseEntry.metadata.create_all(self.db_engine)

    def __init__(self, path: str = DEFAULT_CONFIG_PATH,
                 *,
                 echo_db: bool = False):
        conf_data = {}
        if not os.path.exists(path):
            # leave defaults as-is
            self._post_init(echo_db)
            return
        with open(path) as conf_file:
            conf_data = json.load(conf_file)
            if not isinstance(conf_data, dict):
                raise TypeError
            self.static_path   = conf_data.get('static_path',
                                               defaults.DEFAULT_STATIC_PATH)
            self.template_path = conf_data.get('template_path',
                                               defaults.DEFAULT_TEMPLATE_PATH)
            self.db_path       = conf_data.get('db_path',
                                               defaults.DEFAULT_DB_PATH)
            self.potential_compressions = \
                conf_data.get('potential_compressions',
                              defaults.DEFAULT_POTENTIAL_COMPRESSIONS)

        self._post_init(echo_db)

__all__ = [
    'ManFlaskConfig',
]

if __name__ == '__main__':
    # test code
    config = ManFlaskConfig(echo_db=False)
    config.populate_man_entries()

    with Session(config.db_engine) as session:
        query = select(ManEntry).order_by(ManEntry.section, ManEntry.manual)
        for entry in session.scalars(query):
            print(f'Section {entry.section} > {entry.manual}')