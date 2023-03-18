import os
import discord
from discord.ext import commands
import requests
import datetime
import pytz

DISCORD_TOKEN = 'your discord bot token here'

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_next_race():
    current_year = datetime.datetime.now().year
    response = requests.get(f'http://ergast.com/api/f1/{current_year}.json')
    data = response.json()

    races = data['MRData']['RaceTable']['Races']
    today = datetime.datetime.now().date()

    for race in races:
        race_date = datetime.datetime.strptime(race['date'], '%Y-%m-%d').date()
        if race_date > today:
            return race
    return None
    
def get_race_info(mode='next'):
    current_year = datetime.datetime.now().year
    url = f'http://ergast.com/api/f1/{current_year}.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']

    if mode == 'all':
        return races

    today = datetime.date.today()
    for race in races:
        race_date = datetime.datetime.strptime(race['date'], '%Y-%m-%d').date()
        if mode == 'current' and race_date == today:
            return race
        elif mode == 'next' and race_date > today:
            return race

    return None


def convert_to_nz_time(date_str, time_str):
    naive_time = datetime.datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
    utc_time = pytz.utc.localize(naive_time)
    nz_time = utc_time.astimezone(pytz.timezone('Pacific/Auckland'))
    return nz_time.strftime('%Y-%m-%d %H:%M:%S')
    
def get_standings(url):
    response = requests.get(url)
    data = response.json()
    return data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']

def get_constructor_standings(url):
    response = requests.get(url)
    data = response.json()
    return data['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings']

def get_qualifying_results(year, round):
    url = f'http://ergast.com/api/f1/{year}/{round}/qualifying.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']
    if not races:
        return None
    return races[0]['QualifyingResults']
    
def get_latest_race_with_qualifying_results():
    current_year = datetime.datetime.now().year
    url = f'http://ergast.com/api/f1/{current_year}/qualifying.json'
    response = requests.get(url)
    data = response.json()
    races = data['MRData']['RaceTable']['Races']

    if not races:
        return None

    latest_race = races[-1]
    return latest_race


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='driver_standings', help='Get the current driver standings.')
async def driver_standings(ctx):
    current_year = datetime.datetime.now().year
    url = f'http://ergast.com/api/f1/{current_year}/driverStandings.json'
    standings = get_standings(url)

    embed = discord.Embed(title=f"Formula 1 {current_year} Driver Standings",
                          color=discord.Color.blue())

    for standing in standings:
        driver_name = f"{standing['Driver']['givenName']} {standing['Driver']['familyName']}"
        embed.add_field(name=f"#{standing['position']} - {driver_name}",
                        value=f"Points: {standing['points']}\nTeam: {standing['Constructors'][0]['name']}",
                        inline=False)

    await ctx.send(embed=embed)

@bot.command(name='constructor_standings', help='Get the current constructor standings.')
async def constructor_standings(ctx):
    current_year = datetime.datetime.now().year
    url = f'http://ergast.com/api/f1/{current_year}/constructorStandings.json'
    standings = get_constructor_standings(url)

    embed = discord.Embed(title=f"Formula 1 {current_year} Constructor Standings",
                          color=discord.Color.blue())

    for standing in standings:
        constructor_name = standing['Constructor']['name']
        embed.add_field(name=f"#{standing['position']} - {constructor_name}",
                        value=f"Points: {standing['points']}",
                        inline=False)

    await ctx.send(embed=embed)
    
