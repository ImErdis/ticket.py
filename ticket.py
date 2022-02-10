import discord
from discord.commands import slash_command
from discord.ext import commands
from io import BytesIO
from datetime import datetime
import math
from bson.objectid import ObjectId

from pymongo import MongoClient
from discord.commands import Option

conn_str = "mongodb+srv://root:gnOudT6T2Wy6vwGI@ticketbot.xrxq4.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)
db = client['test-database']
collection = db['active-tickets']
persistent_views_added = False
guild_id = [859201687264690206]


class TicketBot(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketMessage())
        self.bot.add_view(ManageTicket())

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.content == '!close':
            channel = collection.find_one({'channel_id': message.channel.id})
            if channel:
                await message.delete()
                await manage_support_ticket(message, 'close', 'command')

    # Set the ticket message channel

    @slash_command(guild_ids=guild_id, description="Send the support message")
    async def set_ticket_message(self, ctx: discord.ApplicationContext,
                                 channel: Option(discord.TextChannel, "Select ticket channel")):
        fetched_message = db['settings'].find_one({'main_ticket_message': {'$exists': 1}})['main_ticket_message']
        new_message = fetched_message.replace(r'\n', '\n') if fetched_message else 'Lorem ipsum'
        embed = discord.Embed(description=new_message)
        await channel.send(embed=embed, view=TicketMessage())
        await ctx.respond("Successfully done", ephemeral=True)

    # Set the ticket log channel
    @slash_command(guild_ids=guild_id, description="Set ticket log channel")
    async def set_ticket_log(self, ctx: discord.ApplicationContext,
                             channel: Option(discord.TextChannel, "Select ticket log channel")):
        if not db['settings'].find_one({'ticket_log_channel': {'$exists': 1}}):
            db['settings'].insert_one({'ticket_log_channel': channel.id})
        else:
            db['settings'].find_one_and_update({'ticket_log_channel': {'$exists': 1}},
                                               {'$set': {'ticket_log_channel': channel.id}})
        await ctx.respond("Successfully done!", ephemeral=True)

    # Set the new ticket channels category
    @slash_command(guild_ids=guild_id, description="Set new tickets category")
    async def set_ticket_category(self, ctx: discord.ApplicationContext,
                                  category: Option(discord.CategoryChannel, "Select category")):
        if not db['settings'].find_one({'ticket_category': {'$exists': 1}}):
            db['settings'].insert_one({'ticket_category': category.id})
        else:
            db['settings'].find_one_and_update({'ticket_category': {'$exists': 1}},
                                               {'$set': {'ticket_log_channel': category.id}})
        await ctx.respond("Successfully done!", ephemeral=True)

    @slash_command(guild_ids=guild_id, description="See the paginated thingy")
    async def send_paginated_thingy(self, ctx):
        tickets = collection.find({'status': 'closed'})
        desc = make_desc(tickets, 0)
        embed = discord.Embed(title=f"[Subject] | [User ID]-[Ticket ID] | [Close date]", description=desc)
        page = f"Page: 1/{math.ceil(collection.count_documents({'status': 'closed'}) / 10)}"
        embed.set_footer(text=page)
        await ctx.respond(embed=embed, view=PaginatedLogs())

    @slash_command(guild_ids=guild_id, description="Get the selected log")
    async def get_log(self, ctx: discord.ApplicationContext,
                      ticket_id: Option(str, "Enter ticket id")):
        try:
            ticket_object = ObjectId(ticket_id)
        except:
            await ctx.respond('You have entered a wrong ticket id', ephemeral=True)
            return
        ticket = collection.find_one({'_id': ticket_object})
        if not ticket:
            await ctx.respond("No ticket found with that id", ephemeral=True)
            return
        if not ticket.get('log', None):
            await ctx.respond("This ticket doesnt have a saved log", ephemeral=True)
            return
        f = BytesIO(bytes(ticket['log'], encoding="utf-8"))
        file = discord.File(fp=f, filename="log.txt")
        embed = discord.Embed(title=f"Here is the ticket log you asked for",
                              description=f"Ticket made by: <@!{ticket['user']}>\nTicket subject: {ticket['subject']}\nTicket creation date: {ticket['date']}")
        await ctx.respond(embed=embed, file=file)

    @slash_command(guild_ids=guild_id, description='Change the /send_ticket_message message')
    async def change_ticket_manage(self, ctx: discord.ApplicationContext,
                                   content: Option(str, "Enter message content")):
        if not db['settings'].find_one({'main_ticket_message': {'$exists': 1}}):
            db['settings'].insert_one({'main_ticket_message': content})
        else:
            db['settings'].find_one_and_update({'main_ticket_message': {'$exists': 1}},
                                               {'$set': {'main_ticket_message': content}})
        await ctx.respond("Successfully done", ephemeral=True)

    @slash_command(guild_ids=guild_id, description='Change the new ticket channel message')
    async def change_support_message(self, ctx: discord.ApplicationContext,
                                     content: Option(str, "Enter message content")):
        if not db['settings'].find_one({'support_message': {'$exists': 1}}):
            db['settings'].insert_one({'support_message': content})
        else:
            db['settings'].find_one_and_update({'support_message': {'$exists': 1}},
                                               {'$set': {'support_message': content}})
        await ctx.respond("Successfully done", ephemeral=True)


