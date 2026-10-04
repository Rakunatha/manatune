"""Manatune: the AI browser. One file: Flask backend, Google sign-in, Groq discovery, Razorpay,
and every page (sign-in, workspace, assets) embedded as templates."""
import os, re, json, time, hmac, hashlib
from datetime import datetime
import requests
from flask import (Flask, Blueprint, request, jsonify, render_template, redirect, flash, url_for, session)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from jinja2 import DictLoader
from sqlalchemy.exc import OperationalError
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix

# ======================= embedded pages =======================
TEMPLATES = {
    "workspace.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manatune: the AI browser</title>
<style>
:root{--bg:#f3f5f9;--card:#fff;--text:#11151b;--mut:#5b6471;--bd:#d9dee7;--blue:#1f7ae8;--blue2:#1665c4;--on:#e6f0fd}
@media (prefers-color-scheme:dark){:root{--bg:#0f1114;--card:#181b20;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--on:#14283f}}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;display:flex;flex-direction:column}
button,input{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
header{display:flex;align-items:center;gap:12px;padding:10px 14px;background:var(--card);border-bottom:1px solid var(--bd);flex-wrap:wrap}
.brand{color:var(--blue);font-size:30px;font-weight:800;letter-spacing:-.02em;line-height:1}
.proj{color:var(--mut);font-size:13px;border:1px solid var(--bd);border-radius:6px;padding:4px 10px}
#cmd{flex:1 1 320px;display:flex;gap:8px}
#q{flex:1;min-width:0;background:var(--bg);color:var(--text);border:1px solid var(--bd);border-radius:20px;padding:10px 16px}
#q:focus{outline:2px solid var(--blue);outline-offset:1px}
.btn{background:var(--blue);color:#fff;border:0;border-radius:20px;padding:10px 18px;font-weight:700;cursor:pointer}
.btn:hover{background:var(--blue2)}
.btn:disabled{opacity:.6;cursor:wait}
.top a,.top button{color:var(--mut);background:none;border:0;text-decoration:none;padding:6px 8px;cursor:pointer;font-size:13px}
.top a:hover,.top button:hover{color:var(--text)}
.top{display:flex;align-items:center;gap:2px;flex-wrap:wrap}
.layout{flex:1;display:flex;min-height:0}
nav{width:168px;flex:none;padding:12px 8px;border-right:1px solid var(--bd);background:var(--card);overflow:auto}
nav button{display:block;width:100%;text-align:left;background:none;border:0;border-left:3px solid transparent;border-radius:0 6px 6px 0;padding:10px 12px;color:var(--mut);cursor:pointer;font-weight:700;font-size:14px}
nav button:hover{color:var(--text)}
nav button[aria-current=page]{background:var(--on);color:var(--text);border-left-color:var(--blue)}
main{flex:1;overflow:auto;padding:24px;min-width:0}
.wrap{max-width:980px;margin:0 auto}
h1{font-size:24px;font-weight:800;line-height:1.2;margin:0 0 6px;letter-spacing:-.02em}
.sub{color:var(--mut);margin:0 0 20px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.chips button{background:var(--card);border:1px solid var(--bd);border-radius:20px;padding:6px 12px;cursor:pointer;font-size:13px}
.chips button:hover{border-color:var(--blue)}
.note{background:var(--on);border-radius:10px;padding:10px 14px;margin:0 0 16px;font-size:14px}
.row{display:grid;grid-template-columns:1.1fr 1.6fr 1fr 1fr 1.6fr auto;gap:14px;align-items:start;padding:14px;border:1px solid var(--bd);border-radius:10px;margin-bottom:10px;background:var(--card)}
.row.h{background:none;border:0;color:var(--mut);font-size:12px;padding:0 14px;margin-bottom:4px}
.nm{font-weight:700}
.sm{color:var(--mut);font-size:12px}
.use{display:inline-block;text-decoration:none;background:var(--blue);color:#fff;border-radius:20px;padding:8px 16px;font-weight:700;font-size:13px;white-space:nowrap}
.use:hover{background:var(--blue2)}
.empty{padding:20px;background:var(--card);border:1px solid var(--bd);border-radius:10px;color:var(--mut)}
@media (max-width:820px){
 nav{width:auto;border-right:0;border-bottom:1px solid var(--bd);display:flex;overflow-x:auto;padding:4px}
 nav button{width:auto;white-space:nowrap;border-left:0;border-bottom:3px solid transparent;border-radius:6px 6px 0 0}
 nav button[aria-current=page]{border-bottom-color:var(--blue)}
 .layout{flex-direction:column}
 .row.h{display:none}
 .row{grid-template-columns:1fr 1fr;background:var(--card);margin-bottom:10px;border:1px solid var(--bd);border-radius:8px}
 .row>*:nth-child(2),.row>*:nth-child(5){grid-column:1/-1}
 main{padding:16px}
}
</style>
</head>
<body>
<header>
  <span class="brand">Manatune</span>
  <span class="proj" title="Current project">Untitled project</span>
  <form id="cmd" role="search"><input id="q" type="text" maxlength="1000" autocomplete="off" aria-label="Command bar" placeholder="What do you want to do? e.g. Find an AI tool for creating product videos"><button class="btn" id="go">Go</button></form>
  <div class="top">
    <a href="/assets" id="assets" hidden>Assets</a><button data-panel="Activity">Activity</button><button data-panel="Pricing">Pricing</button>
    <form id="acct" method="post" action="/logout" style="margin:0" hidden><button>Sign out</button></form>
  </div>
</header>
<div class="layout">
  <nav id="stages" aria-label="Stages"></nav>
  <main><div class="wrap" id="view" aria-live="polite"></div></main>
</div>
<script>
const STAGES=["DISCOVER","CREATE","PROVE","PROTECT","EXECUTE","DISTRIBUTE","MONITOR","MONETISE"];
const LABEL={DISCOVER:"Discover",CREATE:"Create",PROVE:"Prove",PROTECT:"Protect",EXECUTE:"Execute",DISTRIBUTE:"Distribute",MONITOR:"Monitor",MONETISE:"Monetise"};
const BLURB={CREATE:"Make the asset with the tool you picked.",PROVE:"Keep a record of how it was made.",PROTECT:"Prepare an IP report for it.",EXECUTE:"Turn the asset into a ready-to-run plan.",DISTRIBUTE:"Prepare it for each platform.",MONITOR:"See where it has been published.",MONETISE:"Find ways to earn from it."};
const EX=["Find an AI tool for creating product videos","Find a tool to turn a paper into a LinkedIn post","Find a voiceover tool for my launch video"];
const view=document.getElementById("view"),nav=document.getElementById("stages"),q=document.getElementById("q"),go=document.getElementById("go");
let stage="DISCOVER";
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
function renderNav(){nav.replaceChildren(...STAGES.map(s=>{const b=el("button",null,LABEL[s]);if(s===stage)b.setAttribute("aria-current","page");b.onclick=()=>show(s);return b}))}
function show(s){stage=s;renderNav();s==="DISCOVER"?home():soon(s)}
function home(){
  view.replaceChildren(el("h1",null,"What are you trying to create?"),el("p","sub","Describe the outcome. Manatune finds the tools that fit it."));
  const c=el("div","chips");EX.forEach(t=>{const b=el("button",null,t);b.onclick=()=>{q.value=t;run()};c.append(b)});view.append(c);
}
function soon(s){view.replaceChildren(el("h1",null,LABEL[s]),el("p","sub",BLURB[s]||""),el("div","empty","This stage opens in a later phase. Start in Discover to choose your tools."))}
function panel(n){stage="";renderNav();view.replaceChildren(el("h1",null,n),el("div","empty",n==="Pricing"?"Plans arrive with Razorpay checkout in a later phase.":"Your activity will appear here once you start a project."))}
document.querySelectorAll("[data-panel]").forEach(b=>b.onclick=()=>panel(b.dataset.panel));
function results(d){
  const box=el("div");box.append(el("h1",null,d.outcome||"Recommended tools"));
  if(d.capabilities&&d.capabilities.length)box.append(el("p","sub","Needs: "+d.capabilities.join(", ")));
  if(!d.ai)box.append(el("div","note","Matched by keyword. AI-ranked recommendations need the Manatune server with a Groq key."));
  if(!d.tools.length){box.append(el("div","empty","No tools matched yet. Try naming the output, such as video, voice, image or writing."));return box}
  const h=el("div","row h");["Tool","What it does","Price","Commercial use","Why recommended",""].forEach(x=>h.append(el("span",null,x)));box.append(h);
  d.tools.forEach(t=>{
    const r=el("div","row"),n=el("div");n.append(el("div","nm",t.name),el("div","sm",t.category));
    const p=el("div");p.append(el("div",null,t.pricing||""),el("div","sm",t.free_tier||""));
    const a=el("a","use","Use tool");a.href=t.url;a.target="_blank";a.rel="noopener noreferrer";
    r.append(n,el("div",null,t.description),p,el("div",null,t.commercial_use||""),el("div",null,t.why),a);box.append(r);
  });
  if(d.limitations)box.append(el("p","sm",d.limitations));
  box.append(el("p","sm","Pricing and licence terms change. Check each tool's own page before you commit."));
  return box;
}
/* ---- Built-in tool database and local engine: lets this single file work with no backend ---- */
const T=[
["Runway","video","https://runwayml.com","Generates and edits video from text, images or clips.","text to video, image to video, video editing","Free credits, paid plans","Free tier available","Check plan terms"],
["HeyGen","video","https://www.heygen.com","Creates talking-avatar product and explainer videos from a script.","avatar video, script to video, translation","Free tier, paid plans","Free tier available","Check plan terms"],
["Descript","video","https://www.descript.com","Edits video and audio by editing the transcript.","transcript editing, captions, podcast","Free tier, paid plans","Free tier available","Check plan terms"],
["ElevenLabs","audio","https://elevenlabs.io","Produces realistic voiceovers and speech in many languages.","voiceover, text to speech, dubbing","Free tier, paid plans","Free tier available","Check plan terms"],
["Suno","audio","https://suno.com","Generates songs and background music from a text prompt.","music generation, lyrics","Free tier, paid plans","Free tier available","Check plan terms"],
["Midjourney","image","https://www.midjourney.com","Generates stylised images and concept art from prompts.","image generation, art direction","Paid plans","No free tier","Check plan terms"],
["Canva","design","https://www.canva.com","Designs social posts, decks and campaign visuals from templates, with AI assist.","templates, social graphics, presentations","Free tier, paid plans","Free tier available","Check licence terms"],
["Claude","writing","https://claude.ai","Drafts and edits long-form writing, campaign copy and summaries of papers.","copywriting, summarising, editing","Free tier, paid plans","Free tier available","Generally permitted; check terms"]
].map(a=>({name:a[0],category:a[1],url:a[2],description:a[3],caps:a[4],pricing:a[5],free_tier:a[6],commercial_use:a[7]}));
const STOP=new Set("a an the to for of and or i want my me is in on with this that how create find tool tools ai use".split(" "));
const INTENT=[["MONETISE","monetis monetiz earn sell revenue price license"],["MONITOR","where has found published copied monitor track"],["PROTECT","ip report copyright protect trademark patent"],["PROVE","prove how this image was created evidence provenance"],["DISTRIBUTE","instagram linkedin youtube post prepare distribute schedule"],["EXECUTE","execute run generate automate"]];
function localRun(text){
  const low=text.toLowerCase();
  for(const [s,w] of INTENT)if(w.split(" ").some(x=>low.includes(x)))return {stage:s,summary:""};
  const words=new Set((low.match(/[a-z0-9]+/g)||[]).map(w=>w.length>3&&w.endsWith("s")?w.slice(0,-1):w).filter(w=>!STOP.has(w)));
  const tools=T.map(t=>{const hay=(t.name+" "+t.category+" "+t.description+" "+t.caps).toLowerCase();
    let s=0;words.forEach(w=>{if(hay.includes(w))s+=t.category.includes(w)?2:1});return [s,t]})
    .filter(x=>x[0]>0).sort((a,b)=>b[0]-a[0]).slice(0,6).map(x=>({...x[1],why:"Matches your request: "+x[1].description}));
  return {stage:"DISCOVER",discover:{outcome:text,capabilities:[],tools,ai:false}};
}
let backend=false;
fetch("/health").then(r=>r.ok?r.json():null).then(j=>{if(j&&j.status==="ok"){backend=true;document.getElementById("acct").hidden=false;document.getElementById("assets").hidden=false}}).catch(()=>{});
async function run(){
  const text=q.value.trim();if(!text)return;
  go.disabled=true;view.replaceChildren(el("p","sub","Working on it..."));
  let d;
  try{
    if(backend){
      const r=await fetch("/api/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({q:text})});
      if(r.status===401){location.href="/login";return}
      if(r.ok)d=await r.json();
    }
  }catch(e){}
  if(!d)d=localRun(text);
  stage=d.stage;renderNav();
  if(d.discover){view.replaceChildren(results(d.discover))}
  else{soon(d.stage);view.prepend(el("div","note","That sounds like "+LABEL[d.stage]+(d.summary?": "+d.summary:".")))}
  go.disabled=false;
}
document.getElementById("cmd").onsubmit=e=>{e.preventDefault();run()};
show("DISCOVER");
</script>
</body>
</html>
''',
    "login.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manatune: sign in</title>
<style>
:root{--bg:#f3f5f9;--card:#fff;--text:#11151b;--mut:#5b6471;--bd:#d9dee7;--blue:#1f7ae8;--blue2:#1665c4;--bad:#c0392b}
@media (prefers-color-scheme:dark){:root{--bg:#0f1114;--card:#181b20;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--bad:#ff7a6b}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;padding:16px}
.box{width:100%;max-width:380px}
.logo{color:var(--blue);font-size:30px;font-weight:800;letter-spacing:-.02em;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:20px}
label{display:block;font-size:12px;color:var(--mut);margin:12px 0 4px}
input,select{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--bd);border-radius:6px;padding:10px;font:inherit}
input:focus,select:focus,button:focus-visible{outline:2px solid var(--blue);outline-offset:1px}
.go{width:100%;margin-top:18px;background:var(--blue);color:#fff;border:0;border-radius:20px;padding:11px;font-weight:700;font-size:14px;cursor:pointer}
.go:hover{background:var(--blue2)}
.err{color:var(--bad);margin:0 0 4px}
.hint{color:var(--mut);font-size:12px;margin:6px 0 0}
.g{display:block;text-align:center;text-decoration:none;color:var(--text);background:var(--bg);border:1px solid var(--bd);border-radius:20px;padding:10px;font-weight:700}
.g:hover{border-color:var(--blue)}
</style>
</head>
<body>
<div class="box">
  <div class="logo">Manatune</div>
  <div class="card">
    {% for m in get_flashed_messages() %}<p class="err">{{ m }}</p>{% endfor %}
    {% if mode == 'advocate' %}
    <p style="margin:0 0 12px"><b>IP advocate sign-in</b></p>
    <p class="hint" style="margin:0 0 14px">For lawyers and firms who receive filing requests from creators.</p>
    <a class="g" href="/auth/google/advocate">Continue with Google</a>
    <p class="hint" style="text-align:center;margin-top:12px"><a href="/login" style="color:var(--mut)">Not an advocate? Creator sign-in</a></p>
    {% else %}
    <a class="g" href="/auth/google">Continue with Google</a>
    <p class="hint" style="text-align:center;margin-top:12px"><a href="/ipadvo" style="color:var(--mut)">IP advocate or firm? Sign in here</a></p>
    {% endif %}
  </div>
</div>
</body>
</html>
''',
    "assets.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Manatune</title>
<style>
:root{--bg:#f3f5f9;--card:#fff;--side:#fff;--text:#11151b;--mut:#5b6471;--bd:#d9dee7;--blue:#1f7ae8;--blue2:#1665c4;--sky:#0a78bd;--ok:#168246;--warn:#a56a0b;--bad:#c0392b;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1114;--card:#181b20;--side:#000;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--sky:#5cc8ff;--ok:#4cc282;--warn:#e0a63a;--bad:#ff7a6b}}
:root[data-theme="dark"]{--bg:#0f1114;--card:#181b20;--side:#000;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--sky:#5cc8ff;--ok:#4cc282;--warn:#e0a63a;--bad:#ff7a6b}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.layout{display:grid;grid-template-columns:208px 1fr;min-height:100%}
.side{background:var(--side);padding:20px 12px;border-right:1px solid var(--bd)}
.logo{color:var(--blue);font-size:21px;font-weight:800;letter-spacing:-.02em;margin:0 8px 4px}
.tag{color:var(--mut);font-size:12px;margin:0 8px 18px}
.modes{display:flex;gap:4px;margin:0 0 18px;background:var(--bg);padding:3px;border-radius:8px}
.modes button{flex:1;border:0;background:none;color:var(--mut);font-size:12px;font-weight:600;padding:7px 2px;border-radius:6px;cursor:pointer}
.modes button.on{background:var(--blue);color:#fff}
.nav{display:block;width:100%;text-align:left;border:0;background:none;color:var(--mut);font-size:14px;font-weight:600;padding:10px 8px;border-radius:6px;cursor:pointer;min-height:42px}
.nav.on{background:var(--card);color:var(--text)}
.main{padding:24px 30px 80px;min-width:0}
h1{font-size:23px;margin:0 0 2px}
.sub{color:var(--mut);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:8px;padding:14px;margin-bottom:14px}
.tabs{display:flex;gap:4px;overflow-x:auto;padding:6px 6px 0;background:var(--side);border-radius:8px 8px 0 0;border:1px solid var(--bd);border-bottom:0}
.tab{padding:8px 12px;border-radius:6px 6px 0 0;background:var(--bg);color:var(--mut);cursor:pointer;white-space:nowrap;font-size:12.5px}
.tab.on{background:var(--card);color:var(--text)}
.tab b{margin-left:8px;font-weight:400}
.bar{display:flex;gap:8px;align-items:center;padding:10px;background:var(--card);border:1px solid var(--bd);border-bottom:0}
.bar input{flex:1;min-width:0}
.view{border:1px solid var(--bd);border-radius:0 0 8px 8px;background:var(--card);margin-bottom:14px;overflow:hidden}
.note{padding:7px 12px;font-size:12px;color:var(--mut);border-bottom:1px solid var(--bd)}
iframe{width:100%;height:340px;border:0;display:block;background:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;padding:14px}
.app{background:var(--bg);border-radius:8px;padding:12px;cursor:pointer;border:1px solid var(--bd)}
.app:hover{border-color:var(--blue)}
.app small{display:block;color:var(--sky);margin-top:2px}
input,textarea,select{background:var(--bg);color:var(--text);border:1px solid var(--bd);border-radius:6px;padding:8px 10px;font:inherit;width:100%}
textarea{min-height:60px;resize:vertical}
input:focus,textarea:focus,select:focus,button:focus-visible{outline:2px solid var(--blue);outline-offset:1px}
label{display:block;font-size:12px;color:var(--mut);margin:10px 0 4px}
.btn{background:var(--blue);color:#fff;border:0;border-radius:18px;padding:8px 16px;font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap}
.btn:hover{background:var(--blue2)}
.btn.ghost{background:none;color:var(--sky);border:1px solid var(--bd)}
.btn.bad{background:var(--bad)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.badge{font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:10px;border:1px solid var(--bd);color:var(--mut)}
.badge.ok{color:var(--ok);border-color:var(--ok)}.badge.warn{color:var(--warn);border-color:var(--warn)}.badge.bad{color:var(--bad);border-color:var(--bad)}
.hash{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11.5px;color:var(--mut);word-break:break-all}
.cite{border-left:3px solid var(--blue);padding:6px 10px;margin-top:8px;background:var(--bg);border-radius:0 6px 6px 0;font-size:12.5px;color:var(--mut)}
.cite b{color:var(--text)}
.empty{color:var(--mut);padding:10px 0}
a{color:var(--sky)}
@media (max-width:700px){.layout{grid-template-columns:1fr}.side{border-right:0;border-bottom:1px solid var(--bd)}.main{padding:18px 14px 70px}.nav{display:inline-block;width:auto}}
</style>
</head>
<body>
<div class="layout">
  <aside class="side">
    <div class="logo">Manatune</div>
    <div class="tag">{{ me.name }}</div><form method="post" action="/logout" style="margin:0 8px 14px"><button class="btn ghost" style="padding:4px 12px;font-size:12px">Sign out</button></form>
    <div class="modes" id="modes"></div>
    <div id="nav"></div>
  </aside>
  <main class="main" id="main"></main>
</div>
<script>
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const sha=async d=>{const b=typeof d==='string'?new TextEncoder().encode(d):d;const h=await crypto.subtle.digest('SHA-256',b);return[...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('')};
const ME={{ me|tojson }};
const TOOLS=[['ChatGPT','Conversational AI','https://chat.openai.com/'],['Claude','Conversational AI','https://claude.ai/'],['Midjourney','Image generation','https://www.midjourney.com/'],['GitHub Copilot','Code generation','https://github.com/features/copilot'],['ElevenLabs','Voice generation','https://elevenlabs.io/'],['Runway','Video generation','https://runwayml.com/']];
let ADVOCATES=[];
const NAV={taste:[['feed','Taste feed'],['browser','Browse & repost']],creator:[['studio','Reaction studio'],['browser','Browser'],['creations','My creations'],['requests','Legal requests']],advocate:[['inbox','Filing inbox']]};
const MODES=[['taste','Taste'],ME.role==='advocate'?['advocate','Advocate']:['creator','Create']];
const S={mode:ME.role==='advocate'?'advocate':'creator',view:ME.role==='advocate'?'inbox':'studio',tabs:[],active:'home',creations:[],requests:[],reposts:[],msg:''};
const ZERO='0'.repeat(64);
const uid=()=>crypto.randomUUID?crypto.randomUUID():Date.now().toString(16)+Math.random().toString(16).slice(2);
const safeUrl=u=>/^https?:\/\//i.test(u)?u:'#';
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(r.status===401){location='/login';return null}return r.json()}
const save=(kind,o)=>api('/api/save',{kind:kind,id:o.id,data:o});
async function load(){
  const r=await fetch('/api/state');if(r.status===401){location='/login';return}
  const d=await r.json();
  S.requests=d.requests;ADVOCATES=d.advocates;
  S.creations=d.creations.map(c=>{const q=d.requests.find(x=>x.cid===c.id);c.status=q?(q.status==='Declined'?'Not filed':q.status):'Not filed';return c});
  S.reposts=d.reposts.map(x=>Object.assign({likes:0,liked:false},x));
  render();
}

function setMode(m){S.mode=m;S.view=NAV[m][0][0];S.msg='';render()}
function setView(v){S.view=v;S.msg='';render()}

/* ---------- provenance chain ---------- */
async function addEvent(c,type,extra){
  const prev=c.events.length?c.events[c.events.length-1].hash:ZERO;
  const ts=new Date().toISOString();
  const hash=await sha(prev+type+ts+c.contentHash);
  c.events.push({type,ts,prev,hash,extra:extra||''});
}
async function verifyChain(c){
  let prev=ZERO;
  for(const e of c.events){
    if(e.prev!==prev||await sha(e.prev+e.type+e.ts+c.contentHash)!==e.hash)return false;
    prev=e.hash;
  }
  return true;
}

/* ---------- browser ---------- */
function platformOf(u){const h=u.hostname.replace(/^www\./,'');
  if(/youtube\.com|youtu\.be/.test(h))return'YouTube';
  if(/spotify\.com/.test(h))return'Spotify';
  if(/instagram\.com/.test(h))return'Instagram';
  if(/soundcloud\.com/.test(h))return'SoundCloud';
  if(/vimeo\.com/.test(h))return'Vimeo';
  return h}
function canonical(raw){
  let t=raw.trim();if(!t)return null;
  if(!/^https?:\/\//i.test(t))t='https://'+t;
  try{const u=new URL(t);const v=u.searchParams.get('v');u.search='';if(v&&/youtube/.test(u.hostname))u.searchParams.set('v',v);u.hash='';return u}catch(e){return null}
}
function openTab(url,title){
  let t=S.tabs.find(x=>x.url===url);
  if(!t){t={id:'t'+Date.now(),url,title};S.tabs.push(t)}
  S.active=t.id;render()
}
function go(){
  const u=canonical($('#addr').value);
  if(!u){S.msg='Enter a valid web address.';return render()}
  const known=TOOLS.find(x=>x[2]===u.href);
  openTab(u.href,known?known[0]:platformOf(u));
}
function closeTab(id,e){e.stopPropagation();S.tabs=S.tabs.filter(t=>t.id!==id);if(S.active===id)S.active='home';render()}
const curTab=()=>S.tabs.find(t=>t.id===S.active);

async function logCreation(){
  const t=curTab();
  const title=$('#cTitle').value.trim();
  if(!title){S.msg='Give the creation a title before logging it.';return render()}
  const prompt=$('#cPrompt').value.trim(),human=$('#cHuman').value.trim();
  const f=$('#cFile').files[0];
  const contentHash=f?await sha(await f.arrayBuffer()):await sha(title+'\n'+prompt+'\n'+human);
  const c={id:'c'+uid(),title,tool:t?t.title:'Unspecified',prompt,human,file:f?f.name:'',contentHash,events:[],status:'Not filed'};
  await addEvent(c,'Created',t?'Session in '+t.title:'');
  S.creations.unshift(c);save('creation',c);
  S.msg='Logged "'+title+'". Fingerprint saved and chain started.';
  S.view='creations';render();
}
async function repost(){
  const t=curTab();if(!t)return;
  const u=canonical(t.url);
  const meta={source_url:u.href,platform:platformOf(u),title:t.title,reposted_by:ME.name,reposted_at:new Date().toISOString(),relationship:'Embed'};
  const hash=await sha(JSON.stringify(meta));
  S.reposts.unshift({id:'r'+uid(),meta,hash,likes:0,liked:false});save('repost',S.reposts[0]);
  S.msg='Reposted with a provenance citation.';S.mode='taste';S.view='feed';render();
}

/* ---------- creator actions ---------- */
async function logDist(id){
  const c=S.creations.find(x=>x.id===id);
  const where=prompt('Where was it shared or delivered? (platform, person or client)');
  if(!where)return;
  await addEvent(c,'Distributed',where);save('creation',c);render();
}
function sendReq(id){
  const c=S.creations.find(x=>x.id===id);
  const adv=($('#adv-'+id)||{}).value;if(!adv){S.msg='No advocates have joined yet.';return render()}
  if(S.requests.find(r=>r.cid===id&&r.status!=='Declined')){S.msg='A request for this creation is already open.';return render()}
  S.requests.unshift({id:'q'+uid(),cid:id,advocate:adv,status:'Requested'});
  c.status='Requested';save('request',S.requests[0]);S.msg='Request sent to '+adv+'.';S.view='requests';render();
}
function setStatus(rid,st){
  const r=S.requests.find(x=>x.id===rid);r.status=st;save('request',r);
  const c=S.creations.find(x=>x.id===r.cid);
  if(c)c.status=st==='Filed'?'Filed':st==='Declined'?'Not filed':st;
  render();
}
function like(id){const r=S.reposts.find(x=>x.id===id);r.liked=!r.liked;r.likes+=r.liked?1:-1;render()}

/* ---------- views ---------- */
const stBadge=s=>'<span class="badge '+(s==='Filed'?'ok':s==='Declined'?'bad':s==='Not filed'?'':'warn')+'">'+esc(s)+'</span>';
const chainHtml=c=>c.events.map(e=>'<div class="hash">'+esc(e.type)+(e.extra?' ('+esc(e.extra)+')':'')+' &middot; '+esc(e.ts.slice(0,19).replace('T',' '))+' UTC &middot; '+e.hash.slice(0,16)+'&hellip;</div>').join('');

function vBrowser(){
  const t=curTab();
  let h='<h1>'+(S.mode==='taste'?'Browse & repost':'Browser')+'</h1><p class="sub">'+(S.mode==='taste'?'Open work from anywhere, then repost it with its source attached.':'Work in your AI tools here, then log what you made so it becomes provable.')+'</p>';
  h+='<div class="tabs"><div class="tab '+(S.active==='home'?'on':'')+'" onclick="S.active=\'home\';render()">Tools</div>'+S.tabs.map(x=>'<div class="tab '+(x.id===S.active?'on':'')+'" onclick="S.active=\''+x.id+'\';render()">'+esc(x.title)+'<b onclick="closeTab(\''+x.id+'\',event)">&times;</b></div>').join('')+'</div>';
  h+='<div class="bar"><input id="addr" placeholder="Paste a link or type an address" value="'+esc(t?t.url:'')+'" onkeydown="if(event.key===\'Enter\')go()"><button class="btn" onclick="go()">Go</button>'+(t?'<a href="'+esc(t.url)+'" target="_blank" rel="noopener">Open in new tab</a>':'')+'</div>';
  h+='<div class="view">';
  if(!t)h+='<div class="grid">'+TOOLS.map((x,i)=>'<div class="app" onclick="openTab(TOOLS['+i+'][2],TOOLS['+i+'][0])"><b>'+esc(x[0])+'</b><small>'+esc(x[1])+'</small></div>').join('')+'</div>';
  else h+='<div class="note">If the page stays blank, the site blocks embedding. Use "Open in new tab".</div><iframe src="'+esc(t.url)+'" title="'+esc(t.title)+'"></iframe>';
  h+='</div>';
  if(S.msg)h+='<div class="card">'+esc(S.msg)+'</div>';
  if(t){
    h+='<div class="two">';
    if(S.mode==='creator')h+='<div class="card"><b>Log a creation from this session</b><label>Title</label><input id="cTitle" placeholder="e.g. Monsoon poster, draft 3"><label>Prompt used</label><textarea id="cPrompt"></textarea><label>What you changed or added yourself</label><textarea id="cHuman" placeholder="Edits, composition, hand-drawn elements, rewriting&hellip;"></textarea><label>Output file (fingerprinted in your browser, never uploaded)</label><input id="cFile" type="file"><p><button class="btn" onclick="logCreation()">Log creation</button></p></div>';
    h+='<div class="card"><b>Repost this page</b><p class="sub" style="margin:6px 0 12px">Adds it to your Taste profile with a citation to the original. Nothing is copied.</p><button class="btn" onclick="repost()">Repost with citation</button></div></div>';
  }
  return h;
}
function vCreations(){
  let h='<h1>My creations</h1><p class="sub">Every record is fingerprinted and chained, so later edits to its history show up.</p>';
  if(S.msg)h+='<div class="card">'+esc(S.msg)+'</div>';
  if(!S.creations.length)return h+'<div class="empty">Nothing logged yet. Open a tool in the Browser and log what you make.</div>';
  return h+S.creations.map(c=>'<div class="card"><div class="row"><b>'+esc(c.title)+'</b>'+stBadge(c.status)+'<span class="badge">'+esc(c.tool)+'</span></div><div class="hash">sha256:'+c.contentHash+'</div>'+(c.human?'<p><span class="sub">Your contribution:</span> '+esc(c.human)+'</p>':'<p class="sub">No human contribution noted. Add this before filing.</p>')+chainHtml(c)+'<div class="row" style="margin-top:10px"><button class="btn ghost" onclick="logDist(\''+c.id+'\')">Log distribution</button><select id="adv-'+c.id+'" style="width:auto">'+ADVOCATES.map(a=>'<option>'+esc(a)+'</option>').join('')+'</select><button class="btn" onclick="sendReq(\''+c.id+'\')">Request IP protection</button></div></div>').join('');
}
function vRequests(){
  let h='<h1>Legal requests</h1><p class="sub">Status of the filings you asked advocates to handle.</p>';
  if(S.msg)h+='<div class="card">'+esc(S.msg)+'</div>';
  if(!S.requests.length)return h+'<div class="empty">No requests yet. Send one from My creations.</div>';
  return h+S.requests.map(r=>{const c=S.creations.find(x=>x.id===r.cid);if(!c)return'';return'<div class="card"><div class="row"><b>'+esc(c.title)+'</b>'+stBadge(r.status)+'</div><div class="sub" style="margin:4px 0 0">With '+esc(r.advocate)+'</div></div>'}).join('');
}
function vInbox(){
  let h='<h1>Filing inbox</h1><p class="sub">Requests from creators, each with its evidence pack.</p>';
  if(!S.requests.length)return h+'<div class="empty">No requests yet. Switch to Create, log a creation, and send one.</div>';
  h+=S.requests.map(r=>{const c=S.creations.find(x=>x.id===r.cid);if(!c)return'';return'<div class="card"><div class="row"><b>'+esc(c.title)+'</b>'+stBadge(r.status)+'<span class="badge">'+esc(r.advocate)+'</span><span class="badge" id="v-'+r.id+'">Checking chain&hellip;</span></div><p><span class="sub">Tool:</span> '+esc(c.tool)+'<br><span class="sub">Prompt:</span> '+esc(c.prompt||'Not provided')+'<br><span class="sub">Human contribution:</span> '+esc(c.human||'Not provided')+'</p><div class="hash">sha256:'+c.contentHash+'</div>'+chainHtml(c)+'<div class="row" style="margin-top:10px"><button class="btn" onclick="setStatus(\''+r.id+'\',\'Accepted\')">Accept</button><button class="btn ghost" onclick="setStatus(\''+r.id+'\',\'Filed\')">Mark as filed</button><button class="btn bad" onclick="setStatus(\''+r.id+'\',\'Declined\')">Decline</button></div></div>'}).join('');
  setTimeout(()=>S.requests.forEach(async r=>{const c=S.creations.find(x=>x.id===r.cid);if(!c)return;const ok=await verifyChain(c);const el=document.getElementById('v-'+r.id);if(el){el.textContent=ok?'Chain intact':'Chain broken';el.className='badge '+(ok?'ok':'bad')}}),0);
  return h;
}
function vFeed(){
  let h='<h1>Taste feed</h1><p class="sub">Work people have picked, with where it came from.</p>';
  if(S.msg)h+='<div class="card">'+esc(S.msg)+'</div>';
  const items=S.reposts.map(r=>r.reaction_url?reactCard(r):'<div class="card"><div class="row"><b>'+esc(r.meta.title)+'</b><span class="badge">'+esc(r.meta.platform)+'</span></div><div class="cite"><b>Source:</b> '+esc(r.meta.platform)+' &middot; <a href="'+esc(safeUrl(r.meta.source_url))+'" target="_blank" rel="noopener">view original</a><br>Reposted by <b>'+esc(r.meta.reposted_by)+'</b> on '+esc(r.meta.reposted_at.slice(0,10))+' as an embed. Attributed to the source, not proof of ownership.<div class="hash">citation sha256:'+r.hash.slice(0,24)+'&hellip;</div></div><p><button class="btn ghost" onclick="like(\''+r.id+'\')">'+(r.liked?'Liked':'Like')+' &middot; '+r.likes+'</button></p></div>').join('');
  const mine=S.creations.map(c=>'<div class="card"><div class="row"><b>'+esc(c.title)+'</b><span class="badge ok">Provenance recorded</span>'+(c.status==='Filed'?'<span class="badge ok">Filed for protection</span>':'')+'</div><div class="sub" style="margin:4px 0 0">Created with '+esc(c.tool)+' &middot; fingerprint '+c.contentHash.slice(0,12)+'&hellip;</div></div>').join('');
  return h+((items||mine)?items+mine:'<div class="empty">Your feed is empty. Open a link in Browse & repost and share it.</div>');
}

/* ---------- reaction studio ---------- */
const ST={src:'',markers:[],stream:null,rec:null,chunks:[],t0:0,recording:false,blobUrl:'',hash:'',ext:'webm',saved:null};
function embedUrl(raw){
  try{const u=new URL(raw),h=u.hostname.replace(/^www\./,'');
    if(h==='youtu.be')return'https://www.youtube.com/embed/'+u.pathname.slice(1);
    if(h==='youtube.com'||h==='m.youtube.com'){const v=u.searchParams.get('v');if(v)return'https://www.youtube.com/embed/'+v;const m=u.pathname.match(/^\/(shorts|embed)\/([\w-]+)/);if(m)return'https://www.youtube.com/embed/'+m[2]}
    if(h==='open.spotify.com')return'https://open.spotify.com/embed'+u.pathname;
    if(h==='vimeo.com'&&/^\/\d+/.test(u.pathname))return'https://player.vimeo.com/video'+u.pathname;
    if(h==='soundcloud.com')return'https://w.soundcloud.com/player/?url='+encodeURIComponent(u.href);
  }catch(e){}
  return null}
const frame=(e,t)=>'<iframe src="'+esc(e)+'" title="'+esc(t)+'" allow="autoplay; encrypted-media; fullscreen" allowfullscreen style="height:300px"></iframe>';
const noEmbed=u=>'<div class="note">This site does not allow embedding. <a href="'+esc(safeUrl(u))+'" target="_blank" rel="noopener">Open it in another tab</a>.</div>';
function srcEmbed(u){if(!u)return'<div class="empty">Paste a link above to load the content.</div>';const e=embedUrl(u);return e?frame(e,'Original content'):noEmbed(u)}
function stInfo(){
  if(ST.recording)return'Recording. '+ST.markers.length+' moment(s) marked.';
  if(ST.blobUrl)return'<a class="btn ghost" download="reaction.'+ST.ext+'" href="'+ST.blobUrl+'">Download recording</a><div class="hash">sha256:'+ST.hash+'</div>'+(ST.saved?'<span class="badge ok">Record saved</span>':'<label>Title</label><input id="stTitle" placeholder="e.g. Reacting to the new trailer"><p><button class="btn" onclick="stSave()">Save record</button></p>');
  return ST.stream?'Camera ready. Press Record, then play the original.':'Start your camera to begin.'}
function stPost(){
  if(!ST.saved)return'<div class="empty">Save your record to unlock publishing.</div>';
  return'<p class="sub" style="margin:0 0 8px">Upload the downloaded file, then paste the link to your posted video.</p><div class="row"><button class="btn ghost" onclick="stOpen(\'https://www.youtube.com/upload\',\'YouTube\')">Upload on YouTube</button><button class="btn ghost" onclick="stOpen(\'https://vimeo.com/upload\',\'Vimeo\')">Upload on Vimeo</button></div><label>Link to your posted reaction</label><div class="row"><input id="stLink" placeholder="https://youtu.be/..."><button class="btn" onclick="stShare()">Share as reaction</button></div><p class="sub" style="margin:12px 0 0">To protect it, use Request IP protection in My creations.</p>'}
function vStudio(){
  return'<h1>Reaction studio</h1><p class="sub">Only your camera and microphone are recorded. The original plays from its own source, so nothing is copied.</p>'+(S.msg?'<div class="card">'+esc(S.msg)+'</div>':'')
  +'<div class="card"><label>Content you are reacting to</label><div class="row"><input id="stSrc" value="'+esc(ST.src)+'" placeholder="Paste a YouTube, Spotify, SoundCloud or Vimeo link" onkeydown="if(event.key===\'Enter\')stLoad()"><button class="btn" onclick="stLoad()">Load</button></div></div>'
  +'<div class="two"><div class="card"><b>Original</b><div id="stEmbed" style="margin-top:8px">'+srcEmbed(ST.src)+'</div></div>'
  +'<div class="card"><b>You</b><video id="stCam" playsinline style="width:100%;margin-top:8px;border-radius:6px;background:#000;max-height:300px"></video><div class="row" style="margin:8px 0"><button class="btn ghost" onclick="stCamOn()">Start camera</button><button class="btn" onclick="stRec()">Record</button><button class="btn bad" onclick="stStop()">Stop</button><button class="btn ghost" onclick="stMark()">Mark moment</button></div><div id="stInfo">'+stInfo()+'</div></div></div>'
  +'<div class="card"><b>Publish</b><div id="stPost" style="margin-top:8px">'+stPost()+'</div></div>'}
function stAttach(){const v=$('#stCam');if(!v)return;if(ST.blobUrl){v.src=ST.blobUrl;v.controls=true}else if(ST.stream){v.srcObject=ST.stream;v.muted=true;v.play()}}
function stLoad(){const u=canonical($('#stSrc').value);if(!u){S.msg='Enter a valid link.';return render()}ST.src=u.href;$('#stEmbed').innerHTML=srcEmbed(ST.src)}
async function stCamOn(){try{ST.stream=await navigator.mediaDevices.getUserMedia({video:true,audio:true});stAttach();$('#stInfo').innerHTML=stInfo()}catch(e){$('#stInfo').textContent='Camera or microphone access was blocked. Allow it in your browser settings and try again.'}}
function stRec(){
  if(!ST.stream){$('#stInfo').textContent='Start your camera first.';return}
  if(!ST.src){$('#stInfo').textContent='Load the content you are reacting to first.';return}
  if(ST.blobUrl){URL.revokeObjectURL(ST.blobUrl);ST.blobUrl='';ST.saved=null;const v=$('#stCam');v.removeAttribute('src');v.controls=false;stAttach();$('#stPost').innerHTML=stPost()}
  ST.chunks=[];ST.markers=[];ST.rec=new MediaRecorder(ST.stream);
  ST.rec.ondataavailable=e=>{if(e.data.size)ST.chunks.push(e.data)};ST.rec.onstop=stDone;
  ST.rec.start();ST.t0=performance.now();ST.recording=true;$('#stInfo').innerHTML=stInfo()}
function stMark(){if(!ST.recording)return;ST.markers.push(+((performance.now()-ST.t0)/1000).toFixed(1));$('#stInfo').innerHTML=stInfo()}
function stStop(){if(ST.recording){ST.recording=false;ST.rec.stop()}}
async function stDone(){
  const b=new Blob(ST.chunks,{type:ST.rec.mimeType||'video/webm'});
  ST.ext=b.type.includes('mp4')?'mp4':'webm';ST.hash=await sha(await b.arrayBuffer());ST.blobUrl=URL.createObjectURL(b);
  const v=$('#stCam');if(v){v.srcObject=null;v.src=ST.blobUrl;v.controls=true;v.muted=false}
  const i=$('#stInfo');if(i)i.innerHTML=stInfo()}
async function stSave(){
  const t=($('#stTitle')||{}).value;
  if(!t||!t.trim()){$('#stInfo').insertAdjacentHTML('beforeend','<span class="badge bad">Add a title first.</span>');return}
  const c={id:'c'+uid(),title:t.trim(),tool:'Manatune Studio',prompt:'',human:'Live reaction recorded on camera and microphone, in response to '+ST.src,contentHash:ST.hash,file:'reaction.'+ST.ext,source:{url:ST.src,platform:platformOf(new URL(ST.src))},markers:ST.markers.slice(),events:[],status:'Not filed'};
  await addEvent(c,'Created','Reaction recorded');
  S.creations.unshift(c);save('creation',c);ST.saved=c.id;
  $('#stInfo').innerHTML=stInfo();$('#stPost').innerHTML=stPost()}
function stOpen(u,t){S.view='browser';openTab(u,t)}
async function stShare(){
  const u=canonical(($('#stLink')||{}).value||'');
  if(!u){$('#stPost').insertAdjacentHTML('beforeend','<span class="badge bad">Paste the link to your posted video.</span>');return}
  const c=S.creations.find(x=>x.id===ST.saved);if(!c)return;
  const meta={source_url:ST.src,platform:c.source.platform,title:c.title,reposted_by:ME.name,reposted_at:new Date().toISOString(),relationship:'Reaction'};
  const p={id:'r'+uid(),cid:c.id,reaction_url:u.href,meta,hash:await sha(JSON.stringify(meta)+u.href+c.contentHash),prov:{contentHash:c.contentHash,events:c.events,markers:c.markers,tool:c.tool},likes:0,liked:false};
  S.reposts.unshift(p);save('repost',p);S.watch=p.id;S.mode='taste';S.view='watch';render()}

/* ---------- watch page ---------- */
const embedBox=(u,label)=>{const e=embedUrl(u);return'<div class="card"><b>'+esc(label)+'</b><div style="margin-top:8px">'+(e?frame(e,label):noEmbed(u))+'</div></div>'};
function toggleCite(){const e=$('#cite');e.hidden=!e.hidden;$('#citeBtn').textContent=e.hidden?'Show citation':'Hide citation'}
function vWatch(){
  const p=S.reposts.find(x=>x.id===S.watch);
  if(!p)return'<div class="empty">That post is no longer available.</div><p><button class="btn ghost" onclick="setView(\'feed\')">Back to feed</button></p>';
  const pv=p.prov||{events:[]};
  return'<div class="row" style="margin-bottom:12px"><button class="btn ghost" onclick="setView(\'feed\')">Back</button><h1 style="margin:0;flex:1">'+esc(p.meta.title)+'</h1><button class="btn" id="citeBtn" onclick="toggleCite()">Show citation</button></div>'
  +'<div id="cite" class="card" hidden><b>Citation and provenance</b>'
  +'<div class="cite"><b>Original:</b> '+esc(p.meta.platform)+' &middot; <a href="'+esc(safeUrl(p.meta.source_url))+'" target="_blank" rel="noopener">view original</a><br>Attributed to the source. This is not proof of ownership.</div>'
  +(p.reaction_url?'<div class="cite"><b>Reaction by '+esc(p.meta.reposted_by)+'</b><br>Recorded with '+esc(pv.tool||'unknown tool')+' &middot; '+((pv.markers||[]).length)+' marked moments<br>Registered on platform: '+esc(p.server_ts||'pending')+'<div class="hash">sha256:'+esc(pv.contentHash||'')+'</div>History: <span id="chain" class="badge">Checking&hellip;</span>'+chainHtml(pv)+'</div>':'')
  +'<div class="cite"><b>Copyright protection:</b> '+stBadge(p.protection||'Not requested')+'</div></div>'
  +'<div class="two">'+(p.reaction_url?embedBox(p.reaction_url,'Reaction by '+p.meta.reposted_by):'')+embedBox(p.meta.source_url,'Original on '+p.meta.platform)+'</div>'}
function watchVerify(){
  const p=S.reposts.find(x=>x.id===S.watch);
  if(p&&p.reaction_url&&p.prov)verifyChain({contentHash:p.prov.contentHash,events:p.prov.events}).then(ok=>{const e=$('#chain');if(e){e.textContent=ok?'Chain intact':'Chain broken';e.className='badge '+(ok?'ok':'bad')}})}
const reactCard=r=>'<div class="card"><div class="row"><b>'+esc(r.meta.title)+'</b><span class="badge ok">Reaction</span><span class="badge">'+esc(r.meta.platform)+'</span>'+(r.protection&&r.protection!=='Not requested'?stBadge(r.protection):'')+'</div><div class="sub" style="margin:4px 0 10px">by '+esc(r.meta.reposted_by)+' &middot; reacting to content on '+esc(r.meta.platform)+'</div><button class="btn" onclick="S.watch=\''+r.id+'\';S.view=\'watch\';render()">Watch with citation</button></div>';

function render(){
  $('#modes').innerHTML=MODES.map(m=>'<button class="'+(S.mode===m[0]?'on':'')+'" onclick="setMode(\''+m[0]+'\')">'+m[1]+'</button>').join('');
  $('#nav').innerHTML=NAV[S.mode].map(n=>'<button class="nav '+(S.view===n[0]?'on':'')+'" onclick="setView(\''+n[0]+'\')">'+n[1]+'</button>').join('');
  const V={studio:vStudio,watch:vWatch,browser:vBrowser,creations:vCreations,requests:vRequests,inbox:vInbox,feed:vFeed};
  $('#main').innerHTML=V[S.view]();
  if(S.view==='studio')stAttach();
  if(S.view==='watch')watchVerify();
  S.msg='';
}
render();load();
</script>
</body>
</html>
''',
}


# ======================= AI browser =======================
STAGES = ["DISCOVER", "CREATE", "PROVE", "PROTECT", "EXECUTE", "DISTRIBUTE", "MONITOR", "MONETISE"]
STOP = set("a an the to for of and or i want my me is in on with this that how create find tool tools ai use".split())


# ---------- AI provider abstraction (add another class + PROVIDERS entry to swap) ----------
class AIProvider:
    def available(self):
        return False

    def complete_json(self, system, user):
        raise NotImplementedError


class GroqProvider(AIProvider):
    url = "https://api.groq.com/openai/v1/chat/completions"

    def available(self):
        return bool(os.environ.get("GROQ_API_KEY"))

    def complete_json(self, system, user):
        r = requests.post(
            self.url, timeout=30,
            headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]},
            json={"model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"), "temperature": 0.2,
                  "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])


PROVIDERS = {"groq": GroqProvider}


def provider():
    return PROVIDERS.get(os.environ.get("AI_PROVIDER", "groq"), GroqProvider)()


DISCOVER_PROMPT = """You are an AI tool discovery assistant.
Understand the user's intended outcome. Identify what they want to accomplish and the required capabilities.
From the supplied candidate tools ONLY (use their ids), pick the best fits and say why each is suitable,
noting pricing, commercial-use considerations and relevant limitations. Do not recommend tools merely because
they are popular; prioritise suitability for the actual objective. Never invent facts beyond the supplied data.
Return JSON: {"outcome": str, "capabilities": [str], "recommendations": [{"id": int, "why": str}], "limitations": str}"""

INTENT_PROMPT = ("Classify the user's request into exactly one stage of: " + ", ".join(STAGES) +
                 ". Requests to find or choose a tool, or to start a new goal, are DISCOVER. "
                 'Return JSON: {"stage": str, "summary": str}')

INTENT_WORDS = [  # fallback when no AI key is configured; first match wins
    ("MONETISE", "monetis monetiz earn sell revenue price license"),
    ("MONITOR", "where has found published copied monitor track"),
    ("PROTECT", "ip report copyright protect trademark patent"),
    ("PROVE", "prove how this image was created evidence provenance"),
    ("DISTRIBUTE", "instagram linkedin youtube post prepare distribute schedule"),
    ("EXECUTE", "execute run generate automate"),
]

# Curated starter set. Pricing/terms change often: confirm each entry and set last_verified before launch.
SEED = [
    ("Runway", "Runway", "https://runwayml.com", "video", "Generates and edits video from text, images or clips.",
     ["text to video", "image to video", "video editing"], "Free credits, paid plans", "Free tier available", "Check plan terms", "Yes", "Review data policy"),
    ("HeyGen", "HeyGen", "https://www.heygen.com", "video", "Creates talking-avatar product and explainer videos from a script.",
     ["avatar video", "script to video", "translation"], "Free tier, paid plans", "Free tier available", "Check plan terms", "Yes", "Review data policy"),
    ("Descript", "Descript", "https://www.descript.com", "video", "Edits video and audio by editing the transcript.",
     ["transcript editing", "captions", "podcast"], "Free tier, paid plans", "Free tier available", "Check plan terms", "Limited", "Review data policy"),
    ("ElevenLabs", "ElevenLabs", "https://elevenlabs.io", "audio", "Produces realistic voiceovers and speech in many languages.",
     ["voiceover", "text to speech", "dubbing"], "Free tier, paid plans", "Free tier available", "Check plan terms", "Yes", "Review data policy"),
    ("Suno", "Suno", "https://suno.com", "audio", "Generates songs and background music from a text prompt.",
     ["music generation", "lyrics"], "Free tier, paid plans", "Free tier available", "Check plan terms", "No public API", "Review data policy"),
    ("Midjourney", "Midjourney", "https://www.midjourney.com", "image", "Generates stylised images and concept art from prompts.",
     ["image generation", "art direction"], "Paid plans", "No free tier", "Check plan terms", "No public API", "Review data policy"),
    ("Canva", "Canva", "https://www.canva.com", "design", "Designs social posts, decks and campaign visuals from templates, with AI assist.",
     ["templates", "social graphics", "presentations"], "Free tier, paid plans", "Free tier available", "Check licence terms", "Limited", "Review data policy"),
    ("Claude", "Anthropic", "https://claude.ai", "writing", "Drafts and edits long-form writing, campaign copy and summaries of papers.",
     ["copywriting", "summarising", "editing"], "Free tier, paid plans", "Free tier available", "Generally permitted; check terms", "Yes", "Review data policy"),
]


def init(app, db):
    class Tool(db.Model):
        __tablename__ = "ai_tools"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), nullable=False)
        company = db.Column(db.String(120))
        url = db.Column(db.String(300))
        category = db.Column(db.String(60), index=True)
        description = db.Column(db.Text)
        capabilities = db.Column(db.Text, default="[]")  # JSON list
        pricing = db.Column(db.String(200))
        free_tier = db.Column(db.String(120))
        commercial_use = db.Column(db.String(200))
        api = db.Column(db.String(120))
        privacy = db.Column(db.String(200))
        last_verified = db.Column(db.String(20), default="unverified")

        def to_dict(self):
            return dict(id=self.id, name=self.name, company=self.company, url=self.url, category=self.category,
                        description=self.description, capabilities=json.loads(self.capabilities or "[]"),
                        pricing=self.pricing, free_tier=self.free_tier, commercial_use=self.commercial_use,
                        api=self.api, privacy=self.privacy, last_verified=self.last_verified)

    bp = Blueprint("aibrowser", __name__)
    seeded = []

    def ensure_seed():
        if seeded:
            return
        db.create_all()
        if Tool.query.count() == 0:
            for n, c, u, cat, d, caps, pr, ft, cu, api, pv in SEED:
                db.session.add(Tool(name=n, company=c, url=u, category=cat, description=d,
                                    capabilities=json.dumps(caps), pricing=pr, free_tier=ft,
                                    commercial_use=cu, api=api, privacy=pv))
            db.session.commit()
        seeded.append(1)

    def candidates(q, n=6):
        words = {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", q.lower())} - STOP
        scored = []
        for t in Tool.query.all():
            hay = " ".join([t.name, t.category or "", t.description or "", t.capabilities or ""]).lower()
            s = sum(2 if w in (t.category or "") else 1 for w in words if w in hay)
            scored.append((s, t))
        scored.sort(key=lambda x: -x[0])
        return [t for s, t in scored if s > 0][:n]

    def discover(q):
        ts = candidates(q)
        out = {"outcome": q, "capabilities": [], "limitations": "", "ai": False}
        why = {}
        p = provider()
        if ts and p.available():
            try:
                r = p.complete_json(DISCOVER_PROMPT, json.dumps({"request": q, "tools": [t.to_dict() for t in ts]}))
                by = {t.id: t for t in ts}
                recs = [x for x in r.get("recommendations", []) if x.get("id") in by]
                if recs:
                    ts = [by[x["id"]] for x in recs]
                    why = {x["id"]: str(x.get("why", "")) for x in recs}
                    out.update(outcome=str(r.get("outcome", q)), capabilities=[str(c) for c in r.get("capabilities", [])],
                               limitations=str(r.get("limitations", "")), ai=True)
            except Exception:
                app.logger.exception("AI discovery failed; using keyword matches")
        out["tools"] = [dict(t.to_dict(), why=why.get(t.id) or "Matches your request: " + (t.description or ""))
                        for t in ts]
        return out

    def detect_stage(q):
        p = provider()
        if p.available():
            try:
                r = p.complete_json(INTENT_PROMPT, q)
                if r.get("stage") in STAGES:
                    return r["stage"], str(r.get("summary", ""))
            except Exception:
                app.logger.exception("Intent detection failed; using keywords")
        low = q.lower()
        for stage, words in INTENT_WORDS:
            if any(w in low for w in words.split()):
                return stage, ""
        return "DISCOVER", ""

    @bp.get("/health")
    def health():
        return jsonify(status="ok")

    @bp.post("/api/command")
    @login_required
    def command():  # one orchestration layer: intent -> stage -> workflow
        q = ((request.get_json(silent=True) or {}).get("q") or "").strip()[:1000]
        if not q:
            return jsonify(error="Type what you want to do."), 400
        ensure_seed()
        stage, summary = detect_stage(q)
        res = {"stage": stage, "summary": summary, "ai": provider().available()}
        if stage == "DISCOVER":
            res["discover"] = discover(q)
        return jsonify(res)

    # ---------- Razorpay ----------
    @bp.post("/api/pay/order")
    @login_required
    def pay_order():
        key, secret = os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET")
        if not (key and secret):
            return jsonify(error="Payments are not configured."), 503
        p = request.get_json(silent=True) or {}
        try:
            amount = int(p.get("amount_inr", 0)) * 100  # paise
        except (TypeError, ValueError):
            amount = 0
        if not 1 <= amount <= 10_000_000:
            return jsonify(error="bad amount"), 400
        r = requests.post("https://api.razorpay.com/v1/orders", auth=(key, secret), timeout=20,
                          json={"amount": amount, "currency": "INR", "receipt": "m-%d" % (int(__import__("time").time()))})
        if not r.ok:
            return jsonify(error="Could not create order."), 502
        return jsonify(order=r.json(), key_id=key)

    @bp.post("/api/pay/webhook")
    def pay_webhook():
        secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
        sig = request.headers.get("X-Razorpay-Signature", "")
        good = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(good, sig):
            return jsonify(error="bad signature"), 400
        app.logger.info("Razorpay event: %s", (request.get_json(silent=True) or {}).get("event"))
        return jsonify(ok=True)

    app.register_blueprint(bp)


# ======================= app =======================
def _db_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///manatune.db")
    # Render gives postgres:// or postgresql://; pin the psycopg2 driver explicitly
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, root_path=BASE)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # Render terminates HTTPS at its proxy
app.jinja_loader = DictLoader(TEMPLATES)  # every page is embedded above; no templates/ folder needed
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
    SQLALCHEMY_DATABASE_URI=_db_url(),
    SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True, "pool_recycle": 280},
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),  # HTTPS-only on Render
)
db = SQLAlchemy(app)
lm = LoginManager(app)

STATUSES = {"Requested", "Accepted", "Filed", "Declined"}

init(app, db)  # /health, /api/command, /api/discover, /api/pay/*


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="creator")  # creator | advocate
    pw = db.Column(db.String(255), nullable=False)


class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.String(64), primary_key=True)
    kind = db.Column(db.String(20), index=True)  # creation | request | repost
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    data = db.Column(db.Text, nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    for attempt in range(6):  # the database can take a moment to accept connections on boot
        try:
            db.create_all()
            break
        except OperationalError:
            if attempt == 5:
                raise
            time.sleep(3)


@app.get("/healthz")
def healthz():
    return "ok"


@lm.user_loader
def load_user(i):
    return db.session.get(User, int(i))


@lm.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify(error="login required"), 401
    return redirect("/login")


# ---------------- pages & auth ----------------
@app.get("/")
@login_required
def index():
    return render_template("workspace.html", me={"name": current_user.name, "role": current_user.role})


@app.get("/assets")
@login_required
def assets():  # saved creations, requests and reposts
    return render_template("assets.html", me={"name": current_user.name, "role": current_user.role})


@app.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect("/")
    return render_template("login.html", mode="signin")


@app.get("/ipadvo")
def ipadvo():
    if current_user.is_authenticated:
        return redirect("/")
    return render_template("login.html", mode="advocate")


@app.post("/logout")
def logout():
    back = "/ipadvo" if current_user.is_authenticated and current_user.role == "advocate" else "/login"
    logout_user()
    return redirect(back)


# ---------------- Google sign-in (the only way in) ----------------
GOOGLE_ENABLED = bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))
oauth = OAuth(app)
if GOOGLE_ENABLED:
    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _callback_url():
    # Must match the "Authorized redirect URI" in Google Cloud exactly.
    # PUBLIC_URL (e.g. https://manatune.onrender.com) wins; otherwise build it, forcing https on Render.
    base = os.environ.get("PUBLIC_URL", "").rstrip("/")
    if base:
        return base + "/auth/google/callback"
    return url_for("google_callback", _external=True, _scheme="https" if os.environ.get("RENDER") else None)


def _start_google(intent):
    if not GOOGLE_ENABLED:
        flash("Google sign-in isn't configured: set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        return redirect("/ipadvo" if intent == "advocate" else "/login")
    session["intent"] = intent  # remembered across the Google round-trip
    try:
        return oauth.google.authorize_redirect(_callback_url(), prompt="select_account")
    except Exception:
        app.logger.exception("Google authorize_redirect failed")
        flash("Could not reach Google. Please try again.")
        return redirect("/ipadvo" if intent == "advocate" else "/login")


@app.get("/auth/google")
def google_login():  # creators and content lovers
    return _start_google("creator")


@app.get("/auth/google/advocate")
def google_login_advocate():  # IP advocates / lawyers, from /ipadvo
    return _start_google("advocate")


@app.get("/auth/google/callback")
def google_callback():
    intent = session.pop("intent", "creator")
    back = "/ipadvo" if intent == "advocate" else "/login"
    if not GOOGLE_ENABLED:
        return redirect(back)
    if request.args.get("error"):  # user cancelled or Google refused
        flash("Google sign-in was cancelled.")
        return redirect(back)
    try:
        token = oauth.google.authorize_access_token()
        info = token.get("userinfo") or oauth.google.userinfo(token=token) or {}
    except Exception:
        app.logger.exception("Google token exchange failed")
        flash("Google sign-in failed. Please try again.")
        return redirect(back)
    email = (info.get("email") or "").strip().lower()
    if not email or info.get("email_verified") not in (True, "true"):
        flash("Google did not confirm that email address.")
        return redirect(back)
    u = User.query.filter_by(email=email).first()
    if u is None:
        name = (info.get("name") or email.split("@")[0])[:120]
        if intent == "advocate" and User.query.filter_by(role="advocate", name=name).first():
            name = f"{name} ({email})"[:120]  # advocate names must be unique; clients pick them by name
        # pw is an unused legacy column (NOT NULL in existing databases); store an unusable value
        u = User(email=email, name=name, role=intent, pw="!google-only")
        db.session.add(u)
        db.session.commit()
    elif u.role != intent:  # keep the two doors separate; roles never change
        flash("This Google account is registered as an IP advocate. Use the advocate sign-in." if u.role == "advocate"
              else "This Google account is registered as a creator. Use the main sign-in.")
        return redirect("/ipadvo" if u.role == "advocate" else "/login")
    login_user(u, remember=True)
    return redirect("/")


# ---------------- data API ----------------
def _out(r):
    d = json.loads(r.data)
    d["id"] = r.id
    return d


@app.get("/api/state")
@login_required
def state():
    uid = current_user.id
    advocates = [u.name for u in User.query.filter_by(role="advocate").order_by(User.name)]
    if current_user.role == "advocate":
        reqs = [r for r in Record.query.filter_by(kind="request")
                if json.loads(r.data).get("advocate") == current_user.name]
        cids = {json.loads(r.data).get("cid") for r in reqs}
        creations = Record.query.filter(Record.kind == "creation", Record.id.in_(cids)).all() if cids else []
    else:
        reqs = Record.query.filter_by(kind="request", owner_id=uid).all()
        creations = Record.query.filter_by(kind="creation", owner_id=uid).order_by(Record.ts.desc()).all()
    reposts = Record.query.filter_by(kind="repost").order_by(Record.ts.desc()).limit(100).all()
    rank = {"Requested": 1, "Accepted": 2, "Filed": 3}
    prot = {}  # (creation id, owner) -> best protection status, shown on that owner's posts only
    for q in Record.query.filter_by(kind="request"):
        d = json.loads(q.data)
        k = (d.get("cid"), q.owner_id)
        if rank.get(d.get("status"), 0) > rank.get(prot.get(k), 0):
            prot[k] = d.get("status")
    posts = []
    for r in reposts:
        d = _out(r)
        d["protection"] = prot.get((d.get("cid"), r.owner_id), "Not requested")
        posts.append(d)
    return jsonify(creations=[_out(r) for r in creations], requests=[_out(r) for r in reqs],
                   reposts=posts, advocates=advocates)


@app.post("/api/save")
@login_required
def save():
    p = request.get_json(silent=True) or {}
    kind, rid, data = p.get("kind"), str(p.get("id", "")), p.get("data")
    if (kind not in ("creation", "request", "repost") or not re.match(r"^[a-z0-9-]{1,64}$", rid)
            or not isinstance(data, dict) or len(json.dumps(data)) > 100_000):
        return jsonify(error="bad request"), 400
    if kind == "repost":  # reposts are public, so validate the link and set the poster server-side
        m = data.get("meta")
        if not isinstance(m, dict) or not str(m.get("source_url", "")).startswith(("http://", "https://")):
            return jsonify(error="bad request"), 400
        m["reposted_by"] = current_user.name
        ru = data.get("reaction_url")
        if ru is not None and not str(ru).startswith(("http://", "https://")):
            return jsonify(error="bad request"), 400
    r = db.session.get(Record, rid)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"  # platform clock, not the user's
    if r is None:
        data["server_ts"] = now
        db.session.add(Record(id=rid, kind=kind, owner_id=current_user.id, data=json.dumps(data)))
    elif r.kind != kind:
        return jsonify(error="bad request"), 400
    elif r.owner_id == current_user.id:
        data["server_ts"] = json.loads(r.data).get("server_ts", now)
        r.data = json.dumps(data)
    elif kind == "request" and current_user.role == "advocate":
        old = json.loads(r.data)  # advocates may change status only, on requests sent to them
        if old.get("advocate") != current_user.name or data.get("status") not in STATUSES:
            return jsonify(error="forbidden"), 403
        old["status"] = data["status"]
        r.data = json.dumps(old)
    else:
        return jsonify(error="forbidden"), 403
    db.session.commit()
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
