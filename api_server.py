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
    app = web.Application()
    app["bridge"] = bridge

    app.router.add_get("/api/snapshot", api_snapshot)
    app.router.add_get("/api/group/{group}", api_group)
    app.router.add_post("/api/diagnostics/refresh", api_refresh_diagnostics)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"HTTP API running at http://{host}:{port}")

    return runner