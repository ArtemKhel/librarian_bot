from typing import List, Union

from telegram import InlineKeyboardButton
from telegram.ext import CommandHandler


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
        footer_buttons: Union[InlineKeyboardButton, List[InlineKeyboardButton]] = None
) -> List[List[InlineKeyboardButton]]:
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons if isinstance(header_buttons, list) else [header_buttons])
    if footer_buttons:
        menu.append(footer_buttons if isinstance(footer_buttons, list) else [footer_buttons])
    return menu
