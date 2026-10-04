"""Manatune: the AI browser. One file: Flask backend, Google sign-in, Groq discovery, Razorpay,
and every page (sign-in, workspace, assets) embedded as templates."""
import os, re, json, time, hmac, hashlib, uuid
from datetime import datetime, timedelta
import requests
from flask import (Flask, Blueprint, request, jsonify, render_template, redirect, flash, url_for, session)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         login_required, current_user)
from jinja2 import DictLoader
from sqlalchemy.exc import OperationalError
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
import io, secrets, zipfile
from functools import wraps
from urllib.parse import urlsplit, urlunsplit
from flask import g, send_file

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
label{display:block;font-size:12px;color:var(--mut);margin:12px 0 4px}
input,select,textarea{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--bd);border-radius:6px;padding:10px;font:inherit}
input[type=checkbox]{width:auto}
#q{width:auto;border-radius:20px;padding:10px 16px}
.proj{width:auto;max-width:200px;padding:6px 10px;font-size:13px}
.wrap .btn{margin-top:14px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;margin-bottom:10px}
.out{white-space:pre-wrap;margin:8px 0 0;font:inherit}
.pill{display:inline-block;border-radius:12px;padding:2px 10px;font-size:12px;font-weight:700;background:var(--on)}
.pill.bad,.note.bad{color:#e5533d}
.plat{display:inline-flex;align-items:center;gap:6px;margin:0 14px 0 0;font-size:14px;color:var(--text)}
.sp{display:flex;justify-content:space-between;gap:10px;align-items:center}
</style>
</head>
<body>
<header>
  <span class="brand">Manatune</span>
  <select id="asset" class="proj" aria-label="Current asset"></select>
  <form id="cmd" role="search"><input id="q" type="text" maxlength="1000" autocomplete="off" aria-label="Command bar" placeholder="What do you want to do? e.g. Find an AI tool for creating product videos"><button class="btn" id="go">Go</button></form>
  <div class="top"><span class="sm" id="plan"></span><button id="buy">Get Creator Pass</button><a href="/assets">Library</a>
  <form method="post" action="/logout" style="margin:0"><button>Sign out</button></form></div>
</header>
<div class="layout"><nav id="stages" aria-label="Stages"></nav><main><div class="wrap" id="view" aria-live="polite"></div></main></div>
<script>
const STAGES=["DISCOVER","CREATE","PROVE","PROTECT","EXECUTE","DISTRIBUTE","MONITOR","MONETISE"];
const LABEL={DISCOVER:"Discover",CREATE:"Create",PROVE:"Prove",PROTECT:"Protect",EXECUTE:"Execute",DISTRIBUTE:"Distribute",MONITOR:"Monitor",MONETISE:"Monetise"};
const EX=["Find an AI tool for creating product videos","Find a tool to turn a paper into a LinkedIn post","Find a voiceover tool for my launch video"];
const $=s=>document.querySelector(s),view=$("#view"),nav=$("#stages"),q=$("#q"),go=$("#go"),sel=$("#asset");
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
const fld=(l,n)=>{const b=el("label",null,l);b.append(n);return b};
const api=async(u,b)=>{const r=await fetch(u,b===undefined?{}:{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});
  if(r.status===401){location.href="/login";throw 0}
  const d=await r.json().catch(()=>({}));if(!r.ok){const e=new Error(d.error||"Request failed");e.code=r.status;throw e}return d};
let stage="DISCOVER",me={},cur=null,pending="";
function fail(e){if(e===0)return;view.querySelectorAll(".note.bad").forEach(n=>n.remove());
  const n=el("div","note bad",e.message||"Something went wrong.");
  if(e.code===402){const b=el("button","btn","Get Creator Pass");b.onclick=buy;n.append(" ",b)}view.prepend(n)}
async function act(b,fn){b.disabled=true;try{await fn()}catch(e){fail(e)}b.disabled=false}
function copyBtn(text){const b=el("button","use","Copy");b.onclick=async()=>{try{await navigator.clipboard.writeText(text);b.textContent="Copied"}catch(e){b.textContent="Copy failed"}};return b}
function dl(kind,label){
  if(me.paid){const a=el("a","use",label);a.href="/api/assets/"+cur.id+"/report/"+kind;a.download="";a.style.marginTop="14px";return a}
  const b=el("button","btn",label);b.onclick=()=>fail(Object.assign(new Error("Report downloads are part of the Creator Pass."),{code:402}));return b}
async function loadMe(){me=await api("/api/me");
  $("#plan").textContent=(me.paid?"Creator Pass: ":"Free: ")+me.left+" of "+me.limit+" generations left";$("#buy").hidden=me.paid}
async function loadAssets(id){const l=await api("/api/assets");
  sel.replaceChildren(...(l.length?l.map(a=>new Option(a.title+" ("+a.kind+")",a.id)):[new Option("No asset yet","")]));
  id=id||(cur&&cur.id)||(l[0]&&l[0].id);if(id){sel.value=id;cur=await api("/api/assets/"+id)}}
sel.onchange=async()=>{if(sel.value){cur=await api("/api/assets/"+sel.value);show(stage)}};
function renderNav(){nav.replaceChildren(...STAGES.map(s=>{const b=el("button",null,LABEL[s]);if(s===stage)b.setAttribute("aria-current","page");b.onclick=()=>show(s);return b}))}
function head(t,s){view.replaceChildren(el("h1",null,t),el("p","sub",s||""))}
function needAsset(t,s){head(t,s);if(cur)return false;view.append(el("div","empty","Create an asset first. Open Create, add your source text and generate."));return true}
function show(s){stage=s;renderNav();({DISCOVER:vDiscover,CREATE:vCreate,PROVE:vProve,PROTECT:vProtect,EXECUTE:vExecute,DISTRIBUTE:vDistribute,MONITOR:vMonitor,MONETISE:vMonetise})[s]()}
async function setCur(a){cur=a;await loadAssets(a.id);loadMe()}

function vDiscover(){head("What are you trying to create?","Describe the outcome. Manatune finds the tools that fit it.");
  const c=el("div","chips");EX.forEach(t=>{const b=el("button",null,t);b.onclick=()=>{q.value=t;run()};c.append(b)});view.append(c)}
function results(d){const box=el("div");box.append(el("h1",null,d.outcome||"Recommended tools"));
  if(d.capabilities&&d.capabilities.length)box.append(el("p","sub","Needs: "+d.capabilities.join(", ")));
  if(!d.ai)box.append(el("div","note","Matched by keyword. Add GROQ_API_KEY for AI-ranked recommendations."));
  if(!d.tools.length){box.append(el("div","empty","No tools matched yet. Try naming the output, such as video, voice, image or writing."));return box}
  const h=el("div","row h");["Tool","What it does","Price","Commercial use","Why recommended",""].forEach(x=>h.append(el("span",null,x)));box.append(h);
  d.tools.forEach(t=>{const r=el("div","row"),n=el("div");n.append(el("div","nm",t.name),el("div","sm",t.category));
    const p=el("div");p.append(el("div",null,t.pricing||""),el("div","sm",t.free_tier||""));
    const a=el("a","use","Use tool");a.href=t.url;a.target="_blank";a.rel="noopener noreferrer";
    r.append(n,el("div",null,t.description),p,el("div",null,t.commercial_use||""),el("div",null,t.why),a);box.append(r)});
  if(d.limitations)box.append(el("p","sm",d.limitations));
  box.append(el("p","sm","Pricing and licence terms change. Check each tool's own page before you commit."));return box}
async function run(){const t=q.value.trim();if(!t)return;go.disabled=true;view.replaceChildren(el("p","sub","Working on it..."));
  try{const d=await api("/api/command",{q:t});stage=d.stage;renderNav();
    if(d.discover)view.replaceChildren(results(d.discover));
    else{pending=t;show(d.stage);view.prepend(el("div","note","That sounds like "+LABEL[d.stage]+(d.summary?": "+d.summary:".")))}
  }catch(e){fail(e)}go.disabled=false}
$("#cmd").onsubmit=e=>{e.preventDefault();run()};

function assetCard(a){const c=el("div","card"),t=el("div","sp");t.append(el("div","nm",a.title),copyBtn(a.content));
  c.append(t,el("div","sm",a.kind+", saved with a provenance record"),el("pre","out",a.content));return c}
function vCreate(){head("Create","Turn your source text into something ready to use. Every result is saved automatically.");
  const obj=el("input");obj.maxLength=500;obj.value=pending;pending="";obj.placeholder="e.g. Launch post for my AI startup";
  const kind=el("select");(me.kinds||[]).forEach(k=>kind.append(new Option(k)));
  const src=el("textarea");src.maxLength=20000;src.rows=8;src.placeholder="Paste your source text here";
  const file=el("input");file.type="file";file.accept=".txt,.md";file.onchange=async()=>{const f=file.files[0];if(f&&f.size<=100000)src.value=(await f.text()).slice(0,20000)};
  const b=el("button","btn","Generate"),out=el("div");
  b.onclick=()=>act(b,async()=>{const a=await api("/api/create",{objective:obj.value,kind:kind.value,source:src.value});await setCur(a);out.replaceChildren(assetCard(a))});
  view.append(fld("Objective",obj),fld("Output",kind),fld("Source text",src),fld("Or load a .txt or .md file",file),b,out)}

function vProve(){if(needAsset("Prove","A provenance record of how this asset was made. It is evidence of origin, not proof of copyright."))return;
  const p=cur.provenance,v=p.versions[p.versions.length-1];
  [["Asset",cur.title+", SHA-256 "+p.sha256],["Source",p.source+", SHA-256 "+p.source_sha256],["Creation",p.created_utc+" by "+p.creator],
   ["AI tool",p.ai_tool+", model "+p.ai_model+", prompt: "+p.prompt_reference],["Transformation",p.transformations.join("; ")],["Current version","v"+v.version+" at "+v.at]]
  .forEach(([k,x])=>{const c=el("div","card");c.append(el("div","nm",k),el("div",null,x));view.append(c)});
  view.append(dl("provenance","Download provenance report"))}

function vProtect(){if(needAsset("Protect","Check what evidence is ready. This is not legal advice or copyright registration."))return;
  Object.entries(cur.protection).forEach(([k,x])=>{const c=el("div","card sp");c.append(el("div","nm",k),el("span","pill"+(x==="REVIEW REQUIRED"||x==="UNKNOWN"?" bad":""),x));view.append(c)});
  const lic=el("input");lic.maxLength=200;lic.value=cur.meta.licence||"";lic.placeholder="e.g. I wrote the source text and own it";
  const b=el("button","btn","Save licence review");b.onclick=()=>act(b,async()=>{cur=await api("/api/assets/"+cur.id+"/licence",{licence:lic.value});vProtect()});
  view.append(fld("Ownership or licence basis",lic),b);
  const d=dl("protection","Download protection evidence report");d.style.marginLeft="8px";view.append(d)}

function vExecute(){if(needAsset("Execute","Where this asset stands and what to do next."))return;
  cur.checklist.forEach(t=>{const c=el("div","card sp");c.append(el("div",null,(t.done?"Done: ":"To do: ")+t.task));view.append(c)});
  const b=el("button","btn","Plan next steps");
  b.onclick=()=>act(b,async()=>{cur=await api("/api/assets/"+cur.id+"/ai/execute",{});loadMe();vExecute()});view.append(b);
  ((cur.meta.execute||{}).tasks||[]).forEach(t=>{const c=el("div","card");c.append(el("div","nm",t.task+" ("+t.priority+")"),el("div",null,t.action||""),el("div","sm","Depends on: "+(t.dependency||"nothing"))); view.append(c)})}

function vDistribute(){if(needAsset("Distribute","Platform-ready versions to copy. Nothing is posted for you."))return;
  const box=el("div"),checks=(me.platforms||[]).map(p=>{const l=el("label","plat"),c=el("input");c.type="checkbox";c.checked=true;c.value=p;l.append(c,p);box.append(l);return c});
  const b=el("button","btn","Generate versions");
  b.onclick=()=>act(b,async()=>{cur=await api("/api/assets/"+cur.id+"/ai/distribute",{platforms:checks.filter(c=>c.checked).map(c=>c.value)});loadMe();vDistribute()});
  view.append(box,b);const pk=(cur.meta.distribute||{}).platforms||{};
  Object.entries(pk).forEach(([p,x])=>{const c=el("div","card"),t=el("div","sp");t.append(el("div","nm",p),copyBtn((x.title?x.title+"\n\n":"")+x.content+((x.hashtags||[]).length?"\n\n"+x.hashtags.join(" "):"")));
    c.append(t,el("div","sm",x.title||""),el("pre","out",x.content),el("div","sm",(x.hashtags||[]).join(" ")),el("div","sm","Format: "+(x.format||"")+(x.changes?". Changes: "+x.changes:"")));view.append(c)});
  if(Object.keys(pk).length)view.append(dl("distribution","Export distribution pack"))}

function vMonitor(){if(needAsset("Monitor","What needs attention, based only on what you record here. No external scanning."))return;
  const a=cur.attention;view.append(a.length?Object.assign(el("div","card"),{}):el("div","note","Nothing needs attention."));
  if(a.length){const c=view.lastChild;c.append(el("div","nm","Needs attention"));a.forEach(x=>c.append(el("div",null,x)))}
  const u=el("input");u.placeholder="https://";const pl=el("select");(me.platforms||[]).forEach(p=>pl.append(new Option(p)));const d=el("input");d.type="date";
  const b=el("button","btn","Add publication");b.onclick=()=>act(b,async()=>{cur=await api("/api/assets/"+cur.id+"/publication",{url:u.value,platform:pl.value,date:d.value});vMonitor()});
  view.append(fld("Published URL",u),fld("Platform",pl),fld("Publication date",d),b);
  (cur.meta.publications||[]).forEach(p=>{const c=el("div","card");c.append(el("div","nm",p.platform+(p.date?", "+p.date:"")),el("div","sm",p.url));view.append(c)})}

function vMonetise(){if(needAsset("Monetise","Realistic ways to earn from this asset. No revenue is guaranteed."))return;
  const au=el("input");au.maxLength=200;au.placeholder="e.g. early-stage founders in India";const b=el("button","btn","Find opportunities");
  b.onclick=()=>act(b,async()=>{cur=await api("/api/assets/"+cur.id+"/ai/monetise",{audience:au.value});loadMe();vMonetise()});view.append(fld("Audience (optional)",au),b);
  ((cur.meta.monetise||{}).opportunities||[]).forEach(o=>{const c=el("div","card");c.append(el("div","nm",o.model),el("div",null,"Sells: "+o.selling+" To: "+o.customer),el("div",null,o.fit),
    el("div","sm","Price: "+o.price+". Next step: "+o.next_step+". Risk: "+o.risk));view.append(c)})}

async function buy(){try{const o=await api("/api/payments/create-order",{});
  await new Promise((res,rej)=>{if(window.Razorpay)return res();const s=document.createElement("script");s.src="https://checkout.razorpay.com/v1/checkout.js";s.onload=res;s.onerror=rej;document.head.append(s)});
  new Razorpay({key:o.key_id,order_id:o.order_id,amount:o.amount,currency:"INR",name:"Manatune",description:"Creator Pass",
    handler:async r=>{try{await api("/api/payments/verify",r);await loadMe();show(stage)}catch(e){fail(new Error("Payment could not be verified yet. If you were charged, access unlocks shortly."))}}}).open()
  }catch(e){fail(e.message?e:new Error("Could not start payment."))}}
$("#buy").onclick=buy;
(async()=>{renderNav();try{await loadMe();await loadAssets()}catch(e){}show("DISCOVER")})();
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
    "extension.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Manatune: Chrome extension</title>
<style>
:root{--bg:#f3f5f9;--card:#fff;--text:#11151b;--mut:#5b6471;--bd:#d9dee7;--blue:#1f7ae8;--blue2:#1665c4;--sky:#0a78bd;--ok:#168246;--bad:#c0392b;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
@media (prefers-color-scheme:dark){:root{--bg:#0f1114;--card:#181b20;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--sky:#5cc8ff;--ok:#4cc282;--bad:#ff7a6b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:720px;margin:0 auto;padding:20px 16px 80px}
.logo{color:var(--blue);font-size:24px;font-weight:800;letter-spacing:-.02em}
.top{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:18px}
h1{font-size:22px;margin:0 0 2px}
h2{font-size:16px;margin:0 0 6px}
.sub{color:var(--mut);margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:14px}
.btn{display:inline-block;background:var(--blue);color:#fff;border:0;border-radius:20px;padding:9px 18px;font:inherit;font-weight:700;font-size:13px;cursor:pointer;text-decoration:none}
.btn:hover{background:var(--blue2)}
.btn.ghost{background:none;color:var(--sky);border:1px solid var(--bd)}
.btn.small{padding:4px 12px;font-size:12px}
.btn:focus-visible,input:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;justify-content:space-between}
.item{padding:10px 0;border-top:1px solid var(--bd)}
.item:first-child{border-top:0}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;word-break:break-all;color:var(--mut)}
.tok{background:var(--bg);border:1px solid var(--blue);border-radius:8px;padding:10px;margin-top:10px}
.badge{font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:10px;border:1px solid var(--bd);color:var(--mut)}
.note{border-left:3px solid var(--blue);padding:6px 10px;background:var(--bg);border-radius:0 6px 6px 0;font-size:12.5px;color:var(--mut)}
.err{color:var(--bad)}
ol{padding-left:20px;margin:6px 0 12px}
a{color:var(--sky)}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="logo">Manatune</div>
    <div class="row" style="gap:8px"><a class="btn ghost small" href="/">Back to workspace</a><span style="color:var(--mut)">{{ me.name }}</span></div>
  </div>
  <h1>Chrome extension</h1>
  <p class="sub">Capture records and reposts from any web page, straight into your Manatune account.</p>

  <div class="card">
    <h2>1. Install</h2>
    <ol>
      <li>Download the extension and unzip it.</li>
      <li>In Chrome open <b>chrome://extensions</b> and switch on <b>Developer mode</b>.</li>
      <li>Choose <b>Load unpacked</b> and select the unzipped folder.</li>
    </ol>
    <a class="btn" href="/extension/download.zip">Download extension</a>
  </div>

  <div class="card">
    <h2>2. Connect with a personal token</h2>
    <p class="sub" style="margin-bottom:8px">Paste the token into the extension. It lets the extension save to your account only, and you can revoke it at any time.</p>
    <button class="btn" id="gen">Generate token</button>
    <div id="fresh"></div>
    <p class="err" id="terr"></p>
    <div id="toks" style="margin-top:10px"></div>
  </div>

  <div class="card">
    <h2>Your capture records</h2>
    <div class="note">{{ notice }}</div>
    <p class="sub" style="margin:10px 0 0">Manatune stores the fingerprint (SHA-256), never the text or image itself. Keep your own copy of the original.</p>
    <div id="caps"></div>
  </div>
</div>
<script>
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
const safeUrl=u=>/^https?:\/\//i.test(u)?u:'#';
async function api(path,opt){const r=await fetch(path,Object.assign({headers:{'Content-Type':'application/json'}},opt));const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||'Something went wrong');return d}
async function loadTokens(){
  const t=await api('/api/tokens');
  $('#toks').innerHTML=t.length?t.map(x=>'<div class="item row"><div><b>'+esc(x.prefix)+'&hellip;</b><div class="mono">Created '+esc(x.created.slice(0,10))+' &middot; '+(x.last_used?'last used '+esc(x.last_used.slice(0,10)):'never used')+'</div></div><button class="btn ghost small" data-rev="'+x.id+'">Revoke</button></div>').join(''):'<p class="sub">No active tokens.</p>';
}
async function loadCaps(){
  const c=await api('/api/captures');
  $('#caps').innerHTML=c.length?c.map(x=>'<div class="item"><div class="row"><b>'+esc(x.title)+'</b><span class="badge">'+esc(x.kind)+'</span></div><div class="mono"><a href="'+esc(safeUrl(x.url))+'" target="_blank" rel="noopener">'+esc(x.url)+'</a></div><div class="mono">Author: '+esc(x.author)+' &middot; Licence: '+esc(x.licence)+'</div><div class="mono">sha256 ('+esc(x.hash_basis)+'): '+esc(x.sha256)+'</div><div class="row"><span class="mono">Server time '+esc(x.server_ts)+'</span><a class="btn ghost small" href="/api/captures/'+esc(x.id)+'?download=1">Download record</a></div></div>').join(''):'<p class="sub" style="margin-top:10px">No capture records yet.</p>';
}
$('#gen').onclick=async()=>{
  $('#terr').textContent='';
  try{const d=await api('/api/tokens',{method:'POST',body:'{}'});
    $('#fresh').innerHTML='<div class="tok"><b>Your token (shown once)</b><div class="mono" id="tv">'+esc(d.token)+'</div><p style="margin:8px 0 0"><button class="btn small" id="cp">Copy</button></p></div>';
    $('#cp').onclick=async()=>{try{await navigator.clipboard.writeText(d.token);$('#cp').textContent='Copied'}catch(e){const r=document.createRange();r.selectNodeContents($('#tv'));const s=getSelection();s.removeAllRanges();s.addRange(r)}};
    loadTokens()}catch(e){$('#terr').textContent=e.message}
};
$('#toks').onclick=async e=>{const id=e.target.dataset&&e.target.dataset.rev;if(!id)return;
  try{await api('/api/tokens/'+id,{method:'DELETE'});$('#fresh').innerHTML='';loadTokens()}catch(x){$('#terr').textContent=x.message}};
loadTokens().catch(e=>{$('#terr').textContent=e.message});loadCaps().catch(()=>{});
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
    ("PROVE", "prove provenance evidence origin show me how"),
    ("CREATE", "turn write summar article outline draft rewrite"),
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
        for stage, words in ([] if "tool" in low else INTENT_WORDS):
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

init(app, db)  # /health, /api/command (intent + discovery)


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


# ======================= Phases 2-8: create, prove, protect, execute, distribute, monitor, monetise =======================
from flask import Response

KINDS = ("summary", "article", "social post", "presentation outline", "campaign copy")
PLATFORMS = ("LinkedIn", "Instagram", "X", "Website")
NOTICE = ("This record documents how the asset was created in Manatune. It is evidence only: "
          "it does not establish copyright ownership or registration, and it is not legal advice.")
PROMPTS = {
    "CREATE": ("You are the content creation planner. Write the requested output using ONLY the supplied source and objective. "
               "Preserve factual accuracy and never invent information the source does not support. "
               'Return JSON: {"title": str, "content": str}'),
    "EXECUTE": ("You are an execution planner. Given the project state, list only what is still missing, prioritised, "
                "with dependencies. Do not repeat completed work; give the shortest practical plan. "
                'Return JSON: {"tasks": [{"task": str, "status": "todo", "dependency": str, "priority": "high|medium|low", "action": str}]}'),
    "DISTRIBUTE": ("You are a content distribution assistant. Adapt the approved content for each requested platform. "
                   "Preserve factual meaning, brand voice and important claims; do not invent claims. "
                   'Return JSON: {"platforms": {"<platform>": {"title": str, "content": str, "hashtags": [str], "format": str, "changes": str}}}'),
    "MONETISE": ("You are an IP monetisation strategist. Suggest the most realistic, practical ways to earn from this asset. "
                 "Do not guarantee revenue. Return JSON: "
                 '{"opportunities": [{"model": str, "customer": str, "selling": str, "fit": str, "price": str, "next_step": str, "risk": str}]} '
                 "ranked best first, at most 4."),
}


class Asset(db.Model):
    __tablename__ = "assets"
    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    title = db.Column(db.String(200))
    kind = db.Column(db.String(30))
    source = db.Column(db.Text)
    content = db.Column(db.Text)
    sha256 = db.Column(db.String(64))
    model = db.Column(db.String(80))
    meta = db.Column(db.Text, default="{}")  # JSON: objective, licence, execute, distribute, monetise, publications
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Generation(db.Model):  # one row per billable AI call; doubles as the response cache
    __tablename__ = "generations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, index=True)
    stage = db.Column(db.String(20))
    key = db.Column(db.String(64), index=True)
    model = db.Column(db.String(80))
    output = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(64), unique=True)
    payment_id = db.Column(db.String(64))
    user_id = db.Column(db.Integer, index=True)
    amount = db.Column(db.Integer)  # paise
    status = db.Column(db.String(20), default="created")
    created = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)


