# from enum import Enum
import enum

from anytree import Node
from telegram import Message

START, ADD = range(2)


class State(enum.Enum):
    WAITING, MKDIR, RM, SAVE = range(100, 100 + 4)


class Directory(Node):
    def __init__(self, name, parent=None, children=None):
        super().__init__(name, parent, children)


class SavedMessage(Node):
    def __init__(self, name, parent, data: Message, children=None):
        super().__init__(name, parent, children)
        self.data = data
