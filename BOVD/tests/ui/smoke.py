import asyncio, json, sys
from playwright.async_api import async_playwright
B="http://127.0.0.1:8765/"
ARGS=["--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader","--use-fake-ui-for-media-stream","--use-fake-device-for-media-stream"]
async def main():
    roles=sys.argv[1].split(",") if len(sys.argv)>1 else ["astro1","cmo1","bhs1","surgeon1","research1"]
    out={}
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=ARGS)
        for u in roles:
            ctx=await b.new_context(viewport={"width":int(__import__("os").environ.get("W","1366")),"height":860})
            pg=await ctx.new_page(); errs=[]
            pg.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
            pg.on("pageerror",lambda e: errs.append("PAGEERR "+str(e)))
            await pg.add_init_script("localStorage.setItem('astra.tour.%s','done');sessionStorage.setItem('astra.introShown','1')"%u)
            await pg.goto(B); await pg.wait_for_selector("[data-act=demoLogin]")
            await pg.click(f"[data-act=demoLogin][data-u={u}]"); await pg.wait_for_selector("#nav .navbtn")
            views=await pg.eval_on_selector_all("#nav .navbtn","e=>e.map(x=>x.dataset.v)")
            res={}
            for v in views:
                n=len(errs)
                await pg.evaluate(f"go('{v}')"); await pg.wait_for_timeout(700)
                txt=await pg.inner_text("#main")
                hs=await pg.evaluate("document.documentElement.scrollWidth>innerWidth+1")
                res[v]={"err":errs[n:], "fail":"⚠" in txt[:60] and "Retry" in txt or "إعادة المحاولة" in txt, "hscroll":hs}
            out[u]=res; await ctx.close()
        await b.close()
    for u,r in out.items():
        bad={v:x for v,x in r.items() if x["err"] or x["fail"] or x["hscroll"]}
        print(u, len(r),"views", "OK" if not bad else json.dumps(bad,ensure_ascii=False)[:1500])
asyncio.run(main())
