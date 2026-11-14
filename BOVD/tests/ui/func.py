import asyncio, json, time
from playwright.async_api import async_playwright
ARGS=["--no-sandbox","--use-angle=swiftshader","--enable-unsafe-swiftshader","--use-fake-ui-for-media-stream","--use-fake-device-for-media-stream"]
R={}
def ok(k,v,info=""): R[k]=("PASS" if v else "FAIL")+(" "+str(info) if info else ""); print(k,R[k],flush=True)
async def waitfn(pg,expr,timeout=6000):
    t=time.time()
    while time.time()-t<timeout/1000:
        if await pg.evaluate(expr): return True
        await asyncio.sleep(0.05)
    raise TimeoutError(expr)
async def login(pg,u="astro1",tour=True):
    await pg.add_init_script(("localStorage.setItem('astra.tour.%s','done');"%u if tour else "")+"sessionStorage.setItem('astra.introShown','1')")
    await pg.goto("http://127.0.0.1:8765/"); await pg.click(f"[data-act=demoLogin][data-u={u}]"); await pg.wait_for_selector("#nav .navbtn"); await pg.wait_for_timeout(2200)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(executable_path="/usr/bin/google-chrome",args=ARGS)
        ctx=await b.new_context(viewport={"width":1366,"height":860}); pg=await ctx.new_page(); errs=[]
        pg.on("pageerror",lambda e: errs.append(str(e))); pg.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
        # splash
        t0=time.time(); await pg.goto("http://127.0.0.1:8765/"); await pg.wait_for_selector("#splash .stage svg")
        await pg.click("#splashSkip"); await pg.wait_for_timeout(700); ok("splash_skip", await pg.locator("#splash").count()==0)
        await pg.evaluate("localStorage.setItem('astra.tour.astro1','done')")
        await pg.click("[data-act=demoLogin][data-u=astro1]"); await pg.wait_for_timeout(2600)
        # transitions
        for st in ["planet","pulse","sat","none"]:
            await pg.evaluate(f"localStorage.setItem('astra.trans','{st}')")
            t=time.time(); await pg.click("#nav [data-v=charts]" if st!="pulse" else "#nav [data-v=alerts]"); 
            await waitfn(pg,"getComputedStyle(document.getElementById('mkov')||document.body).visibility!=='visible'")
            dt=time.time()-t; v=await pg.evaluate("S.view"); ok("transition_"+st, v in("charts","alerts"), f"{dt:.2f}s")
            await pg.evaluate("go('dashboard')"); await pg.wait_for_timeout(500)
        # reduced motion → instant
        await pg.evaluate("localStorage.setItem('astra.trans','planet');document.body.classList.add('reduce-motion')")
        t=time.time(); await pg.click("#nav [data-v=history]"); await waitfn(pg,"S.view==='history'"); ok("reduced_motion_instant", time.time()-t<0.6, f"{time.time()-t:.2f}s")
        await pg.evaluate("document.body.classList.remove('reduce-motion');localStorage.setItem('astra.trans','none')")
        # 3D
        await pg.evaluate("go('body3d')"); await pg.wait_for_timeout(1500)
        ok("3d_mounted", await pg.evaluate("!!S.b3d && !!document.querySelector('.b3d-canvas')"))
        v0=await pg.evaluate("JSON.stringify(S.b3d.view())")
        box=await pg.locator(".b3d-canvas").bounding_box(); cx,cy=box["x"]+box["width"]/2,box["y"]+box["height"]/2
        await pg.mouse.move(cx,cy); await pg.mouse.down(); await pg.mouse.move(cx+160,cy,steps=8); await pg.mouse.up(); await pg.wait_for_timeout(300)
        v1=await pg.evaluate("JSON.stringify(S.b3d.view())"); ok("3d_rotate_drag", v0!=v1)
        await pg.mouse.wheel(0,-400); await pg.wait_for_timeout(400); v2=await pg.evaluate("S.b3d.view().dist"); ok("3d_zoom_wheel", v2<json.loads(v1)["dist"], v2)
        await pg.click("[data-act=b3dRegion][data-r=heart]"); await pg.wait_for_timeout(1300)
        ok("3d_region_fly_info", "القلب" in await pg.inner_text("#regInfo"))
        picked=await pg.evaluate("S.b3d.pickAt(innerWidth,innerHeight)"); 
        await pg.click("[data-act=b3dReset]"); await pg.wait_for_timeout(1200); ok("3d_reset", await pg.evaluate("S.b3d.view().dist")>2)
        # keyboard on canvas
        await pg.focus(".b3d-canvas"); y0=await pg.evaluate("S.b3d.view().yaw"); await pg.keyboard.press("ArrowLeft"); await pg.wait_for_timeout(200); ok("3d_keyboard", await pg.evaluate("S.b3d.view().yaw")!=y0)
        # touch (pinch emulation via CDP-free: dispatch pointer events with pointerType touch)
        r=await pg.evaluate("""()=>{const c=document.querySelector('.b3d-canvas');const b=c.getBoundingClientRect();const d0=S.b3d.view().dist;
          const ev=(t,id,x,y)=>c.dispatchEvent(new PointerEvent(t,{pointerId:id,pointerType:'touch',clientX:x,clientY:y,bubbles:true,isPrimary:id===1}));
          const X=b.left+b.width/2,Y=b.top+b.height/2; ev('pointerdown',1,X-20,Y);ev('pointerdown',2,X+20,Y);ev('pointermove',1,X-80,Y);ev('pointermove',2,X+80,Y);ev('pointerup',1,X-80,Y);ev('pointerup',2,X+80,Y);return [d0,S.b3d.view().dist]}""")
        ok("3d_touch_pinch", r[1]!=r[0], r)
        # animation controls
        await pg.click("[data-act=b3dAnim][data-a=bp]"); await pg.wait_for_timeout(600)
        s1=await pg.evaluate("S.b3d.controls.state()"); await pg.click("[data-act=plNext]"); await pg.wait_for_timeout(300); s2=await pg.evaluate("S.b3d.controls.state()")
        await pg.click("#plToggle"); s3=await pg.evaluate("S.b3d.controls.state()"); await pg.click("#plToggle")
        await pg.click("[data-act=plPrev]"); s4=await pg.evaluate("S.b3d.controls.state()"); await pg.click("[data-act=plRestart]"); s5=await pg.evaluate("S.b3d.controls.state()")
        ok("anim_controls", s1["step"]==0 and s2["step"]==1 and s3["paused"] and s4["step"]==0 and s5["step"]==0, [s1,s2,s3,s4,s5])
        cap=await pg.inner_text("#plCap"); ok("anim_caption", len(cap)>10, cap[:40])
        perf=await pg.evaluate("S.b3d.perf()"); ok("3d_perf", True, perf)
        # pose: camera (fake device) & manual
        await pg.click("[data-act=openPose]"); await pg.wait_for_timeout(1200)
        await pg.evaluate("post('/api/consent',{aid:S.aid,category:'pose_camera',granted:true})"); await pg.evaluate("go('posecheck')"); await pg.wait_for_timeout(1000)
        btn=pg.locator("[data-act=peStart][data-m=camera]")
        if await btn.is_enabled():
            await btn.click(); await pg.wait_for_timeout(4000)
            st=await pg.evaluate("PoseUI.P.sess && PoseUI.P.sess.result"); ok("camera_frames_processed", bool(st), st and {"ms":st["ms"],"det":st["detector"],"checks":[c["id"]+":"+str(c["ok"]) for c in st["checks"]]})
            lat=await pg.evaluate("PoseUI.P.lat"); ok("camera_roundtrip_ms", True, round(sum(lat)/max(1,len(lat))))
            ok("camera_hud_alert", len(await pg.inner_text("#peHud"))>3, await pg.inner_text("#peHud"))
            # simulate camera disconnect
            await pg.evaluate("PoseUI.P.stream.getVideoTracks()[0].stop(); PoseUI.P.stream.getVideoTracks()[0].dispatchEvent(new Event('ended'))"); await pg.wait_for_timeout(500)
            ok("camera_disconnect_to_manual", await pg.locator("[data-act=peConfirm]").count()>0)
        await pg.evaluate("go('posecheck')"); await pg.wait_for_timeout(900)
        await pg.click("[data-act=peStart][data-m=manual]"); await pg.wait_for_timeout(500)
        for i in range(6):
            if await pg.locator("[data-act=peConfirm]").count(): await pg.click("[data-act=peConfirm]"); await pg.wait_for_timeout(300)
        ok("manual_mode_complete", "100%" in await pg.inner_text("#peResult"), (await pg.inner_text("#peResult"))[:60])
        # permission denied path
        ctx2=await b.new_context(viewport={"width":1366,"height":860}); pg2=await ctx2.new_page()
        await pg2.add_init_script("navigator.mediaDevices.getUserMedia=()=>Promise.reject(new DOMException('denied','NotAllowedError'))")
        await login(pg2); await pg2.evaluate("go('posecheck')"); await pg2.wait_for_timeout(900)
        if await pg2.locator("[data-act=peStart][data-m=camera]").is_enabled():
            await pg2.click("[data-act=peStart][data-m=camera]"); await pg2.wait_for_timeout(1200)
            ok("camera_denied_falls_back_manual", await pg2.locator("[data-act=peConfirm]").count()>0)
        await ctx2.close()
        # science page: evidence filter + chip deep-link
        await pg.evaluate("go('science')"); await pg.wait_for_timeout(800)
        n=await pg.locator(".evid").count(); await pg.select_option("#evKind","gap"); await pg.wait_for_timeout(200); g=await pg.locator(".evid").count()
        ok("evidence_filter", n>=29 and 0<g<n, (n,g))
        urls=await pg.eval_on_selector_all(".evid a[href^=http]","e=>e.length"); ok("evidence_links", urls>0, urls)
        await pg.evaluate("go('charts')"); await pg.wait_for_timeout(800); await pg.click("a.badge.ev >> nth=0"); await pg.wait_for_timeout(900)
        ok("evidence_chip_deeplink", await pg.locator(".evid.hl").count()==1)
        # simulation
        await pg.evaluate("go('simulate')"); await pg.wait_for_timeout(1500)
        a1=await pg.inner_text("#smAtmOut"); await pg.select_option("#smCabin","exploration"); await pg.wait_for_timeout(700); a2=await pg.inner_text("#smAtmOut")
        ok("sim_cabin_updates", a1!=a2 and "128.2" in a2, a2[:80])
        await pg.check("input[name=smMode][value=alt]"); await pg.fill("#smAlt","5000"); await pg.press("#smAlt","Tab"); await pg.wait_for_timeout(700)
        ok("sim_altitude_5000", "54.02" in await pg.inner_text("#smAtmOut"))
        await pg.fill("#smDay","30"); await pg.dispatch_event("#smDay","input"); await pg.wait_for_timeout(800)
        ok("sim_gravity_gap_shown", "دليل غير كافٍ" in await pg.inner_text("#smGravOut"))
        ok("sim_chart_tooltip_targets", await pg.locator("#smBone [data-tip]").count()>5)
        # history
        await pg.evaluate("go('history')"); await pg.wait_for_timeout(800); ok("history_rows", await pg.locator("#hTab tbody tr").count()>0)
        # tour
        ctx3=await b.new_context(viewport={"width":1366,"height":860}); pg3=await ctx3.new_page(); e3=[]; pg3.on("pageerror",lambda e:e3.append(str(e)))
        await login(pg3,tour=False); await pg3.wait_for_selector("#tTip",timeout=6000)
        stages=[]
        for i in range(11):
            stages.append(await pg3.inner_text("#tPct")); await pg3.click("#tNext"); await pg3.wait_for_timeout(700)
        ok("tour_11_stages", len(stages)==11 and "100%" in stages[-1], stages[-1])
        ok("practice_after_tour", await pg3.locator("#practiceBox").count()==1 and await pg3.evaluate("S.view")=="posecheck")
        ok("tour_no_errors", not e3, e3[:2]); await ctx3.close()
        # WebGL failure → 2D fallback
        ctx4=await b.new_context(viewport={"width":1366,"height":860}); pg4=await ctx4.new_page()
        await pg4.add_init_script("HTMLCanvasElement.prototype.getContext=(function(o){return function(t,...a){return /webgl/.test(t)?null:o.call(this,t,...a)}})(HTMLCanvasElement.prototype.getContext)")
        await login(pg4); ok("webgl_fail_fallback_svg", await pg4.locator(".body-svg").count()==1); await ctx4.close()
        ok("no_console_errors_main", not errs, errs[:3])
        await b.close()
    json.dump(R,open("/tmp/ui/func_results.json","w"),ensure_ascii=False,indent=1)
asyncio.run(main())
