

def get_stock_no(order_book_id):
    return order_book_id.split('.')[0]

def get_order_book_id(stock_no):
    if stock_no[0] in ('6', '5'):
        return '{}.XSHG'.format(stock_no)
    elif stock_no[0] in ['3', '0', '1']:
        return '{}.XSHE'.format(stock_no)