def _int(k, d):
    try:
        return int(os.environ.get(k, d))
    except ValueError:
        return d


def err(m, c):
    return jsonify(error=m), c


def iso(d):
    return d.isoformat(timespec="seconds") + "Z"


def M(a):
    return json.loads(a.meta or "{}")


def mine(aid):  # ownership check on every asset access: other users' ids return 404
    a = db.session.get(Asset, aid)
    return a if a and a.user_id == current_user.id else None


def is_paid(uid):
    since = datetime.utcnow() - timedelta(days=_int("PASS_DAYS", 30))
    return Payment.query.filter(Payment.user_id == uid, Payment.status == "paid", Payment.verified_at > since).first() is not None


def month_used(uid):
    n = datetime.utcnow()
    return Generation.query.filter(Generation.user_id == uid, Generation.created >= datetime(n.year, n.month, 1)).count()


def limit_for(uid):
    return _int("PAID_GENERATIONS", 50) if is_paid(uid) else _int("FREE_GENERATIONS", 3)


_hits = {}


def rate_ok(uid, n=20):  # per-worker limiter: n AI calls per minute per user
    now = time.time()
    q = [t for t in _hits.get(uid, []) if now - t < 60]
    ok = len(q) < n
    if ok:
        q.append(now)
    _hits[uid] = q
    return ok


