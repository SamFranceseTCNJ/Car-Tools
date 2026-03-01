from aiohttp import web

def get_group_latest(bridge, group: str):
    groups = {
        "live": bridge.live_data_latest,
        "engine": bridge.engine_data_latest,
        "fuel_air": bridge.fuel_air_data_latest,
        "status": bridge.status_data_latest,
        "diagnostics": bridge.diagnostics_data_latest,
    }
    return groups.get(group)

@web.middleware
async def cors(request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        resp = await handler(request)
        
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

async def api_health(request):
    return web.json_response({"ok": True})

async def api_snapshot(request):
    bridge = request.app["bridge"]
    return web.json_response(bridge.snapshot())

async def api_group(request):
    bridge = request.app["bridge"]
    group = request.match_info["group"]
    data = get_group_latest(bridge, group)
    if data is None:
        return web.json_response({"error": "unknown group", "group": group}, status=404)
    return web.json_response(data)

async def api_refresh_diagnostics(request):
    bridge = request.app["bridge"]
    data = await bridge.refresh_diagnostics()
    return web.json_response(data)

async def start_api_server(bridge, host="127.0.0.1", port=8080):
    app = web.Application(middlewares=[cors])
    app["bridge"] = bridge

    app.router.add_get("/api/health", api_health)
    app.router.add_get("/api/snapshot", api_snapshot)
    app.router.add_get("/api/group/{group}", api_group)
    app.router.add_post("/api/diagnostics/refresh", api_refresh_diagnostics)
    app.router.add_route("OPTIONS", "/{tail:.*}", lambda r: web.Response(status=204))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"HTTP API running at http://{host}:{port}")
    return runner