import asyncio,json
from playwright.async_api import async_playwright
def lum(h):
    h=h.lstrip('#'); c=[int(h[i:i+2],16)/255 for i in (0,2,4)]
    c=[x/12.92 if x<=0.03928 else ((x+0.055)/1.055)**2.4 for x in c]; return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
def cr(a,b): A,B=sorted([lum(a),lum(b)],reverse=True); return (A+0.05)/(B+0.05)
L={"ink/bg":("#0d1735","#eef1f6"),"ink/surface":("#0d1735","#fcfcfc"),"muted/surface":("#56637f","#fcfcfc"),"muted/surface2":("#56637f","#f3f5f9"),"accent-ink/info-bg":("#0a6a88","#e1f3f9"),
"green/green-bg":("#12804a","#e3f4ea"),"amber/amber-bg":("#a86400","#fbefdc"),"red/red-bg":("#c3303c","#fbe5e7"),"btn-primary":("#04202b","#1ba6cf"),"link/surface":("#0a6a88","#fcfcfc")}
D={"ink/bg":("#e6f4fa","#070b16"),"muted/surface":("#9aabc8","#0e1527"),"accent-ink/info-bg":("#6fdcf9","#0d2633"),"green/green-bg":("#3ccf7d","#0f2a1d"),"amber/amber-bg":("#f2b441","#2c2109"),"red/red-bg":("#ff6f78","#2e1218"),"link/surface":("#6fdcf9","#0e1527")}
res={"light":{k:round(cr(*v),2) for k,v in L.items()},"dark":{k:round(cr(*v),2) for k,v in D.items()}}
print(json.dumps(res,indent=0)); print("min",min(min(r.values()) for r in res.values()))
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=["--no-sandbox","--use-angle=swiftshader"])
        pg=await b.new_page(viewport={"width":1366,"height":860})
        await pg.add_init_script("localStorage.setItem('astra.tour.astro1','done');sessionStorage.setItem('astra.introShown','1');localStorage.setItem('astra.trans','none')")
        await pg.goto("http://127.0.0.1:8765/"); await pg.click("[data-act=demoLogin][data-u=astro1]"); await pg.wait_for_selector("#nav .navbtn"); await pg.wait_for_timeout(800)
        out={}
        for v in ["dashboard","body3d","measure","posecheck","simulate","science","history","settings","help"]:
            await pg.evaluate(f"go('{v}')"); await pg.wait_for_timeout(900)
            out[v]=await pg.evaluate("""()=>{const bad=[...document.querySelectorAll('button,a,input,select,textarea,[role=button]')].filter(e=>e.offsetParent!==null).filter(e=>{
               const n=(e.getAttribute('aria-label')||e.textContent||e.title||e.value||'').trim(); const lab=e.id&&document.querySelector('label[for="'+e.id+'"]'); const wrapped=e.closest('label');
               return !n && !lab && !wrapped && e.type!=='hidden'}).map(e=>e.outerHTML.slice(0,90));
               const small=[...document.querySelectorAll('#main button')].filter(e=>e.offsetParent&&(e.getBoundingClientRect().height<36)).length;
               return {unlabeled:bad.slice(0,5),n_unlabeled:bad.length,small_targets:small,h2:!!document.querySelector('#main h2'),lang:document.documentElement.lang,dir:document.documentElement.dir}}""")
        # keyboard: tab through sidebar & activate
        await pg.evaluate("go('dashboard')"); await pg.wait_for_timeout(600)
        await pg.focus("#nav .navbtn[data-v=charts]"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(700)
        out["keyboard_nav_enter"]=await pg.evaluate("S.view")
        foc=[]; await pg.focus("body")
        for i in range(12): await pg.keyboard.press("Tab"); foc.append(await pg.evaluate("document.activeElement.tagName+'#'+(document.activeElement.id||document.activeElement.dataset.v||'')"))
        out["tab_order_sample"]=foc
        out["focus_ring_css"]=await pg.evaluate("[...document.styleSheets].some(s=>[...s.cssRules].some(r=>r.selectorText===':focus-visible'))")
        print(json.dumps(out,ensure_ascii=False,indent=0)); json.dump({"contrast":res,"pages":out},open("/tmp/ui/a11y_results.json","w"),ensure_ascii=False,indent=1)
        await b.close()
asyncio.run(main())
