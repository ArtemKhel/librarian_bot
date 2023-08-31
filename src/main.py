import logging
import os

from telegram import MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    PicklePersistence,
    ContextTypes,
)
from telegram.helpers import escape_markdown

from src.bot_types import *
from src.utils import cd, chunks, mkdir, rm, contains

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([('start', 'Start the bot'), ('kb', 'Show keyboard'), ('cancel', 'Cancel')])


# TODO: reply buttons for delete/move
# TODO: search
# TODO: show selected only
# TODO: fix albums (save only first)
# TODO: localization?

data_folder = '/lib_bot/'
xdg_data = os.environ.get('XDG_DATA_HOME', '/var/lib/')
if not os.path.exists(xdg_data + data_folder):
    os.mkdir(xdg_data + data_folder)
persistence = PicklePersistence(filepath=xdg_data + data_folder + 'persistence')
application = (
    ApplicationBuilder()
    .token(os.getenv('BOT_TOKEN'))
    .persistence(persistence=persistence)
    .post_init(post_init)
    .build()
)

LAST_KB: Message | None = None


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Unknown command')


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    await keyboard(update, context)
    return State.WAITING


async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    queue: list = context.user_data['QUEUE']
    queue.append(update.message)
    return await keyboard(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    await context.bot.set_chat_menu_button(update.effective_chat.id, menu_button=MenuButtonCommands())
    greeting = 'Welcome to LibrarianBot 📚'
    if not context.user_data.get('INIT'):
        context.user_data['INIT'] = True
        root = Directory('root')
        context.user_data['PWD'] = root
        context.user_data['QUEUE'] = []
    await update.message.reply_markdown_v2(text=f'*{greeting}*')
    await keyboard(update, context)
    return State.WAITING


def make_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    buttons = (
        [
            []
            if not len(context.user_data['QUEUE'])
            else [
                InlineKeyboardButton(text='save', callback_data='/save'),
                InlineKeyboardButton(text='save w/ name', callback_data='/save_rename'),
                InlineKeyboardButton(text='skip', callback_data='/skip'),
            ]
        ]
        + [
            [
                InlineKeyboardButton(text='list', callback_data='/ls'),
                InlineKeyboardButton(text='mkdir', callback_data='/mkdir'),
                # InlineKeyboardButton(text='move', callback_data='/mv'),
                InlineKeyboardButton(text='remove', callback_data='/rm'),
            ],
            [InlineKeyboardButton(text='..', callback_data='..')],
        ]
        + chunks(
            list(
                InlineKeyboardButton(text=x.name, callback_data=x.name)
                for x in filter(lambda x: isinstance(x, Directory), context.user_data['PWD'].children)
            )
        )
    )

    kb = InlineKeyboardMarkup(buttons)
    return kb


async def keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    global LAST_KB
    pwd: Node = context.user_data['PWD']
    queue = context.user_data['QUEUE']
    head_id = queue[-1].id if len(queue) else None
    if LAST_KB is not None:
        try:
            await LAST_KB.delete()
        except BadRequest:
            pass
    LAST_KB = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f'''
*Current dir:* {pwd.name}
*Content:*
{os.linesep.join(map(lambda x: f'• {escape_markdown(x.name,version=2)}', filter(lambda x: isinstance(x, SavedMessage), pwd.children)))}''',
        reply_markup=make_keyboard(context),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_to_message_id=head_id,
    )
    return State.WAITING


async def keyboard_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pwd: Node = context.user_data['PWD']
    try:
        await update.callback_query.edit_message_text(
            text=f'''
*Current dir:* {pwd.name}
*Content:*
{os.linesep.join(map(lambda x: f'• {escape_markdown(x.name,version=2)}', filter(lambda x: isinstance(x, SavedMessage), pwd.children)))}''',
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=make_keyboard(context),
        )
    except BadRequest:
        pass


async def keyboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    query = update.callback_query
    await query.answer()
    if query.data.startswith('/'):
        return await cmd(update, context)

    if cd(context, query.data):
        await keyboard_update(update, context)
    return State.WAITING


async def cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    query = update.callback_query
    match query.data:
        case '/mkdir':
            await query.edit_message_text(text=f'Enter a name for the new folder')
            return State.MKDIR

        case '/rm':
            await query.edit_message_text(text=f'Enter the name of the directory/post to be deleted')
            return State.RM

        case '/save':

            def gen_name(x: str, max_len: int = 50) -> str:
                return x[:max_len].rsplit(maxsplit=1)[0] + '...' if len(x) > max_len else x

            pwd: Node = context.user_data['PWD']
            msg: Message = context.user_data['QUEUE'].pop()
            name = gen_name(
                msg.caption
                if msg.caption is not None
                else msg.text
                if msg.text is not None
                else msg.date.strftime('%Y-%m-%d-%H:%M:%S')
            )
            SavedMessage(name=name, parent=pwd, data=msg)
            await keyboard(update, context)
            return State.WAITING

        case '/save_rename':
            await query.edit_message_text(text=f'Enter a name under which the post will be saved')
            return State.SAVE

        case '/skip':
            context.user_data['QUEUE'].pop()
            await keyboard_update(update, context)
            return State.WAITING

        case '/ls':
            msg: Message
            for msg_name, msg in map(
                lambda x: (x.name, x.data),
                filter(lambda x: isinstance(x, SavedMessage), context.user_data['PWD'].children),
            ):
                try:
                    await msg.forward(update.effective_chat.id)
                    await keyboard(update, context)
                except BadRequest:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id, text=f'Looks like `{msg_name}` was deleted'
                    )


async def mkdir_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    if mkdir(context, update.message.text):
        return await keyboard(update, context)
    else:
        await update.message.reply_text(text='Already exist/invalid')
        return State.MKDIR


async def rm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    if rm(context, update.message.text):
        return await keyboard(update, context)
    else:
        await update.message.reply_text(text='Already exist/invalid')
        return State.RM


async def save_with_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    if not contains(context, update.message.text):
        pwd: Node = context.user_data['PWD']
        msg: Message = context.user_data['QUEUE'].pop()
        SavedMessage(name=update.message.text, parent=pwd, data=msg)
        return await keyboard(update, context)
    else:
        await update.message.reply_text(text='Already exist/invalid')
        return State.SAVE


def main() -> None:
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
        ],
        states={
            State.WAITING: [
                CommandHandler('kb', keyboard),
                CallbackQueryHandler(keyboard_callback, pattern='^.*$'),
                MessageHandler(filters=~filters.COMMAND & filters.FORWARDED, callback=message),
            ],
            State.MKDIR: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=mkdir_handler)],
            State.RM: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=rm_handler)],
            State.SAVE: [MessageHandler(filters=filters.TEXT & ~filters.COMMAND, callback=save_with_name_handler)],
        },
        fallbacks=[
            CommandHandler('stop', stop),
            CommandHandler('cancel', cancel)
        ],
    )
    application.add_handler(conv_handler)

    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    application.run_polling()


if __name__ == '__main__':
    main()
