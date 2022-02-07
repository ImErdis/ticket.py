import discord
from io import BytesIO
from datetime import datetime

from pymongo import MongoClient
from discord.commands import Option


conn_str = "mongodb+srv://root:gnOudT6T2Wy6vwGI@ticketbot.xrxq4.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
client = MongoClient(conn_str, serverSelectionTimeoutMS=5000)

class TicketBot(discord.Bot):
    def __init__(self):
        super().__init__()
        self.db = client['test-database']
        self.collection = self.db['active-tickets']
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(TicketMessage())
            self.add_view(ManageTicket())
            self.persistent_views_added = True
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")

bot = TicketBot()
  
##################################
########## Bot views #############
##################################

class TicketMessage(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.ticket_num = 0

    @discord.ui.button(label='Buy coin', style=discord.ButtonStyle.green, row=1, custom_id="persistent_view:buy_coin")
    async def buy_coin_callback(self, button, interaction):
        await manage_support_ticket(interaction, self)

    @discord.ui.button(label='Buy island', style=discord.ButtonStyle.red, row=1, custom_id="persistent_view:buy_island")
    async def buy_island_callback(self, button, interaction):
        await manage_support_ticket(interaction, self)

    @discord.ui.button(label='Need support', style=discord.ButtonStyle.secondary, row=2,
                       custom_id="persistent_view:need_support")
    async def support_callback(self, button, interaction):
        await manage_support_ticket(interaction, self)


class ManageTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close ticket', style=discord.ButtonStyle.red, custom_id="persistent_view:manage_ticket")
    async def command_callback(self, button, interaction):
        await manage_support_ticket(interaction, self, "close")



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

async def manage_support_ticket(interaction, self, status="create"):
    if not bot.collection.find_one({'user': interaction.user.id, 'status': 'open'}) and status == "create":
        embed = discord.Embed(title="Support ticket", description="No idea, lorem ipsum maybe?")
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }
        fetched_category = bot.db['settings'].find_one({'ticket_category': {'$exists': 1}})
        channel = await create_channel(interaction.guild,
                                    f'{generate_string_for_ticket_num(bot.collection.count_documents({}))}-{interaction.user.name}',
                                    overwrites, fetched_category)
        await channel.send(embed=embed, view=ManageTicket())
        bot.collection.insert_one({'channel_id': channel.id, 'user': interaction.user.id, 'status': 'open'})
    elif status == "close":
        messages = await interaction.channel.history().flatten()
        numbers = "\n".join([f"{message.author}: {message.clean_content}" for message in messages[::-1]])
        f = BytesIO(bytes(numbers, encoding="utf-8"))
        file = discord.File(fp=f, filename="log.txt")
        fetched_channel = bot.db['settings'].find_one({'ticket_log_channel': {'$exists': 1}})
        if fetched_channel:
            channel = interaction.guild.get_channel(fetched_channel['ticket_log_channel'])
            embed = discord.Embed(title=f"{interaction.channel.name}", description="A ticket just got closed, here is the log")
            await channel.send(file=file, embed=embed)
        await interaction.channel.delete()
        bot.collection.find_one_and_update({'channel_id': interaction.channel.id, 'status': 'open'}, {'$set': {'status': 'closed', 'log': numbers, 'date': datetime.now()}})
    else:

        await interaction.response.send_message("You already have created 1 ticket", ephemeral=True)


async def create_channel(guild, name, overwrites={}, category=None):
    cat = guild.get_channel(category['ticket_category'])
    if cat:
        return await guild.create_text_channel(name, overwrites=overwrites, category=cat)
    return await guild.create_text_channel(name, overwrites=overwrites)


##################################
########## Bot commands ##########
##################################

# Set the ticket message channel

@bot.slash_command(guild_ids=[859201687264690206], description="Send the support message")
@discord.commands.has_role(897256963224776725)
gasync def set_ticket_message(ctx: discord.ApplicationContext,
                channel: Option(discord.TextChannel, "Select ticket channel")):
    await ctx.respond("Successfully done", ephemeral=True)
    embed = discord.Embed(title=f"{ctx.guild.name}", description="Developing test...")
    await channel.send(embed=embed, view=TicketMessage())

# Set the ticket log channel
@bot.slash_command(guild_ids=[859201687264690206], description="Set ticket log channel")
@discord.commands.has_role(897256963224776725)
async def set_ticket_log(ctx: discord.ApplicationContext,
                channel: Option(discord.TextChannel, "Select ticket log channel")):
    if not bot.db['settings'].find_one({'ticket_log_channel': {'$exists': 1}}):
        bot.db['settings'].insert_one({'ticket_log_channel': channel.id})
    else:
        bot.db['settings'].find_one_and_update({'ticket_log_channel': {'$exists': 1}}, {'$set': {'ticket_log_channel': channel.id}})
    await ctx.respond("Successfully done!", ephemeral=True)

# Set the new ticket channels category
@bot.slash_command(guild_ids=[859201687264690206], description="Set new tickets categoru")
@discord.commands.has_role(897256963224776725)
async def set_ticket_category(ctx: discord.ApplicationContext,
                category: Option(discord.CategoryChannel, "Select category")):
    if not bot.db['settings'].find_one({'ticket_category': {'$exists': 1}}):
        bot.db['settings'].insert_one({'ticket_category': category.id})
    else:
        bot.db['settings'].find_one_and_update({'ticket_category': {'$exists': 1}}, {'$set': {'ticket_log_channel': category.id}})
    await ctx.respond("Successfully done!", ephemeral=True)

bot.run("OTM5MTcyMjgyNzcxODQ5MjY3.Yf0-WQ.C3DI0sKwqvuXBtWHMpjYCZDlWm8")
