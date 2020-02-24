from rqalpha.interface import AbstractMod
from rqalpha.data.data_proxy import DataProxy
from rqalpha.const import DEFAULT_ACCOUNT_TYPE

from rqalpha.utils.logger import (
    user_std_handler_log_formatter ,system_log, 
    basic_system_log, std_log, user_log, user_system_log
)

from .data_source.tusharepro import TushareProDataSource
from .event_source import McTraderEventSource
from .broker.ths_broker import ThsBroker
from .misc.price_board import McTraderPriceBoard
from .misc.persist_provider import McPersistProvider
from .account.stock_account import StockAccount 
from .position.stock_position import StockPosition

import tushare as ts

from logbook import FileHandler

class McTraderMod(AbstractMod):

    def __init__(self):
        pass


    def start_up(self, env, mod_config):
        
        if mod_config.data_source == 'tushare_pro':
            apis = [ts.pro_api(token) for token in mod_config.tushare_tokens]
            env.set_data_source(TushareProDataSource(env, apis))

        if mod_config.broker.startswith('thsauto'):
            env.set_broker(ThsBroker(env, mod_config))
            
        env.set_account_model(DEFAULT_ACCOUNT_TYPE.STOCK.name, StockAccount)
        env.set_position_model(DEFAULT_ACCOUNT_TYPE.STOCK.name, StockPosition)

        env.set_price_board(McTraderPriceBoard(env))
        env.set_event_source(McTraderEventSource(env, mod_config))
        env.set_persist_provider(McPersistProvider(env, mod_config))

        env.set_data_proxy(DataProxy(env.data_source, env.price_board))

        if mod_config.log_file:
            user_log.handlers = []
            user_system_log.handlers = []
            user_handler = FileHandler(mod_config.log_file, bubble=True)
            if not env.config.extra.user_log_disabled:
                user_log.handlers.append(user_handler)
            if not env.config.extra.user_system_log_disabled:
                user_system_log.handlers.append(user_handler)
            system_log.handlers = [FileHandler(mod_config.log_file, mode='a', bubble=True)]
            basic_system_log.handlers = [FileHandler(mod_config.log_file, bubble=True)]

        system_log.info('\n{}'.format(mod_config))


    def tear_down(self, code, exception=None):
        system_log.info('tear_down %s' % code)
