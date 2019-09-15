from rqalpha.core.bar_dict_price_board import BarDictPriceBoard


class McTraderPriceBoard(BarDictPriceBoard):
    def __init__(self):
        super(McTraderPriceBoard, self).__init__()

    def get_last_price(self, order_book_id):
        return super(McTraderPriceBoard, self).get_last_price(order_book_id)

    def get_limit_up(self, order_book_id):
        return super(McTraderPriceBoard, self).get_limit_up(order_book_id)

    def get_limit_down(self, order_book_id):
        return super(McTraderPriceBoard, self).get_limit_down(order_book_id)
