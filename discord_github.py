"""Python code for discord link storage bot"""
import csv
import datetime
import difflib
# IMPORT DISCORD.PY. ALLOWS ACCESS TO DISCORD'S API.
import io
import math
# IMPORT THE OS MODULE.
import os
import random
import string
from io import BytesIO
from operator import itemgetter
from typing import Union

import boto3
import cv2
import discord
import emoji as emo
import imagehash
import PIL
import pytesseract
import requests
from discord.ext import commands
from discord.ui import Button, Select, View
# IMPORT LOAD_DOTENV FUNCTION FROM DOTENV MODULE.
from dotenv import load_dotenv
from PIL import Image, ImageOps
from PIL.Image import Resampling
from pytesseract import Output
from quart import Quart

# import pandas as pd
# import plotly.express as px

# LOADS THE .ENV FILE THAT RESIDES ON THE SAME LEVEL AS THE SCRIPT.
load_dotenv()

# GRAB THE API TOKEN FROM THE .ENV FILE.
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TESTING_GUILD_ID = os.getenv("TESTING_GUILD_ID")

# GETS THE BOT OBJECT FROM DISCORD.PY.
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

testing = False

app = Quart(__name__)


class FlaskBot(commands.Bot):
    async def setup_hook(self):
        self.loop.create_task(app.run_task(port=8080))


class Ctx:
    """Ctx class to simulate in-built ctx object in discord.py"""

    def __init__(self, guild_id: int, channel_id: int, author=None, message=None):
        self.guild = bot.get_guild(guild_id)
        self.channel = self.guild.get_channel(channel_id)
        self.author = author
        self.message = message

    async def send(self, message=None, embed=None, file=None, view=None):
        return await self.channel.send(message, embed=embed, file=file, view=view)


# bot = FlaskBot(command_prefix="$", intents=intents)
bot = commands.Bot(command_prefix="$", intents=intents)


@app.route('/<guild>/<channel>/<keyword>')
async def get_media_request(guild, channel, keyword):
    ctx = Ctx(int(guild), int(channel))
    bot.loop.create_task(get(ctx, keyword))
    # return f'Sent media "{keyword}" in Discord!'
    return "<script>window.onload = window.close();</script>"

# EVENT LISTENER FOR WHEN THE BOT HAS SWITCHED FROM OFFLINE TO ONLINE.
@bot.event
async def on_ready() -> None:
    """Execute when bot is ready"""
    # CREATES A COUNTER TO KEEP TRACK OF HOW MANY GUILDS / SERVERS THE BOT IS CONNECTED TO.
    guild_count = 0

    # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
    for guild in bot.guilds:
        if (guild.id == TESTING_GUILD_ID) == testing:
            # PRINT THE SERVER'S ID AND NAME.
            print(f"- {guild.id} (name: {guild.name})")
            # INCREMENTS THE GUILD COUNTER.
            guild_count = guild_count + 1

    # PRINTS HOW MANY GUILDS / SERVERS THE BOT IS IN.
    print(f"{bot.user.name} is in " + str(guild_count) + " guilds.")
    wait_until_ready()


def wait_until_ready():
    existing_tables = dynamodb.tables.all()
    for guild in bot.guilds:
        if (guild.id == TESTING_GUILD_ID) == testing:
            # creates table
            initialize_tables(guild, existing_tables)
            print(f'Initialized tables for {guild.name}')
            prev_messages['cat'][guild.id] = None
            prev_messages['key'][guild.id] = None
            prev_messages['search'][guild.id] = None
            prev_messages['like'][guild.id] = None
            prev_messages['top'][guild.id] = None
            prev_messages['memes'][guild.id] = None
            last_key[guild.id] = None
            # initialize key and emoji lists
            initialize_key_list(guild)
            initialize_emoji_dict(guild)
            # update and sort categories dict
            initialize_categories(guild)
    print('Done')


def initialize_key_list(guild) -> None:
    """Initializes key list"""
    scanned_items = media_tables[guild.id].scan()['Items']
    key_dates = []
    no_dates = []

    # sort items by date from most recent to oldest
    for key in scanned_items:
        if 'time_added' in key:
            key_dates.append((datetime.datetime.strptime(key['time_added'], '%m/%d/%Y, %H:%M:%S'), key))
        else:
            no_dates.append(key)
    key_dates.sort(key=itemgetter(0))
    scanned_items = no_dates + [key_date[1] for key_date in key_dates]
    global_key_dict[guild.id] = {}
    global_key_list[guild.id] = []
    i = 0
    for item in scanned_items:
        if 'category' in item:
            category = item['category']
        else:
            category = ''
        if 'time_added' in item:
            time_added = item['time_added']
        else:
            time_added = ''
        if 'image_hash' in item:
            image_hash = item['image_hash']
        else:
            image_hash = ''

        global_key_list[guild.id].append(
            {'keyword': item['keyword'],
             'description': item['description'],
             'author': item['author'],
             'category': category,
             'text_guess': item['text_guess'],
             'image_hash': image_hash,
             'link': item['link'],
             'likes': item['likes'],
             'time_added': time_added,
             'file_content': ''}
        )
        global_key_dict[guild.id][item['keyword']] = i
        i += 1


def initialize_emoji_dict(guild) -> None:
    """Initializes emoji set"""
    emoji_dict = {}
    scanned_items = likes_tables[guild.id].scan()['Items']
    for item in scanned_items:
        if 'emoji' in item:
            emoji_dict[item['user']] = item['emoji']
        elif 'pfp_emoji' in item:
            emoji_dict[item['user']] = item['pfp_emoji']

    emojis[guild.id] = emoji_dict


def initialize_tables(guild, existing_tables) -> None:
    """Initializes tables"""
    table_name = f'media_table_{guild.id}'
    if dynamodb.Table(table_name) in existing_tables:
        media_tables[guild.id] = dynamodb.Table(table_name)
    else:
        media_tables[guild.id] = create_table(table_name, 'keyword', 'S', dynamodb)

    category_table_name = f'media_table_{guild.id}_cat'
    if dynamodb.Table(category_table_name) in existing_tables:
        cat_tables[guild.id] = dynamodb.Table(category_table_name)
    else:
        cat_tables[guild.id] = create_table(category_table_name, 'category', 'S', dynamodb)

    likes_table_name = f'media_table_{guild.id}_likes'
    if dynamodb.Table(likes_table_name) in existing_tables:
        likes_tables[guild.id] = dynamodb.Table(likes_table_name)
    else:
        likes_tables[guild.id] = create_table(likes_table_name, 'user', 'N', dynamodb)


def initialize_categories(guild) -> None:
    """Initialize categories dict"""
    cat_table = cat_tables[guild.id]
    scanned_items = cat_table.scan()['Items']
    cat_dates = []
    no_dates = []
    for cat in scanned_items:
        if 'time_added' in cat:
            cat_dates.append((datetime.datetime.strptime(cat['time_added'], '%m/%d/%Y, %H:%M:%S'), cat))
        else:
            no_dates.append(cat)
    cat_dates.sort(key=itemgetter(0))
    temp_list = (no_dates + [cat_date[1] for cat_date in cat_dates])
    categories[guild.id] = [item['category'] for item in temp_list]


# EVENT LISTENER FOR WHEN A NEW MESSAGE IS SENT TO A CHANNEL.
@bot.event
async def on_message(message) -> None:
    """Execute when message is sent"""
    if (message.guild.id == TESTING_GUILD_ID) == testing:
        await bot.process_commands(message)
        if message.author.id in messages:
            if (datetime.datetime.now() - messages[message.author.id][0]) > datetime.timedelta(minutes=60):
                messages[message.author.id] = (datetime.datetime.now(), messages[message.author.id][1])
                if not message.content.startswith("$") and not message.content.lower() in {'y', 'n'}:
                    await message.channel.send(random.choice(messages[message.author.id][1]))
                    response = likes_tables[message.guild.id].get_item(
                        Key={
                            'user': message.author.id
                        }
                    )
                    if 'Item' in response and 'liked_items' in response['Item'] and not message.content.startswith(
                            'https://') and message.attachments == []:
                        response = likes_tables[message.guild.id].get_item(
                            Key={
                                'user': message.author.id
                            }
                        )
                        blacklist = set()
                        if 'Item' in response and 'blacklist' in response['Item']:
                            blacklist = set(response['Item']['blacklist'])
                        liked_keys = [key for key in response['Item']['liked_items'] if
                                      keyword_to_item(message.guild, key)['category'] not in blacklist]
                        rand_int = random.randint(0, len(liked_keys) - 1)
                        rand_key = liked_keys[rand_int]
                        response2 = {'Item': keyword_to_item(message.guild, rand_key)}
                        await send_media(message.channel, response2, False, liked_keys, rand_int)
            else:
                messages[message.author.id] = (datetime.datetime.now(), messages[message.author.id][1])


def keyword_to_item(guild, keyword) -> dict:
    return global_key_list[guild.id][global_key_dict[guild.id][keyword]]


@bot.command(brief='Send embed ranking members by number of items added.',
             description='Send embed ranking members by number of items added.')
