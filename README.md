
[![Discord](https://discord.com/api/guilds/812811774831231016/widget.png)](https://discord.gg/B4k9sar2ke)

# Incident Reporter

Incident Reporter, the ideal bot for managing incidents.

- [Invite Me!](https://discord.com/oauth2/authorize?client_id=812700360450768896&scope=bot&permissions=19456)

![Example](https://cdn.discordapp.com/attachments/808282485104443393/812733121539604500/example.png)

## Deployment

- **Redis**

Incident uses [redis](https://redis.io) as database, so you'll need to 
install it and run a server.  
I recommend hosting it locally for minimum latency.

- **Python dependencies**

All python dependencies are in `requirements.txt`, you can install them with
`pip install -r requirements.txt`

Optionally, on Unix system, you can install [uvloop](https://pypi.org/project/uvloop/) 
for a faster asyncio implementation.

<details>
<summary>Commands</summary>
<p>

  - Unix
    
    ```bash
    python3 -m pip install -r requirements.txt
    
    # Optional
    python3 -m pip install uvloop
    ```
  
  - Windows
    
    ```
    py -3 -m pip install -r requirements.txt
    ```
  
</p>
</details>

- **Config**

Put your discord bot token into config.ini and optionally adjust the URI
to your redis server.

- **Run**

You can now execute `run.py` to start the bot.
