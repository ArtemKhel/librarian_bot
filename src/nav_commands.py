import anytree
from anytree import Node, Resolver, RenderTree
from telegram import Update
from telegram.ext import ContextTypes

from src.main import WAITING


async def cd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pwd: Node = context.user_data['PWD']
    resolver = Resolver()

    try:
        dir_: Node = resolver.get(pwd, '/'.join(context.args))
        if dir_ is None:
            raise anytree.ChildResolverError
        context.user_data['PWD'] = dir_
        return WAITING  # True
    except anytree.ChildResolverError as e:
        await update.message.reply_text(text=e.args[0])
        return WAITING  # False


async def mkdir(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if len(context.args) != 1:
        await update.message.reply_text(text="Expected directory name")
        return WAITING  # False
    name = context.args[0]
    pwd: Node = context.user_data['PWD']
    if anytree.find(pwd, filter_=lambda x: x.name == name, maxlevel=1):
        await update.message.reply_text(text="Directory already exists")
        return WAITING  # False
    else:
        Node(name, parent=pwd, type='DIR')
        return WAITING  # True


async def pwd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(text='/' + '/'.join(map(lambda x: x.name, context.user_data['PWD'].path)))
    return WAITING


async def ls(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(text=str(RenderTree(context.user_data['PWD'], maxlevel=2)))
    return WAITING