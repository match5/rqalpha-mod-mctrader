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
            pass
        return np.nan

    def get_limit_up(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['limit_up']
        except Exception:
            pass
        return np.nan

    def get_limit_down(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['limit_down']
        except Exception:
            pass
        return np.nan

    def get_a1(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['a1']
        except Exception:
            pass
        return np.nan

    def get_b1(self, order_book_id):
        try:
            return self.snapshot.loc[order_book_id]['b1']
        except Exception:
            pass
        return np.nan