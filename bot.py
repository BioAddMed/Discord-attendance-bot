import os
import discord
from discord.ext import commands
import asyncio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
ADMIN_ROLE_NAME = "Zarząd"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.dm_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

meeting_config = {"godzina": "19:00", "budynek": "B-4", "sala": "2.40"}

user_responses = {}
poll_embed_message = None 


@bot.command(name="setGodzina")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_godzina(ctx, *, godzina: str):
    meeting_config["godzina"] = godzina
    await ctx.send(f"🕒 Ustawiono godzinę spotkania na: **{godzina}**")

@bot.command(name="setBudynek")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_budynek(ctx, *, budynek: str):
    meeting_config["budynek"] = budynek
    await ctx.send(f"🏫 Ustawiono budynek na: **{budynek}**")

@bot.command(name="setSala")
@commands.has_role(ADMIN_ROLE_NAME)
async def set_sala(ctx, *, sala: str):
    meeting_config["sala"] = sala
    await ctx.send(f"🏠 Ustawiono salę na: **{sala}**")

@bot.command(name="ankieta")
@commands.has_role(ADMIN_ROLE_NAME)
async def create_poll(ctx, *, data: str):
    """Tworzy ankietę na podstawie ustawień i daty."""
    global poll_embed_message
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Nie znaleziono kanału!")
        return

    user_responses.clear()
    poll_embed_message = None

    embed = discord.Embed(
        title="📅 Ankieta: Czy pojawisz się na najbliższym spotkaniu?",
        description=(
            f"**Godzina:** {meeting_config['godzina']}\n"
            f"**Data:** {data}\n"
            f"**Budynek:** {meeting_config['budynek']}\n"
            f"**Sala:** {meeting_config['sala']}\n\n"
            "Zareaguj, aby potwierdzić:\n✅ Tak\n❌ Nie"
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )

    message = await channel.send("@everyone", embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    await update_poll_embed(channel)

async def update_poll_embed(channel):
    global poll_embed_message
    embed = discord.Embed(title="📋 Odpowiedzi na ankietę", color=discord.Color.green(), timestamp=datetime.now())

    yes_list = []
    no_list = []

    for uid, data in user_responses.items():
        member = channel.guild.get_member(uid)
        name = member.display_name if member else str(uid)
        if data["response"] == "yes":
            yes_list.append(f"✅ {name}")
        else:
            reason = data.get("reason") or "brak powodu"
            no_list.append(f"❌ {name} — {reason}")

    embed.add_field(name="✅ Obecni", value="\n".join(yes_list) or "Brak", inline=False)
    embed.add_field(name="❌ Nieobecni", value="\n".join(no_list) or "Brak", inline=False)

    if poll_embed_message:
        await poll_embed_message.edit(embed=embed)
    else:
        poll_embed_message = await channel.send(embed=embed)

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user or reaction.message.author != bot.user:
        return

    prev = user_responses.get(user.id)
    if prev:
        if (prev["response"] == "yes" and str(reaction.emoji) == "❌") or \
           (prev["response"] == "no" and str(reaction.emoji) == "✅"):
            await reaction.remove(user)
            try:
                await user.send("⚠️ Nie możesz zaznaczyć dwóch odpowiedzi. Aby zmienić decyzję, usuń swoją poprzednią reakcję.")
            except discord.Forbidden:
                pass
            return

    if str(reaction.emoji) == "✅":
        user_responses[user.id] = {"response": "yes", "reason": None}
    elif str(reaction.emoji) == "❌":
        try:
            await user.send("Hej! Zaznaczyłeś, że nie będziesz na spotkaniu. Podaj krótko powód:")
            def check(m):
                return m.author == user and isinstance(m.channel, discord.DMChannel)
            msg = await bot.wait_for("message", check=check, timeout=120)
            user_responses[user.id] = {"response": "no", "reason": msg.content}
            await user.send("Dziękuję! Twój powód został zapisany.")
        except asyncio.TimeoutError:
            await user.send("Nie otrzymałem odpowiedzi w ciągu 2 minut.")
        except discord.Forbidden:
            print(f"Nie mogłem wysłać DM do {user}")

    await update_poll_embed(reaction.message.channel)


@bot.event
async def on_reaction_remove(reaction, user):
    """Obsługa zmiany decyzji użytkownika (usunięcie reakcji)"""
    if user == bot.user or reaction.message.author != bot.user:
        return
    if user.id in user_responses:
        del user_responses[user.id]
    await update_poll_embed(reaction.message.channel)

@bot.command(name="pomoc")
@commands.has_role(ADMIN_ROLE_NAME)
async def pomoc(ctx):
    help_text = (
        "**📖 Instrukcja obsługi bota:**\n\n"
        "🔧 **Ustawienia spotkania:**\n"
        "`!setGodzina <godzina>`\n"
        "`!setBudynek <nazwa>`\n"
        "`!setSala <numer>`\n\n"
        "📅 **Tworzenie ankiety:**\n"
        "`!ankieta <data>` — np. `!ankieta 12.12.2025`\n\n"
        "📋 **Lista odpowiedzi:**\n"
        "Aktualizowana dynamicznie po reakcjach.\n\n"
        "📬 **Wyświetlanie wyników dla admina:**\n"
        "`!odpowiedzi` — wysyła prywatnie listę obecnych i nieobecnych."
    )
    await ctx.author.send(help_text)
    await ctx.message.add_reaction("✅")

@bot.command(name="odpowiedzi")
@commands.has_role(ADMIN_ROLE_NAME)
async def show_responses(ctx):
    channel = ctx.channel
    await update_poll_embed(channel)
    await ctx.author.send("📋 Aktualny stan ankiety został wysłany na DM.")

bot.run(TOKEN)
