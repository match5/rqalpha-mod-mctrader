import six
from datetime import date
from dateutil.relativedelta import relativedelta

from rqalpha.data.base_data_source import BaseDataSource
from rqalpha.utils.datetime_func import convert_dt_to_int
from rqalpha.model.bar import NAMES as bar_fields
from rqalpha.utils.logger import user_system_log

import pandas as pd
import tushare as ts

from rqalpha_mod_mctrader.misc.util import get_order_book_id


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
    'D': '1d',
    '1min': '1m',
    '5min': '5m',
}

adjust_map = {
    'pre' : 'qfq',
    'post' : 'hfq',
    'qfq' : 'pre',
    'hfq' : 'post',
}

code_map = {
    'sh': '000001.XSHG',
    'sz': '399001.XSHE',
    'sz50': '000016.XSHG',
    'hs300': '000300.XSHG',
    'sz500': '000905.XSHG',
    'zxb': '399005.XSHE',
    'cyb': '399006.XSHE',
    '000001.XSHG': 'sh',
    '399001.XSHE': 'sz',
    '000016.XSHG': 'sz50',
    '000300.XSHG': 'hs300',
    '000905.XSHG': 'sz500',
    '399005.XSHE': 'zxb',
    '399006.XSHE': 'cyb',
}

def ts_code(rqcode):
    return code_map.get(rqcode, None) or rqcode.split('.')[0]


def ts_code_pro(rqcode):
    split = rqcode.split('.')
    return split[0] + '.' + suffix_map[split[1]]


def order_book_id(ts_code):
    try:
        return code_map[ts_code]
    except KeyError as e:
        code = get_order_book_id(ts_code)
        if not code:
            raise e
        return code


def order_book_id_pro(tscode):
    return ts_code_pro(ts_code)


def convert_date_str_to_int(datestr):
    return convert_dt_to_int(pd.Timestamp(datestr))



class TushareProDataSource(BaseDataSource):


    def __init__(self, env, apis):
        super(TushareProDataSource, self).__init__(
            env.config.base.data_bundle_path, {}
        )
        self.apis = apis
        self._env = env
        self.calendar = None


    def get_api(self):
        api = self.apis.pop(0)
        self.apis.append(api)
        return api


    def update_realtime_quotes(self, order_book_ids, print_log=False):
        if not order_book_ids:
            return

        codes = [ts_code(book_id) for book_id in order_book_ids]
        try:
            df = ts.get_realtime_quotes(codes)
        except Exception as e:
            user_system_log.warn(repr(e))
            return

        columns = set(df.columns) - set(['name', 'time', 'date', 'code'])
        for label in columns:
            df[label] = df[label].map(lambda x: 0 if str(x).strip() == '' else x)
            df[label] = df[label].astype(float)

        df['chg'] = df['price'] / df['pre_close'] - 1
        df['order_book_id'] = df['code'].apply(order_book_id)
        df = df.set_index('order_book_id').sort_index()
        df['order_book_id'] = df.index
        df['datetime'] = df['date'] + ' ' + df['time']
        df['close'] = df['price']
        df['last'] = df['price']
        df = df.rename(columns={
            'pre_close': 'prev_close',
            'amount': 'total_turnover',
            'b1_p':'b1', 'a1_p':'a1',
            'b2_p':'b2', 'a2_p':'a2',
            'b3_p':'b3', 'a3_p':'a3',
            'b4_p':'b4', 'a4_p':'a4',
            'b5_p':'b5', 'a5_p':'a5',
        })

        df['limit_up'] = df.apply(
            lambda row: row.prev_close * (1.1 if 'ST' not in row['name'] else 1.05), axis=1).round(2)
        df['limit_down'] = df.apply(
            lambda row: row.prev_close * (0.9 if 'ST' not in row['name'] else 0.95), axis=1).round(2)

        del df['code']
        del df['date']
        del df['time']

        self._env.price_board.set_snapshot(df)

        if print_log:
            user_system_log.info('update_realtime_quotes\n%s\n%s' % (order_book_ids, repr(df)))


    def get_bar(self, instrument, dt, frequency):
        try:
            quote = self._env.price_board.snapshot.loc[instrument.order_book_id]
            quote = quote[bar_fields].to_dict()
            quote['datetime'] = convert_dt_to_int(dt)
            return quote
        except Exception as e:
            user_system_log.warn(repr(e))
        return None


    def history_bars(self, instrument, bar_count, frequency, fields, dt, skip_suspended=True, include_now=False,
                     adjust_type='pre', adjust_orig=None):
        if frequency == '1d':
            prev_date = self._env.data_proxy.get_previous_trading_date(dt)
            base = super(TushareProDataSource, self)
            if prev_date.date() <= base.available_data_range(frequency)[1]:
                return base.history_bars(
                    instrument, bar_count, frequency, fields, dt,
                    skip_suspended, include_now, adjust_type, adjust_orig
                )
        start_dt_loc = self.get_trading_calendar().get_loc(dt.replace(hour=0, minute=0, second=0, microsecond=0)) - bar_count + 1
        start_dt = self.get_trading_calendar()[start_dt_loc]
        try:
            bar_data = ts.pro_bar(
                api=self.get_api(),
                ts_code=ts_code_pro(instrument.order_book_id),
                start_date=start_dt.strftime('%Y%m%d'),
                end_date=dt.strftime('%Y%m%d'),
                asset='I' if instrument.type == 'INDX' else 'E',
                adj=adjust_map.get(adjust_type, None),
                freq=freq_map.get(frequency, None)
            )
        except Exception as e:
            user_system_log.warn(repr(e))
            return None
        if not bar_data.empty:
            bar_data = bar_data.rename(columns={
                'vol': 'volume',
                'amount': 'total_turnover',
            })
            bar_data['volume'] = bar_data['volume'] * 100
            bar_data['total_turnover'] = bar_data['total_turnover'] * 1000
            bar_data['datetime'] = bar_data['trade_date'].apply(convert_date_str_to_int)
            if isinstance(fields, six.string_types):
                fields = [fields]
            fields = [field for field in fields if field in bar_data.columns]
            bar_data.sort_index(ascending=False, inplace=True)
            return bar_data[fields].values.flatten()
        return None


    def available_data_range(self, frequency):
        return date.today(), date.max


    def get_trading_calendar(self):
        return super(TushareProDataSource, self).get_trading_calendar()
        # if self.calendar is None:
        #     start_date = date.today() - relativedelta(years=1)
        #     start_date = start_date.strftime("%Y-%m-%d")
        #     df = self.get_api().trade_cal(start_date=start_date)
        #     df = df[df['is_open'] == 1]
        #     self.calendar = pd.Index(pd.Timestamp(str(d)) for d in df['cal_date'])
        # return self.calendar