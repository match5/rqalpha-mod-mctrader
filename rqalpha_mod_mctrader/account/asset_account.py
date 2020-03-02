
import six

from rqalpha.interface import AbstractAccount
from rqalpha.utils.repr import property_repr
from rqalpha.events import EVENT
from rqalpha.environment import Environment

class AssetAccount(AbstractAccount):

    __repr__ = property_repr

    def __init__(self, total_cash, positions, frozen_cash=0, register_event=True):
        self._total_cash = total_cash
        self._positions = positions
        self._frozen_cash = frozen_cash
        self._backward_trade_set = set()
        if register_event:
            self.register_event()

    def register_event(self):
        event_bus = Environment.get_instance().event_bus
        event_bus.add_listener(EVENT.TRADE, self._on_trade)
        event_bus.add_listener(EVENT.ORDER_PENDING_NEW, self._on_order_pending_new)
        event_bus.add_listener(EVENT.ORDER_CREATION_REJECT, self._on_order_unsolicited_update)
        event_bus.add_listener(EVENT.ORDER_UNSOLICITED_UPDATE, self._on_order_unsolicited_update)
        event_bus.add_listener(EVENT.ORDER_CANCELLATION_PASS, self._on_order_unsolicited_update)
        event_bus.add_listener(EVENT.BAR, self._update_last_price)
        event_bus.add_listener(EVENT.TICK, self._update_last_price)

    def _on_order_pending_new(self, event):
        raise NotImplementedError

    def _on_order_unsolicited_update(self, event):
        raise NotImplementedError

    def _on_trade(self, event):
        raise NotImplementedError
    
    def _update_last_price(self, _):
        for position in self._positions.values():
            position.update_last_price()

    def get_state(self):
        return {}

    def set_state(self, state):
        pass

    @property
    def positions(self):
        return self._positions

    @property
    def frozen_cash(self):
        return self._frozen_cash

    @property
    def cash(self):
        return self.total_cash - self._frozen_cash

    @property
    def market_value(self):
        return sum(position.market_value for position in six.itervalues(self._positions))

    @property
    def transaction_cost(self):
        return sum(position.transaction_cost for position in six.itervalues(self._positions))

    @property
    def margin(self):
        return sum(position.margin for position in six.itervalues(self._positions))

    @property
    def daily_pnl(self):
        return sum(p.daily_pnl for p in six.itervalues(self._positions))

    @property
    def total_value(self):
        return self._total_cash + self.market_value

    @property
    def total_cash(self):
        return self._total_cash

    @property
    def position_pnl(self):
        return sum(p.position_pnl for p in six.itervalues(self._positions))

    @property
    def trading_pnl(self):
        return sum(p.trading_pnl for p in six.itervalues(self._positions))
