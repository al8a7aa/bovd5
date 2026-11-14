import asyncio
from playwright.async_api import async_playwright
ARGS=["--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader","--use-fake-ui-for-media-stream","--use-fake-device-for-media-stream"]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=ARGS)
        pg=await b.new_page(viewport={"width":1366,"height":860})
        await pg.goto("http://127.0.0.1:8765/"); await pg.wait_for_timeout(2600); await pg.screenshot(path="splash.png")
        await pg.wait_for_timeout(6000); await pg.screenshot(path="login.png")
        await pg.evaluate("localStorage.setItem('astra.tour.astro1','done')")
        await pg.click("[data-act=demoLogin][data-u=astro1]"); await pg.wait_for_timeout(380); await pg.screenshot(path="trans_planet.png")
        await pg.wait_for_timeout(2500); await pg.screenshot(path="dash.png")
        await pg.evaluate("localStorage.setItem('astra.trans','pulse')"); await pg.click("#nav [data-v=simulate]"); await pg.wait_for_timeout(450); await pg.screenshot(path="trans_pulse.png")
        await pg.wait_for_timeout(2500); await pg.screenshot(path="sim.png",full_page=True)
        await pg.evaluate("localStorage.setItem('astra.trans','sat')"); await pg.click("#nav [data-v=body3d]"); await pg.wait_for_timeout(500); await pg.screenshot(path="trans_sat.png")
        await pg.wait_for_timeout(2500); await pg.click("[data-act=b3dAnim][data-a=bp]"); await pg.wait_for_timeout(2500); await pg.screenshot(path="b3d.png")
        await pg.evaluate("go('science')"); await pg.wait_for_timeout(900); await pg.screenshot(path="sci.png")
        await pg.evaluate("go('posecheck')"); await pg.wait_for_timeout(900); await pg.screenshot(path="pose.png")
        await pg.evaluate("go('settings')"); await pg.wait_for_timeout(900); await pg.screenshot(path="settings.png")
        await b.close()
asyncio.run(main())
