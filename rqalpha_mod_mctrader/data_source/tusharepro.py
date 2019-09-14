# -*- coding: utf-8 -*-
#
# Copyright 2017 Ricequant, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
from datetime import date
from dateutil.relativedelta import relativedelta
from rqalpha.data.base_data_source import BaseDataSource

from rqalpha.utils.datetime_func import convert_dt_to_int

import pandas as pd
import tushare as ts

suffix_map = {
    'SZ': 'XSHE',
    'XSHE': 'SZ',
    'SH': 'XSHG',
    'XSHG': 'SH',
}

freq_map = {
    '1d': 'D',
    '1m': '1min',
    '5m': '5min',
}

adjust_map = {
    'pre' : 'qfq',
    'post' : 'hfq',
}

class TushareProDataSource(BaseDataSource):
    def __init__(self, env, path, apis):
        super(TushareProDataSource, self).__init__(path)
        self.apis = apis
        self._env = env
        self.calendar = None

    def get_api(self):
        api = self.apis.pop(0)
        self.apis.append(api)
        return api

    def code_map(self, code):
        split = code.split(".")
        return split[0] + '.' + suffix_map[split[1]]

    def get_bar(self, instrument, dt, frequency):
        bar_data = ts.pro_bar(
            api=self.get_api(),
            ts_code=self.code_map(instrument.order_book_id),
            start_date=dt.strftime('%Y%m%d'),
            end_date=dt.strftime('%Y%m%d'),
            asset='I' if instrument.type == 'INDX' else 'E',
            freq=freq_map.get(frequency, None)
        )
        if not bar_data.empty:
            bar_data = bar_data.iloc[0].to_dict()
            bar_data['datetime'] = convert_dt_to_int(dt)
            bar_data['volume'] = six.MAXSIZE
            return bar_data
        return None

    def history_bars(self, instrument, bar_count, frequency, fields, dt, skip_suspended=True, include_now=False,
                     adjust_type='pre', adjust_orig=None):
        start_dt_loc = self.get_trading_calendar().get_loc(dt.replace(hour=0, minute=0, second=0, microsecond=0)) - bar_count + 1
        start_dt = self.get_trading_calendar()[start_dt_loc]
        bar_data = ts.pro_bar(
            api=self.get_api(),
            ts_code=self.code_map(instrument.order_book_id),
            start_date=start_dt.strftime('%Y%m%d'),
            end_date=dt.strftime('%Y%m%d'),
            asset='I' if instrument.type == 'INDX' else 'E',
            adj=adjust_map.get(adjust_type, None),
            freq=freq_map.get(frequency, None)
        )
        if not bar_data.empty:
            if isinstance(fields, six.string_types):
                fields = [fields]
            fields = [field for field in fields if field in bar_data.columns]
            bar_data.sort_index(ascending=False, inplace=True)
            return bar_data[fields].values.flatten()
        return None

    def available_data_range(self, frequency):
        return date(2005, 1, 1), date.today() - relativedelta(days=1)

    def get_trading_calendar(self):
        if self.calendar is None:
            start_date = str(self._env.config.base.start_date).replace('-', '')
            end_date = str(self._env.config.base.end_date).replace('-', '')
            df = self.get_api().trade_cal(start_date=start_date, end_date=end_date)
            df = df[df['is_open'] == 1]
            self.calendar = pd.Index(pd.Timestamp(str(d)) for d in df['cal_date'])
        return self.calendar