import discord
from discord import app_commands
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import datetime
from typing import Optional
from presets import tile_codes, towers
import os
from typing import Literal
from datetime import datetime, timezone

load_dotenv()

# Google Sheets Setup
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open('CT Hero Solos').sheet1

# Discord Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Config
VALID_TILES = tile_codes

def calculate_event():
    base_date = datetime(2025, 2, 4, 22, 0, tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)
    delta = current_time - base_date
    delta_seconds = delta.total_seconds()
    periods = delta_seconds // (14 * 86400)  # 14 days in seconds
    return 65 + int(periods)

@bot.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {bot.user}')

@tree.command(name="add", description="Add a new strat")
@app_commands.describe(
    tile="3-letter tile code",
    tower="Tower name",
    relics="Have you used relics?",
    daily="Have you used a daily relic?",
    media="Media URL (optional)",
    notes="Additional notes (optional)"
)
async def add_strat(interaction: discord.Interaction,
                   tile: str,
                   tower: towers,
                   relics: bool,
                   daily: bool,
                   media: Optional[str] = None,
                   notes: Optional[str] = None):
    # Validation
    tile = tile.upper()
    if tile not in VALID_TILES:
        return await interaction.response.send_message("Invalid tile code!", ephemeral=True)

    event = calculate_event()
    
    # Prepare data
    new_row = [
        event,
        tile,
        tower,
        relics,
        daily,
        media or 'None',
        notes or 'None',
        interaction.user.display_name
    ]
    
    sheet.append_row(new_row)
    await interaction.response.send_message("Strat added successfully!", ephemeral=True)

@tree.command(name="search", description="Search for strats")
@app_commands.describe(
    tile="Tile code (optional)",
    tower="Tower name (optional)",
    relics="Have relics been used? (optional)",
    daily="Have daily relics been used? (optional)"
)
async def search_strats(interaction: discord.Interaction,
                       event: Optional[int] = None,
                       tile: Optional[str] = None,
                       tower: Optional[str] = None,
                       relics: Optional[bool] = None,
                       daily: Optional[bool] = None):
    all_strats = sheet.get_values(range_name="A2:H")
    results = []
    for strat in all_strats:
        if event and strat[0] != str(event):
            continue
        if tile and strat[1] != tile.upper():
            continue
        if tower and strat[2] != tower:
            continue
        if relics and strat[3] != relics:
            continue
        if daily is not None and strat[4] != daily:
            continue
        results.append(strat)
    
    if not results:
        return await interaction.response.send_message("No strats found!", ephemeral=True)
    
    # Display first 10 results
    embed = discord.Embed(title=f"Found {len(results)} Strats")
    for idx, strat in enumerate(results[:10]):
        val_string = f"Event: {strat[0]}\nTile: {strat[1]}\nTower: {strat[2]}\nRelics used? : {strat[3]}\nDaily used? : {strat[4]}"
        if (strat[5] != "None"):
            val_string += f"\nLink: {strat[5]}"
        if (strat[6] != "None"):
            val_string += f"\nNotes: {strat[6]}"
        val_string += f"\nCompleted by {strat[7]}"
        embed.add_field(
            name=f"Result {idx+1}",
            value=val_string,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="admin_remove", description="Remove a strat (Admin only)")
@app_commands.describe(row_number="Spreadsheet row number to remove")
@app_commands.default_permissions(administrator=True)
async def remove_strat(interaction: discord.Interaction, row_number: int):
    if row_number < 2 or row_number > sheet.row_count:
        return await interaction.response.send_message("Invalid row number!", ephemeral=True)
        
    sheet.delete_rows(row_number)
    await interaction.response.send_message(f"Row {row_number} removed!", ephemeral=True)

bot.run(os.getenv('TOKEN'))