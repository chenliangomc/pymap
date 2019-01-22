
from abc import abstractmethod
from typing import Union, Sequence, Mapping
from typing_extensions import Protocol

from pymap.interfaces.message import AppendMessage

__all__ = ['FilterInterface', 'FilterActionInterface', 'FilterActionArg']

FilterActionArg = Union[bool, str, Sequence[str]]


class FilterInterface(Protocol):
    """Protocol defining the interface for message filters. Filters apply to
    all mailboxes for a login and allow various actions to be taken to messages
    that meet custom criteria. The actions include choosing a mailbox,
    discarding, or forwarding.

    """

    @abstractmethod
    def apply(self, append_msg: AppendMessage) \
            -> Sequence['FilterActionInterface']:
        """

        Args:
            append_msg: The message to be appended.

        """
        ...


class FilterActionInterface(Protocol):
    """An action taken on the message."""

    @property
    def name(self) -> str:
        """The action name."""
        ...

    @property
    def arguments(self) -> Mapping[str, FilterActionArg]:
        """The action arguments."""
        ...