def ai_run(stage, uid, payload):
    """Cached, quota-checked Groq call. Identical requests are served from the database for free."""
    p = provider()
    if not p.available():
        return None, err("AI is not configured. Set GROQ_API_KEY.", 503)
    if not rate_ok(uid):
        return None, err("Slow down a little and try again.", 429)
    key = hashlib.sha256((stage + json.dumps(payload, sort_keys=True)).encode()).hexdigest()
    hit = Generation.query.filter_by(user_id=uid, key=key).first()
    if hit:
        return json.loads(hit.output), None
    if month_used(uid) >= limit_for(uid):
        return None, err("You have used all your generations this month. The Creator Pass raises the limit.", 402)
    try:
        out = p.complete_json(PROMPTS[stage], json.dumps(payload))
    except Exception:
        app.logger.exception("AI call failed")
        return None, err("The AI request failed. Try again.", 502)
    db.session.add(Generation(user_id=uid, stage=stage, key=key, model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
                              output=json.dumps(out)))
    db.session.commit()
    return out, None


# ---- deterministic stages (no AI cost): provenance, protection, checklist, monitoring ----
def provenance(a):
    u = db.session.get(User, a.user_id)
    src = a.source or ""
    return {"asset_id": a.id, "sha256": a.sha256, "created_utc": iso(a.created),
            "creator": "%s <%s>" % (u.name, u.email) if u else "UNKNOWN",
            "source": "Pasted text" if src else "UNKNOWN",
            "source_sha256": hashlib.sha256(src.encode()).hexdigest() if src else "UNKNOWN",
            "ai_tool": "Groq API", "ai_model": a.model or "UNKNOWN",
            "prompt_reference": M(a).get("objective") or "UNKNOWN",
            "transformations": ["%s to %s" % ("source text" if src else "objective", a.kind)],
            "versions": [{"version": 1, "sha256": a.sha256, "at": iso(a.created)}]}


