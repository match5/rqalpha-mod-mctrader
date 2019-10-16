import json
import time
from urllib import request

from rqalpha.const import SIDE
from rqalpha.utils.logger import user_system_log
from rqalpha.events import EVENT
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
        self._env.event_bus.add_listener(EVENT.POST_BAR, self._on_post_bar)

    def submit_order(self, order):
        route = '/sell' if order.side == SIDE.SELL else '/buy'
        parmas = 'stock_no=%s&amount=%d&price=%f' % (
            stock_no(order.order_book_id),
            order.quantity,
            order.price,
        )
        url = '%s%s?%s' % (self._address, route, parmas)
        user_system_log.info('loading: %s' % url)
        with request.urlopen(url) as f:
            user_system_log.info('status: %d %s' % (f.status, f.reason))
            if f.status == 200:
                data = f.read().decode('utf-8')
                try:
                    resp = json.loads(data)
                    if resp.get('success', False):
                        account = self._env.get_account(order.order_book_id)
                        self._env.event_bus.publish_event(Event(EVENT.ORDER_PENDING_NEW, account=account, order=order))
                        order.active()
                        self._env.event_bus.publish_event(Event(EVENT.ORDER_CREATION_PASS, account=account, order=order))
                        str_order_id = str(order.order_id)
                        entrust_no = resp['entrust_no']
                        self._open_orders[str_order_id] = order
                        self._order_id_map[entrust_no] = str_order_id
                        self._order_id_map[str_order_id] = entrust_no
                        return
                    else:
                        order.mark_rejected(data)
                        return
                except Exception as e:
                    user_system_log.info(repr(e))
        order.mark_rejected('request faild')

    def cancel_order(self, order):
        if self._open_orders.get(order.order_id, None):
            url = '%s%s?%s' % (self._address, '/cancel', self._order_id_map[order.order_id])
            user_system_log.info('loading: %s' % url)
            with request.urlopen(url) as f:
                user_system_log.info('status: %d %s' % (f.status, f.reason))
                if f.status == 200:
                    data = f.read().decode('utf-8')
                    try:
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
                    except Exception as e:
                        user_system_log.info(repr(e))
                        return
        else:
            user_system_log.info('cancel order not fund: %s' % order.order_id)

    def _query_filled_orders(self):
        url = '%s%s' % (self._address, '/orders/filled')
        user_system_log.info('loading: %s' % url)
        with request.urlopen(url) as f:
            user_system_log.info('status: %d %s' % (f.status, f.reason))
            if f.status == 200:
                data = f.read().decode('utf-8')
                try:
                    return json.loads(data)
                except Exception as e:
                    user_system_log.info(repr(e))
        return None

    def _on_post_bar(self, event):
        if self._open_orders:
            data = self._query_filled_orders()
            if data is not None:
                for item in data:
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
                            self._env.event_bus.publish_event(RqEvent(EVENT.TRADE, account=account, trade=trade))
                            str_order_id = str(order.order_id)
                            del self._open_orders[str_order_id]
                            del self._order_id_map[entrust_no]
                            del self._order_id_map[str_order_id]


