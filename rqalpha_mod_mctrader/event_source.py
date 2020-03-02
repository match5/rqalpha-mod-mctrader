import time

from datetime import datetime, date

from collections import defaultdict

from rqalpha.interface import AbstractEventSource
from rqalpha.events import Event, EVENT


class McTraderEventSource(AbstractEventSource):


    def __init__(self, env, mod_config):
        self._env = env
        self._mod_config = mod_config
        self.before_trading_fire_date = date(2000, 1, 1)
        self.after_trading_fire_date = date(2000, 1, 1)


    def is_trading_day(self, time):
        return self._env.data_proxy.is_trading_date(time.date())


    def is_trading_time(self, time):
        if time.hour == 9 and time.minute > 30:
            return True
        elif time.hour == 10:
            return True
        elif time.hour == 11 and time.minute < 30:
            return True
        elif 13 <= time.hour < 15:
            return True
        return False


    def events(self, start_date, end_date, frequency):
        while True:
            now = datetime.now()
            if self.is_trading_day(now):
                begin = now
                if now.date() > self.before_trading_fire_date and 8 <= now.hour < 15:
                    self.before_trading_fire_date = now.date()
                    yield Event(EVENT.BEFORE_TRADING, calendar_dt=now, trading_dt=now)
                    now = datetime.now()
                if self.is_trading_time(now):
                    yield Event(EVENT.BAR, calendar_dt=now, trading_dt=now)
                    now = datetime.now()
                elif self.after_trading_fire_date < now.date() == self.before_trading_fire_date and now.hour >= 15:
                    self.after_trading_fire_date = now.date()
                    yield Event(EVENT.AFTER_TRADING, calendar_dt=now, trading_dt=now)
                    if now.date() >= end_date:
                        return
                    now = datetime.now()
                time.sleep(60 - (now - begin).total_seconds())
            else:
                time.sleep(1800)

