import json
import time
from urllib import request

from rqalpha.const import SIDE, ORDER_TYPE
from rqalpha.utils.logger import user_system_log
from rqalpha.events import Event, EVENT
from rqalpha.model.trade import Trade
from rqalpha.utils import account_type_str2enum


def stock_no(book_id):
    return book_id.split('.')[0]

def order_book_id(stock_no):
    if stock_no.startswith('6'):
        return '{}.XSHG'.format(stock_no)
    elif stock_no[0] in ['3', '0']:
        return '{}.XSHE'.format(stock_no)


class ThsautoGatway:

    def __init__(self, env, address):
        self._env = env
        self._address = 'http://%s/thsauto' % address
        self._open_orders = {}
        self._order_id_map = {}
        self._trade_no = set()
        self._env.event_bus.add_listener(EVENT.POST_BAR, self._on_post_bar)
        self._env.event_bus.add_listener(EVENT.PRE_AFTER_TRADING, self._on_pre_after_trading)

    def submit_order(self, order):
        route = '/sell' if order.side == SIDE.SELL else '/buy'
        price = order.price
        if order.type == ORDER_TYPE.MARKET:
            if order.side == SIDE.SELL:
                price = self._env.price_board.get_limit_down(order.order_book_id)
            else:
                price = self._env.price_board.get_limit_up(order.order_book_id)
        parmas = 'stock_no=%s&amount=%d&price=%f' % (
            stock_no(order.order_book_id),
            order.quantity, price,
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
                    resp = json.loads(data)
                    if resp.get('success', False):
                        order.active()
                        self._env.event_bus.publish_event(Event(EVENT.ORDER_CREATION_PASS, account=account, order=order))
                        str_order_id = str(order.order_id)
                        entrust_no = resp['entrust_no']
                        self._open_orders[str_order_id] = order
                        self._order_id_map[entrust_no] = str_order_id
                        self._order_id_map[str_order_id] = entrust_no
                        return
                    else:
                        reason = resp.get('msg', reason)
        except Exception as e:
            user_system_log.warn(repr(e))
        order.mark_rejected(reason)
        self._env.event_bus.publish_event(Event(EVENT.ORDER_UNSOLICITED_UPDATE, account=account, order=order))

    def cancel_order(self, order):
        if self._open_orders.get(order.order_id, None):
            url = '%s%s?%s' % (self._address, '/cancel', self._order_id_map[order.order_id])
            user_system_log.info('loading: %s' % url)
            try:
                with request.urlopen(url) as f:
                    user_system_log.info('status: %d %s' % (f.status, f.reason))
                    if f.status == 200:
                        data = f.read().decode('utf-8')
                        resp = json.loads(data)
                        if resp.get('success', False):
                            account = self._env.get_account(order.order_book_id)
                            self._env.event_bus.publish_event(Event(EVENT.ORDER_PENDING_CANCEL, account=account, order=order))
                            order.mark_cancelled("%d order has been cancelled." % order.order_id)
                            self._env.event_bus.publish_event(Event(EVENT.ORDER_CANCELLATION_PASS, account=account, order=order))
                            str_order_id = str(order.order_id)
                            entrust_no = self._order_id_map[str_order_id]
                            del self._open_orders[str_order_id]
                            del self._order_id_map[entrust_no]
                            del self._order_id_map[str_order_id]
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
                    return json.loads(data)
        except Exception as e:
            user_system_log.warn(repr(e))
        return None

    def _on_post_bar(self, event):
        if self._open_orders:
            data = self._query_filled_orders()
            if data is not None:
                for item in data:
                    trade_no = item[u'成交编号']
                    if trade_no in self._trade_no:
                        continue
                    entrust_no = item[u'合同编号']
                    order_id = self._order_id_map.get(entrust_no, None)
                    if order_id:
                        order = self._open_orders.get(order_id, None)
                        if order:
                            trade = Trade.__from_create__(
                                order_id=order.order_id,
                                price=float(item[u'成交均价']),
                                amount=int(item[u'成交数量']),
                                side=order.side,
                                position_effect=order.position_effect,
                                order_book_id=order.order_book_id,
                                frozen_price=order.frozen_price,
                            )
                            account = self._env.get_account(order.order_book_id)
                            trade._commission = self._env.get_trade_commission(account_type_str2enum(account.type), trade)
                            trade._tax = self._env.get_trade_tax(account_type_str2enum(account.type), trade)
                            order.fill(trade)
                            self._env.event_bus.publish_event(Event(EVENT.TRADE, account=account, trade=trade, order=order))
                            self._trade_no.add(trade_no)
                            if order.is_final():
                                str_order_id = str(order.order_id)
                                del self._open_orders[str_order_id]
                                del self._order_id_map[entrust_no]
                                del self._order_id_map[str_order_id]

    def _on_pre_after_trading(self, event):
        for order in self._open_orders.values():
            order.mark_cancelled('order {} volume {} is unmatched'.format(order.order_book_id, order.quantity))
            self._env.event_bus.publish_event(Event(EVENT.ORDER_UNSOLICITED_UPDATE, account=account, order=order))