def protection(a):
    p, m = provenance(a), M(a)
    s = {"Ownership": "AVAILABLE" if p["creator"] != "UNKNOWN" else "UNKNOWN",
         "Provenance": "COMPLETE" if "UNKNOWN" not in (p["source"], p["ai_model"], p["prompt_reference"]) else "REVIEW REQUIRED",
         "Source": "RECORDED" if p["source"] != "UNKNOWN" else "UNKNOWN",
         "Licence": "REVIEWED" if m.get("licence") else "REVIEW REQUIRED"}
    s["Evidence"] = "READY" if set(s.values()) <= {"AVAILABLE", "COMPLETE", "RECORDED", "REVIEWED"} else "REVIEW REQUIRED"
    return s


def checklist(a):
    m = M(a)
    return [{"task": t, "done": d} for t, d in [
        ("Content created", True), ("Provenance recorded", True), ("Rights reviewed", bool(m.get("licence"))),
        ("Distribution pack prepared", bool(m.get("distribute"))), ("Publication tracked", bool(m.get("publications"))),
        ("Monetisation reviewed", bool(m.get("monetise")))]]


def attention(a):
    m, out = M(a), []
    if protection(a)["Provenance"] != "COMPLETE":
        out.append("Provenance is incomplete.")
    if not m.get("licence"):
        out.append("Licence not reviewed.")
    elif (datetime.utcnow() - datetime.fromisoformat(m["licence_reviewed"].rstrip("Z"))).days > 180:
        out.append("Licence review is more than 180 days old.")
    if not m.get("distribute"):
        out.append("Distribution pack not prepared.")
    if not m.get("publications"):
        out.append("No publication recorded yet.")
    return out


