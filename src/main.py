import logging
import os

from anytree import Node
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonCommands
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([('start', 'Starts the bot')])


application = ApplicationBuilder().token(os.getenv('BOT_TOKEN')).post_init(post_init).build()

START, ADD = range(2)
START_OVER, WAITING, BROWSING = range(42, 42 + 3)
DIRS: dict = {
    'Recipies': {'Soups': {}, 'Sweets': {}},
    'Memes': {}
}

# DIRS = Node('root')


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Unknown command')


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = 'Should I save it?'
    # TODO: reply to msg and, if yes, start save dialog
    pass


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TODO: same as message?
    pass


async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TODO: browsing dialog with create/delete/move? dir options + stop
    return BROWSING


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.bot.set_chat_menu_button(update.effective_chat.id, menu_button=MenuButtonCommands())
    greeting = 'Welcome to LibrariannBot 📚'
    tooltip = 'start tooltip'
    buttons = [
        [
            # InlineKeyboardButton(text='Browse', callback_data=str(BROWSE)),
        ],
        [
            InlineKeyboardButton(text='Add', callback_data=str(ADD)),
            # InlineKeyboardButton(text="Done", callback_data=str(END)),
        ],
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need to send a new message
    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=tooltip, reply_markup=keyboard)
    else:
        await update.message.reply_text(greeting)
        await update.message.reply_text(text=tooltip, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return WAITING


def main() -> None:
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING: [
                CommandHandler('browse', browse),
                MessageHandler(filters=~filters.COMMAND, callback=message),  # Should be in fallbacks?
            ],
            BROWSING: [
                MessageHandler(filters=filters.Regex(f"^({'|'.join(DIRS.keys())})$"), callback=browse),
            ]
        },
        fallbacks=[
            CommandHandler('stop', stop)
        ]
    )
    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.COMMAND, unknown))  # TODO: help
    application.run_polling()


if __name__ == '__main__':
    main()
