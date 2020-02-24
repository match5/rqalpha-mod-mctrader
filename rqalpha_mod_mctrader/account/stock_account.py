
from rqalpha.const import SIDE, DEFAULT_ACCOUNT_TYPE
from rqalpha.mod.rqalpha_mod_sys_accounts.api.api_stock import order_shares

from .asset_account import AssetAccount


class StockAccount(AssetAccount):

    def __init__(self, total_cash, positions, frozen_cash=0, register_event=True):
        super(StockAccount, self).__init__(total_cash, positions, frozen_cash, register_event)
        self._dividend_receivable = {}
        self._pending_transform = {}

    def order(self, order_book_id, quantity, style, target=False):
        position = self.positions[order_book_id]
        if target:
            # For order_to
            quantity = quantity - position.quantity
        return order_shares(order_book_id, quantity, style=style)

    def _on_order_pending_new(self, event):
        if event.account != self:
            return
        order = event.order
        self._frozen_cash += self._frozen_cash_of_order(order)

    def _on_order_unsolicited_update(self, event):
        if event.account != self:
            return
        order = event.order
        if order.filled_quantity != 0:
            self._frozen_cash -= order.unfilled_quantity / order.quantity * self._frozen_cash_of_order(order)
        else:
            self._frozen_cash -= self._frozen_cash_of_order(event.order)

    def _on_trade(self, event):
        if event.account != self:
            return
        self._apply_trade(event.trade, event.order)

    def _on_before_trading(self, event):
        pass

    def _on_settlement(self, event):
        pass

    @property
    def type(self):
        return DEFAULT_ACCOUNT_TYPE.STOCK.name

    @property
    def dividend_receivable(self):
        return 0

    def _apply_trade(self, trade, order=None):
        if trade.exec_id in self._backward_trade_set:
            return
        position = self._positions.get_or_create(trade.order_book_id)
        position.apply_trade(trade)
        if order:
            if trade.last_quantity != order.quantity:
                self._frozen_cash -= trade.last_quantity / order.quantity * self._frozen_cash_of_order(order)
            else:
                self._frozen_cash -= self._frozen_cash_of_order(order)
        self._backward_trade_set.add(trade.exec_id)
        
    @staticmethod
    def _frozen_cash_of_order(order):
        return order.frozen_price * order.quantity if order.side == SIDE.BUY else 0

    def fast_forward(self, orders, trades=list()):
        pass