def full(a):
    return dict(id=a.id, title=a.title, kind=a.kind, content=a.content, created=iso(a.created), meta=M(a),
                provenance=provenance(a), protection=protection(a), checklist=checklist(a), attention=attention(a))


def _save_meta(a, **kv):
    m = M(a)
    m.update(kv)
    a.meta = json.dumps(m)
    db.session.commit()


@app.get("/api/me")
@login_required
def me_info():
    uid = current_user.id
    lim = limit_for(uid)
    return jsonify(name=current_user.name, paid=is_paid(uid), limit=lim, left=max(0, lim - month_used(uid)),
                   price=_int("PASS_PRICE_INR", 199), kinds=KINDS, platforms=PLATFORMS)


@app.get("/api/assets")
@login_required
def assets_list():
    rows = Asset.query.filter_by(user_id=current_user.id).order_by(Asset.created.desc()).limit(50).all()
    return jsonify([dict(id=a.id, title=a.title, kind=a.kind) for a in rows])


@app.get("/api/assets/<aid>")
@login_required
def asset_get(aid):
    a = mine(aid)
    return jsonify(full(a)) if a else err("not found", 404)


@app.post("/api/create")
@login_required
def create():
    b = request.get_json(silent=True) or {}
    kind, obj, src = b.get("kind"), str(b.get("objective", "")).strip()[:500], str(b.get("source", "")).strip()[:20000]
    if kind not in KINDS or not (obj or src):
        return err("Add an objective or some source text.", 400)
    out, e = ai_run("CREATE", current_user.id, {"objective": obj, "output": kind, "source": src[:6000]})
    if e:
        return e
    content = str(out.get("content", "")).strip()
    if not content:
        return err("The AI returned no content. Try again.", 502)
    a = Asset(id=uuid.uuid4().hex, user_id=current_user.id, title=str(out.get("title") or obj or kind)[:200], kind=kind,
              source=src, content=content, sha256=hashlib.sha256(content.encode()).hexdigest(),
              model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"), meta=json.dumps({"objective": obj}))
    db.session.add(a)
    db.session.commit()
    return jsonify(full(a))


@app.post("/api/assets/<aid>/licence")
@login_required
def set_licence(aid):
    a = mine(aid)
    lic = str((request.get_json(silent=True) or {}).get("licence", "")).strip()[:200]
    if not a or not lic:
        return err("Describe the licence or ownership basis.", 400)
    _save_meta(a, licence=lic, licence_reviewed=iso(datetime.utcnow()))
    return jsonify(full(a))


@app.post("/api/assets/<aid>/publication")
@login_required
def add_publication(aid):
    a, b = mine(aid), request.get_json(silent=True) or {}
    url = str(b.get("url", "")).strip()[:500]
    if not a or not url.startswith(("http://", "https://")) or b.get("platform") not in PLATFORMS:
        return err("Add a full link starting with http:// or https:// and pick a platform.", 400)
    pubs = M(a).get("publications", []) + [{"url": url, "platform": b["platform"], "date": str(b.get("date", ""))[:10]}]
    _save_meta(a, publications=pubs[-50:])
    return jsonify(full(a))


@app.post("/api/assets/<aid>/ai/<stage>")
@login_required
def ai_stage(aid, stage):
    a, stage, b = mine(aid), stage.upper(), request.get_json(silent=True) or {}
    if not a or stage not in ("EXECUTE", "DISTRIBUTE", "MONETISE"):
        return err("not found", 404)
    payload = {"asset": {"title": a.title, "kind": a.kind, "content": a.content[:6000]}}
    if stage == "DISTRIBUTE":
        payload["platforms"] = sorted(p for p in b.get("platforms", []) if p in PLATFORMS) or list(PLATFORMS)
    elif stage == "EXECUTE":
        payload["state"] = checklist(a)
    else:
        payload["audience"] = str(b.get("audience", ""))[:200]
    out, e = ai_run(stage, current_user.id, payload)
    if e:
        return e
    _save_meta(a, **{stage.lower(): out})
    return jsonify(full(a))


@app.get("/api/assets/<aid>/report/<kind>")
@login_required
def report(aid, kind):
    a = mine(aid)
    if not a or kind not in ("provenance", "protection", "distribution"):
        return err("not found", 404)
    if not is_paid(current_user.id):
        return err("Report downloads are part of the Creator Pass.", 402)
    f = full(a)
    body = {"provenance": {"report": "PROVENANCE RECORD", "provenance": f["provenance"]},
            "protection": {"report": "PROTECTION EVIDENCE REPORT", "provenance": f["provenance"], "status": f["protection"],
                           "licence": f["meta"].get("licence", "UNKNOWN")},
            "distribution": {"report": "DISTRIBUTION PACK", "platforms": f["meta"].get("distribute", {})}}[kind]
    body.update(notice=NOTICE, generated_utc=iso(datetime.utcnow()))
    return Response(json.dumps(body, indent=2), mimetype="application/json",
                    headers={"Content-Disposition": 'attachment; filename="%s-%s.json"' % (kind, a.id[:8])})


# ---- Razorpay: the backend creates the order, verifies the signature and trusts the webhook, never the browser ----
@app.post("/api/payments/create-order")
@login_required
def pay_create():
    key, secret = os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET")
    if not (key and secret):
        return err("Payments are not configured.", 503)
    amount = _int("PASS_PRICE_INR", 199) * 100
    r = requests.post("https://api.razorpay.com/v1/orders", auth=(key, secret), timeout=20,
                      json={"amount": amount, "currency": "INR", "receipt": "u%d-%d" % (current_user.id, int(time.time()))})
    if not r.ok:
        return err("Could not create the order.", 502)
    oid = r.json()["id"]
    db.session.add(Payment(order_id=oid, user_id=current_user.id, amount=amount))
    db.session.commit()
    return jsonify(order_id=oid, amount=amount, key_id=key)


def _mark_paid(order_id, payment_id):
    p = Payment.query.filter_by(order_id=order_id).first()
    if p and p.status != "paid":
        p.status, p.payment_id, p.verified_at = "paid", payment_id, datetime.utcnow()
        db.session.commit()
    return p


@app.post("/api/payments/verify")
@login_required
def pay_verify():
    b = request.get_json(silent=True) or {}
    oid, pid, sig = str(b.get("razorpay_order_id", "")), str(b.get("razorpay_payment_id", "")), str(b.get("razorpay_signature", ""))
    p = Payment.query.filter_by(order_id=oid, user_id=current_user.id).first()
    good = hmac.new(os.environ.get("RAZORPAY_KEY_SECRET", "").encode(), (oid + "|" + pid).encode(), hashlib.sha256).hexdigest()
    if not p or not os.environ.get("RAZORPAY_KEY_SECRET") or not hmac.compare_digest(good, sig):
        return err("Payment could not be verified.", 400)
    _mark_paid(oid, pid)
    return jsonify(ok=True)


@app.post("/api/payments/webhook")
def pay_webhook():
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    good = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not secret or not hmac.compare_digest(good, request.headers.get("X-Razorpay-Signature", "")):
        return err("bad signature", 400)
    d = request.get_json(silent=True) or {}
    ent = ((d.get("payload") or {}).get("payment") or {}).get("entity") or {}
    if d.get("event") in ("payment.captured", "order.paid") and ent.get("order_id"):
        _mark_paid(ent["order_id"], ent.get("id"))
    return jsonify(ok=True)


# ======================= Phase 1: API tokens, capture records, extension endpoints =======================
CAPTURE_NOTICE = ("A capture record shows that this page address, title and fingerprint were recorded by your Manatune "
                  "account at the server time shown. It is evidence only: it is not proof of authorship, copyright "
                  "ownership or registration, and it is not legal advice.")
CAPTURE_KINDS = {"text", "image", "page"}
HASH_BASES = {"selected_text_utf8", "image_bytes", "image_url", "page_metadata"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ApiToken(db.Model):  # personal token for the Chrome extension; only a SHA-256 hash is stored
    __tablename__ = "api_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    prefix = db.Column(db.String(12))  # first characters, shown so people can tell tokens apart
    created = db.Column(db.DateTime, default=datetime.utcnow)
    expires = db.Column(db.DateTime)
    last_used = db.Column(db.DateTime)
    revoked = db.Column(db.Boolean, default=False)


class Capture(db.Model):  # a capture record: evidence only, never proof of authorship or copyright
    __tablename__ = "captures"
    id = db.Column(db.String(32), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True, nullable=False)
    kind = db.Column(db.String(10))  # text | image | page
    url = db.Column(db.Text, nullable=False)
    target_url = db.Column(db.Text)  # the image address, for image captures
    title = db.Column(db.String(300))
    author = db.Column(db.String(300))  # NULL means UNKNOWN
    licence = db.Column(db.String(500))  # NULL means UNKNOWN
    sha256 = db.Column(db.String(64), nullable=False)
    hash_basis = db.Column(db.String(30), nullable=False)
    size = db.Column(db.Integer)  # characters for text, bytes for images
    client_ts = db.Column(db.String(40))  # claimed by the browser, never trusted
    record_sha256 = db.Column(db.String(64))  # fingerprint of the stored fields plus the server time
    created = db.Column(db.DateTime, default=datetime.utcnow)  # server timestamp


def _clean(v, n):
    v = " ".join(str(v).split()) if v is not None else ""
    return v[:n] or None


def _web_url(v, n=2000):
    """Return a normalised http(s) URL without fragment or credentials, or None."""
    try:
        s = urlsplit(str(v or "").strip())
        if s.scheme not in ("http", "https") or not s.hostname or s.username or s.password or len(str(v)) > n:
            return None
        return urlunsplit((s.scheme, s.netloc, s.path or "/", s.query, ""))
    except ValueError:
        return None


def _tok_hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


def token_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        h = request.headers.get("Authorization", "")
        raw = h[7:].strip() if h.startswith("Bearer ") else ""
        t = ApiToken.query.filter_by(token_hash=_tok_hash(raw), revoked=False).first() if raw.startswith("mt_") else None
        if not t or (t.expires and t.expires < datetime.utcnow()):
            return err("Invalid or expired token. Generate a new one on the Manatune website.", 401)
        u = db.session.get(User, t.user_id)
        if not u or u.role != "creator":
            return err("The extension is for creator accounts.", 403)
        if not rate_ok(("ext", u.id), _int("EXT_RATE_PER_MIN", 30)):
            return err("Slow down a little and try again.", 429)
        if not t.last_used or (datetime.utcnow() - t.last_used).total_seconds() > 3600:
            t.last_used = datetime.utcnow()
            db.session.commit()
        g.ext_user = u
        return f(*a, **k)
    return wrapper


def creator_only(f):  # website pages for creators (session login)
    @wraps(f)
    @login_required
    def wrapper(*a, **k):
        if current_user.role != "creator":
            return err("This is for creator accounts.", 403)
        return f(*a, **k)
    return wrapper


def cap_json(c, detail=False):
    d = dict(id=c.id, kind=c.kind, url=c.url, target_url=c.target_url, title=c.title or "UNKNOWN", author=c.author or "UNKNOWN",
             licence=c.licence or "UNKNOWN", sha256=c.sha256, hash_basis=c.hash_basis, size=c.size,
             server_ts=iso(c.created))
    if detail:
        d.update(client_ts_claimed=c.client_ts or "UNKNOWN", record_sha256=c.record_sha256, notice=CAPTURE_NOTICE)
    return d


# ---- website side (session login): manage tokens, view capture records, download the extension ----
@app.get("/extension")
@login_required
def extension_page():
    if current_user.role != "creator":
        return redirect("/")
    return render_template("extension.html", me={"name": current_user.name, "role": current_user.role}, notice=CAPTURE_NOTICE)


@app.get("/api/tokens")
@creator_only
def tokens_list():
    rows = ApiToken.query.filter_by(user_id=current_user.id, revoked=False).order_by(ApiToken.created.desc()).all()
    return jsonify([dict(id=t.id, prefix=t.prefix, created=iso(t.created), expires=iso(t.expires) if t.expires else None,
                         last_used=iso(t.last_used) if t.last_used else None) for t in rows])


@app.post("/api/tokens")
@creator_only
def tokens_create():
    active = ApiToken.query.filter_by(user_id=current_user.id, revoked=False).count()
    if active >= _int("MAX_TOKENS", 3):
        return err("You already have %d active tokens. Revoke one first." % active, 400)
    raw = "mt_" + secrets.token_urlsafe(32)
    t = ApiToken(user_id=current_user.id, token_hash=_tok_hash(raw), prefix=raw[:9],
                 expires=datetime.utcnow() + timedelta(days=_int("TOKEN_DAYS", 180)))
    db.session.add(t)
    db.session.commit()
    return jsonify(id=t.id, token=raw, prefix=t.prefix, expires=iso(t.expires),
                   note="Copy this token now. It is shown once and cannot be recovered.")


@app.delete("/api/tokens/<int:tid>")
@creator_only
def tokens_revoke(tid):
    t = ApiToken.query.filter_by(id=tid, user_id=current_user.id).first()  # other users' ids return 404
    if not t:
        return err("not found", 404)
    t.revoked = True
    db.session.commit()
    return jsonify(ok=True)


@app.get("/api/captures")
@creator_only
def captures_list():
    rows = Capture.query.filter_by(user_id=current_user.id).order_by(Capture.created.desc()).limit(50).all()
    return jsonify([cap_json(c) for c in rows])


@app.get("/api/captures/<cid>")
@creator_only
def capture_get(cid):
    c = Capture.query.filter_by(id=cid, user_id=current_user.id).first()
    if not c:
        return err("not found", 404)
    body = cap_json(c, detail=True)
    if request.args.get("download") == "1":
        return Response(json.dumps(body, indent=2), mimetype="application/json",
                        headers={"Content-Disposition": 'attachment; filename="capture-%s.json"' % c.id[:8]})
    return jsonify(body)


def _origin():
    base = os.environ.get("PUBLIC_URL", "").rstrip("/") or request.url_root.rstrip("/")
    s = urlsplit(base)
    o = "%s://%s" % (s.scheme, s.netloc)
    return o if re.match(r"^https?://[A-Za-z0-9.\-]+(:\d{1,5})?$", o) else None


@app.get("/extension/download.zip")
@creator_only
def extension_zip():
    """Serve the extension with this site's address baked in, so host permission matches this deployment."""
    o, folder = _origin(), os.path.join(BASE, "extension")
    if not o or not os.path.isdir(folder):
        return err("The extension is not available on this server.", 503)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(folder)):
            p = os.path.join(folder, name)
            if not os.path.isfile(p) or name.startswith("."):
                continue
            data = open(p, "rb").read()
            if name.endswith((".json", ".js")):
                data = data.replace(b"__MANATUNE_URL__", o.encode())
            z.writestr(name, data)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="manatune-extension.zip")