@bot.command(name='starting_grid', help='Get the starting positions for the next race.')
async def starting_grid(ctx):
    race = get_next_race()

    if race:
        year = race['season']
        round = race['round']
        qualifying_results = get_qualifying_results(year, round)

        if qualifying_results is None:
            await ctx.send("Qualifying results are not yet available for the next race.")
            return

        embed = discord.Embed(title=f"Starting Grid for {race['raceName']}",
                              description=f"Date: {race['date']}\nCircuit: {race['Circuit']['circuitName']}",
                              color=discord.Color.blue())

        for result in qualifying_results:
            driver_name = f"{result['Driver']['givenName']} {result['Driver']['familyName']}"
            embed.add_field(name=f"#{result['position']} - {driver_name}",
                            value=f"Team: {result['Constructor']['name']}",
                            inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send("There are no more races scheduled for this season or qualifying results are not yet available for the next race.")
        
        
@bot.command(name='qualifying_results', help='Get the latest qualifying results.')
async def qualifying_results(ctx):
    race = get_latest_race_with_qualifying_results()

    if race:
        year = race['season']
        round = race['round']
        qualifying_results = get_qualifying_results(year, round)

        embed = discord.Embed(title=f"Qualifying Results for {race['raceName']}",
                              description=f"Date: {race['date']}\nCircuit: {race['Circuit']['circuitName']}",
                              color=discord.Color.blue())

        for result in qualifying_results:
            driver_name = f"{result['Driver']['givenName']} {result['Driver']['familyName']}"
            embed.add_field(name=f"#{result['position']} - {driver_name}",
                            value=f"Team: {result['Constructor']['name']}",
                            inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send("There are no qualifying results available for this season.")


@bot.command(name='current_race', help='Get information about the current race, including the time in NZT.')
async def current_race(ctx):
    race = get_race_info(mode='current')

    if race:
        race_name = race['raceName']
        circuit_name = race['Circuit']['circuitName']
        date_str = race['date']
        time_str = race['time'][:-1]  # Remove the 'Z' from the time string
        nz_time_str = convert_to_nz_time(date_str, time_str)

        embed = discord.Embed(title=f"Current Race: {race_name}",
                              description=f"Circuit: {circuit_name}",
                              color=discord.Color.blue())

        embed.add_field(name="Date", value=date_str, inline=True)
        embed.add_field(name="Local Time", value=time_str, inline=True)
        embed.add_field(name="NZT", value=nz_time_str, inline=True)

        await ctx.send(embed=embed)
    else:
        await ctx.send("There is no race happening today.")

@bot.command(name='schedule', help='Get the schedule of races for the current season.')
async def schedule(ctx):
    races = get_race_info(mode='all')

    if races:
        embed = discord.Embed(title=f"Formula 1 {races[0]['season']} Schedule",
                              color=discord.Color.blue())

        for race in races:
            race_name = race['raceName']
            circuit_name = race['Circuit']['circuitName']
            date_str = race['date']
            time_str = race['time'][:-1]  # Remove the 'Z' from the time string
            nz_time_str = convert_to_nz_time(date_str, time_str)

            embed.add_field(name=f"{race_name} - {circuit_name}", value=f"Date: {date_str}\nUTC: {time_str}\nNZT: {nz_time_str}", inline=False)

        await ctx.send(embed=embed)
    else:
        await ctx.send("No races found for this season.")


@bot.command(name='next_race', help='Get information about the next race, or the current race if there is one happening, including the time in NZT.')
async def next_race(ctx):
    current_race = get_race_info(mode='current')
    race = current_race if current_race else get_race_info(mode='next')
    race_status = "Current Race" if current_race else "Next Race"

    if race:
        race_name = race['raceName']
        circuit_name = race['Circuit']['circuitName']
        date_str = race['date']
        time_str = race['time'][:-1]  # Remove the 'Z' from the time string
        nz_time_str = convert_to_nz_time(date_str, time_str)

        embed = discord.Embed(title=f"{race_status}: {race_name}",
                              description=f"Circuit: {circuit_name}",
                              color=discord.Color.blue())

        embed.add_field(name="Date", value=date_str, inline=True)
        embed.add_field(name="UTC", value=time_str, inline=True)
        embed.add_field(name="NZT", value=nz_time_str, inline=True)

        await ctx.send(embed=embed)
    else:
        await ctx.send("There are no more races scheduled for this season.")

bot.run(DISCORD_TOKEN)