async def rank(ctx) -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        member_ranking = {}
        for item in global_key_list[ctx.guild.id]:
            if 'author' in item:
                if item['author'] in member_ranking:
                    member_ranking[item['author']] += 1
                else:
                    member_ranking[item['author']] = 1
        i = 1
        members_sorted = [(key, member_ranking[key]) for key in member_ranking]
        members_sorted.sort(key=lambda elem: elem[1], reverse=True)
        member_list = []

        for member in members_sorted:
            key_string = ''
            author_user = discord.utils.get(ctx.guild.members, name=member[0])
            user_emoji = await get_user_emoji(ctx, author_user)
            key_string += user_emoji + '\u200b ' * 2
            key_string += f'`{i}.` **' + member[0] + '**' + '\u200B \u200b \u200b ⎯ \u200B \u200b \u200b' + str(
                member[1])
            member_list.append(key_string)
            i += 1

        pages = []
        size = 20
        num_pages = math.ceil(len(member_list) / size)
        for i in range(num_pages):
            if i == num_pages - 1:
                end = len(member_list)
            else:
                end = (i + 1) * size
            page = discord.Embed(
                title=f'Member ranking - {len(global_key_list[ctx.guild.id])} items',
                description='\n'.join(member_list[i * size:end]),
                colour=discord.Colour.purple()
            )
            pages.append(page)

        if len(pages) > 0:
            message = await ctx.send(embed=pages[0])
            await create_embed(ctx, num_pages, message, pages, [])
        else:
            await ctx.send('No keys added by members')


@bot.command(brief='Add specified keyword to user\'s list of liked items.',
             description='Add specified keyword to user\'s list of liked items.')
async def like(ctx, keyword: str) -> None:
    """Add specified keyword to user's list of liked items"""
    await like_helper(ctx, keyword, ctx.author)


async def like_helper(ctx, keyword, author) -> Union[set, int]:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        table = media_tables[ctx.guild.id]
        likes_table = likes_tables[ctx.guild.id]
        response = table.get_item(
            Key={
                'keyword': keyword
            }
        )
        if 'Item' in response:  # if the keyword exists in the database
            if response['Item']['likes'] == 0 or response['Item'][
                'likes'] is None:  # if the item has no likes then add user's name to like set
                new_likes = {author.name}
                table.update_item(
                    Key={
                        'keyword': keyword
                    },
                    UpdateExpression='SET likes = :val1',
                    ExpressionAttributeValues={
                        ':val1': new_likes
                    }
                )
            else:
                if author.name in response['Item'][
                    'likes']:  # if the item is liked by user then return (initialize user liked list if not already created)
                    add_to_liked_table(likes_table, keyword, author)
                    await ctx.send(f"{response['Item']['keyword']} is already liked by {author.name}")
                    return response['Item']['likes']
                else:  # if the item is not liked by user then add user's name to liked set
                    new_likes = response['Item']['likes']
                    new_likes.add(author.name)
                    table.update_item(
                        Key={
                            'keyword': keyword
                        },
                        UpdateExpression='SET likes = :val1',
                        ExpressionAttributeValues={
                            ':val1': new_likes
                        }
                    )
            add_to_liked_table(likes_table, keyword, author)
            await ctx.send(f"{response['Item']['keyword']} liked by {author.name}!")
        else:
            await ctx.send('Keyword not in database')
            new_likes = 0
        original_item = keyword_to_item(ctx.guild, keyword)
        original_item['likes'] = new_likes
        return new_likes


@bot.command(brief='Remove specified keyword from user\'s list of liked items.',
             description='Remove specified keyword from user\'s list of liked items.')
async def unlike(ctx, keyword: str) -> None:
    """Remove specified keyword from user's list of liked items"""
    await unlike_helper(ctx, keyword, ctx.author)


async def unlike_helper(ctx, keyword, author) -> Union[set, int]:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        table = media_tables[ctx.guild.id]
        likes_table = likes_tables[ctx.guild.id]
        response = table.get_item(
            Key={
                'keyword': keyword
            }
        )
        if 'Item' in response:  # if the keyword exists in the database
            if isinstance(response['Item']['likes'], set) and author.name in response['Item']['likes']:
                new_likes = response['Item']['likes']
                new_likes.remove(author.name)
                if len(new_likes) == 0:
                    new_likes = 0
                table.update_item(
                    Key={
                        'keyword': keyword
                    },
                    UpdateExpression='SET likes = :val1',
                    ExpressionAttributeValues={
                        ':val1': new_likes
                    }
                )
                remove_from_liked_table(likes_table, keyword, author)
                await ctx.send(f"{response['Item']['keyword']} unliked by {author.name}!")
            else:
                await ctx.send(f"{response['Item']['keyword']} not liked by {author.name}")
                new_likes = response['Item']['likes']
        else:
            await ctx.send('Keyword not in database')
            new_likes = 0
        original_item = keyword_to_item(ctx.guild, keyword)
        original_item['likes'] = new_likes
        return new_likes


def add_to_liked_table(likes_table, keyword, member) -> None:
    """Add keyword to user's list of liked items"""
    response2 = likes_table.get_item(
        Key={
            'user': member.id
        }
    )
    if 'Item' in response2:
        if 'liked_items' in response2['Item']:
            like_list = response2['Item']['liked_items']
        else:
            like_list = []
        if keyword not in like_list:
            like_list.append(keyword)
        likes_table.update_item(
            Key={
                'user': member.id
            },
            UpdateExpression='SET liked_items = :val1',
            ExpressionAttributeValues={
                ':val1': like_list
            }
        )
    else:
        likes_table.put_item(
            Item={
                'user': member.id,
                'liked_items': [keyword]
            }
        )


def remove_from_liked_table(likes_table, keyword, member) -> None:
    """Remove keyword from user's list of liked items"""
    response2 = likes_table.get_item(
        Key={
            'user': member.id
        }
    )
    if 'Item' in response2:
        if 'liked_items' in response2['Item']:
            like_list = response2['Item']['liked_items']
        else:
            like_list = []
        if keyword in like_list:
            like_list.remove(keyword)
        likes_table.update_item(
            Key={
                'user': member.id
            },
            UpdateExpression='SET liked_items = :val1',
            ExpressionAttributeValues={
                ':val1': like_list
            }
        )
    else:
        likes_table.put_item(
            Item={
                'user': member.id,
                'liked_items': []
            }
        )


@bot.command(brief="Send embed containing list of memes added by specified user.",
             description="Send embed containing list of memes added by specified user. Either type user's name or @.")
async def memes(ctx, user: str) -> None:
    """Sends an embed displaying list of memes added by user"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if prev_messages['memes'][ctx.guild.id] is not None:
            for item in prev_messages['memes'][ctx.guild.id]:
                if item:
                    await item.delete()
            prev_messages['memes'][ctx.guild.id] = None

        if '@' in user:
            user = user.strip('<>@')
            member = bot.get_user(int(user))
        else:
            member = discord.utils.get(ctx.guild.members, name=user)

        if member is None:
            await ctx.send('User not in the server.')
            return
        scanned_items = [item for item in global_key_list[ctx.guild.id] if item['author'] == member.name]
        key_list = await make_key_list(ctx, scanned_items, True)

        pages = []
        size = 20
        num_pages = math.ceil(len(key_list) / size)
        for i in range(num_pages):
            if i == num_pages - 1:
                end = len(key_list)
            else:
                end = (i + 1) * size
            if num_pages > 1:
                title = f'Memes added by {member.name} (Page {i + 1}/{num_pages}) - {len(key_list)} items'
            else:
                title = f'Memes added by {member.name} - {len(key_list)} items'
            page = discord.Embed(
                title=title,
                description='\n'.join(key_list[i * size:end]),
                colour=discord.Colour.magenta()
            )
            pages.append(page)

        if len(pages) > 0:
            message = await ctx.send(embed=pages[0])
            view_message = await create_embed(ctx, num_pages, message, pages, [scanned_items[i]['keyword'] for i in range(len(scanned_items) - 1, -1, -1)])
            prev_messages['memes'][ctx.guild.id] = [message, view_message]
        else:
            await ctx.send('No keys present')


@bot.command(brief="Sends embed displaying list of user's liked memes.",
             description="Sends embed displaying list of user's liked memes.")
async def myliked(ctx) -> None:
    """Sends an embed displaying list of user's liked memes"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if prev_messages['like'][ctx.guild.id] is not None and prev_messages['like'][ctx.guild.id][-1] == ctx.author.id:
            try:
                for item in prev_messages['like'][ctx.guild.id]:
                    if item and not isinstance(item, int):
                        await item.delete()
            except:
                pass
            prev_messages['like'][ctx.guild.id] = None

        user_liked = likes_tables[ctx.guild.id].get_item(
            Key={
                'user': ctx.author.id
            }
        )
        # sort items by date from most recent to oldest
        if 'Item' in user_liked:
            liked_list = user_liked['Item']['liked_items']
            # scanned_items = media_tables[ctx.guild.id].scan(ProjectionExpression='author, keyword, category, description')['Items']
            scanned_items = [item for item in global_key_list[ctx.guild.id] if item['keyword'] in liked_list]
            sorted_keys = [{}] * len(scanned_items)
            for item in scanned_items:
                sorted_keys[liked_list.index(item['keyword'])] = item

            key_list = await make_key_list(ctx, sorted_keys, True)

            pages = []
            size = 20
            num_pages = math.ceil(len(key_list) / size)
            for i in range(num_pages):
                if i == num_pages - 1:
                    end = len(key_list)
                else:
                    end = (i + 1) * size
                if num_pages > 1:
                    title = f'{ctx.author.name}\'s liked keys (Page {i + 1}/{num_pages})'
                else:
                    title = f'{ctx.author.name}\'s liked keys'
                page = discord.Embed(
                    title=title,
                    description='\n'.join(key_list[i * size:end]),
                    colour=discord.Colour.red()
                )
                pages.append(page)

            if len(pages) > 0:
                message = await ctx.send(embed=pages[0])
                view_message = await create_embed(ctx, num_pages, message, pages, [sorted_keys[i]['keyword'] for i in range(len(sorted_keys) - 1, -1, -1)])
                prev_messages['like'][ctx.guild.id] = [message, view_message, ctx.author.id]
            else:
                await ctx.send('Keys not present')
        else:
            await ctx.send('Keys not present')