# ---- extension side (Bearer token, no cookies, so no CSRF surface) ----
@app.get("/api/ext/ping")
@token_required
def ext_ping():
    return jsonify(ok=True, name=g.ext_user.name)


@app.post("/api/ext/capture")
@token_required
def ext_capture():
    b = request.get_json(silent=True) or {}
    url, kind, digest, basis = _web_url(b.get("url")), b.get("kind"), str(b.get("sha256", "")).lower(), b.get("hash_basis")
    if not url or kind not in CAPTURE_KINDS or not HEX64.match(digest) or basis not in HASH_BASES:
        return err("This capture could not be validated.", 400)
    target = _web_url(b.get("target_url"))  # data: and blob: image addresses are not stored
    if kind == "image" and basis == "image_url" and not target:
        return err("An image address fingerprint needs a web address for the image.", 400)
    size = b.get("size")
    size = size if isinstance(size, int) and not isinstance(size, bool) and 0 <= size <= 2_000_000_000 else None
    if Capture.query.filter_by(user_id=g.ext_user.id).count() >= _int("MAX_CAPTURES", 5000):
        return err("You have reached the capture limit.", 400)
    c = Capture(id=uuid.uuid4().hex, user_id=g.ext_user.id, kind=kind, url=url, target_url=target if kind == "image" else None, title=_clean(b.get("title"), 300),
                author=_clean(b.get("author"), 300), licence=_clean(b.get("licence"), 500), sha256=digest,
                hash_basis=basis, size=size, client_ts=_clean(b.get("client_ts"), 40), created=datetime.utcnow())
    c.record_sha256 = hashlib.sha256(json.dumps([c.id, c.user_id, c.kind, c.url, c.target_url, c.title, c.author, c.licence, c.sha256,
                                                  c.hash_basis, iso(c.created)]).encode()).hexdigest()
    db.session.add(c)
    db.session.commit()
    return jsonify(cap_json(c, detail=True)), 201


