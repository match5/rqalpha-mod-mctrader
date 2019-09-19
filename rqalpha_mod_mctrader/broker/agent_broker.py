from rqalpha.interface import AbstractBroker

from rqalpha.model.order import Order
from rqalpha.model.trade import Trade
from rqalpha.model.portfolio import Portfolio
from rqalpha.const import DEFAULT_ACCOUNT_TYPE

from rqalpha.utils.logger import user_system_log

from rqalpha.mod.rqalpha_mod_sys_simulation.simulation_broker import init_portfolio

class AgentBroker(AbstractBroker):
    def __init__(self, env, mod_config):
        self._env = env
        self._open_orders = []

    def after_trading(self):
        pass

    def before_trading(self):
        pass

    def get_open_orders(self, order_book_id=None):
        return []

    def submit_order(self, order):
        user_system_log.info('submit_order {side} {code}'.format(side=order.side, code=order.order_book_id))

    def cancel_order(self, order):
        user_system_log.info('cancel_order {side} {code}'.format(side=order.side, code=order.order_book_id))

    def update(self, calendar_dt, trading_dt, bar_dict):
        pass

    def get_portfolio(self):
        return init_portfolio(self._env)

    def get_benchmark_portfolio(self):
        return None