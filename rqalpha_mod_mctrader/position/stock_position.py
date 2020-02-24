from rqalpha.mod.rqalpha_mod_sys_accounts.position_model.stock_position import StockPositionProxy


class StockPosition(StockPositionProxy):

    def apply_settlement(self):
        pass

    def get_state(self):
        return {}

    def set_state(self, state):
        pass