@bot.command(brief='Add new category for items in database.', description='Add new category for items in database.')
async def newcat(ctx, category: str) -> None:
    """Creates new category with specified name"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if category in categories[ctx.guild.id]:
            await ctx.send(f"Category '{category}' already present")
        else:
            await ctx.send(f"Are you sure you want to create a new category '{category}'? (Y/N)")
            try:
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author, timeout=30.0)
            except:
                return
            if msg.content.lower() == 'y':
                cat_tables[ctx.guild.id].put_item(
                    Item={
                        'category': category,
                        'time_added': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                        'item_list': []
                    }
                )
                categories[ctx.guild.id].append(category)
                await ctx.send('Category added successfully!')
            else:
                await ctx.send('Category not added')


@bot.command(brief='Add item specified by keyword to a category.',
             description='Add item specified by keyword to a category. Type full name of category.')
async def cat(ctx, keyword: str, category: str = '') -> None:
    """Assigns category to item"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        table = media_tables[ctx.guild.id]
        response = table.get_item(
            Key={
                'keyword': keyword
            }
        )
        if 'Item' in response:
            if category in categories[ctx.guild.id] or category == '':
                if 'category' in response['Item']:
                    orig_category = response['Item']['category']
                else:
                    orig_category = ''

                item_index = global_key_dict[ctx.guild.id][keyword]
                global_key_list[ctx.guild.id][item_index]['category'] = category
                print(global_key_list[ctx.guild.id][item_index])
                remove_key_from_original_category(ctx, response, keyword)
                if category != '':
                    add_key_to_new_category(ctx, keyword, category)

                table.update_item(
                    Key={
                        'keyword': keyword
                    },
                    UpdateExpression='SET category = :val1',
                    ExpressionAttributeValues={
                        ':val1': category
                    }
                )
                if category == '':
                    await ctx.send(f'{keyword} removed from {orig_category}!')
                else:
                    await ctx.send(f'Category of {keyword} changed to {category}!')
            else:
                await ctx.send('Category not in database. Use the command $newcat to add a category.')
        else:
            await ctx.send('Keyword not in database')


@bot.command(brief='Add or change description of keyword.',
             description='Add or change description of keyword. Enter description after keyword.')
async def desc(ctx, keyword: str, *args) -> None:
    """Changes description of item with specified keyword"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        description = ' '.join(args)
        table = media_tables[ctx.guild.id]
        response = table.get_item(
            Key={
                'keyword': keyword
            }
        )
        if 'Item' in response:
            item_index = global_key_dict[ctx.guild.id][keyword]
            global_key_list[ctx.guild.id][item_index]['description'] = description
            table.update_item(
                Key={
                    'keyword': keyword
                },
                UpdateExpression='SET description = :val1',
                ExpressionAttributeValues={
                    ':val1': description
                }
            )
            await ctx.send('Item description changed successfully!')
            print(global_key_list[ctx.guild.id][item_index])
        else:
            await ctx.send('Keyword not in database')


@bot.command(brief='Sends embed containing list of all categories.',
             description='Sends embed containing list of all categories.')
async def allcats(ctx) -> None:
    """Sends an embed containing all of the categories in database"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if prev_messages['cat'][ctx.guild.id] is not None:
            await prev_messages['cat'][ctx.guild.id].delete()
            prev_messages['cat'][ctx.guild.id] = None

        scanned_items = categories[ctx.guild.id]
        cat_list = []
        i = 1
        for key in scanned_items:
            key_string = f'`{i}.` **' + key + '**'
            cat_list.append(key_string)
            i += 1

        pages = []
        size = 20
        num_pages = math.ceil(len(cat_list) / size)
        for i in range(num_pages):
            if i == num_pages - 1:
                end = len(cat_list)
            else:
                end = (i + 1) * size
            if num_pages > 1:
                title = f'Categories (Page {i + 1}/{num_pages})'
            else:
                title = 'Categories'
            page = discord.Embed(
                title=title,
                description='\n'.join(cat_list[i * size:end]),
                colour=discord.Colour.green()
            )
            pages.append(page)

        if len(pages) > 0:
            message = await ctx.send(embed=pages[0])
            prev_messages['cat'][ctx.guild.id] = message

            await create_embed(ctx, num_pages, message, pages, [])
        else:
            await ctx.send('No categories added yet')


async def create_embed(ctx, num_pages, message, pages, key_list, size=20):
    """Creates embed"""
    async def start_callback(inter):
        global current_page
        current_page = 0
        await message.edit(embed=pages[current_page])
        await check_active_and_update(inter)

    async def left_callback(inter):
        global current_page
        if current_page > 0:
            current_page -= 1
        await message.edit(embed=pages[current_page])
        await check_active_and_update(inter)

    async def right_callback(inter):
        global current_page
        if current_page < num_pages - 1:
            current_page += 1
        await message.edit(embed=pages[current_page])
        await check_active_and_update(inter)

    async def end_callback(inter):
        global current_page
        current_page = num_pages - 1
        await message.edit(embed=pages[current_page])
        await check_active_and_update(inter)

    async def keyword_select_callback(inter):
        await inter.response.defer()
        ctx.message = None
        if keyword_select.values[0] != 'Choose a keyword':
            await get(ctx, keyword_select.values[0])

    async def page_select_callback(inter):
        global current_page
        current_page = int(page_select.values[0]) - 1
        await message.edit(embed=pages[current_page])
        await check_active_and_update(inter)

    async def check_active_and_update(inter):
        if current_page == 0:
            start.disabled = True
            left.disabled = True
        else:
            start.disabled = False
            left.disabled = False
        if current_page == num_pages - 1:
            right.disabled = True
            end.disabled = True
        else:
            right.disabled = False
            end.disabled = False
        if inter:
            if current_page - 12 < 0:
                start_range = 0
                end_range = min(num_pages, start_range + 25)
            elif current_page + 12 > num_pages:
                end_range = num_pages
                start_range = max(0, end_range - 25)
            else:  # no overlap
                start_range = current_page - 12
                end_range = current_page + 12
            if key_list != []:
                if current_page == num_pages - 1:
                    end_key = len(key_list)
                else:
                    end_key = (current_page + 1) * size
                global keyword_select
                keyword_select.options = [discord.SelectOption(label='Choose a keyword', default=True)] + [discord.SelectOption(label=key_list[i]) for i in range(current_page * size, end_key)]
            global page_select
            page_select.options = [discord.SelectOption(label=str(i + 1), default=i == current_page) for i in
                                   range(start_range, end_range)]
            await inter.response.edit_message(view=view)

    view = View()
    global current_page
    current_page = 0
    if num_pages > 1:
        left = Button(label='❮')  # emoji='◀'
        right = Button(label='❯')  # emoji='▶'
        start = Button(label='❮❮')
        end = Button(label='❯❯')
        left.callback = left_callback
        right.callback = right_callback
        start.callback = start_callback
        end.callback = end_callback
        view.add_item(start)
        view.add_item(left)
        view.add_item(right)
        view.add_item(end)

    if key_list != []:
        if current_page == num_pages - 1:
            end_key = len(key_list)
        else:
            end_key = (current_page + 1) * size
        global keyword_select
        keyword_select = Select(
            options=[discord.SelectOption(label='Choose a keyword', default=True)] + [discord.SelectOption(label=key_list[i]) for i in range(current_page * size, end_key)])
        keyword_select.callback = keyword_select_callback
        view.add_item(keyword_select)

    if num_pages > 5:
        global page_select
        page_select = Select(
            options=[discord.SelectOption(label=str(i + 1), default=i == 0) for i in range(min(num_pages, 25))])
        page_select.callback = page_select_callback
        await check_active_and_update(None)
        view.add_item(page_select)

    try:
        view_message = await ctx.send(view=view)
        return view_message
    except:
        return

    # await message.add_reaction('⏮')
    # await message.add_reaction('◀')
    # await message.add_reaction('▶')
    # await message.add_reaction('⏭')
    #
    # i = 0
    # reaction = None
    #
    # while True:
    #     if str(reaction) == '⏮':
    #         i = 0
    #         await message.edit(embed=pages[i])
    #     elif str(reaction) == '◀':
    #         if i > 0:
    #             i -= 1
    #             await message.edit(embed=pages[i])
    #     elif str(reaction) == '▶':
    #         if i < num_pages - 1:
    #             i += 1
    #             await message.edit(embed=pages[i])
    #     elif str(reaction) == '⏭':
    #         i = num_pages - 1
    #         await message.edit(embed=pages[i])
    #
    #     try:
    #         reaction, user = await bot.wait_for('reaction_add', check=lambda reaction2, user2: user2 != bot.user and reaction2.message == message,
    #                                             timeout=30.0)
    #         await message.remove_reaction(reaction, user)
    #     except:
    #         break
    # try:
    #     await message.clear_reactions()
    # except:
    #     pass


def remove_key_from_original_category(ctx, response, keyword) -> None:
    """Removes key from category"""
    if 'category' in response['Item'] and response['Item']['category'] != '':
        response2 = cat_tables[ctx.guild.id].get_item(
            Key={
                'category': response['Item']['category']
            }
        )
        cat_list = response2['Item']['item_list']
        try:
            cat_list.remove(keyword)
        except:
            pass
        cat_tables[ctx.guild.id].update_item(
            Key={
                'category': response['Item']['category']
            },
            UpdateExpression='SET item_list = :val1',
            ExpressionAttributeValues={
                ':val1': cat_list
            }
        )


