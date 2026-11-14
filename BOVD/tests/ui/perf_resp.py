import asyncio,json,time
from playwright.async_api import async_playwright
ARGS=["--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader"]
async def main():
    out={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=ARGS)
        for (w,h,name,dark) in [(1920,1080,"desktop_1920",False),(1366,768,"laptop_1366",True),(768,1024,"tablet_768",False),(375,812,"phone_375",False)]:
            ctx=await b.new_context(viewport={"width":w,"height":h},has_touch=w<800,is_mobile=w<500,color_scheme="dark" if dark else "light")
            pg=await ctx.new_page()
            await pg.add_init_script("localStorage.setItem('astra.tour.astro1','done');sessionStorage.setItem('astra.introShown','1');localStorage.setItem('astra.trans','none')")
            t=time.time(); await pg.goto("http://127.0.0.1:8765/"); await pg.wait_for_selector("[data-act=demoLogin]"); tl=time.time()-t
            nav=await pg.evaluate("JSON.stringify(performance.getEntriesByType('navigation')[0].toJSON())")
            await pg.click("[data-act=demoLogin][data-u=astro1]"); t=time.time(); await pg.wait_for_selector(".b3d-canvas"); t3=time.time()-t
            await pg.wait_for_timeout(1200)
            hs=await pg.evaluate("document.documentElement.scrollWidth>innerWidth+1")
            await pg.screenshot(path=f"/tmp/ui/r_{name}.png")
            if w<800:
                await pg.click("#bottomnav [data-act=menu]"); await pg.wait_for_timeout(400); await pg.screenshot(path=f"/tmp/ui/r_{name}_menu.png")
                await pg.keyboard.press("Escape")
            mem=await pg.evaluate("performance.memory?Math.round(performance.memory.usedJSHeapSize/1e6):null")
            n=json.loads(nav); out[name]={"login_page_s":round(tl,2),"domContentLoaded_ms":round(n["domContentLoadedEventEnd"]),"dash_with_3d_s":round(t3,2),"hscroll":hs,"js_heap_mb":mem,"perf3d":await pg.evaluate("S.b3d&&S.b3d.perf()")}
            await ctx.close()
        await b.close()
    import os
    out["js_total_kb"]=round(sum(os.path.getsize("/home/claude/ASTRA-Health/web/"+f) for f in os.listdir("/home/claude/ASTRA-Health/web") if f.endswith((".js",".css",".html")))/1024,1)
    print(json.dumps(out,indent=1)); json.dump(out,open("/tmp/ui/perf_results.json","w"),indent=1)
asyncio.run(main())
