
import asyncio
from argparse import Namespace
from typing import Dict

import pytest  # type: ignore

from pymap.backend.dict import DictBackend
from pymap.context import subsystem
from .mocktransport import MockTransport


class FakeArgs(Namespace):
    debug = True
    insecure_login = True
    cert = None
    key = None
    demo_data = True
    demo_user = 'testuser'
    demo_password = 'testpass'


class TestBase:

    @classmethod
    @pytest.fixture(autouse=True)
    async def init_backend(cls, request, args):
        test = request.instance
        test._fd = 1
        test.backend = await DictBackend.init(args)
        test.config = test.backend.config
        test.config.disable_search_keys = [b'DRAFT']
        test.matches: Dict[str, bytes] = {}
        test.transport = test.new_transport()

    @pytest.fixture
    def args(self):
        return FakeArgs()

    def _incr_fd(self):
        fd = self._fd
        self._fd += 1
        return fd

    def new_transport(self):
        return MockTransport(self.matches, self._incr_fd())

    def new_events(self, n=1):
        if n == 1:
            return subsystem.get().new_event()
        else:
            return (subsystem.get().new_event() for _ in range(n))

    def _check_queue(self, transport):
        queue = transport.queue
        assert 0 == len(queue), 'Items left on queue: ' + repr(queue)

    async def _run_transport(self, transport):
        return await self.backend(transport, transport)

    async def run(self, *transports):
        failures = []
        transport_tasks = [asyncio.create_task(
            self._run_transport(transport)) for transport in transports]
        try:
            await self._run_transport(self.transport)
        except Exception as exc:
            failures.append(exc)
        for task in transport_tasks:
            try:
                await task
            except Exception as exc:
                failures.append(exc)
        if failures:
            raise failures[0]
        self._check_queue(self.transport)
        for transport in transports:
            self._check_queue(transport)