##################################
########## Bot views #############
##################################

class TicketMessage(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ticket_num = 0

    @discord.ui.button(label='Buy coin', style=discord.ButtonStyle.green, row=1, custom_id="persistent_view:buy_coin")
    async def buy_coin_callback(self, button, interaction):
        await manage_support_ticket(interaction, subject='Buy Coin')

    @discord.ui.button(label='Buy island', style=discord.ButtonStyle.green, row=1,
                       custom_id="persistent_view:buy_island")
    async def buy_island_callback(self, button, interaction):
        await manage_support_ticket(interaction, subject='Buy Island')

    @discord.ui.button(label='Buy minion', style=discord.ButtonStyle.green, row=2,
                       custom_id="persistent_view:buy_minion")
    async def buy_minion_callback(self, button, interaction):
        await manage_support_ticket(interaction, subject='Buy Minion')

    @discord.ui.button(label='Need support', style=discord.ButtonStyle.secondary, row=2,
                       custom_id="persistent_view:need_support")
    async def support_callback(self, button, interaction):
        await manage_support_ticket(interaction, subject='Support')


class ManageTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close ticket', style=discord.ButtonStyle.red, custom_id="persistent_view:manage_ticket")
    async def callback(self, button, interaction):
        await manage_support_ticket(interaction, "close")


class DeleteTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Delete ticket', style=discord.ButtonStyle.red, custom_id="persistent_view:delete_ticket")
    async def callback(self, button, interaction):
        await interaction.channel.delete()


class PaginatedLogs(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=900000)
        self.tickets = [x for x in collection.find({'status': 'closed'})]
        self.ticket_count = collection.count_documents({'status': 'closed'})
        self.starting = 0

    @discord.ui.button(label='Previous Page', style=discord.ButtonStyle.red)
    async def previous_page(self, button, interaction):
        if self.starting == 0:
            return

        self.starting -= 10
        desc = make_desc(self.tickets, self.starting)
        embed = discord.Embed(title=f"[User ID]-[Ticket ID]-[Log status]", description=desc)
        page = f"Page: {int(self.starting / 10 + 1)}/{math.ceil(self.ticket_count / 10)}"
        embed.set_footer(text=page)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label='Next Page', style=discord.ButtonStyle.red)
    async def next_page(self, button, interaction):
        if collection.count_documents({'status': 'closed'}) < self.starting + 10:
            return

        self.starting += 10
        desc = make_desc(self.tickets, self.starting)
        embed = discord.Embed(title=f"[User ID]-[Ticket ID]-[Log status]", description=desc)
        page = f"Page: {int(self.starting / 10 + 1)}/{math.ceil(self.ticket_count / 10)}"
        embed.set_footer(text=page)
        await interaction.response.edit_message(embed=embed)


