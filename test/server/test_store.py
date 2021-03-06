
import pytest  # type: ignore

from .base import TestBase

pytestmark = pytest.mark.asyncio


class TestStore(TestBase):

    async def test_store(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX')
        self.transport.push_readline(
            b'store1 STORE * +FLAGS (\\Seen)\r\n')
        self.transport.push_write(
            b'* 4 FETCH (FLAGS (\\Recent \\Seen))\r\n'
            b'store1 OK STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()

    async def test_store_silent(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX')
        self.transport.push_readline(
            b'store1 STORE * +FLAGS.SILENT (\\Seen)\r\n')
        self.transport.push_write(
            b'store1 OK STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()

    async def test_uid_store(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX')
        self.transport.push_readline(
            b'store1 UID STORE * +FLAGS (\\Seen)\r\n')
        self.transport.push_write(
            b'* 4 FETCH (FLAGS (\\Recent \\Seen) UID 104)\r\n'
            b'store1 OK UID STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()

    async def test_store_add_recent(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX')
        self.transport.push_readline(
            b'store1 STORE 1 +FLAGS (\\Recent)\r\n')
        self.transport.push_write(
            b'* 1 FETCH (FLAGS (\\Seen))\r\n'
            b'store1 OK STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()

    async def test_store_remove_recent(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX')
        self.transport.push_readline(
            b'store1 STORE * -FLAGS (\\Recent)\r\n')
        self.transport.push_write(
            b'* 4 FETCH (FLAGS (\\Recent))\r\n'
            b'store1 OK STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()

    async def test_store_set_non_recent(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX')
        self.transport.push_readline(
            b'store1 STORE * FLAGS ()\r\n')
        self.transport.push_write(
            b'* 4 FETCH (FLAGS (\\Recent))\r\n'
            b'store1 OK STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()

    async def test_store_invalid(self):
        self.transport.push_login()
        self.transport.push_select(b'INBOX', 4, 1)
        self.transport.push_readline(
            b'store1 STORE * +FLAGS (\\Invalid)\r\n')
        self.transport.push_write(
            b'* 4 FETCH (FLAGS (\\Recent))\r\n'
            b'store1 OK STORE completed.\r\n')
        self.transport.push_logout()
        await self.run()
