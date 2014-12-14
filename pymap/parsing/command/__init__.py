# Copyright (c) 2014 Ian C. Good
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import re

from .. import Parseable, NotParseable
from ..primitives import Atom

__all__ = ['CommandNotFound', 'BadCommand', 'Tag', 'Command',
           'CommandAny', 'CommandAuth', 'CommandNonAuth', 'CommandSelect']


class CommandNotFound(NotParseable):
    """Error indicating the data was not parseable because the command was not
    found.

    """

    def __init__(self, buf, command):
        super(CommandNotFound, self).__init__(buf)
        self.command = command


class BadCommand(NotParseable):
    """Error indicating the data was not parseable because the command had
    invalid arguments.

    """

    def __init__(self, buf, command):
        super(BadCommand, self).__init__(buf)
        self.command = command


class Tag(Parseable):
    """Represents the tag prefixed to every client command in an IMAP stream.

    :param bytes tag: The contents of the tag.

    """

    _pattern = re.compile(rb'[\x21\x23\x24\x26\x27\x2C-\x5B'
                          rb'\x5D\x5E-\x7A\x7C\x7E]+')

    #: May be passed in to the constructor to indicate the continuation
    #: response tag, ``+``.
    CONTINUATION = object()

    def __init__(self, tag=None):
        super(Tag, self).__init__()
        if not tag:
            self.value = b'*'
        elif tag == self.CONTINUATION:
            self.value = b'+'
        else:
            self.value = tag

    @classmethod
    def try_parse(cls, buf, start=0):
        start += cls._whitespace_length(buf, start)
        match = cls._pattern.match(buf, start)
        if not match:
            raise NotParseable(buf)
        end = cls._enforce_whitespace(buf, match.end(0))
        return cls(match.group(0)), end

    def __bytes__(self):
        return self.value

Parseable.register_type(Tag)


class Command(Parseable):
    """Base class to represent the commands available to clients.

    :param bytes cmd: The actual IMAP command string.

    """

    def __init__(self, cmd):
        super(Command, self).__init__()
        self.command = cmd

    @classmethod
    def try_parse(cls, buf, start=0):
        from . import any, auth, nonauth, select
        tag, cur = Tag.try_parse(buf, start)
        atom, cur = Atom.try_parse(buf, cur)
        cur += cls._whitespace_length(buf, cur)
        command = atom.value.upper()
        for cmd_type in [CommandAny, CommandAuth,
                         CommandNonAuth, CommandSelect]:
            for regex, cmd_subtype in cmd_type._commands:
                match = regex.match(command)
                if match:
                    if cmd_subtype:
                        return cmd_subtype._try_parse(command, buf, cur)
                    return cmd_type(command), cur
        raise CommandNotFound(buf, command)

    def __bytes__(self):
        return self.cmd + self.remaining

Parseable.register_type(Command)


class CommandNoArgs(object):
    """Convenience class used to fail parsing when args are given to a command
    that expects nothing.

    """

    @classmethod
    def _try_parse(cls, cmd, buf, start):
        remaining, end = cls._line_match(buf, start)
        if remaining:
            raise BadCommand(buf, cmd)
        return cls(cmd), end


class CommandAny(Command):
    """Represents a command available at any stage of the IMAP session.

    """

    _commands = []


class CommandAuth(Command):
    """Represents a command available when the IMAP session has been
    authenticated.

    """

    _commands = []


class CommandNonAuth(Command):
    """Represents a command available only when the IMAP session has not yet
    authenticated.

    """

    _commands = []


class CommandSelect(CommandAuth):
    """Represents a command available only when the IMAP session has been
    authenticated and a mailbox has been selected.

    """

    _commands = []