def add_key_to_new_category(ctx, keyword, category) -> None:
    """Adds key to specified category"""
    response3 = cat_tables[ctx.guild.id].get_item(
        Key={
            'category': category
        },
    )
    new_cat_list = response3['Item']['item_list']
    new_cat_list.append(keyword)
    cat_tables[ctx.guild.id].update_item(
        Key={
            'category': category
        },
        UpdateExpression='SET item_list = :val1',
        ExpressionAttributeValues={
            ':val1': new_cat_list
        }
    )


async def get_user_emoji(ctx, user) -> str:
    if user:
        if user.id in emojis[ctx.guild.id] and emojis[ctx.guild.id][user.id] != '':
            user_emoji = emojis[ctx.guild.id][user.id]
        else:
            user_emoji = (await update_user_emoji(ctx, user, False))[0]
        return user_emoji
    else:
        return ':white_large_square:'


async def update_user_emoji(ctx, user, replace=False) -> tuple:
    start = datetime.datetime.now()
    user_info = likes_tables[ctx.guild.id].get_item(
        Key={
            'user': user.id
        }
    )
    print(f'Getting item: {datetime.datetime.now() - start}')
    if 'Item' in user_info:
        if 'pfp_emoji' in user_info['Item'] and user_info['Item']['pfp_emoji'] != '':
            if replace:
                old_emoji = bot.get_emoji(int(user_info['Item']['pfp_emoji'][3 + len(user.name): -1]))
                if old_emoji is not None:
                    await old_emoji.delete()
            else:
                return user_info['Item']['pfp_emoji'], user_info['Item']
        else:
            print('Pfp emoji not present')
        response = requests.get(user.avatar.url, stream=True)
        user_emoji = ''
        try:
            user_emoji = await ctx.guild.create_custom_emoji(name=user.name, image=response.content)
        except:
            await ctx.send('Unsupported image or custom emojis full')
        print(f'Creating emoji time: {datetime.datetime.now() - start}')
        likes_tables[ctx.guild.id].update_item(
            Key={
                'user': user.id
            },
            UpdateExpression='SET pfp_emoji = :val1',
            ExpressionAttributeValues={
                ':val1': str(user_emoji)
            }
        )
        if 'emoji' not in user_info['Item']:
            emojis[ctx.guild.id][user.id] = str(user_emoji)
    else:
        response = requests.get(user.avatar.url, stream=True)
        start2 = datetime.datetime.now()
        try:
            user_emoji = await ctx.guild.create_custom_emoji(name=user.name, image=response.content)
        except:
            await ctx.send('Unsupported image or custom emojis full')
            return '', user_info['Item']
        print(f'Creating emoji time: {datetime.datetime.now() - start2}')
        likes_tables[ctx.guild.id].put_item(
            Item={
                'user': user.id,
                'pfp_emoji': str(user_emoji)
            },
        )
        emojis[ctx.guild.id][user.id] = str(user_emoji)
    print(f'Update pfp emoji time: {datetime.datetime.now() - start}')
    return str(user_emoji), user_info['Item']


@bot.command(brief="Sets user's emoji to emoji or reports current emoji.",
             description="Sets user's emoji to an emoji if specified or reports current emoji. Remove current emoji by typing _ after command.")
async def emoji(ctx, input_emoji='') -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        user_emoji, user_info = await update_user_emoji(ctx, ctx.author, True)
        if input_emoji == '_':
            start_time = datetime.datetime.now()
            likes_tables[ctx.guild.id].update_item(
                Key={
                    'user': ctx.author.id
                },
                UpdateExpression='REMOVE emoji',
            )
            print(f'Remove emoji time: {datetime.datetime.now() - start_time}')
            await ctx.send(f'Emoji removed for {ctx.author.name}!')
            emojis[ctx.guild.id][ctx.author.id] = user_emoji
        elif input_emoji == '':
            if ctx.message.attachments == []:
                if 'emoji' in user_info:
                    await ctx.send(f'{ctx.author.name} has emoji {user_info["emoji"]}')
                else:
                    print('User info: ' + str(user_info))
                    await ctx.send(f'{ctx.author.name} has no emoji set.')
                    emojis[ctx.guild.id][ctx.author.id] = user_emoji
            else:
                start = datetime.datetime.now()
                response = requests.get(ctx.message.attachments[0].url, stream=True)
                if len(response.content) > 256000:
                    img = Image.open(BytesIO(response.content)).convert('RGB')
                    if img.size[0] > img.size[1]:
                        basewidth = 100
                    else:
                        basewidth = int(img.size[0] / img.size[1] * 100)
                    wpercent = (basewidth / float(img.size[0]))
                    hsize = int((float(img.size[1]) * float(wpercent)))
                    print(img.size[0], img.size[1])
                    img = img.resize((basewidth, hsize), Resampling.LANCZOS)
                    print(img.size[0], img.size[1])
                    print(f'Resize time: {datetime.datetime.now() - start}')
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    img_content = img_byte_arr.getvalue()
                else:
                    img_content = response.content
                try:
                    image_emoji = await ctx.guild.create_custom_emoji(name=ctx.author.name + '_emoji',
                                                                      image=img_content)
                except:
                    await ctx.send('Unsupported image type or custom emojis full')
                    return
                print(f'Creating emoji time: {datetime.datetime.now() - start}')
                likes_tables[ctx.guild.id].update_item(
                    Key={
                        'user': ctx.author.id
                    },
                    UpdateExpression='SET emoji = :val1',
                    ExpressionAttributeValues={
                        ':val1': str(image_emoji)
                    }
                )
                await ctx.send(f'Emoji {image_emoji} set for {ctx.author.name}!')
                emojis[ctx.guild.id][ctx.author.id] = str(image_emoji)

        else:
            if emo.is_emoji(input_emoji) or (input_emoji.startswith('<:') and input_emoji.endswith('>') and
                                             ':' in input_emoji[2:-1]) and input_emoji not in {'❤️', '◀', '▶'}:
                if input_emoji in emojis[ctx.guild.id].values():
                    user_with_emoji = list(emojis[ctx.guild.id].keys())[
                        list(emojis[ctx.guild.id].values()).index(input_emoji)]
                    user_with_emoji = bot.get_user(int(user_with_emoji))
                    await ctx.send(f'{user_with_emoji.name} already has emoji {input_emoji}')
                    return
                else:
                    likes_tables[ctx.guild.id].update_item(
                        Key={
                            'user': ctx.author.id
                        },
                        UpdateExpression='SET emoji = :val1',
                        ExpressionAttributeValues={
                            ':val1': input_emoji
                        }
                    )
                    await ctx.send(f'Emoji {input_emoji} set for {ctx.author.name}!')
                    emojis[ctx.guild.id][ctx.author.id] = input_emoji
            else:
                await ctx.send('Invalid emoji.')


# @bot.command(brief='Displays graph showing number of items added by users recently', description='Displays graph showing number of items added by users recently')
# async def history(ctx) -> None:
#     if (ctx.guild.id == TESTING_GUILD_ID) == testing:
#         i = 0
#         while global_key_list[ctx.guild.id][i]['time_added'] == '':
#             i += 1
#         start_date = datetime.datetime.strptime(global_key_list[ctx.guild.id][i]['time_added'], "%m/%d/%Y, %H:%M:%S")
#         current = datetime.datetime.now()
#         time_interval = list(pd.period_range(f'{start_date.year}-{start_date.month}', f'{current.year}-{current.month}', freq='M').strftime('%Y-%m'))
#         print(time_interval)
#         print(global_key_list[ctx.guild.id][i])
#
#         users = []
#         media_numbers = [[] for _ in range(len(time_interval))]
#         for item in global_key_list[ctx.guild.id]:
#             if item['time_added'] != '':
#                 index_of_month = time_interval.index(datetime.datetime.strptime(item['time_added'], "%m/%d/%Y, %H:%M:%S").strftime('%Y-%m'))
#             else:
#                 index_of_month = 0
#             if item['author'] in users:
#                 media_numbers[index_of_month][users.index(item['author'])] += 1
#             else:
#                 users.append(item['author'])
#                 for sublist in media_numbers:
#                     sublist.append(0)
#                 media_numbers[index_of_month][-1] += 1
#
#         print(users)
#         print(media_numbers)
#         print(time_interval)
#
#         time_interval = [calendar.month_abbr[int(item[-2:])] + ' ' + item[:4] for item in time_interval]
#         data = pd.DataFrame(data=media_numbers,
#                             columns=users,
#                             index=time_interval)
#         print(data)
#
#         fig = px.bar(data, title="Media added per user", text_auto=True,
#                      color_discrete_sequence=px.colors.qualitative.Pastel)
#         fig.update_traces(textfont_size=10, textfont_color='#373940')
#         fig.update_layout(xaxis_title='Months', yaxis_title='Items added', legend_title_text='Users', legend=dict(x=1.05, y=0.99), margin=dict(pad=5), xaxis_tickformat='%B %Y',
#                           template='plotly_white', title_font_size=25, paper_bgcolor='#373940', font_color='#cfd0d0', barmode='group')
#         fig.update_yaxes(ticksuffix=" ")
#         # fig.show()
#         image_bytes = fig.to_image(format='png', scale=3)
#         await ctx.send(file=discord.File(fp=BytesIO(image_bytes), filename='usage_graph.png'))


@bot.command(brief='Stores last media recently sent by user using specified keyword.',
             description='Stores last media recently sent by user using specified keyword. Provide a keyword and a description, '
                         'or specify an optional keyword and a category number.')
