
from io import BytesIO
from typing import TypeVar, Type, Optional, List, Dict, Tuple, Hashable

from ...bytes import MaybeBytes, BytesFormat, WriteStream, Writeable

__all__ = ['ResponseCode', 'Response', 'ResponseContinuation', 'ResponseBad',
           'ResponseNo', 'ResponseOk', 'ResponseBye', 'ResponsePreAuth',
           'ResponseT']

#: Type variable with an upper bound of :class:`Response`.
ResponseT = TypeVar('ResponseT', bound='Response')

_Mergeable = Dict[Tuple[Type['Response'], Hashable], int]


class ResponseCode:
    """Base class for response codes that may be returned along with IMAP
    server responses.

    """

    def __bytes__(self) -> bytes:
        raise NotImplementedError

    @classmethod
    def of(cls, code: Optional[MaybeBytes]) -> Optional['ResponseCode']:
        """Build and return an anonymous response code object.

        Args:
            code: The code string, without square brackets.

        """
        if code is not None:
            return _AnonymousResponseCode(code)
        else:
            return None


class _AnonymousResponseCode(ResponseCode):

    def __init__(self, code: MaybeBytes) -> None:
        super().__init__()
        self.code = code

    def __bytes__(self) -> bytes:
        return BytesFormat(b'[%b]') % self.code


class Response(Writeable):
    """Base class for all responses sent from the server to the client. These
    responses may be sent unsolicited (e.g. idle timeouts) or in response to a
    tagged command from the client.

    Args:
        tag: The tag bytestring of the associated command, a plus (``+``) to
            indicate a continuation requirement, or an asterisk (``*``) to
            indicate an untagged response.
        text: The response text.
        code: Optional response code.

    Attributes:
        tag: The tag bytestring.

    """

    #: The condition bytestring, e.g. ``OK``.
    condition: Optional[bytes] = None

    def __init__(self, tag: MaybeBytes, text: MaybeBytes = None,
                 code: ResponseCode = None) -> None:
        super().__init__()
        self.tag = bytes(tag)
        self._code = code
        self._text = text or b''
        self._untagged: List['Response'] = []
        self._mergeable: _Mergeable = {}
        self._raw: Optional[bytes] = None

    @property
    def text(self) -> bytes:
        """The response text."""
        if self.condition:
            if self.code:
                return BytesFormat(b'%b %b %b') \
                    % (self.condition, self.code, self._text)
            else:
                return BytesFormat(b'%b %b') % (self.condition, self._text)
        else:
            return bytes(self._text)

    @property
    def code(self) -> Optional[ResponseCode]:
        """Optional response code."""
        return self._code

    @code.setter
    def code(self, code: Optional[ResponseCode]) -> None:
        self._code = code
        self._raw = None

    def add_untagged(self, *responses: 'Response') -> None:
        """Add an untagged response. These responses are shown before the
        parent response.

        Args:
            responses: The untagged responses to add.

        """
        for resp in responses:
            try:
                merge_key = resp.merge_key
            except TypeError:
                self._untagged.append(resp)
            else:
                key = (type(resp), merge_key)
                try:
                    untagged_idx = self._mergeable[key]
                except KeyError:
                    untagged_idx = len(self._untagged)
                    self._mergeable[key] = untagged_idx
                    self._untagged.append(resp)
                else:
                    merged = self._untagged[untagged_idx].merge(resp)
                    self._untagged[untagged_idx] = merged
        self._raw = None

    def add_untagged_ok(self, text: MaybeBytes,
                        code: Optional[ResponseCode] = None) -> None:
        """Add an untagged ``OK`` response.

        See Also:
            :meth:`.add_untagged`, :class:`ResponseOk`

        Args:
            text: The response text.
            code: Optional response code.

        """
        response = ResponseOk(b'*', text, code)
        self.add_untagged(response)

    @property
    def is_terminal(self) -> bool:
        """True if the response contained an untagged ``BYE`` response
        indicating that the session should be terminated.

        """
        for resp in self._untagged:
            if resp.is_terminal:
                return True
        return False

    @property
    def is_bad(self) -> bool:
        """True if the response indicates an error in the command received from
        the client.

        """
        return False

    @property
    def merge_key(self) -> Hashable:
        """Returns a hashable value which can be compared to other
        :attr:`.merge_key` values of the same response type to see if the
        two responses can be merged.

        Raises:
            TypeError: This response type may not be merged.

        """
        raise TypeError(self)

    def merge(self: ResponseT, other: ResponseT) -> ResponseT:
        """Return a copy of this response with the other response merged in.

        Args:
            other: The other response to merge.

        Raises:
            TypeError: This response type may not be merged.
            ValueError: The two responses are not mergeable.

        """
        raise TypeError(self)

    def write(self, writer: WriteStream) -> None:
        """Write the object to the stream, with one or more calls to
        :meth:`~asyncio.WriteStream.write`.

        Args:
            writer: The output stream.

        """
        for untagged in self._untagged:
            untagged.write(writer)
        writer.write(b'%b %b\r\n' % (self.tag, self.text))

    def __bytes__(self) -> bytes:
        if self._raw is None:
            out = BytesIO()
            self.write(out)
            self._raw = out.getvalue()
        return self._raw


