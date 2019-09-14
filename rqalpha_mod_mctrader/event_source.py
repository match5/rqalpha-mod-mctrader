
import gevent

from datetime import datetime, date

from collections import defaultdict

from rqalpha.interface import AbstractEventSource
from rqalpha.events import Event, EVENT

class RealtimeEventSource(AbstractEventSource):

    def __init__(self, env, mod_config):
        self._env = env
        self._mod_config = mod_config
        self.before_trading_fire_date = date(2000, 1, 1)
        self.after_trading_fire_date = date(2000, 1, 1)
        self.settlement_fire_date = date(2000, 1, 1)

    def is_trading_day(self, time):
        return self._env.data_proxy.is_trading_date(time.date())

    def is_trading_time(self, time):
        if 13 <= time.hour <= 15:
            return True
        if time.hour == 9:
            return time.minute >= 30
        if time.hour == 10:
            return True
        if time.hour == 11:
            return time.minute <= 30

    def events(self, start_date, end_date, frequency):
        while True:
            now = datetime.now()
            if self.is_trading_day(now):
                if now.date() > self.before_trading_fire_date and now.hour > 8:
                    self.before_trading_fire_date = now.date()
                    yield Event(EVENT.BEFORE_TRADING, calendar_dt=now, trading_dt=now)
                elif self.is_trading_time(now):
                    yield Event(EVENT.BAR, calendar_dt=now, trading_dt=now)
                elif now.date() > self.after_trading_fire_date and now.hour > 3:
                    self.after_trading_fire_date = now.date()
                    yield Event(EVENT.AFTER_TRADING, calendar_dt=now, trading_dt=now)
                elif now.date() > self.settlement_fire_date and now.hour > 4:
                    yield Event(EVENT.SETTLEMENT, calendar_dt=now, trading_dt=now)
            sec = datetime.now().second
            gevent.sleep(60 - sec if 5 < sec < 55 else 60)
            