async def add(ctx, keyword, *args) -> None:
    """Stores last sent image in database using keyword"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        start = datetime.datetime.now()
        message_history = [ctx.message] + [item async for item in ctx.channel.history(limit=10)]
        print(f'Time to get message history: {datetime.datetime.now() - start}')
        message_links = []
        messages_from_author = []
        for message in message_history:
            if message.content.startswith('https://'):
                message_links.append(message.content)
                if message.author == ctx.author:
                    messages_from_author.append(message.content)
            elif message.attachments != []:
                message_links.append(message.attachments[0].url)
                if message.author == ctx.author:
                    messages_from_author.append(message.attachments[0].url)

        if messages_from_author != []:
            message_links = messages_from_author
        print(f'Time to get message link: {datetime.datetime.now() - start}')
        print(message_links)

        table = media_tables[ctx.guild.id]
        category = ''
        if keyword.isnumeric():
            if 1 <= int(keyword) <= len(categories[ctx.guild.id]):
                category = categories[ctx.guild.id][int(keyword) - 1]
                keyword = ''
                desc = ' '.join(args)
            else:
                await ctx.send('Invalid category number.')
                return
        else:
            if len(args) > 0 and args[0].isnumeric():
                if 1 <= int(args[0]) <= len(categories[ctx.guild.id]):
                    category = categories[ctx.guild.id][int(args[0]) - 1]
                    desc = ' '.join(args[1:])
                else:
                    await ctx.send('Invalid category number.')
                    return
            else:
                desc = ' '.join(args)
        print(f'Time before get item: {datetime.datetime.now() - start}')
        if keyword != '':
            response = table.get_item(
                Key={
                    'keyword': keyword
                }
            )
        else:
            response = {}
        print(f'Time to get item and complete attributes: {datetime.datetime.now() - start}')
        if 'Item' in response:
            await ctx.send('This keyword already stores an item. Do you want to overwrite the current item? (Y/N)')
            try:
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                         timeout=30.0)
            except:
                return
            if msg.content.lower() == 'y':
                remove_key_from_original_category(ctx, response, keyword)
                if isinstance(response['Item']['likes'], set):
                    likes_table = likes_tables[ctx.guild.id]
                    for user in response['Item']['likes']:
                        member = discord.utils.get(ctx.guild.members, name=user)
                        remove_from_liked_table(likes_table, keyword, member)
            else:
                await ctx.send('Item not changed')
                return

        if keyword == '' and category != '':
            category_length = len(cat_tables[ctx.guild.id].get_item(
                Key={
                    'category': category
                }
            )['Item']['item_list'])
            keyword = category + str(category_length + 1)
            while keyword in global_key_dict[ctx.guild.id]:
                keyword += '_'
        print(f'Time before image hashing/checking duplicates: {datetime.datetime.now() - start}')
        start2 = datetime.datetime.now()
        if len(message_links) > 0:
            img = get_image_from_link(message_links[0])
            text = ''
            try:
                text = get_text_from_image(img)[0]
            except:
                pass
            print(f'Time after image OCR: {datetime.datetime.now() - start2}')
            try:
                image_hash = imagehash.phash(img)
            except:
                image_hash = ''
            duplicate = check_image_duplicate(ctx.guild, image_hash)
            print(f'Time after image OCR + checking duplicates: {datetime.datetime.now() - start2}')
            if duplicate != '' and duplicate != keyword:
                await ctx.send(f'Database contains possible duplicate ({duplicate}). Do you want to add anyway? (Y/N)')
                try:
                    msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                             timeout=30.0)
                except:
                    return
                if msg.content.lower() == 'y':
                    pass
                else:
                    await ctx.send('Item not added')
                    return

            table.put_item(
                Item={
                    'keyword': keyword,
                    'likes': 0,
                    'link': message_links[0],
                    'description': desc,
                    'category': category,
                    'author': ctx.author.name,
                    'time_added': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                    'text_guess': text,
                    'image_hash': str(image_hash)
                }
            )
        else:
            await ctx.send('No media found in last ten messages.')
            return

        if category == '':
            await ctx.send(f'{keyword} added successfully! \nAdded media: ')
        else:
            add_key_to_new_category(ctx, keyword, category)
            await ctx.send(f'{keyword} added to category {category}! \nAdded media: ')
        response = media_tables[ctx.guild.id].get_item(
            Key={
                'keyword': keyword
            }
        )
        global_key_list[ctx.guild.id].append({'keyword': keyword,
                                              'description': desc,
                                              'author': ctx.author.name,
                                              'category': category,
                                              'text_guess': text,
                                              'image_hash': str(image_hash),
                                              'link': message_links[0],
                                              'likes': 0,
                                              'time_added': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                                              'file_content': ''})
        global_key_dict[ctx.guild.id][keyword] = len(global_key_list[ctx.guild.id]) - 1
        all_keys = [item['keyword'] for item in global_key_list[ctx.guild.id]]
        await send_media(ctx, response, False, all_keys, global_key_dict[ctx.guild.id][keyword])


@bot.command(brief='Stores media in database using specified keyword.',
             description='Stores media in database using specified keyword. Specify the keyword associated '
                         'with the media, the link, an optional description, and an optional category number.')
async def put(ctx, keyword, link, *args) -> None:
    """Puts the specified link into database with given keyword"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        table = media_tables[ctx.guild.id]
        category = ''
        if len(args) > 0 and args[0].isnumeric():
            if 1 <= int(args[0]) <= len(categories[ctx.guild.id]):
                category = categories[ctx.guild.id][int(args[0]) - 1]
                desc = ' '.join(args[1:])
            else:
                await ctx.send('Invalid category number.')
                return
        else:
            desc = ' '.join(args)

        link = link.replace('media.discordapp.net', 'cdn.discordapp.com')
        if 'https://' not in link:
            await ctx.send('Not a valid image link: must start with https://')
        else:
            response = table.get_item(
                Key={
                    'keyword': keyword
                }
            )
            if 'Item' in response:
                await ctx.send('This keyword already stores an item. Do you want to overwrite the current item? (Y/N)')
                try:
                    msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                             timeout=30.0)
                except:
                    return
                if msg.content.lower() == 'y':
                    remove_key_from_original_category(ctx, response, keyword)
                    if isinstance(response['Item']['likes'], set):
                        likes_table = likes_tables[ctx.guild.id]
                        for user in response['Item']['likes']:
                            member = discord.utils.get(ctx.guild.members, name=user)
                            remove_from_liked_table(likes_table, keyword, member)
                else:
                    await ctx.send('Item not changed')
                    return
            img = get_image_from_link(link)
            text = ''
            try:
                text = get_text_from_image(img)[0]
            except:
                pass
            try:
                image_hash = imagehash.phash(img)
            except:
                image_hash = ''
            duplicate = check_image_duplicate(ctx.guild, image_hash)
            if duplicate != '' and duplicate != keyword:
                await ctx.send(f'Database contains possible duplicate ({duplicate}). Do you want to add anyway? (Y/N)')
                try:
                    msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                             timeout=30.0)
                except:
                    return
                if msg.content.lower() == 'y':
                    pass
                else:
                    await ctx.send('Item not added')
                    return
            table.put_item(
                Item={
                    'keyword': keyword,
                    'likes': 0,
                    'link': link,
                    'description': desc,
                    'category': category,
                    'author': ctx.author.name,
                    'time_added': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                    'text_guess': text,
                    'image_hash': str(image_hash)
                }
            )
            if category == '':
                await ctx.send(f'{keyword} added successfully! \nAdded media: ')
            else:
                add_key_to_new_category(ctx, keyword, category)
                await ctx.send(f'{keyword} added to category {category}! \nAdded media: ')
            response = media_tables[ctx.guild.id].get_item(
                Key={
                    'keyword': keyword
                }
            )
            global_key_list[ctx.guild.id].append({'keyword': keyword,
                                                  'description': desc,
                                                  'author': ctx.author.name,
                                                  'category': category,
                                                  'text_guess': text,
                                                  'image_hash': str(image_hash),
                                                  'link': link,
                                                  'likes': 0,
                                                  'time_added': datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                                                  'file_content': ''})
            global_key_dict[ctx.guild.id][keyword] = len(global_key_list[ctx.guild.id]) - 1
            all_keys = [item['keyword'] for item in global_key_list[ctx.guild.id]]
            await send_media(ctx, response, False, all_keys, global_key_dict[ctx.guild.id][keyword])


@bot.command(brief='Gets media from specified keyword.',
             description='Gets media from specified keyword. Type \'info\' or \'i\' after keyword to get additional information.')
