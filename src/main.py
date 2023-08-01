import logging
import os

from telegram import MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters, CallbackQueryHandler)

from nav_commands import *
from src.utils import _cd, chunks, _mkdir

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands(
        [
            ('start', 'Starts the bot'),
            ('kb', 'kb'),
            # ('pwd', 'Get current directory'),
            # ('cd', 'Go to directory'),
            # ('ls', 'List directory content'),
            # ('mkdir', 'Create the directory')
        ]
    )


application = ApplicationBuilder().token(os.getenv('BOT_TOKEN')).post_init(post_init).build()

START, ADD = range(2)
WAITING, MKDIR = range(42, 42 + 2)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Unknown command')


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # .append(update.message)
    queue: list = context.user_data['QUEUE']
    queue.append(update.message)
    return await keyboard(update, context)

    # msg: Message
    # for msg in queue:
    #     await msg.reply_text('reply', reply_to_message_id=msg.id)
    # await msg.forward(update.effective_chat.id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.set_chat_menu_button(update.effective_chat.id, menu_button=MenuButtonCommands())
    greeting = 'Welcome to LibrariannBot 📚'
    tooltip = 'start tooltip'
    if not context.user_data.get('INIT'):
        context.user_data['INIT'] = True
        root = Node('root', type='DIR')
        context.user_data['PWD'] = root
        context.user_data['QUEUE'] = []

        one = Node('one', parent=root, type='DIR')
        two = Node('two', parent=root, type='DIR')
        three = Node('three', parent=root, type='DIR')
        one_one = Node('one_one', parent=one, type='DIR')
        one_one_one = Node('one_one_one', parent=one_one, type='DIR')
        one_two = Node('one_two', parent=one, type='DIR')
        two_one = Node('two_one', parent=two, type='DIR')

    await update.message.reply_markdown_v2(text=f'*{greeting}*\n_{tooltip}_')
    return WAITING


def make_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    buttons = (
            [
                [] if not len(context.user_data['QUEUE']) else [
                    InlineKeyboardButton(text='save', callback_data='/save'),
                    InlineKeyboardButton(text='skip', callback_data='/skip')
                ]
            ]
            + [
                [
                    InlineKeyboardButton(text='list', callback_data='/ls'),
                    InlineKeyboardButton(text='create', callback_data='/mkdir'),
                    InlineKeyboardButton(text='move', callback_data='/mv'),
                    InlineKeyboardButton(text='remove', callback_data='/rm')
                ],
                [
                    InlineKeyboardButton(text='..', callback_data='..')
                ]
            ] +
            chunks(list(
                InlineKeyboardButton(
                    text=x.name,
                    callback_data=x.name
                ) for x in filter(lambda x: x.type == "DATA", context.user_data['PWD'].children))))

    # kb = ReplyKeyboardMarkup(buttons)
    kb = InlineKeyboardMarkup(buttons)
    return kb


async def keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    queue = context.user_data['QUEUE']
    head_id = queue[-1].id if len(queue) else None
    await update.message.reply_text(  # TODO: store and delete old kb when new one is created?
        text=f"Current dir: {context.user_data['PWD'].name}",
        reply_markup=make_keyboard(context),
        reply_to_message_id=head_id
    )
    return WAITING


async def keyboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data.startswith('/'):
        return await cmd(update, context)

    if _cd(context, query.data):
        queue = context.user_data['QUEUE']
        head: Message = queue[-1] if len(queue) else None
        pwd: Node = context.user_data['PWD']
        await query.edit_message_text(
            text=f"""
            Current dir: {pwd.name}
            Content:
            {os.linesep.join(map(lambda x: x.name, filter(lambda x: x.type == 'DATA', pwd.children)))}""",
            reply_markup=make_keyboard(context),
        )
    return WAITING


async def cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query.data == '/mkdir':
        await query.edit_message_text(text=f'What should it be called?')
        return MKDIR

    elif query.data == '/save':
        pwd: Node = context.user_data['PWD']
        Node('some data', parent=pwd, type='DATA', data=context.user_data['QUEUE'].pop())
        return WAITING

    elif query.data == '/skip':
        context.user_data['QUEUE'].pop()
        return WAITING

    elif query.data == '/ls':
        msg: Message
        for msg in map(lambda x: x.data, filter(lambda x: x.type == 'DATA', context.user_data['PWD'].children)):
            await msg.forward(update.effective_chat.id)
        return await keyboard(update, context)


async def create_dir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if _mkdir(context, update.message.text):
        return await keyboard(update, context)
    else:
        await update.message.reply_text(text='exist/invalid,try again')
        return MKDIR


def main() -> None:
    conv_handler = ConversationHandler(
        # entry_points=[CommandHandler('start', start())],
        entry_points=[
            CommandHandler('start', start),
        ],
        states={
            WAITING: [
                CommandHandler('kb', keyboard),
                # CommandHandler('cd', cd),
                # CommandHandler('mkdir', mkdir),
                # CommandHandler('pwd', pwd),
                # CommandHandler('ls', ls),
                CallbackQueryHandler(keyboard_callback, pattern="^.*$"),
                MessageHandler(filters=~filters.COMMAND & filters.FORWARDED, callback=message),
                # Should be in fallbacks?
            ],
            MKDIR: [
                MessageHandler(filters=filters.TEXT, callback=create_dir)
            ]
            # BROWSING: [
            #     MessageHandler(filters=filters.Regex(f"^({'|'.join(DIRS.keys())})$"), callback=browse),
            # ]
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
