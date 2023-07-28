import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler, \
    CallbackQueryHandler, ConversationHandler

import src.utils as utils
from src.utils import command_handler

# from src.reference import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([('start', 'Starts the bot')])


application = ApplicationBuilder().token(os.getenv('BOT_TOKEN')).post_init(post_init).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Saved")


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Got ${update.message}")
    context.user_data['last'] = update.message


async def last(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'last' in context.user_data:
        await context.user_data['last'].forward(update.effective_chat.id)
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="No last message"
    )
    # msg = f"""{sp.run(['json_pp'], input=f'"{context.user_data["last"]}"', capture_output=True, text=True).stdout}"""


@command_handler(application, "menu")
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # custom_keyboard = [['top-left', 'top-right'],
    #                    ['bottom-left', 'bottom-right']]
    # reply_markup = ReplyKeyboardMarkup(custom_keyboard)
    # await context.bot.send_message(
    #     chat_id=update.effective_chat.id,
    #     text="Custom Keyboard Test",
    #     reply_markup=reply_markup
    # )
    button_list = [
        InlineKeyboardButton("col1", callback_data="col1"),
        InlineKeyboardButton("col2", callback_data="col2"),
        InlineKeyboardButton("row2", callback_data="row2")
    ]
    reply_markup = InlineKeyboardMarkup(utils.build_menu(button_list, n_cols=2))
    await context.bot.send_message(
        update.effective_chat.id,
        "A two-column menu",
        reply_markup=reply_markup
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    await query.edit_message_text(text=f"Selected option: {query.data}")


START, NAV = range(2)
DIRS: dict = {
    'Recipies': {'Soups': {}, 'Sweets': {}},
    'Memes': {}
}


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


async def nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("nav()")
    reply_keyboard = [list(DIRS.keys())]
    await update.message.reply_text(
        'Select dir or type `/exit`',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            input_field_placeholder='Dir name'
        )
    )

    # await update.message.reply_text(
    #     "nav()",
    #     reply_markup=ReplyKeyboardMarkup(
    #         reply_keyboard, one_time_keyboard=True, input_field_placeholder="Dirs"
    #     ),
    # )

    return NAV


async def exit_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END

async def exit_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END

def main() -> None:
    start_handler = CommandHandler('start', start)
    application.add_handler(CallbackQueryHandler(button))
    last_handler = CommandHandler('last', last)
    message_handler = MessageHandler(~filters.COMMAND, message)
    unknown_handler = MessageHandler(filters.COMMAND, unknown)

    application.add_handler(start_handler)
    application.add_handler(last_handler)
    application.add_handler(message_handler)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nav', nav)],
        states={
            NAV: [
                MessageHandler(filters=filters.Regex(f"^({'|'.join(DIRS.keys())})$"), callback=nav)
                # CommandHandler('new', new_dir)
            ]
        },
        fallbacks=[CommandHandler('exit', exit_nav)]
    )
    application.add_handler(conv_handler)

    application.add_handler(unknown_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
