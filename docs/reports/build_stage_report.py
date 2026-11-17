"""Build a teacher stage report from this repository, with real UI captures.
Only a temporary demo database is used. No real model request or API key is used.
"""
from pathlib import Path
import os, sys, re, json, time, tempfile, subprocess, shutil, textwrap
import httpx
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.xmlchemy import OxmlElement

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/reports/2026-11-17/output"
ASSETS = OUT / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(exist_ok=True)
SOURCE = "f1396f10f6e4a6a1671f6e5ffdfd45222b3f528f"
BG, INK, BLUE, MUTED, LINE, TEAL, AMBER = "F5F7FB", "20324E", "3264D8", "52627A", "E0E7F1", "16866A", "B87926"
FONT = "Noto Sans CJK SC"
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333333), Inches(7.5)
prs.core_properties.title = "数据结构智育助教：阶段进展与系统架构"
prs.core_properties.subject = "2026-11-17 阶段汇报，含真实项目截图"
prs.core_properties.author = "数据结构智育助教项目"
notes = []
evidence = {}

def run(args, cwd=ROOT, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        print(result.stdout)
        raise RuntimeError("Command failed: " + " ".join(map(str, args)))
    return result.stdout

def prepare_and_capture():
    tmp = Path(tempfile.mkdtemp(prefix="zhiyu-report-"))
    env = {**os.environ, "APP_DB_PATH": str(tmp / "demo.db"), "VECTOR_DB_DIR": str(tmp / "vectors")}
    log = (OUT / "demo-server.log").open("w")
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"], cwd=ROOT / "backend", env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        base = "http://127.0.0.1:8765"
        for _ in range(90):
            try:
                if httpx.get(base + "/api/health", timeout=1).status_code == 200: break
            except Exception: pass
            time.sleep(1)
        else: raise RuntimeError("Demo server did not start")
        def post(path, data, token=None):
            r = httpx.post(base + path, json=data, headers={"Authorization": "Bearer " + token} if token else {}, timeout=30)
            r.raise_for_status()
            return r.json()
        teacher = post("/api/auth/register", {"username": "demo_teacher", "password": "demo123456", "role": "teacher", "display_name": "演示教师"})
        classroom = post("/api/classes", {"name": "数据结构与算法 · 阶段演示班", "term": "2026 秋季"}, teacher["token"])
        student = post("/api/auth/register", {"username": "demo_student", "password": "demo123456", "role": "student", "display_name": "演示学生"})
        post("/api/classes/join", {"code": classroom["code"]}, student["token"])
        (OUT / "seed-demo.log").write_text(run([sys.executable, "scripts/seed_demo.py"], cwd=ROOT / "backend", env=env), encoding="utf-8")
        node_code = r"""
const { chromium } = require(process.cwd() + '/frontend/node_modules/playwright');
const path = require('path');
(async () => {
 const browser = await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 const context = await browser.newContext({viewport:{width:1440,height:1050},deviceScaleFactor:1});
 const page = await context.newPage();
 page.setDefaultTimeout(20000);
 const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 const folder=process.env.REPORT_ASSETS;
 async function shot(name, selector='.view') {
   await page.evaluate(()=>window.scrollTo(0,0));
   await page.evaluate(()=>document.fonts.ready);
   await page.waitForTimeout(350);
   if(!selector) await page.screenshot({path:path.join(folder,name+'.png')});
   else {
     const b=await page.locator(selector).first().boundingBox();
     if(!b) throw Error('Missing screenshot target '+name);
     await page.screenshot({path:path.join(folder,name+'.png'),clip:{x:b.x,y:Math.max(b.y,0),width:b.width,height:Math.min(b.height,1025-Math.max(b.y,0))}});
   }
   console.log('Captured '+name);
 }
 async function login(user) {
   await page.goto('http://127.0.0.1:8765/');
   await page.locator('#username').fill(user);
   await page.locator('#password').fill('demo123456');
   await page.getByRole('button',{name:'登录',exact:true}).click();
   await page.locator('.shell').waitFor();
 }
 await page.goto('http://127.0.0.1:8765/');
 await page.locator('#username').waitFor(); await shot('login',null);
 await login('demo_stu01');
 await page.locator('.hello').waitFor(); await shot('student-home');
 let nav=page.getByRole('navigation',{name:'主要导航'});
 await nav.getByRole('button',{name:'作业中心',exact:true}).click();
 await page.locator('.detail h3').waitFor(); await shot('homework');
 await page.locator('.list .item').filter({hasText:'单链表插入训练'}).first().click();
 await page.locator('.grade-box').waitFor(); await shot('my-feedback');
 await nav.getByRole('button',{name:'学习助手',exact:true}).click();
 await page.locator('.chat-welcome').waitFor(); await shot('assistant');
 await page.getByRole('button',{name:'代码诊断',exact:true}).click();
 await page.locator('.cm-content').fill('void insertAfter(Node* p, Node* q) {\n    p->next = q;\n    q->next = p->next;\n}');
 await shot('code-diagnosis');
 await nav.getByRole('button',{name:'知识库',exact:true}).click();
 await page.locator('.cat-card').first().waitFor(); await shot('knowledge');
 await page.locator('.cat-card').last().click();
 await page.locator('.item-head').first().waitFor(); await page.locator('.item-head').first().click();
 await shot('knowledge-detail');
 await page.getByRole('button',{name:'模型设置',exact:true}).first().click();
 await page.getByRole('dialog').waitFor(); await shot('settings','[role="dialog"]'); await page.keyboard.press('Escape');
 await page.setViewportSize({width:390,height:844});
 await page.getByRole('navigation',{name:'移动端导航'}).getByRole('button',{name:'首页',exact:true}).click();
 await page.locator('.hello').waitFor(); await shot('mobile',null);
 await page.setViewportSize({width:1440,height:1050});
 page.once('dialog',d=>d.accept());
 await page.getByRole('button',{name:'退出登录',exact:true}).click();
 await login('demo_teacher');
 await page.getByRole('button',{name:'进入班级管理',exact:true}).waitFor(); await shot('teacher-home');
 await page.getByRole('button',{name:/去批阅/}).click();
 await page.locator('.teacher-panel').waitFor();
 await page.waitForTimeout(500);
 if(!await page.getByRole('dialog').isVisible()) await page.locator('#submission-list').getByRole('button',{name:'批阅',exact:true}).first().click();
 await page.getByRole('dialog').waitFor();
 await shot('grading','[role="dialog"]');
 await page.keyboard.press('Escape'); await shot('teacher-workspace');
 console.log(JSON.stringify({page_errors:errors}));
 if(errors.length) throw Error('Browser runtime errors');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
"""
        capfile = tmp / "capture.cjs"
        capfile.write_text(node_code, encoding="utf-8")
        capture_env = {**env, "REPORT_ASSETS": str(ASSETS)}
        capture_log = run(["node", str(capfile)], env=capture_env)
        (OUT / "capture.log").write_text(capture_log, encoding="utf-8")
        print(capture_log)
        evidence["screenshots"] = "2026-11-17 source branch, temporary seeded demo database; no live LLM call"
        tests_env = {**env, "E2E_BASE_URL": base}
        logs = {
            "backend-tests": run([sys.executable, "-m", "pytest", "tests", "-q"], cwd=ROOT / "backend", env=env),
            "frontend-tests": run(["npm", "test"], cwd=ROOT / "frontend", env=env),
            "browser-tests": run(["npm", "run", "test:e2e", "--", "--reporter=line"], cwd=ROOT / "frontend", env=tests_env),
        }
        for name, text in logs.items(): (OUT / (name + ".txt")).write_text(text, encoding="utf-8")
        evidence["test_counts"] = {
            "backend": int(re.search(r"(\d+) passed", logs["backend-tests"]).group(1)),
            "frontend": int(re.search(r"tests\s+(\d+)", logs["frontend-tests"]).group(1)),
            "browser": int(re.search(r"(\d+) passed", logs["browser-tests"]).group(1)),
        }
        print("TEST COUNTS", evidence["test_counts"])
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill()
        log.close()
    eval_log = run([sys.executable, "scripts/eval_rag.py", "--mode", "lexical", "--audience", "all", "--strict", "--output", str(OUT / "rag-evaluation.json")], cwd=ROOT / "backend", env=env)
    (OUT / "rag-evaluation.txt").write_text(eval_log, encoding="utf-8")
    evidence["evaluation"] = json.loads((OUT / "rag-evaluation.json").read_text(encoding="utf-8"))
    fontfiles = list(Path("/usr/share/fonts").rglob("NotoSansCJK-Regular.ttc"))
    fontpath = str(fontfiles[0])
    for name, title in [("rag-evaluation", "RAG 离线评测日志 · 本次构建实际执行"), ("backend-tests", "后端自动测试日志 · 本次构建实际执行")]:
        text = (OUT / (name + ".txt")).read_text(encoding="utf-8")
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        if name == "backend-tests":
            text = "\n".join([line for line in text.splitlines() if "passed" in line or "[100%]" in line][:3])
        lines = [title, "", "$ " + ("python scripts/eval_rag.py --mode lexical --audience all --strict" if name == "rag-evaluation" else "python -m pytest tests -q"), ""] + text.strip().splitlines()
        im = Image.new("RGB", (1500, max(320, 54 * len(lines) + 40)), "#12213A")
        draw = ImageDraw.Draw(im)
        f = ImageFont.truetype(fontpath, 28)
        for i, line in enumerate(lines): draw.text((35, 25 + i * 50), line[:105], font=f, fill="#DFE8F9" if i > 0 else "#8FB7FF")
        im.save(ASSETS / (name + ".png"))

def rgb(value): return RGBColor.from_string(value)
def shape(slide,x,y,w,h,fill="FFFFFF",line=None,rounded=False):
    s=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, Inches(x),Inches(y),Inches(w),Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb=rgb(fill)
    s.line.fill.background() if not line else None
    if line: s.line.color.rgb=rgb(line)
    if rounded:
        try: s.adjustments[0]=0.12
        except Exception: pass
    return s
def text(slide, value,x,y,w,h,size=20,color=INK,bold=False,align=None):
    s=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=s.text_frame;tf.clear();tf.word_wrap=True
    tf.margin_left=tf.margin_right=Inches(.02);tf.margin_top=tf.margin_bottom=Inches(.02)
    for i,line in enumerate(str(value).split("\n")):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text=line; p.font.name=FONT; p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=rgb(color)
        p.space_after=Pt(8);p.line_spacing=1.1
        if align is not None: p.alignment=align
        for run_ in p.runs:
            ea=OxmlElement("a:ea");ea.set("typeface",FONT);run_._r.get_or_add_rPr().append(ea)
    return s
def note(slide, title, body):
    slide.notes_slide.notes_text_frame.text=title+"\n\n"+body
    notes.append((title,body))
def page(title,kicker="项目阶段汇报",subtitle=""):
    s=prs.slides.add_slide(prs.slide_layouts[6])
    s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(BG)
    shape(s,.45,.42,.07,.62,BLUE)
    text(s,kicker,.68,.35,10,.28,11,BLUE,True)
    text(s,title,.65,.79,12.0,.65,29,INK,True)
    if subtitle: text(s,subtitle,.68,1.39,12,.42,13,MUTED)
    shape(s,.68,7.04,11.95,.012,LINE)
    text(s,"数据结构智育助教 · 2026.11.17",.7,7.13,8,.22,9,MUTED)
    text(s,f"{len(prs.slides):02d}",12.05,7.09,.55,.25,10,MUTED,align=PP_ALIGN.RIGHT)
    return s
def image(slide,name,x,y,w,h,caption="",bg="FFFFFF"):
    path=ASSETS/(name+".png")
    if not path.exists(): raise RuntimeError("Missing required screenshot "+str(path))
    shape(slide,x,y,w,h,bg,LINE,True)
    iw,ih=Image.open(path).size
    scale=min((w-.1)/iw,(h-.1)/ih)
    pw,ph=iw*scale,ih*scale
    slide.shapes.add_picture(str(path), Inches(x+(w-pw)/2),Inches(y+(h-ph)/2),width=Inches(pw),height=Inches(ph))
    if caption: text(slide,caption,x,y+h+.06,w,.38,10,MUTED)
def card(slide,title,body,x,y,w,h=1.35,num=None):
    shape(slide,x,y,w,h,"FFFFFF",LINE,True)
    if num is not None: text(slide,str(num),x+.18,y+.13,.4,.4,20,BLUE,True)
    dx=.75 if num is not None else .2
    text(slide,title,x+dx,y+.15,w-dx-.15,.4,18,INK,True)
    text(slide,body,x+.2,y+.65,w-.4,h-.7,14,MUTED)
def bullets(slide,items,x,y,w):
    for i,(head,body) in enumerate(items):
        yy=y+i*1.46
        text(slide,f"{i+1:02d}",x,yy,.48,.35,15,BLUE,True)
        text(slide,head,x+.56,yy,w-.56,.4,19,INK,True)
        text(slide,body,x+.56,yy+.51,w-.56,.84,15,MUTED)
def arrow(slide,x,y,w=.44,h=.24):
    s=slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x),Inches(y),Inches(w),Inches(h));s.fill.solid();s.fill.fore_color.rgb=rgb(BLUE);s.line.fill.background()