@app.post("/api/ext/repost")
@token_required
def ext_repost():
    """Save a web post to the creator's profile as a link. Nothing is downloaded, copied or hosted."""
    b = request.get_json(silent=True) or {}
    url = _web_url(b.get("url"))
    if not url:
        return err("Only full http:// or https:// links can be reposted.", 400)
    pv = b.get("preview") if isinstance(b.get("preview"), dict) else {}
    image = _web_url(pv.get("image"), 500)  # hotlinked by the browser only; the server never fetches it
    host = (urlsplit(url).hostname or "").replace("www.", "", 1)
    meta = {"source_url": url, "platform": host[:80], "title": _clean(b.get("title"), 200) or host,
            "reposted_by": g.ext_user.name, "reposted_at": iso(datetime.utcnow()), "relationship": "Embed",
            "note": _clean(b.get("note"), 500), "preview_image": image, "preview_text": _clean(pv.get("description"), 300),
            "via": "extension"}
    rid = "x" + hashlib.sha256(("%d|%s" % (g.ext_user.id, url)).encode()).hexdigest()[:31]  # one repost per link per user
    data = {"meta": meta, "hash": hashlib.sha256((json.dumps(meta, sort_keys=True) + url).encode()).hexdigest(),
            "likes": 0, "liked": False, "server_ts": meta["reposted_at"]}
    r = db.session.get(Record, rid)
    if r is None:
        db.session.add(Record(id=rid, kind="repost", owner_id=g.ext_user.id, data=json.dumps(data)))
        dup = False
    elif r.owner_id == g.ext_user.id and r.kind == "repost":
        old = json.loads(r.data)
        old["meta"]["note"], dup = meta["note"], True  # reposting again only updates the note
        r.data = json.dumps(old)
    else:
        return err("forbidden", 403)
    db.session.commit()
    return jsonify(ok=True, id=rid, duplicate=dup, source_url=url, title=meta["title"]), (200 if dup else 201)



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
