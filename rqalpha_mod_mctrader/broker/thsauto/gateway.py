import json
import time
from urllib import request

from rqalpha.const import (
    SIDE, ORDER_TYPE,
    DEFAULT_ACCOUNT_TYPE,
    POSITION_EFFECT,
)
from rqalpha.utils.logger import user_system_log
from rqalpha.events import Event, EVENT
from rqalpha.model.trade import Trade
from rqalpha.model.positions import Positions
from rqalpha.model.portfolio import Portfolio
from rqalpha.utils import account_type_str2enum
from rqalpha.mod.rqalpha_mod_sys_simulation.utils import _fake_trade

import pandas as pd

from  rqalpha_mod_mctrader.misc.util import get_order_book_id, get_stock_no


class ThsautoGatway:


    def __init__(self, env, mod_config):
        self._env = env
        self._mod_config = mod_config
        host = mod_config.broker.split('://')[-1]
        self._address = 'http://%s/thsauto' % host
        self._env.event_bus.prepend_listener(EVENT.PRE_BAR, self._on_pre_bar)
        self._env.event_bus.prepend_listener(EVENT.PRE_BEFORE_TRADING, self._on_pre_before_trading)
        self.reset()


    def reset(self):
        self._orders = {}
        self._order_id_map = {}
        self._trade_no = set()


    @property
    def open_oders(self):
        return [order for order in self._orders.values() if order.is_active()]


    def submit_order(self, order):
        route = '/sell' if order.side == SIDE.SELL else '/buy'
        price = order.price
        if order.type == ORDER_TYPE.MARKET:
            if order.side == SIDE.SELL:
                price = self._env.price_board.get_bids(order.order_book_id)[-1]
            else:
                price = self._env.price_board.get_asks(order.order_book_id)[-1]
        parmas = 'stock_no=%s&amount=%d&price=%f' % (
            get_stock_no(order.order_book_id),
            order.quantity - order.quantity % 100,
            price,
        )
        url = '%s%s?%s' % (self._address, route, parmas)
        user_system_log.info('loading: %s' % url)
        reason = 'request failed'
        try:
            account = self._env.get_account(order.order_book_id)
            self._env.event_bus.publish_event(Event(EVENT.ORDER_PENDING_NEW, account=account, order=order))
            with request.urlopen(url) as f:
                user_system_log.info('status: %d %s' % (f.status, f.reason))
                if f.status == 200:
                    data = f.read().decode('utf-8')
                    user_system_log.info(data)
                    resp = json.loads(data)
                    code = resp.get('code', 1)
                    if code == 0:
                        entrust_no = resp['entrust_no']
                        order.set_secondary_order_id(entrust_no)
                        order.active()
                        self._env.event_bus.publish_event(Event(EVENT.ORDER_CREATION_PASS, account=account, order=order))
                        str_order_id = str(order.order_id)
                        self._orders[str_order_id] = order
                        self._order_id_map[entrust_no] = str_order_id
                        return
                    elif code == 1:
                        reason = resp.get('msg', reason)
                    else:
                        user_system_log.info(data)
                        return
        except Exception as e:
            user_system_log.warn(repr(e))
        order.mark_rejected(reason)
        self._env.event_bus.publish_event(Event(EVENT.ORDER_UNSOLICITED_UPDATE, account=account, order=order))


    def cancel_order(self, order):
        if self._orders.get(order.order_id, None):
            url = '%s/cancel?entrust_no=%s' % (self._address, order.secondary_order_id)
            user_system_log.info('loading: %s' % url)
            try:
                with request.urlopen(url) as f:
                    user_system_log.info('status: %d %s' % (f.status, f.reason))
                    if f.status == 200:
                        data = f.read().decode('utf-8')
                        resp = json.loads(data)
                        code = resp.get('code', 1)
                        if code == 0:
                            account = self._env.get_account(order.order_book_id)
                            self._env.event_bus.publish_event(Event(EVENT.ORDER_PENDING_CANCEL, account=account, order=order))
                            order.mark_cancelled("%d order has been cancelled." % order.order_id)
                            self._env.event_bus.publish_event(Event(EVENT.ORDER_CANCELLATION_PASS, account=account, order=order))
                            return
                        else:
                            user_system_log.warn(resp.get('msg', 'request failed'))
            except Exception as e:
                user_system_log.warn(repr(e))
                return
        else:
            user_system_log.info('cancel order not fund: %s' % order.order_id)


    def _query_filled_orders(self):
        url = '%s%s' % (self._address, '/orders/filled')
        user_system_log.info('loading: %s' % url)
        try:
            with request.urlopen(url) as f:
                user_system_log.info('status: %d %s' % (f.status, f.reason))
                if f.status == 200:
                    data = f.read().decode('utf-8')
                    return json.loads(data).get('data', None)
        except Exception as e:
            user_system_log.warn(repr(e))
        return None


    def _on_pre_bar(self, event):
        if self.open_oders:
            data = self._query_filled_orders()
            if data is not None:
                for item in data:
                    trade_no = item[u'成交编号']
                    if trade_no in self._trade_no:
                        continue
                    entrust_no = item[u'合同编号']
                    order_id = self._order_id_map.get(entrust_no, None)
                    if order_id:
                        order = self._orders.get(order_id, None)
                        if order:
                            account = self._env.get_account(order.order_book_id)
                            user_system_log.info(repr(item))
                            trade = Trade.__from_create__(
                                order_id=order.order_id,
                                price=float(item[u'成交均价']),
                                amount=int(item[u'成交数量']),
                                side=order.side,
                                position_effect=order.position_effect,
                                order_book_id=order.order_book_id,
                                frozen_price=order.frozen_price,
                            )
                            order.fill(trade)
                            self._env.event_bus.publish_event(Event(EVENT.TRADE, account=account, trade=trade, order=order))
                            self._trade_no.add(trade_no)


    def _query_balance(self):
        url = '%s%s' % (self._address, '/balance')
        user_system_log.info('loading: %s' % url)
        try:
            with request.urlopen(url) as f:
                user_system_log.info('status: %d %s' % (f.status, f.reason))
                if f.status == 200:
                    data = f.read().decode('utf-8')
                    return json.loads(data).get('data', None)
        except Exception as e:
            user_system_log.warn(repr(e))
        return None


    def _query_position(self):
        url = '%s%s' % (self._address, '/position')
        user_system_log.info('loading: %s' % url)
        try:
            with request.urlopen(url) as f:
                user_system_log.info('status: %d %s' % (f.status, f.reason))
                if f.status == 200:
                    data = f.read().decode('utf-8')
                    return json.loads(data).get('data', None)
        except Exception as e:
            user_system_log.warn(repr(e))
        return None

    
    def sync_portfolio(self, portfolio, retry=10):
        balance_data = self._query_balance()
        while balance_data is None and retry > 0:
            time.sleep(5)
            retry -= 1
            user_system_log.info('retry %d' % retry)
            balance_data = self._query_balance()

        position_data = self._query_position()
        while position_data is None and retry > 0:
            time.sleep(5)
            retry -= 1
            user_system_log.info('retry %d' % retry)
            position_data = self._query_position()

        stock = DEFAULT_ACCOUNT_TYPE.STOCK.name
        account = portfolio.accounts[stock]

        if balance_data:
            account._frozen_cash = float(balance_data.get(u'冻结金额'))
            account._total_cash = float(balance_data.get(u'可用金额')) + account._frozen_cash

        order_book_ids = set()
        if position_data:
            user_system_log.info('sync_positions')
            position_model = self._env.get_position_model(stock)
            positions = Positions(position_model)
            for pos in position_data:
                order_book_id = get_order_book_id(pos[u'证券代码'])
                if not (order_book_id and self._env.get_instrument(order_book_id)):
                    continue
                quantity = int(pos.get(u'持股数量') or pos.get(u'股票余额'))
                if quantity > 0:
                    price = float(pos.get(u'成本价') or pos.get(u'参考成本'))
                    trade = _fake_trade(order_book_id, quantity, price)
                    position = position_model(order_book_id)
                    positions[order_book_id] = position
                    position.apply_trade(trade)
                    last_price = float(pos.get(u'市价'))
                    position._last_price = last_price
                    frozen_quantity = pos.get(u'冻结数量')
                    if frozen_quantity is None and pos.get(u'持股数量') and pos.get(u'可用余额'):
                        frozen_quantity = int(pos[u'持股数量']) - int(pos[u'可用余额'])
                    position.long._non_closable = int(frozen_quantity or 0)
                    user_system_log.info('%s %d %f %f' % (order_book_id, quantity, price, last_price))
                    order_book_ids.add(order_book_id)

            account._positions = positions


    def _on_pre_before_trading(self, event):
        self.reset()
        self.sync_portfolio(self._env.portfolio)