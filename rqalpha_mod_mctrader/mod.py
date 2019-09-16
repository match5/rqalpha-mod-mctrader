
# from gevent import monkey
# monkey.patch_all

from rqalpha.interface import AbstractMod
from rqalpha.data.data_proxy import DataProxy

from .data_source.tusharepro import TushareProDataSource
from .event_source import McTraderEventSource
from .broker.agent_broker import AgentBroker
from .price_board import McTraderPriceBoard

import tushare as ts

class McTraderMod(AbstractMod):
    def __init__(self):
        pass

    def start_up(self, env, mod_config):
        print(mod_config)
        if mod_config.data_source == 'tushare_pro':
            apis = [ts.pro_api(token) for token in mod_config.tushare_tokens]
            env.set_data_source(TushareProDataSource(env, apis))
        env.set_price_board(McTraderPriceBoard())
        env.set_data_proxy(DataProxy(env.data_source, env.price_board))
        env.set_event_source(McTraderEventSource(env, mod_config))
        env.set_broker(AgentBroker(env, mod_config))

    def tear_down(self, code, exception=None):
        pass
