import os
from aiohttp import web

async def index(request):
    return web.FileResponse("build/web/index.html")

app = web.Application()
app.router.add_get("/", index)
app.router.add_static("/", "build/web")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
