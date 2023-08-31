from typing import List, Union

import anytree
from anytree import Resolver
from telegram import InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes

from src.bot_types import *

resolver = Resolver()


def chunks(lst, n=2):
    return list(lst[i : i + n] for i in range(0, len(lst), n))


def cd(context: ContextTypes.DEFAULT_TYPE, dir_: str) -> bool:
    pwd: Node = context.user_data["PWD"]
    try:
        dir_: Node = resolver.get(pwd, dir_)
        if dir_ is None:
            return False
        context.user_data["PWD"] = dir_
        return True
    except anytree.ChildResolverError:
        return False


def mkdir(context: ContextTypes.DEFAULT_TYPE, dir_: str) -> bool:
    pwd: Node = context.user_data["PWD"]
    try:
        dir_: Node = resolver.get(pwd, dir_)
        return False
    except anytree.ChildResolverError:
        Directory(dir_, parent=pwd)
        return True


def rm(context: ContextTypes.DEFAULT_TYPE, dir_: str) -> bool:
    pwd: Node = context.user_data["PWD"]
    try:
        dir_: Node = resolver.get(pwd, dir_)
        if dir_ is None:
            return False
        dir_.parent = None
        del dir_  # TODO: del?
        return True
    except anytree.ChildResolverError:
        return False


def contains(context: ContextTypes.DEFAULT_TYPE, name: str) -> bool:
    pwd: Node = context.user_data["PWD"]
    try:
        name: Node = resolver.get(pwd, name)
        if name is None:
            return False
        return True
    except anytree.ChildResolverError:
        return False


def command_handler(application, command):
    def decorator(func):
        handler = CommandHandler(command, func)
        application.add_handler(handler)
        return func

    return decorator


def build_menu(
    buttons: List[InlineKeyboardButton],
    n_cols: int = 1,
    header_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]] = None,
    footer_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]] = None,
) -> List[List[InlineKeyboardButton]]:
    menu = [buttons[i : i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])
    return menu