class ResponseContinuation(Response):
    """Class used for server responses that indicate a continuation
    requirement. This is when the server needs more data from the client to
    finish handling the command. The ``AUTHENTICATE`` command and any command
    that uses a literal string argument will send this response as needed.

    Args:
        text: The continuation text.

    """

    def __init__(self, text: MaybeBytes) -> None:
        super().__init__(b'+', text)


class ResponseBad(Response):
    """``BAD`` response indicating the server encountered a protocol-related
    error in responding to the command.

    Args:
        tag: The tag bytestring to associate the response to a command.
        text: The response text.
        code: Optional response code.

    """

    condition = b'BAD'

    def __init__(self, tag: MaybeBytes, text: MaybeBytes,
                 code: Optional[ResponseCode] = None) -> None:
        super().__init__(tag, text, code)

    @property
    def is_bad(self) -> bool:
        return True


class ResponseNo(Response):
    """``NO`` response indicating the server successfully parsed the command
    but failed to execute it successfully.

    Args:
        tag: The tag bytestring to associate the response to a command.
        text: The response text.
        code: Optional response code.

    """

    condition = b'NO'

    def __init__(self, tag: MaybeBytes, text: MaybeBytes,
                 code: Optional[ResponseCode] = None) -> None:
        super().__init__(tag, text, code)


class ResponseOk(Response):
    """``OK`` response indicating the server successfully parsed and executed
    the command.

    Args:
        tag: The tag bytestring to associate the response to a command.
        text: The response text.
        code: Optional response code.

    """

    condition = b'OK'

    def __init__(self, tag: MaybeBytes, text: MaybeBytes,
                 code: Optional[ResponseCode] = None) -> None:
        super().__init__(tag, text, code)


class ResponseBye(Response):
    """``BYE`` response indicating that the server will be closing the
    connection immediately after sending the response is sent. This may be sent
    in response to a command (e.g. ``LOGOUT``) or unsolicited.

    Args:
        text: The reason for disconnection.
        code: Optional response code.

    """

    condition = b'BYE'

    def __init__(self, text: MaybeBytes,
                 code: Optional[ResponseCode] = None) -> None:
        super().__init__(b'*', text, code)

    @property
    def is_terminal(self) -> bool:
        """This response is always terminal."""
        return True


class ResponsePreAuth(Response):
    """``PREAUTH`` response during server greeting to indicate the client is
    already logged in.

    Args:
        tag: The tag bytestring to associate the response to a command.
        text: The response text.
        code: Optional response code.

    """

    condition = b'PREAUTH'

    def __init__(self, tag: MaybeBytes, text: MaybeBytes,
                 code: Optional[ResponseCode] = None) -> None:
        super().__init__(tag, text, code)
