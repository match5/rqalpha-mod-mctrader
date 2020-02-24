from rqalpha.interface import AbstractBroker

from rqalpha.model.order import Order
from rqalpha.model.trade import Trade
from rqalpha.const import DEFAULT_ACCOUNT_TYPE, ORDER_TYPE, SIDE
from rqalpha.mod.rqalpha_mod_sys_simulation.simulation_broker import init_portfolio

from .thsauto.gateway import ThsautoGatway


class ThsBroker(AbstractBroker):

    def __init__(self, env, mod_config):
        self._env = env
        self._mod_config = mod_config
        self._gateway = ThsautoGatway(env, mod_config)


    def get_portfolio(self):
        return init_portfolio(self._env)
    

    def get_open_orders(self, order_book_id=None):
        if order_book_id is not None:
            return [
                order for order in self._gateway._open_orders.values() if
                order.order_book_id == order_book_id
            ]
        else:
            return self._gateway._open_orders.values()


    def submit_order(self, order):
        self._gateway.submit_order(order)


    def cancel_order(self, order):
        self._gateway.cancel_order(order)