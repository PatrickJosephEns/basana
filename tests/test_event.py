# Basana
#
# Copyright 2022-2023 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional
import asyncio
import datetime
import random

import pytest

from basana.core import dispatcher, dt, event


class Number(event.Event):
    def __init__(self, when: datetime.datetime, number: float):
        super().__init__(when)
        self.number = number


class RandIntSource(event.EventSource):
    def __init__(self, a: int, b: int):
        super().__init__()
        self.a = a
        self.b = b

    def pop(self) -> Optional[event.Event]:
        return Number(dt.utc_now(), random.randint(self.a, self.b))


class FailingEventSource(event.EventSource):
    def pop(self) -> Optional[event.Event]:
        raise Exception("Error during pop")


class HeadEventSource(event.EventSource):
    def __init__(self, event_source: event.EventSource, count: int):
        super().__init__()
        assert count > 0
        self.event_source = event_source
        self.count = count

    def pop(self) -> Optional[event.Event]:
        if self.count:
            self.count -= 1
            return self.event_source.pop()
        return None


def test_mutiple_sources():
    event_count = 0

    async def on_event(event):
        nonlocal event_count
        event_count += 1

    d = dispatcher.EventDispatcher()

    src1 = HeadEventSource(RandIntSource(1000, 10000), 1500)
    src2 = HeadEventSource(RandIntSource(1, 50), 1300)

    d.subscribe(src1, on_event)
    d.subscribe(src2, on_event)
    asyncio.run(d.run())

    assert event_count == 2800


def test_stop_dispatcher_when_idle():
    d = dispatcher.EventDispatcher(stop_when_idle=False)

    event_count = 0

    async def on_event(event):
        nonlocal event_count
        event_count += 1

    async def on_idle():
        d.stop()

    src1 = HeadEventSource(RandIntSource(1000, 10000), 10)

    d.subscribe(src1, on_event)
    d.subscribe_idle(on_idle)
    asyncio.run(d.run())

    assert event_count == 10


def test_unhandled_exception_during_pop():
    event_count = 0
    d = dispatcher.EventDispatcher()

    async def on_event(event):
        nonlocal event_count
        event_count += 1

    src1 = FailingEventSource()
    d.subscribe(src1, on_event)
    with pytest.raises(Exception, match="Error during pop"):
        asyncio.run(d.run())

    assert event_count == 0