##################################
######### extra methods ##########
##################################


def generate_string_for_ticket_num(num):
    if num < 10:
        return f'000{num}'
    elif num < 100:
        return f'00{num}'
    elif num < 1000:
        return f'0{num}'
    elif num < 10000:
        return f'{num}'
    else:
        return f'{num}'


async def manage_support_ticket(interaction, status="create", called='Button', subject='Support'):
    user_id = collection.find_one({'channel_id': interaction.channel.id})['user']
    user_ticket = collection.find_one({'user': user_id, 'status': 'open'})
    already_created_ticket = False
    if user_ticket and status == "create":
        channel = interaction.guild.get_channel(user_ticket['channel_id'])
        if not channel:
            collection.find_one_and_update({'user': user_id, 'status': 'open'}, {'$set': {'status': 'closed'}})
            already_created_ticket = False
        else:
            already_created_ticket = True
    if not already_created_ticket and status == "create":
        fetched_message = db['settings'].find_one({'support_message': {'$exists': 1}})
        new_message = fetched_message['support_message'].replace(r'\n', '\n') if fetched_message else 'Lorem ipsum'
        embed = discord.Embed(description=new_message)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }
        fetched_category = db['settings'].find_one({'ticket_category': {'$exists': 1}})
        channel = await create_channel(interaction.guild,
                                       f'{generate_string_for_ticket_num(collection.count_documents({}))}-{interaction.user.name}',
                                       overwrites, fetched_category)
        await channel.send(embed=embed, view=ManageTicket())
        collection.insert_one({'channel_id': channel.id,
                               'user': interaction.user.id,
                               'status': 'open',
                               'subject': subject})
    elif status == "close":
        messages = await interaction.channel.history().flatten()
        numbers = "\n".join(
            [f"{message.author} [{message.created_at.hour}:{message.created_at.minute}]: {message.clean_content}" for
             message in messages[::-1]])
        f = BytesIO(bytes(numbers, encoding="utf-8"))
        file = discord.File(fp=f, filename="log.txt")
        fetched_channel = db['settings'].find_one({'ticket_log_channel': {'$exists': 1}})
        user = collection.find_one({'channel_id': interaction.channel.id, 'status': 'open'})
        fetched_user = await interaction.guild.fetch_member(user['user'])
        collection.find_one_and_update({'channel_id': interaction.channel.id, 'status': 'open'},
                                       {'$set': {'status': 'closed', 'log': numbers, 'date': datetime.now()}})
        if fetched_channel:
            channel = interaction.guild.get_channel(fetched_channel['ticket_log_channel'])
            embed = discord.Embed(title=f"{interaction.channel.name}",
                                  description="A ticket just got closed, here is the log")
            await channel.send(file=file, embed=embed)
        await interaction.channel.set_permissions(fetched_user,
                                                  overwrite=discord.PermissionOverwrite(read_messages=False))
        embed = discord.Embed(title='Delete the ticket')
        await interaction.response.send_message(embed=embed, view=DeleteTicket())
    else:

        await interaction.response.send_message("You already have created 1 ticket", ephemeral=True)


async def create_channel(guild, name, overwrites=None, category=None):
    if overwrites is None:
        overwrites = {}
    cat = guild.get_channel(category['ticket_category'])
    if cat:
        return await guild.create_text_channel(name, overwrites=overwrites, category=cat)
    return await guild.create_text_channel(name, overwrites=overwrites)


def make_desc(tickets, starting):
    return "\n".join([
        f"{ticket['subject']} | <@!{ticket['user']}>-{ticket['_id']} | {ticket.get('date') if ticket.get('log', None) else 'doesnt have log'}\n "
        for ticket in tickets[starting:starting + 10:]])


##################################
########## Bot commands ##########
##################################


############################
###### Ticket !close #######
############################

# Soon

def setup(bot):
    bot.add_cog(TicketBot(bot))
