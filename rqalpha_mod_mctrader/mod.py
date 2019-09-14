# -*- coding: utf-8 -*-
#
# Copyright 2017 Ricequant, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from gevent import monkey
monkey.patch_all

from rqalpha.interface import AbstractMod
from rqalpha.data.data_proxy import DataProxy

from .data_source.tusharepro import TushareProDataSource
from .event_source import RealtimeEventSource
from .broker.agent_broker import AgentBroker

import tushare as ts

class McTraderMod(AbstractMod):
    def __init__(self):
        pass

    def start_up(self, env, mod_config):
        print(mod_config)
        bundle_path = env.config.base.data_bundle_path
        if mod_config.data_source == 'tushare_pro':
            apis = [ts.pro_api(token) for token in mod_config.tushare_tokens]
            env.set_data_source(TushareProDataSource(env, bundle_path, apis))
            env.set_data_proxy(DataProxy(env.data_source, env.price_board))
        env.set_event_source(RealtimeEventSource(env, mod_config))
        env.set_broker(AgentBroker(env, mod_config))

    def tear_down(self, code, exception=None):
        pass