def feature(title,shot,items,body,caption="本次构建采集 · 临时演示数据"):
    s=page(title)
    bullets(s,items,.75,1.9,3.55)
    image(s,shot,4.65,1.76,7.95,4.85,caption)
    note(s,title,body)
    return s

def build_deck():
    counts=evidence["test_counts"]
    s=page("数据结构智育助教", "新阶段进展与系统架构", "面向《数据结构与算法》的启发式课程助教")
    text(s,"从功能跑通\n走向检索可靠与教学闭环",.8,2.0,4.55,1.65,28,INK,True)
    text(s,"学生学习空间 · 教师教学工作台\n课程知识支持 · 苏格拉底式引导",.82,4.03,4.2,1.0,19,MUTED)
    text(s,"汇报日期 2026.11.17\n源码依据 f1396f1（含 NumPy 索引更新）",.82,5.58,4.3,.9,13,BLUE)
    image(s,"student-home",5.5,1.9,7.1,4.7,"项目实际界面；所有班级和提交均为演示样例")
    note(s,"开场：项目定位","本项目面向数据结构与算法课程，目标不是替学生写答案，而是围绕任务、提问、代码诊断和教师反馈形成教学流程。本次汇报说明已经实现的模块、系统如何组织、RAG 如何改进，以及下一阶段还需要验证什么。截图为本次在独立临时数据库采集的演示界面，没有使用个人模型密钥或发起真实大模型请求。")

    s=page("本阶段进度：已有可演示闭环，正在完善质量验证","阶段总览","不使用主观“完成百分比”，按已实现、已验证和待验证区分进展")
    for x,title,body in [(.75,"功能闭环","学生任务、代码诊断、教师批阅与重做"),(4.85,"工程优化","统一界面、移动导航、草稿与错误恢复"),(8.95,"检索可靠性","混合召回、版本化索引、离线评测")]:
        card(s,title,body,x,1.95,3.75,1.55)
    image(s,"homework",.75,3.85,3.75,2.05,"任务与提交")
    image(s,"teacher-home",4.85,3.85,3.75,2.05,"教师概览")
    image(s,"knowledge-detail",8.95,3.85,3.75,2.05,"课程知识")
    text(s,"已实现：双端流程与 RAG 工程链路    已记录：本机建库与离线评测    待验证：真实问答质量与学习效果",.8,6.45,11.8,.4,13,BLUE)
    note(s,"阶段总览","功能层面已经能从教师发布任务走到学生提交、诊断、批阅和反馈。最近一阶段重点是界面与可用性，以及检索和索引的可靠性。必须区分功能实现和教学效果：本机建库、自动化测试和词法评测提供工程证据，但不能替代真实学生试用，也不能证明混合检索优于词法或模型绝不泄题。")

    s=page("业务组织架构：两类角色，共用课程助教服务","组织架构")
    card(s,"学生端","加入班级 / 完成任务\n提问 / 代码诊断 / 查看反馈",.8,1.95,3.55,1.7)
    card(s,"共享助教服务","身份与权限 / 对话编排\n课程检索 / 诊断与记录",4.9,1.95,3.55,1.7)
    card(s,"教师端","建班与发任务 / 统一建库\n批阅 / 学情分析 / 成绩导出",9.0,1.95,3.55,1.7)
    arrow(s,4.45,2.6);arrow(s,8.48,2.6)
    image(s,"student-home",.8,4.0,5.65,2.28,"学生角色入口")
    image(s,"teacher-home",6.85,4.0,5.65,2.28,"教师角色入口")
    note(s,"业务组织架构","这里的组织架构指系统内角色、功能模块与服务的分工，不虚构团队人员分工。学生和教师拥有不同入口与操作权限，底层共享认证、课程资料、检索、模型调用和数据记录。教师承担人工教学判断；AI 提供启发与诊断线索，未承担自动判题职责。")

    feature("学生学习空间：任务优先，反馈可见","student-home",
        [("待办与截止时间","优先处理退回任务，再按截止时间组织待办。"),("提交与教师反馈","查看提交状态、分数、评语和提交内容。"),("薄弱知识点","依据诊断信号展示学习参考，支持跳转知识点。")],
        "学生首页把待办任务、最近提交和知识点参考集中到一页。退回重做需要重新进入待办，不能仅用“是否提交过”来判断任务是否完成。知识点掌握度由诊断提示层级和严重程度等信号估算，不是经教学测量验证的精确分数。")

    s=page("作业中心：从提交记录回到可执行的下一步","学生模块","代码类进入诊断，问答类在任务内提交；教师退回后可重新完成")
    image(s,"homework",.75,1.92,5.75,4.25,"任务分类与详情")
    image(s,"my-feedback",6.85,1.92,5.75,4.25,"已批阅提交：分数、评语与原始内容")
    text(s,"待提交 → 待批阅 → 已批阅；被退回的任务进入“待重做”",.85,6.52,11.9,.35,16,BLUE,True)
    note(s,"作业中心","展示左侧的任务列表与右侧详情，并说明问答类和代码类的不同提交入口。右图展示种子演示数据中的教师分数和评语，这些不是本次模型生成结果，更不代表真实班级成绩。闭环的重点是学生能根据反馈重做，教师能查看当前提交与反馈。")

    feature("教师工作台：把班级进度与待批阅集中起来","teacher-home",
        [("班级概览","学生人数、任务数、提交率与每日趋势。"),("待批阅入口","从首页进入班级与任务，定位需要处理的提交。"),("学情参考","查看错因、知识点和学生进度，支持成绩导出。")],
        "教师首页服务于快速掌握班级状态。当前交互的直达入口是待批阅标题栏的“去批阅”，不应把列表行说成可点击操作。数据来自独立演示班，数量只是演示状态。学情指标是辅助信息，教师仍需结合提交原文与课堂情况作判断。")

    feature("教师批阅：保留人工判断与退回重做","grading",
        [("查看原始提交","同时参考学生代码或文字，以及已有 AI 诊断。"),("分数与评语","教师输入 0–100 分及文字反馈。"),("退回重做","清楚区分已批阅与需重做，反馈回到学生端。")],
        "批阅页面是教学闭环中的人工环节。老师可以看原始提交、诊断与标签，决定评分和是否退回。当前系统没有在线编译、运行测试用例的判题能力，不能把 AI 诊断或教师评分描述为自动判分。")

    s=page("学习助手：对话提问与代码诊断共用知识支持","核心交互")
    image(s,"assistant",.75,1.85,5.75,4.2,"对话：问题引导、流式输出与来源引用")
    image(s,"code-diagnosis",6.85,1.85,5.75,4.2,"代码：编辑器、静态线索与结构化诊断")
    text(s,"SSE 流式响应  /  停止与重试  /  页面草稿保留  /  诊断标签回到教学数据",.85,6.48,11.8,.4,16,BLUE)
    note(s,"学习助手","两种交互都先检索课程资料，再组织模型上下文。代码诊断先提取启发式静态线索，不是完整编译器或精确 AST 分析。结果采用结构化诊断协议，包含错因、知识点、严重程度和提示层级。截图只展示界面与输入能力，本次制作没有调用真实大模型。")

    feature("知识组织架构：四类资料，连接章节与诊断","knowledge-detail",
        [("讲义与知识点","讲义解释概念；20 个结构化知识点覆盖 8 章。"),("Bug 库与题解","错误案例帮助定位；题解内容按教学层级控制使用。"),("统一元数据","来源、章节、知识点编号、难度与前置知识支持追溯。")],
        "课程资料分为讲义、题解、Bug 库和结构化知识点。知识点文件中有编号、章节、难度和前置知识等字段，但当前不是知识图谱推理系统。默认 hint 检索排除完整题解和被识别的答案层级小节。资料浏览权限与模型上下文分层是两个问题，不应混同。")

    s=page("总体技术架构：前端、API、教学编排与数据分层","技术架构","按当前版本讲解：向量检索使用 NumPy，不再依赖 ChromaDB / hnswlib")
    layers=[("表现层","Vue 3 + Vite ｜ CodeMirror ｜ Markdown + DOMPurify",BLUE),
            ("接口层","FastAPI + Uvicorn ｜ JWT 角色校验 ｜ SSE / BYOK",TEAL),
            ("业务与智能层","班级任务 / 提交批阅 ｜ 苏格拉底编排 / 结构化诊断",BLUE),
            ("检索与数据层","BM25 + NumPy 余弦检索 ｜ SQLite ｜ Markdown + 索引文件",TEAL)]
    for i,(head,body,col) in enumerate(layers):
        y=1.93+i*1.08
        shape(s,.8,y,8.0,.87,"FFFFFF",LINE,True);shape(s,.8,y,.07,.87,col)
        text(s,head,1.0,y+.13,1.65,.5,17,col,True);text(s,body,2.8,y+.16,5.7,.62,14,INK)
        if i<3: text(s,"↓",4.25,y+.86,.7,.23,16,BLUE,align=PP_ALIGN.CENTER)
    image(s,"assistant",9.12,1.95,3.4,2.05,"交互入口")
    image(s,"knowledge-detail",9.12,4.43,3.4,1.9,"课程资料入口")
    text(s,"模型能力：本地 BGE / ONNX 生成向量；DeepSeek 生成回答（用户自带密钥）",.85,6.55,11.8,.32,13,MUTED)
    note(s,"总体技术架构","前端通过 API 获取业务数据，通过 SSE 接收模型输出。后端将教学业务、智能编排、检索和数据访问分层。BGE 通过 fastembed/ONNX 在本地向量化，DeepSeek 通过兼容 OpenAI 的接口生成回答。当前版本已将 ChromaDB/HNSW 改为 NumPy 矩阵余弦检索，以解决 Windows 原生库兼容问题。")

    s=page("RAG 检索链路：两路召回，用排名融合","RAG 核心","课程文件与检索共用分块，引用对应实际进入上下文的证据")
    card(s,"输入处理","短追问补充学生上下文\n代码先提取指针、内存、递归线索",.8,1.9,3.4,1.6)
    card(s,"BM25 词法召回","中文二字组 / 代码标识符\n标题、章节权重与确定性别名",4.6,1.9,3.6,1.6)
    card(s,"向量召回","BGE 查询向量仅计算一次\n归一化矩阵 × 查询；距离过滤",4.6,3.85,3.6,1.6)
    shape(s,4.32,2.67,.018,1.9,BLUE)
    arrow(s,4.22,2.55);arrow(s,4.22,4.45)
    card(s,"融合与教学证据","RRF → 去重 / 多样性\n类别配额 → 预算 → 可追溯引用",8.62,2.9,3.85,1.85)
    shape(s,8.34,2.7,.018,1.95,BLUE)
    shape(s,8.2,2.7,.15,.018,BLUE);shape(s,8.2,4.63,.15,.018,BLUE)
    arrow(s,8.22,3.65)
    image(s,"knowledge-detail",.8,3.86,3.4,1.95,"实际课程知识点页面")
    text(s,"默认 hint 内容层级；无足够证据可返回空，提示助教澄清，而不是强行引用",4.62,5.93,7.8,.75,15,BLUE)
    note(s,"RAG 检索链路","词法与向量检索互补，分数不直接混在一起比较，而是通过 RRF 融合排名。普通提问默认 top-3，代码诊断会保留知识点和 Bug 案例的配额。上下文只放入预算内完整片段，并由实际入选片段生成引用。关键词模式能独立运行；向量未就绪时能回答，不等于混合检索已经生效。")

    s=page("本阶段关键修复：用 NumPy 索引解决本机建库阻塞","索引工程","问题有本机记录：Windows Smart App Control 拦截 hnswlib 原生库")
    card(s,"一代索引的组成","vectors.npy：归一化 float32 矩阵\nchunks.json：与矩阵行对应的元数据\nactive-index.json：format 2 活动清单",.8,1.95,6.2,2.1)
    card(s,"构建与切换","内容哈希复用旧向量 → 新代完整写入\n校验成功后原子发布；失败保留旧代\n只保留当前代与上一代",.8,4.33,6.2,1.85)
    image(s,"knowledge",7.4,1.95,5.1,3.48,"知识库入口；向量统计取决于该演示环境是否建库")
    text(s,"仓库本机记录：334 片段\n建库 9.5 秒（含模型加载）\n讲义 35 / 题解 18 / Bug 24 / 知识点 257",7.55,5.6,4.8,1.05,17,BLUE,True)
    note(s,"索引实现更换","11 月 17 日最新修复是本阶段的重要进展。课程规模只有 334 个分块，NumPy 暴力余弦检索足够应对当前小规模语料，因此不必依赖被系统策略拦截的 hnswlib。9.5 秒来自仓库记录的 Windows 11 本机验证，不是本次 CI 重测值，也不是对所有硬件的承诺。现版本只保留当前代和上一代；旧文档中“所有旧代一直保留”的描述已经过时。")

    s=page("检索评测：报告改进，也保留退步指标","评测与证据","32 题 · top-3 · 全语料 all · 新旧词法链路同范围比较；不等同于混合检索或回答质量")
    current=evidence["evaluation"]["metrics"]
    metrics=[("Hit@3",96.55,current["hit_at_k"]*100),("Recall@3",76.44,current["recall_at_k"]*100),("MRR",89.66,current["mrr"]*100),("片段相关率",82.76,current["returned_precision"]*100)]
    for i,(label,old,new) in enumerate(metrics):
        y=2.05+i*.92
        text(s,label,.85,y,1.8,.3,16,INK,True)
        shape(s,2.6,y+.01,4.1*old/100,.2,"BCC8DC")
        shape(s,2.6,y+.3,4.1*new/100,.2,BLUE if new>=old else AMBER)
        text(s,f"{old:.2f}% → {new:.2f}%",6.9,y+.05,2.4,.45,15,BLUE if new>=old else AMBER,True)
    image(s,"rag-evaluation",9.45,2.0,3.08,3.8,"本次构建实际运行日志")
    text(s,"无答案准确率：33.33% → 100%，但仅 3 个无答案样本；不能据此声称泛化保证。",.85,6.28,11.8,.35,13,MUTED)
    text(s,"旧版    新版",2.6,5.97,4,.24,11,MUTED)
    note(s,"检索评测","本页比较同一 32 题和同一 all 语料范围的词法检索。新值由本次构建运行离线评测取得，旧值来自仓库基线报告。命中率、文档召回和首个相关结果排序改善，但片段相关率略降，必须保留。无答案查询只有三个，不应夸大 100%。真实向量混合质量、大模型回答的引用忠实度和教学收益仍需要单独评估。")

    s=page("代码组织架构：按职责划分，而不是把逻辑堆在页面里","工程组织")
    blocks=[(.8,1.95,3.8,"frontend/src","App.vue / components\napi.js / session.js / sse.js","页面交互、请求与会话"),
            (4.85,1.95,3.7,"backend/app/api","auth / classes / chat / code\nknowledge / conversation","接口、角色与业务入口"),
            (8.8,1.95,3.7,"backend/app/agents","socratic / prompts\ndiagnosis / stream_filter","检索编排与教学约束"),
            (.8,4.2,5.8,"backend/app/core","corpus → retrieval → rag → rag_index\nembedding / llm / store / db","知识、模型与数据访问"),
            (6.9,4.2,5.6,"data / tests / scripts","knowledge / app.db / vector_db\ntests / eval_rag / check_kp","内容、持久化与验证")]
    for x,y,w,head,files,desc in blocks:
        shape(s,x,y,w,1.9,"FFFFFF",LINE,True)
        text(s,head,x+.2,y+.17,w-.4,.4,18,BLUE,True)
        text(s,files,x+.2,y+.7,w-.4,.65,14,INK)
        text(s,desc,x+.2,y+1.48,w-.4,.27,12,MUTED)
    note(s,"代码组织架构","这一页对应仓库的实际目录。前端负责页面与交互，API 负责接口入口和权限，agents 负责教学流程及模型输出协议，core 负责分块检索、索引、模型和数据库。数据、脚本和测试独立保存。这样可以替换向量检索实现而保持上层接口基本不变，本次 NumPy 替换就是一个例子。")

    s=page("质量保障：用自动测试守住教学流程与索引事务","验证进度","以下数量来自本次报告构建的实际执行；不等同于测试覆盖率")
    for x,num,label in [(.8,counts["backend"],"后端测试"),(4.88,counts["frontend"],"前端单元测试"),(8.96,counts["browser"],"浏览器回归")]:
        shape(s,x,1.9,3.55,1.25,"FFFFFF",LINE,True)
        text(s,str(num),x+.2,2.04,1.3,.65,33,BLUE,True);text(s,label,x+1.5,2.25,1.85,.35,16,INK)
    image(s,"backend-tests",.8,3.48,7.15,2.37,"本次后端测试日志")
    image(s,"mobile",8.4,3.48,1.33,2.87,"移动界面")
    text(s,"重点回归\n• 删除 / 修改资料不引用旧块\n• 建库失败保留活动索引\n• 草稿保留与网络恢复\n• 角色切换、弹窗与引用跳转",10.0,3.56,2.55,2.6,15,INK)
    note(s,"质量保障","测试覆盖教学流程、角色限制、索引发布、失败恢复、分块和融合等行为；浏览器回归还检查任务直达、草稿、停止生成、引用跳转和手机布局。数量不是覆盖率，更不能代表模型回答质量。本页截图和计数是此次仓库自动构建生成。")

    # ---- 模型接入现状：为什么曾经要求使用者自带密钥
    s=page("接入现状：先用使用者自己的密钥把流程跑通","模型接入",
        "严格 BYOK：不填个人密钥就无法调用模型。这是当时的工程取舍，不是终态设计")
    text(s,"现在的链路",.8,1.86,5.5,.35,15,BLUE,True)
    for i,(head,body) in enumerate([("登录并使用","学生 / 教师账号，与密钥无关"),
            ("打开「模型设置」","右上角入口，任意页面可访问"),
            ("填写自己的 API Key","默认掩码显示；可选记住本机"),
            ("请求携带 X-LLM-Key","缺 key 直接拒绝，服务端不代调")]):
        y=2.24+i*.92
        shape(s,.8,y,5.5,.8,"FFFFFF",LINE,True)
        text(s,f"{i+1:02d}",.95,y+.18,.45,.35,15,BLUE,True)
        text(s,head,1.45,y+.1,2.3,.3,15,INK,True)
        text(s,body,1.45,y+.42,4.7,.3,12,MUTED)
    text(s,"当时为什么这样选",6.85,1.86,5.5,.35,15,BLUE,True)
    for i,(head,body) in enumerate([("实现最省","一个请求头 + 十几行代码\n不需要账号与支付体系"),
            ("没有付费体系","学生不付费、学校不报销\n没有充值与退款流程"),
            ("没有配额会失控","演示 key 被整班共用\n一天就能刷掉整月额度"),
            ("密钥责任最小","密钥不落服务器与数据库\n泄露面只剩使用者本机")]):
        card(s,head,body,6.85+(i%2)*3.0,2.24+(i//2)*1.62,2.85,1.52,num=f"{i+1}")
    text(s,"代价：学生要自己注册并充值；教师看不到班级用量；没有 token 记录，也就没有成本与效果数据",.85,6.08,11.8,.35,13,AMBER,True)
    text(s,"服务端默认 ALLOW_SERVER_KEY=0：仓库里不保存任何密钥，也不替使用者付费",.85,6.5,11.8,.3,12,TEAL)
    note(s,"接入现状","这一页正面回答“为什么要学生自己配密钥”。当前是严格 BYOK：密钥由使用者在「模型设置」里填写，只存在浏览器会话或本机存储，请求通过 X-LLM-Key 头校验，服务端默认关闭统一密钥（ALLOW_SERVER_KEY=0）。"
        "当初这样做的原因有四条：实现成本最低；没有面向学生的收费与退款体系；服务端统一密钥若没有配额，一个演示 key 会被整班共用、额度很快被刷光；密钥不落服务器，责任与泄露面最小。"
        "必须承认代价：学生要自己注册充值才能用，教师无法查看班级用量，系统也没有 token 记录，因此没有成本与学习效果的量化数据。这不是设计目标，是当时的取舍。")

    # ---- 改进方案：三步改造
    s=page("改进方案：从自带密钥走到学生零配置","改进方案",
        "先止血、再托管、最后治理；三步可分别上线，密钥优先级 个人 > 班级 > 服务端")
    for i,(head,body,cost,col) in enumerate([
            ("阶段一 · 统一密钥 + 配额","服务端持演示密钥，按用户按日记账\n超限直接拒绝，避免额度被单点刷光","1–2 天 · 学生直接用",BLUE),
            ("阶段二 · 班级密钥托管","教师上传班级密钥，AES-GCM 加密存储\n学生请求自动带，教师承担班级费用","3–4 天 · 教师承担费用",TEAL),
            ("阶段三 · 统一 LLM 网关","统一出口，多供应商切换与限流\n记录 token 与延迟，便于审计","1–2 周 · 可审计可切换",BLUE)]):
        x=.8+i*4.1
        shape(s,x,1.95,3.75,2.95,"FFFFFF",LINE,True)
        shape(s,x,1.95,3.75,.07,col)
        text(s,head,x+.22,2.16,3.35,.45,17,INK,True)
        text(s,body,x+.22,2.78,3.35,1.1,13,MUTED)
        text(s,f"落地成本 {cost}",x+.22,4.06,3.35,.3,12,col,True)
    shape(s,.8,5.12,11.85,1.05,"FFFFFF",LINE,True)
    text(s,"目标状态",1.0,5.26,1.6,.3,14,BLUE,True)
    text(s,"学生注册后即可对话与代码诊断，无需自备密钥；教师能看到班级用量与额度；所有调用都有 token 与成本记录",2.4,5.24,9.9,.4,14,INK)
    text(s,"风险对策：密钥加密存储、按日/按月双配额、超限降级为纯检索回答（不调用模型）、留一键停用开关",1.0,5.66,11.4,.35,12,MUTED)
    text(s,"现状已具备改造基础：X-LLM-Key 请求头、ALLOW_SERVER_KEY 开关与密钥优先级判断都在服务端，不涉及前端重构",.85,6.42,11.8,.35,12,TEAL)
    note(s,"改进方案","方案分三步，每步都能独立上线。第一步先止血：服务端放一个演示密钥，按用户按日记账并设配额，超限直接拒绝，这样学生打开就能用，成本也可控。"
        "第二步解决付费归属：教师上传班级密钥，服务端加密存储，学生请求自动带上；密钥优先级是个人 > 班级 > 服务端，学生想用自己的仍然可以。"
        "第三步做治理：所有模型调用走统一网关，支持多供应商切换、限流、token 与延迟审计，将来换模型不用改业务代码。"
        "配套风险对策：加密存储、日/月双配额、超限时降级为只用检索结果回答、保留一键停用。这些改造集中在服务端的模型调用入口，前端不需要重构。")

    s=page("下一阶段：从工程可用走向真实教学验证","阶段计划")
    card(s,"已完成","双端教学流程、界面与错误恢复\nRAG 混合召回、NumPy 索引与测试\n词法离线评测和来源追溯",.8,1.95,3.72,2.45)
    card(s,"接下来优先做","教师标注真实追问与困难负例\n固定样本比较 lexical / hybrid\n校准距离阈值与内容层级",4.8,1.95,3.72,2.45)
    card(s,"验证后再引入","评估 reranker 的收益与延迟\n开展小范围真实课堂试用\n语料变大后再考虑 ANN / 数据库升级",8.8,1.95,3.72,2.45)
    image(s,"knowledge-detail",.8,4.75,3.72,1.35,"扩充教师认可的课程样本")
    image(s,"assistant",4.8,4.75,3.72,1.35,"验证引导质量与引用忠实度")
    image(s,"teacher-home",8.8,4.75,3.72,1.35,"结合教师反馈迭代")
    text(s,"仍未具备：在线编译判题、已验证的学习成效、绝对不泄题保证。",.85,6.6,11.8,.3,14,AMBER)
    note(s,"下一阶段计划","后续优先补教师认可的真实学生问题和困难负例，并固定评测集比较词法与混合检索。阈值需要校准。reranker 还没有引入，应先验证实际收益，再考虑增加模型与部署成本。之后做小范围课堂试用，评价提示层级是否合适、引用是否可信、学生是否真正理解。")

    s=page("现场展示路线：把一项任务完整走一遍","汇报收束","建议顺序：教师任务 → 学生提交 → 助教诊断 → 教师反馈 → 学生重做")
    for x,shot,label in [(.8,"teacher-home","1  教师查看班级"),(3.9,"homework","2  学生打开任务"),(7.0,"code-diagnosis","3  进入代码诊断"),(10.1,"grading","4  教师批阅反馈")]:
        image(s,shot,x,2.0,2.5,2.3,label)
    text(s,"请老师重点指导",.85,5.05,11.5,.5,24,INK,True)
    text(s,"任务流程是否贴合课堂？    启发式提示是否合适？    评测样本是否覆盖教学难点？",.85,5.87,11.6,.72,20,BLUE)
    note(s,"现场演示与结束","演示时不要临时依赖网络密钥或首次模型下载。先展示可重复的班级、任务、提交与批阅流程，再在已配置的环境中演示一次真实问答。当前报告中的所有界面采用演示数据。希望老师从课程流程、提示层级和评测问题覆盖三个方面给出意见。")

    s=page("附录：事实来源、参数与验证边界","备查")
    text(s,"源码快照",.85,1.95,2,.4,18,BLUE,True)
    text(s,"Liqingqing001/Heuristic-agent\nf1396f1 · 2026-11-17 核对版本\n截图由本次构建在该代码上采集，均为独立演示数据库。",3.0,1.95,9.5,1.05,17,INK)
    text(s,"资料与报告",.85,3.28,2,.4,18,BLUE,True)
    text(s,"README.md；docs/索引实现改动-2026-11-17.md\n32 题评测集与 docs/eval/rag-baseline.json\n本次构建日志、评测 JSON、PPT 备注均随文件提供。",3.0,3.28,9.5,1.1,16,INK)
    text(s,"参数与边界",.85,4.72,2,.4,18,BLUE,True)
    text(s,"默认 top-3；余弦距离门槛 0.45（仍需校准）；失败冷却 60 秒。\n350 / 1800 / 2000 为局部估算 token 预算，不是精确计费 token。\n本次没有调用真实大模型；真实混合质量与学习效果仍待评测。",3.0,4.72,9.5,1.3,16,INK)
    note(s,"附录","最新文档覆盖旧文档中的 Chroma 和旧代清理策略。54 项后端、10 项浏览器等记录还通过本次构建重新执行。32 题离线集合不是隐藏测试集，只有三个无答案样本；报告中的 100% 不应被理解为泛化保证。性能记录只适用于注明的机器和场景。")

def verify_and_render():
    path=OUT/"Zhiyu_Stage_Report_2026-11-17.pptx"
    prs.save(path)
    check=Presentation(path)
    assert len(check.slides)==20, len(check.slides)
    pictures=0
    for i,s in enumerate(check.slides,1):
        assert any(getattr(sh,"has_text_frame",False) for sh in s.shapes), i
        assert s.notes_slide.notes_text_frame.text.strip(), i
        for sh in s.shapes:
            if sh.shape_type==13: pictures+=1
            assert sh.left>=0 and sh.top>=0, (i,sh.name)
            assert sh.left+sh.width <= check.slide_width+10, (i,sh.name,"width")
            assert sh.top+sh.height <= check.slide_height+10, (i,sh.name,"height")
    assert pictures>=20
    (OUT/"讲稿.txt").write_text("\n\n".join(f"{i+1:02d} {title}\n{body}" for i,(title,body) in enumerate(notes)),encoding="utf-8")
    run(["libreoffice","-env:UserInstallation=file:///tmp/zhiyu-report-office","--headless","--convert-to","pdf","--outdir",str(OUT),str(path)])
    pdf=path.with_suffix(".pdf");assert pdf.exists()
    info=run(["pdfinfo",str(pdf)])
    assert re.search(r"Pages:\s+20\b",info),info
    preview=Path(tempfile.mkdtemp(prefix="zhiyu-slide-preview-"))
    run(["pdftoppm","-scale-to","1000","-png",str(pdf),str(preview/"slide")])
    files=sorted(preview.glob("slide-*.png"))
    assert len(files)==20
    thumbs=[]
    for file in files:
        im=Image.open(file).convert("RGB");im.thumbnail((360,203));thumbs.append(im)
    sheet=Image.new("RGB",(1480,5*233+20),"#E8EDF5")
    d=ImageDraw.Draw(sheet)
    for i,im in enumerate(thumbs):
        x=20+(i%4)*365;y=20+(i//4)*233
        sheet.paste(im,(x,y));d.text((x+8,y+206),f"{i+1:02d}",fill="#20324E")
    sheet.save(OUT/"slides-overview.png")
    # Keep readable per-slide previews for teacher review.
    prevout=OUT/"previews";prevout.mkdir(exist_ok=True)
    for i,file in enumerate(files,1): shutil.copy(file,prevout/f"slide-{i:02d}.png")
    evidence.update({"source_commit":SOURCE,"slide_count":20,"picture_count":pictures,"rendered_pdf_pages":20,"format":"16:9; editable text and diagrams; PNG screenshots"})
    (OUT/"verification.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PRESENTATION VERIFIED: 20 slides, 20 PDF pages,",pictures,"project pictures")

if __name__=="__main__":
    prepare_and_capture()
    build_deck()
    verify_and_render()
