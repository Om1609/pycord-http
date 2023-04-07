import asyncio
import os

import orjson
from aiohttp import web
from discord.ext import commands
from dotenv import load_dotenv
from nacl.signing import VerifyKey

load_dotenv()


class MyBot(commands.Bot):
    def __init__(self, public_key: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.public_key = public_key
        self.init_webapp()

    def init_webapp(self):
        self.verify_key = VerifyKey(bytes.fromhex(self.public_key))
        self.inter_app = web.Application()
        self.inter_app.router.add_post("/interactions", self.web_inter_req)
        self.inter_runner = web.AppRunner(self.inter_app)

    async def web_inter_req(self, request: web.Request):
        signature = request.headers["X-Signature-Ed25519"]
        timestamp = request.headers["X-Signature-Timestamp"]
        body = await request.read()

        message = timestamp.encode() + body
        try:
            assert signature is not None
            assert timestamp is not None
            self.verify_key.verify(message, bytes.fromhex(signature))
        except:
            return web.Response(reason="invalid request signature", status=401)
        json: dict = orjson.loads(body)
        inter_type = json.get("type")
        if inter_type == 1:
            return web.json_response(body=orjson.dumps({"type": 1}))

        bot._connection.parse_interaction_create(json)
        await asyncio.sleep(3)
        return web.Response(status=200)

    async def start_app(self):
        await self.wait_until_ready()
        await self.inter_runner.setup()
        site = web.TCPSite(self.inter_runner, "0.0.0.0", os.getenv("PORT", 8080))
        await site.start()
        print("Webserver is ready")

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        self.loop.create_task(self.start_app())
        return await super().start(token, reconnect=reconnect)

    async def close(self):
        await asyncio.gather(self.inter_runner.cleanup(), super().close())


bot = MyBot(os.getenv("PUBLIC_KEY"), command_prefix="!")


@bot.event
async def on_ready():
    print("Bot is ready")


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.slash_command()
async def hello(ctx):
    await ctx.respond("Hello, world!")


bot.run(os.getenv("TOKEN"))