async def get(ctx, keyword, info: str = '') -> None:
    """Retrieves link associated with given keyword"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        table = media_tables[ctx.guild.id]
        response = table.get_item(
            Key={
                'keyword': keyword
            }
        )
        if 'Item' in response:
            if ctx.message:
                await ctx.message.delete()
            attach_info = info == 'info' or info == 'i'
            all_keys = [item['keyword'] for item in global_key_list[ctx.guild.id]]
            await send_media(ctx, response, attach_info, all_keys, global_key_dict[ctx.guild.id][keyword])
        else:
            keywords = [item['keyword'] for item in global_key_list[ctx.guild.id]]
            possible_keys = difflib.get_close_matches(keyword, keywords, cutoff=0.3)

            print(possible_keys)
            if len(possible_keys) > 0:
                message1 = await ctx.send(
                    f"Keyword not in database. Did you mean to get '{possible_keys[0]}' instead? (Y/N)")
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                         timeout=30.0)
                if msg.content.lower() == 'y':
                    response = table.get_item(
                        Key={
                            'keyword': possible_keys[0]
                        }
                    )
                    await message1.delete()
                    await msg.delete()
                    await ctx.message.delete()
                    attach_info = info == 'info' or info == 'i'
                    print(response)
                    all_keys = [item['keyword'] for item in global_key_list[ctx.guild.id]]
                    await send_media(ctx, response, attach_info, all_keys,
                                     global_key_dict[ctx.guild.id][possible_keys[0]])
                elif msg.content.lower() == 'n':
                    await ctx.send('No action taken.')
                return
            else:
                await ctx.send('Keyword not in database')


def update_info_string(response) -> str:
    info_string = ''
    info_string += 'Keyword: ' + response['Item']['keyword']
    if 'description' in response['Item'] and response['Item']['description'] != '':
        info_string += '\nDescription: ' + response['Item']['description']
    if 'category' in response['Item'] and response['Item']['category'] != '':
        info_string += '\nCategory: ' + response['Item']['category']
    info_string += '\nAdded by: ' + response['Item']['author']
    if isinstance(response['Item']['likes'], set) and len(response['Item']['likes']) > 0:
        like_string = ', '.join(response['Item']['likes'])
        info_string += '\nLiked by: ' + like_string
    if 'time_added' in response['Item']:
        info_string += '\nTime uploaded: ' + response['Item']['time_added']
    return info_string


async def send_media(ctx, response, attach_info: bool, item_list: list, index: int) -> None:
    start = datetime.datetime.now()
    url = response['Item']['link']
    extension = url.split('.')[-1].lower()
    if extension in {'mp4', 'mov'}:
        try:
            file_name = response['Item']['keyword'] + '.' + extension
            item = keyword_to_item(ctx.guild, response['Item']['keyword'])
            if item['file_content'] == '':
                file_response = requests.get(url, stream=True)
                # file_content = file_response.content
                file_bytes = BytesIO(file_response.content)
                # item['file_content'] = file_content
            else:
                print(item['file_content'])
                file_bytes = BytesIO(item['file_content'])
            print(f'Time to get bytes: {datetime.datetime.now() - start}')
            message = await ctx.send(file=discord.File(fp=file_bytes, filename=file_name))
        except:
            message = await ctx.send(url)
    else:
        message = await ctx.send(url)

    print(f'Sent media: {datetime.datetime.now() - start}')
    last_key[ctx.guild.id] = response['Item']['keyword']

    info_message = None
    if attach_info:
        info_string = update_info_string(response)
        info_message = await ctx.send(info_string)

    async def left_callback(inter):
        await message.delete()
        if info_message is not None:
            await info_message.delete()
        new_index = max(0, index - 1)
        print(item_list[new_index])
        response = {'Item': keyword_to_item(ctx.guild, item_list[new_index])}
        await arrow_message.delete()
        await send_media(ctx, response, attach_info, item_list, new_index)

    async def right_callback(inter):
        await message.delete()
        if info_message is not None:
            await info_message.delete()
        new_index = min(len(item_list) - 1, index + 1)
        response = {'Item': keyword_to_item(ctx.guild, item_list[new_index])}
        await arrow_message.delete()
        await send_media(ctx, response, attach_info, item_list, new_index)

    left = Button(label='❮')  # emoji='◀'
    right = Button(label='❯')  # emoji='▶'
    left.callback = left_callback
    right.callback = right_callback
    if index == 0:
        left.disabled = True
    if index == len(item_list) - 1:
        right.disabled = True
    view = View()
    view.add_item(left)
    view.add_item(right)
    arrow_message = await ctx.send(view=view)

    await message.add_reaction('❤️')

    if isinstance(response['Item']['likes'], set) and len(response['Item']['likes']) > 0:
        for react_user in response['Item']['likes']:
            try:
                member = discord.utils.get(ctx.guild.members, name=react_user)
                user_emoji = await get_user_emoji(ctx, member)
                await message.add_reaction(user_emoji)
            except:
                pass

    reaction = None
    liked_by = response['Item']['likes']

    react_user = bot.user
    while True:
        if str(reaction) == '❤️':
            if liked_by == 0 or liked_by is None or react_user.name not in liked_by:
                liked_by = await like_helper(ctx, response['Item']['keyword'], react_user)
                user_emoji = await get_user_emoji(ctx, react_user)
                await message.add_reaction(user_emoji)
            else:
                liked_by = await unlike_helper(ctx, response['Item']['keyword'], react_user)
                user_emoji = await get_user_emoji(ctx, react_user)
                await message.remove_reaction(user_emoji, bot.user)
        try:
            reaction, react_user = await bot.wait_for('reaction_add', check=lambda reaction2,
                                                                                   user2: user2 != bot.user and reaction2.message == message,
                                                      timeout=60.0)
            await message.remove_reaction(reaction, react_user)
        except:
            break
    try:
        await message.clear_reactions()
    except:
        pass


@bot.command(brief='Outputs information of last media sent.', description='Outputs information of last media sent.')
async def last(ctx) -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if last_key[ctx.guild.id] is None:
            await ctx.send('No media has been sent.')
        else:
            response = {'Item': keyword_to_item(ctx.guild, last_key[ctx.guild.id])}
            info_string = update_info_string(response)
            await ctx.send(info_string)


@bot.command(name='random', aliases=["r", "rand"], brief='Sends media corresponding to a random keyword.',
             description='Sends media corresponding to a random keyword.')
async def random_key(ctx, cat: str = '') -> None:
    """Gets link from a random keyword. Can get a random link from specified category."""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        start = datetime.datetime.now()
        response = likes_tables[ctx.guild.id].get_item(
            Key={
                'user': ctx.author.id
            }
        )
        black_list = set()
        if 'Item' in response and 'blacklist' in response['Item']:
            black_list = set(response['Item']['blacklist'])
        if cat == '':
            scanned_keys = [item['keyword'] for item in global_key_list[ctx.guild.id] if
                            item['category'] not in black_list]
        elif cat == 'l':
            scanned_keys = [item['keyword'] for item in global_key_list[ctx.guild.id] if
                            isinstance(item['likes'], set) and
                            len(item['likes']) > 0 and item['category'] not in black_list]
        else:
            if cat == '0':
                if 'Item' in response and 'liked_items' in response['Item']:
                    scanned_keys = [item for item in response['Item']['liked_items'] if
                                    keyword_to_item(ctx.guild, item)['category'] not in black_list]
                else:
                    await ctx.send(f'{ctx.author.name} has no liked keys')
                    return
            elif 1 <= int(cat) <= len(categories[ctx.guild.id]):
                category = categories[ctx.guild.id][int(cat) - 1]
                scanned_keys = cat_tables[ctx.guild.id].get_item(
                    Key={
                        'category': category
                    }
                )['Item']['item_list']
            else:
                await ctx.send('Category index not defined')
                return

        if len(scanned_keys) == 0:
            await ctx.send('No keys present')
            return

        random_int = random.randint(0, len(scanned_keys) - 1)
        random_selection = scanned_keys[random_int]

        response = {'Item': keyword_to_item(ctx.guild, random_selection)}
        print(f'Made random selection: {datetime.datetime.now() - start}')
        await send_media(ctx, response, False, scanned_keys, random_int)


@bot.command(brief='Deletes category if less than 10 items or if user is admin.',
             description='Deletes specified category if it has less than 10 items or if user is admin.')
async def delcat(ctx, category: str) -> None:
    """Deletes specified category if it has less than 10 items or if user is admin. Otherwise, prints error message."""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if category in categories[ctx.guild.id]:
            cat_table = cat_tables[ctx.guild.id]
            table = media_tables[ctx.guild.id]
            scanned_items = [item for item in global_key_list[ctx.guild.id] if item['category'] == category]
            if ctx.author.guild_permissions.administrator or len(scanned_items) <= 10:
                await ctx.send(f'Are you sure? This action cannot be undone. (Y/N)')
                try:
                    msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                             timeout=30.0)
                except:
                    return
                if msg.content.lower() == 'y':
                    if len(scanned_items) > 10:
                        await ctx.send(f'This will clear a category of more than 10 items. Confirm again. (Y/N)')
                        try:
                            msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                                     timeout=30.0)
                        except:
                            return
                        if msg.content.lower() != 'y':
                            await ctx.send('Category not deleted.')
                            return
                    cat_table.delete_item(
                        Key={
                            'category': category
                        }
                    )
                    for item in scanned_items:
                        table.update_item(
                            Key={
                                'keyword': item['keyword']
                            },
                            UpdateExpression='SET category = :val1',
                            ExpressionAttributeValues={
                                ':val1': ''
                            }
                        )
                    categories[ctx.guild.id].remove(category)
                    await ctx.send(f'Category {category} deleted successfully!')
                else:
                    await ctx.send('Category not deleted.')
            else:
                await ctx.send('Insufficient permissions to delete category with more than 10 items')
        else:
            await ctx.send(f'Category {category} not in database.')


@bot.command(brief='Deletes media associated with keyword from database.',
             description='Deletes media associated with keyword from database.')
async def delete(ctx, keyword='') -> None:
    """Deletes link associated with keyword"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if keyword == '':
            keyword = global_key_list[ctx.guild.id][-1]['keyword']
            await ctx.send(f'Are you sure you want to delete \'{keyword}\'?')
            try:
                msg = await bot.wait_for('message', check=lambda message: message.author == ctx.author,
                                         timeout=30.0)
            except:
                return
            if msg.content.lower() != 'y':
                await ctx.send('No action taken')
                return

        table = media_tables[ctx.guild.id]
        response = table.get_item(
            Key={
                'keyword': keyword
            }
        )
        if 'Item' in response:
            remove_key_from_original_category(ctx, response, keyword)
            item_index = global_key_dict[ctx.guild.id][keyword]
            global_key_list[ctx.guild.id].pop(item_index)
            for i in range(item_index, len(global_key_list[ctx.guild.id])):
                dict_keyword = global_key_list[ctx.guild.id][i]['keyword']
                assert global_key_dict[ctx.guild.id][dict_keyword] == i + 1
                global_key_dict[ctx.guild.id][dict_keyword] = i

            if isinstance(response['Item']['likes'], set):
                likes_table = likes_tables[ctx.guild.id]
                for user in response['Item']['likes']:
                    member = discord.utils.get(ctx.guild.members, name=user)
                    remove_from_liked_table(likes_table, keyword, member)
            table.delete_item(
                Key={
                    'keyword': keyword
                }
            )
            await ctx.send('Keyword and item removed from database!')
        else:
            await ctx.send('Keyword not in database.')


