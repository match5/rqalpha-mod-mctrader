import numpy as np

from rqalpha.interface import AbstractPriceBoard


class McTraderPriceBoard(AbstractPriceBoard):

    def __init__(self, env):
        self._env = env
        self.snapshot = None


    def set_snapshot(self, snapshot):
        self.snapshot = snapshot


    def get_last_price(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['last']
        except Exception:
            return np.nan


    def get_limit_up(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['limit_up']
        except Exception:
            return np.nan


    def get_limit_down(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['limit_down']
        except Exception:
            return np.nan


    def get_a1(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['a1']
        except Exception:
            return np.nan


    def get_b1(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['b1']
        except Exception:
            return np.nan


    def get_asks(self, order_book_id):
        try:
            info = self.snapshot.loc[order_book_id]
            return [info['a1'], info['a2'], info['a3'], info['a4'], info['a5']]
        except Exception:
            return []


    def get_bids(self, order_book_id):
        try:
            info = self.snapshot.loc[order_book_id]
            return [info['b1'], info['b2'], info['b3'], info['b4'], info['b5']]
        except Exception:
            return []