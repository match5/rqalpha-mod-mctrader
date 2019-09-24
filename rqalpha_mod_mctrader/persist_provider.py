import datetime
import os

from rqalpha.interface import AbstractPersistProvider
from rqalpha.utils.logger import user_system_log


class McPersistProvider(AbstractPersistProvider):
    def __init__(self, env, mod_config):
        self._env = env
        self._mod_config = mod_config
        self._sid = mod_config.sid
        self._should_run_init = mod_config.should_run_init
        self._should_resume = mod_config.should_resume
        self._persist_dir = mod_config.persist_dir

    def store(self, key, value):
        user_system_log.info('store {key} {value}'.format(key=key, value=value))
        path = os.path.join(self._persist_dir, '%s.dat' % key)
        file = open(path, 'wb')
        file.write(value)
        file.close()

    def load(self, key):
        user_system_log.info('load {key}'.format(key=key))
        path = os.path.join(self._persist_dir, '%s.dat' % key)
        try:
            file = open(path, 'rb')
            value = file.read()
            file.close()
            return value
        except Exception:
            return None
        
    def should_resume(self):
        return self._should_resume

    def should_run_init(self):
        return self._should_run_init
