"""Module containing the general exceptions that may be used by pymap."""

from typing import Optional

from .parsing.response import Response, ResponseCode, ResponseNo, ResponseOk, \
    ResponseBye
from .parsing.response.code import TryCreate, ReadOnly

__all__ = ['ResponseError', 'CloseConnection', 'CommandNotAllowed',
           'SearchNotAllowed', 'MailboxError', 'MailboxNotFound',
           'MailboxConflict', 'MailboxHasChildren', 'MailboxReadOnly',
           'AppendFailure']


class ResponseError(Exception):
    """The base exception for all custom errors that are used to generate a
    response to an IMAP command.

    """

    def get_response(self, tag: bytes) -> Response:
        """Build an IMAP response for the error.

        Args:
            tag: The command tag that generated the error.

        """
        raise NotImplementedError


class CloseConnection(ResponseError):
    """Raised when the connection should be closed immediately after sending
    the provided response.

    """

    def get_response(self, tag: bytes) -> ResponseOk:
        response = ResponseOk(tag, b'Logout successful.')
        response.add_untagged(ResponseBye(b'Logging out.'))
        return response


class CommandNotAllowed(ResponseError):
    """The command is syntactically valid, but not allowed.

    Args:
        command: The name of the command.
        code: Optional response code for the error.

    """

    def __init__(self, command: bytes, code: ResponseCode = None) -> None:
        super().__init__()
        self.command = command
        self.code = code

    def get_response(self, tag: bytes) -> Response:
        return ResponseNo(tag, self.command + b' not allowed.', self.code)


class SearchNotAllowed(CommandNotAllowed):
    """The ``SEARCH`` command contained a search key that could not be
    executed by the mailbox.

    Args:
        key: The search key that failed.

    """

    def __init__(self, key: bytes = None) -> None:
        command = b'SEARCH ' + key if key else b'SEARCH'
        super().__init__(command)


class MailboxError(ResponseError):
    """Parent exception for errors related to a mailbox.

    Args:
        mailbox: The name of the mailbox.
        message: The response message for the error.
        code: Optional response code for the error.

    """

    def __init__(self, mailbox: str, message: bytes,
                 code: Optional[ResponseCode] = None) -> None:
        super().__init__()
        self.mailbox = mailbox
        self.message = message
        self.code = code

    def get_response(self, tag: bytes) -> ResponseNo:
        return ResponseNo(tag, self.message, self.code)


class MailboxNotFound(MailboxError):
    """The requested mailbox was not found.

    Args:
        mailbox: The name of the mailbox
        try_create: Whether to include ``[TRYCREATE]`` in the error.

    """

    def __init__(self, mailbox: str, try_create: bool = False) -> None:
        super().__init__(mailbox, b'Mailbox does not exist.',
                         TryCreate() if try_create else None)


class MailboxConflict(MailboxError):
    """The mailbox cannot be created or renamed because of a naming conflict
    with another mailbox.

    Args:
        mailbox: The name of the mailbox.

    """

    def __init__(self, mailbox: str) -> None:
        super().__init__(mailbox, b'Mailbox already exists.')


class MailboxHasChildren(MailboxError):
    """The mailbox cannot be deleted because there are other inferior
    heirarchical mailboxes below it.

    Args:
        mailbox: The name of the mailbox.

    """

    def __init__(self, mailbox: str) -> None:
        super().__init__(mailbox, b'Mailbox has inferior hierarchical names.')


class MailboxReadOnly(MailboxError):
    """The mailbox is opened read-only and the requested operation is not
    allowed.

    Args:
        mailbox: The name of the mailbox.

    """

    def __init__(self, mailbox: str) -> None:
        super().__init__(mailbox, b'Mailbox is read-only.', ReadOnly())


class AppendFailure(MailboxError):
    """The mailbox append operation failed."""
    pass