@bot.command(brief='Sends embed containing all media with specified string.',
             description='Sends embed containing all media with specified string.')
async def search(ctx, *args):
    """Sends an embed containing all of the keys with term in them"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        term = ' '.join(args)
        if term == '':
            await ctx.send('No search term given.')
            return
        if prev_messages['search'][ctx.guild.id] is not None and prev_messages['search'][ctx.guild.id][-1] == ctx.author.id:
            for item in prev_messages['search'][ctx.guild.id]:
                if item and not isinstance(item, int):
                    await item.delete()
            prev_messages['search'][ctx.guild.id] = None

        searched_items = []
        for item in global_key_list[ctx.guild.id]:
            if term.lower() in item['keyword'].lower() or (
                    'text_guess' in item and term.lower() in item['text_guess'].lower()) \
                    or 'description' in item and term.lower() in item['description'].lower():
                searched_items.append(item)

        key_list = await make_key_list(ctx, searched_items, True)

        pages = []
        size = 20
        num_pages = math.ceil(len(key_list) / size)
        for i in range(num_pages):
            if i == num_pages - 1:
                end = len(key_list)
            else:
                end = (i + 1) * size
            if num_pages > 1:
                title = f'Media containing \'{term}\' (Page {i + 1} / {num_pages})'
            else:
                title = f'Media containing \'{term}\''
            page = discord.Embed(
                title=title,
                description='\n'.join(key_list[i * size:end]),
                colour=discord.Colour.blue()
            )
            pages.append(page)

        if len(pages) > 0:
            message = await ctx.send(embed=pages[0])
            view_message = await create_embed(ctx, num_pages, message, pages, [searched_items[i]['keyword'] for i in range(len(searched_items) - 1, -1, -1)])
            prev_messages['search'][ctx.guild.id] = [message, view_message, ctx.author.id]
        else:
            await ctx.send('No keys present')


@bot.command(brief='Displays list of top 20 liked keywords', description='Displays list of top 20 liked keywords')
async def top(ctx) -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if prev_messages['top'][ctx.guild.id] is not None:
            await prev_messages['top'][ctx.guild.id].delete()
            prev_messages['top'][ctx.guild.id] = None
        liked_media = []
        for item in global_key_list[ctx.guild.id]:
            if item['likes'] != 0 and len(item['likes']) > 0:
                liked_media.append(item)
        liked_media.sort(key=lambda item: len(item['likes']), reverse=True)
        key_list = []
        for key in liked_media:
            key_list.append(await key_list_helper(ctx, key, True))

        if len(key_list) >= 20:
            key_list = key_list[:20]

        title = f'Top liked keys'
        page = discord.Embed(
            title=title,
            description='\n'.join(key_list),
            colour=discord.Colour.gold()
        )
        if len(key_list) > 0:
            message = await ctx.send(embed=page)
            prev_messages['top'][ctx.guild.id] = message
        else:
            await ctx.send('No keys present')


async def key_list_helper(ctx, key, top: bool) -> str:
    key_string = ''
    author_user = discord.utils.get(ctx.guild.members, name=key['author'])
    user_emoji = await get_user_emoji(ctx, author_user)
    key_string += user_emoji + '\u200b ' * 2
    # if top:
    #     key_string += f'[`{key["keyword"]}`]({link}/{ctx.guild.id}/{ctx.channel.id}/{key["keyword"]})' + '\u200B \u200b \u200b ⎯ \u200B \u200b \u200b' + str(len(key['likes']))
    # else:
    #     if key['description'] == '':
    #         key_string += f'[`{key["keyword"]}`]({link}/{ctx.guild.id}/{ctx.channel.id}/{key["keyword"]})'
    #     else:
    #         key_string += f'[`{key["keyword"]}`]({link}/{ctx.guild.id}/{ctx.channel.id}/{key["keyword"]})' + '\u200b \u200b \u200b ⎯ \u200B \u200b \u200b' + key['description']
    if top:
        key_string += f'`{key["keyword"]}`' + '\u200B \u200b \u200b ⎯ \u200B \u200b \u200b' + str(len(key['likes']))
    else:
        if key['description'] == '':
            key_string += f'`{key["keyword"]}`'
        else:
            key_string += f'`{key["keyword"]}`' + '\u200b \u200b \u200b ⎯ \u200B \u200b \u200b' + key['description']
    return key_string


async def make_key_list(ctx, scanned_items, rev=False) -> list:
    key_list = []
    # add items to key_list in order to show in embed
    if rev:
        for i in range(len(scanned_items) - 1, -1, -1):
            key = scanned_items[i]
            key_list.append(await key_list_helper(ctx, key, False))
    else:
        for key in scanned_items:
            key_list.append(await key_list_helper(ctx, key, False))
    return key_list


@bot.command(brief='Makes media in category hidden for user when rolling random.',
             description='Makes media in category hidden for user when rolling random.')
async def hide(ctx, category: str = '') -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if category in categories[ctx.guild.id]:
            response = likes_tables[ctx.guild.id].get_item(
                Key={
                    'user': ctx.author.id
                }
            )
            if 'Item' in response:
                if 'blacklist' in response['Item']:
                    prev_blacklist = response['Item']['blacklist']
                else:
                    prev_blacklist = []
                if category not in prev_blacklist:
                    prev_blacklist.append(category)
                else:
                    await ctx.send(f'Category {category} already hidden by {ctx.author.name}')
                    return
                likes_tables[ctx.guild.id].update_item(
                    Key={
                        'user': ctx.author.id
                    },
                    UpdateExpression='SET blacklist = :val1',
                    ExpressionAttributeValues={
                        ':val1': prev_blacklist
                    }
                )
            else:
                likes_tables[ctx.guild.id].put_item(
                    Item={
                        'user': ctx.author.id,
                        'blacklist': [category]
                    }
                )
            await ctx.send(f'Category {category} hidden by {ctx.author.name}!')
        else:
            await ctx.send('Category not in database.')


@bot.command(brief='Makes media in category hidden for user when rolling random.',
             description='Makes media in category hidden for user when rolling random.')
async def show(ctx, category: str = '') -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        if category in categories[ctx.guild.id]:
            response = likes_tables[ctx.guild.id].get_item(
                Key={
                    'user': ctx.author.id
                }
            )
            if 'Item' in response and 'blacklist' in response['Item']:
                prev_blacklist = response['Item']['blacklist']
                try:
                    prev_blacklist.remove(category)
                except:
                    await ctx.send(f'Category {category} not hidden by {ctx.author.name}')
                    return
                likes_tables[ctx.guild.id].update_item(
                    Key={
                        'user': ctx.author.id
                    },
                    UpdateExpression='SET blacklist = :val1',
                    ExpressionAttributeValues={
                        ':val1': prev_blacklist
                    }
                )
                await ctx.send(f'Category {category} unhidden by {ctx.author.name}!')
            else:
                await ctx.send(f'Category {category} not hidden by {ctx.author.name}')
        else:
            await ctx.send('Category not in database.')


@bot.command(brief='Sends embed containing list of categories blacklisted by user.',
             description='Sends embed containing list of categories blacklisted by user.')
async def blacklist(ctx) -> None:
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        response = likes_tables[ctx.guild.id].get_item(
            Key={
                'user': ctx.author.id
            }
        )
        if 'Item' in response and 'blacklist' in response['Item'] and len(response['Item']['blacklist']) > 0:
            b_list = response['Item']['blacklist']
        else:
            await ctx.send(f'No categories blacklisted by {ctx.author.name}')
            return

        cat_list = []
        i = 1
        for key in b_list:
            key_string = f'`{i}.` **' + key + '**'
            cat_list.append(key_string)
            i += 1

        pages = []
        size = 20
        num_pages = math.ceil(len(cat_list) / size)
        if num_pages > 1:
            title = f'Categories blacklisted by {ctx.author.name} (Page {i + 1}/{num_pages})'
        else:
            title = f'Categories blacklisted by {ctx.author.name}'
        for i in range(num_pages):
            if i == num_pages - 1:
                end = len(cat_list)
            else:
                end = (i + 1) * size
            page = discord.Embed(
                title=title,
                description='\n'.join(cat_list[i * size:end]),
                colour=discord.Colour.from_rgb(25, 25, 25)
            )
            pages.append(page)

        message = await ctx.send(embed=pages[0])
        await create_embed(ctx, num_pages, message, pages, [])


@bot.command(brief='Displays all keywords in database or in specified category.',
             description='Displays all keywords in database or in specified category.')
async def keys(ctx, category: str = '') -> None:
    """Sends an embed containing all of the keys in database"""
    if (ctx.guild.id == TESTING_GUILD_ID) == testing:
        start = datetime.datetime.now()
        if category != '' and category not in categories[ctx.guild.id]:
            await ctx.send('Category not in database.')
            return
        if category == '':
            sorted_keys = global_key_list[ctx.guild.id]
            key_list = await make_key_list(ctx, sorted_keys, True)
            print(f'Make key list time: {datetime.datetime.now() - start}')
        else:
            start2 = datetime.datetime.now()
            category_items = cat_tables[ctx.guild.id].get_item(
                Key={
                    'category': category
                }
            )['Item']['item_list']
            sorted_keys = []
            for keyword in category_items:
                index_of_key = global_key_dict[ctx.guild.id][keyword]
                sorted_keys.append(global_key_list[ctx.guild.id][index_of_key])
                assert global_key_list[ctx.guild.id][index_of_key]['keyword'] == keyword
            key_list = await make_key_list(ctx, sorted_keys, True)

            print(f'Category sort time: {datetime.datetime.now() - start2}')

        start3 = datetime.datetime.now()
        pages = []
        size = 20
        num_pages = math.ceil(len(key_list) / size)
        for i in range(num_pages):
            if i == num_pages - 1:
                end = len(key_list)
            else:
                end = (i + 1) * size
            if category == '':
                if num_pages > 1:
                    title = f'Keys (Page {i + 1}/{num_pages}) - {len(key_list)} items'
                else:
                    title = f'Keys - {len(key_list)} items'
            else:
                if num_pages > 1:
                    title = f'Keys from category {category} (Page {i + 1}/{num_pages}) - {len(key_list)} items'
                else:
                    title = f'Keys from category {category} - {len(key_list)} items'
            page = discord.Embed(
                title=title,
                description='\n'.join(key_list[i * size:end]),
                colour=discord.Colour.orange()
            )
            pages.append(page)

        print(f'Embed creation: {datetime.datetime.now() - start3}')

        if len(pages) > 0:
            start4 = datetime.datetime.now()
            message = await ctx.send(embed=pages[0])
            print(f'Sending embed: {datetime.datetime.now() - start4}')
            print(f'Total: {datetime.datetime.now() - start}')
            if prev_messages['key'][ctx.guild.id] is not None:
                for item in prev_messages['key'][ctx.guild.id]:
                    if item:
                        await item.delete()
                prev_messages['key'][ctx.guild.id] = None
            view_message = await create_embed(ctx, num_pages, message, pages, [sorted_keys[i]['keyword'] for i in range(len(sorted_keys) - 1, -1, -1)])
            prev_messages['key'][ctx.guild.id] = [message, view_message]
        else:
            await ctx.send('No keys present')


def create_table(table_name: str, key: str, key_type: str, dynamodb=None):
    """Creates table"""
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb')

    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': key,
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': key,
                'AttributeType': key_type
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    table.wait_until_exists()
    return table


# noinspection PyUnresolvedReferences
def convert_to_monochrome(image, invert: bool):
    if invert:
        image = PIL.ImageOps.invert(image)
    pixels = image.load()
    for i in range(image.size[0]):  # for every pixel:
        for j in range(image.size[1]):
            r, g, b = pixels[i, j]
            if r > 200 and g > 200 and b > 200:
                pixels[i, j] = (0, 0, 0)
            else:
                pixels[i, j] = (255, 255, 255)
    return image


def interpret_chips(image, invert: bool):
    _image = convert_to_monochrome(image, invert)

    results = pytesseract.image_to_data(_image, output_type=Output.DICT)  # time-consuming
    return results


def download_file(url: str, keyword: str):
    # NOTE the stream=True parameter
    if keyword == '':
        file_name = 'video.mp4'
    else:
        file_name = keyword + '.' + url.lower().split('.')[-1]
    r = requests.get(url, stream=True)
    with open(file_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return file_name


# helper
def get_image_from_link(url: str):
    if '.mp4' in url.lower() or '.mov' in url.lower():
        file_name = download_file(url, '')
        vidcap = cv2.VideoCapture(file_name)
        success, image = vidcap.read()
        if success:
            img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            return img
        else:
            return None
    else:
        response = requests.get(url, stream=True)
        try:
            img = Image.open(BytesIO(response.content)).convert('RGB')
            if img.size[0] > 800 or img.size[1] > 800:
                if img.size[0] > img.size[1]:
                    basewidth = 800
                else:
                    basewidth = int(img.size[0] / img.size[1] * 800)
                wpercent = (basewidth / float(img.size[0]))
                hsize = int((float(img.size[1]) * float(wpercent)))
                img = img.resize((basewidth, hsize), Resampling.LANCZOS)
            return img
        except:
            data = str(response.content)
            start = data.find('https://c.tenor.com/')
            if start == -1:
                start = data.find('https://media4.giphy.com')
            if start == -1:
                return None
            i = start
            while data[i - 3:i] != 'gif':
                i += 1
            response = requests.get(data[start:i], stream=True)
            try:
                img = Image.open(BytesIO(response.content)).convert('RGB')
                return img
            except:
                return None


def get_text_from_image(img):
    if img is None:
        return '', -1
    start = datetime.datetime.now()
    text_info = [pytesseract.image_to_data(img.copy(), output_type=Output.DICT),
                 interpret_chips(img.copy(), False),
                 interpret_chips(img.copy(), True)]
    print(f'Image OCR time: {datetime.datetime.now() - start}')

    text_scores = []
    for text_result in text_info:
        text_guess = text_result['text']
        valid_words = []
        score = 0
        for i in range(len(text_guess)):
            word = text_guess[i].translate(str.maketrans('', '', string.punctuation))
            if (len(word) <= 2 and word.lower() not in small and not word.isnumeric()) or float(
                    text_result['conf'][i]) < 25:
                text_guess[i] = ''
                word = ''
            if (len(word) > 2 and (word.lower() in dictionary or word in dictionary)) or word.lower() in small:
                valid_words.append(word)

            score += float(text_result['conf'][i]) / 100 * len(word)
        print(valid_words)
        print(f'Text: ' + ' '.join(text_guess))
        if text_guess == []:
            text_scores.append(0)
        else:
            text_scores.append(score + len(' '.join(valid_words)))

    index = text_scores.index(max(text_scores))
    print(f'Total OCR time: {datetime.datetime.now() - start}')
    return ' '.join((' '.join(text_info[index]['text'])).split()), index


async def update_ocr_texts(guild) -> None:
    """Updates meme texts based on Tesseract OCR processing"""
    table = media_tables[guild.id]
    scanned_items = table.scan(ProjectionExpression='keyword, link')['Items']
    i = 0
    for item in scanned_items:
        print(item['link'])
        text = ''
        try:
            img = get_image_from_link(item['link'])
            text = get_text_from_image(img)[0]
        except:
            pass
        table.update_item(
            Key={
                'keyword': item['keyword']
            },
            UpdateExpression='SET text_guess = :val1',
            ExpressionAttributeValues={
                ':val1': text
            }
        )
        i += 1
        print(f'Iteration {i}')


def update_image_hashes(guild) -> None:
    """Updates image hashes using Imagehash library """
    table = media_tables[guild.id]
    scanned_items = table.scan(ProjectionExpression='keyword, link')['Items']
    for i in range(len(scanned_items)):
        item = scanned_items[i]
        print(item['link'])
        print(item['keyword'])
        img = get_image_from_link(item['link'])
        try:
            image_hash = imagehash.phash(img)
        except:
            image_hash = ''
        print(image_hash)
        table.update_item(
            Key={
                'keyword': item['keyword']
            },
            UpdateExpression='SET image_hash = :val1',
            ExpressionAttributeValues={
                ':val1': str(image_hash)
            }
        )
        print(f'Iteration {i}')


def check_image_duplicate(guild, hash1) -> str:
    str_hash = str(hash1)
    if str_hash != '' and str_hash != len(str_hash) * str_hash[0]:
        duplicates = []
        for item in global_key_list[guild.id]:
            if 'image_hash' in item:
                img_hash = item['image_hash']
                if img_hash != '' and hash1 - imagehash.hex_to_hash(img_hash) < 8 and img_hash != len(img_hash) * \
                        img_hash[0]:
                    duplicates.append(item['keyword'])
        if len(duplicates) > 0:
            return duplicates[0]
    return ''


def check_all_duplicates(guild) -> None:
    table = media_tables[guild.id]
    scanned_items = table.scan(ProjectionExpression='keyword, description, image_hash')['Items']
    duplicates = []
    for i in range(len(scanned_items)):
        for j in range(i + 1, len(scanned_items)):
            if 'image_hash' in scanned_items[i] and 'image_hash' in scanned_items[j]:
                print(f'Testing image {i} with image {j}')
                img_hash1 = scanned_items[i]['image_hash']
                img_hash2 = scanned_items[j]['image_hash']

                if img_hash1 != '' and img_hash2 != '' and imagehash.hex_to_hash(img_hash1) - imagehash.hex_to_hash(
                        img_hash2) < 8 and \
                        img_hash1 != len(img_hash1) * img_hash1[0] and img_hash2 != len(img_hash2) * img_hash2[0]:
                    duplicates.append((scanned_items[i]['keyword'], scanned_items[j]['keyword']))
    from pprint import pprint
    pprint(duplicates)


if __name__ == "__main__":
    media_tables = {}
    cat_tables = {}
    likes_tables = {}
    categories = {}
    prev_messages = {'cat': {}, 'key': {}, 'search': {}, 'like': {}, 'top': {}, 'memes': {}}
    global_key_list = {}
    global_key_dict = {}
    emojis = {}
    last_key = {}
    with open('word_freq.csv', mode='r') as inp:
        reader = csv.reader(inp)
        dictionary = {rows[0]: rows[1] for rows in reader}
    small = {'am', 'an', 'as', 'at', 'be', 'by', 'do', 'ex', 'go', 'he', 'hi', 'if', 'in', 'is', 'it', 'me',
             'my', 'no', 'of', 'on', 'or', 'ox', 'so', 'to', 'up', 'us', 'we', 'yo', 'im', 'a', 'i', 'u'}

    # Initialize dynamodb profile
    os.environ['AWS_PROFILE'] = "rsrinivasan"
    dynamodb = boto3.resource('dynamodb')
    bot.run(DISCORD_TOKEN)
