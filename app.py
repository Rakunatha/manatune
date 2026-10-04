"""Manatune: the AI browser. One file: Flask backend, Google sign-in, provenance capture, tool discovery.
Social features live in social.py. Every page is embedded below as a template."""
import os, re, json, time, hmac, hashlib, uuid, io, secrets, zipfile
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlsplit, urlunsplit
import requests
from flask import (Flask, request, jsonify, render_template, redirect, flash, url_for, session, g, send_file, Response)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from jinja2 import DictLoader
from sqlalchemy.exc import OperationalError
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
import social  # profiles, follow, tags, ranked feed, report/takedown (social.py)

# ======================= embedded pages =======================
TEMPLATES = {
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
    "workspace.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Manatune: the AI browser</title>
<style>
:root{--bg:#f3f5f9;--card:#fff;--text:#11151b;--mut:#5b6471;--bd:#d9dee7;--blue:#1f7ae8;--blue2:#1665c4;--on:#e6f0fd;--ok:#168246;--bad:#c0392b}
@media (prefers-color-scheme:dark){:root{--bg:#0f1114;--card:#181b20;--text:#fff;--mut:#a7adb6;--bd:#262b33;--blue:#2d8cff;--blue2:#1a5fb4;--on:#14283f;--ok:#4cc282;--bad:#ff7a6b}}
*{box-sizing:border-box}
html,body{height:100%;margin:0}
body{background:var(--bg);color:var(--text);font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;display:flex;flex-direction:column}
button,input,textarea{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
header{display:flex;align-items:center;gap:12px;padding:10px 14px;background:var(--card);border-bottom:1px solid var(--bd);flex-wrap:wrap}
.brand{color:var(--blue);font-size:30px;font-weight:800;letter-spacing:-.02em;line-height:1}
#cmd{flex:1 1 320px;display:flex;gap:8px}
#q{flex:1;min-width:0;background:var(--bg);border:1px solid var(--bd);border-radius:20px;padding:10px 16px}
.btn{background:var(--blue);color:#fff;border:0;border-radius:20px;padding:10px 18px;font-weight:700;cursor:pointer}
.btn:hover{background:var(--blue2)}
.btn:disabled{opacity:.6;cursor:wait}
.btn.ghost{background:none;color:var(--blue);border:1px solid var(--bd);padding:6px 14px;font-size:13px}
.top{display:flex;align-items:center;gap:2px;flex-wrap:wrap}
.top a,.top button{color:var(--mut);background:none;border:0;text-decoration:none;padding:6px 8px;cursor:pointer;font-size:13px}
.top a:hover,.top button:hover{color:var(--text)}
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
.note.bad{color:var(--bad)}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px;margin-bottom:10px}
.row{display:grid;grid-template-columns:1.1fr 1.6fr 1fr 1fr 1.6fr auto;gap:14px;align-items:start;padding:14px;border:1px solid var(--bd);border-radius:10px;margin-bottom:10px;background:var(--card)}
.row.h{background:none;border:0;color:var(--mut);font-size:12px;padding:0 14px;margin-bottom:4px}
.nm{font-weight:700}
.sm{color:var(--mut);font-size:12px}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;word-break:break-all;color:var(--mut)}
.use{display:inline-block;text-decoration:none;background:var(--blue);color:#fff;border-radius:20px;padding:8px 16px;font-weight:700;font-size:13px;white-space:nowrap}
.empty{padding:20px;background:var(--card);border:1px solid var(--bd);border-radius:10px;color:var(--mut)}
.sp{display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}
.pill{display:inline-block;border-radius:12px;padding:2px 10px;font-size:12px;font-weight:700;background:var(--on)}
.pill.ok{color:var(--ok)}.pill.bad{color:var(--bad)}
label{display:block;font-size:12px;color:var(--mut);margin:12px 0 4px}
input,textarea{width:100%;background:var(--bg);border:1px solid var(--bd);border-radius:6px;padding:10px}
#q{width:auto}
@media (max-width:820px){
 nav{width:auto;border-right:0;border-bottom:1px solid var(--bd);display:flex;overflow-x:auto;padding:4px}
 nav button{width:auto;white-space:nowrap;border-left:0;border-bottom:3px solid transparent;border-radius:6px 6px 0 0}
 nav button[aria-current=page]{border-bottom-color:var(--blue)}
 .layout{flex-direction:column}
 .row.h{display:none}
 .row{grid-template-columns:1fr 1fr}
 .row>*:nth-child(2),.row>*:nth-child(5){grid-column:1/-1}
 main{padding:16px}
}
</style>
</head>
<body>
<header>
  <span class="brand">Manatune</span>
  <form id="cmd" role="search"><input id="q" type="text" maxlength="1000" autocomplete="off" aria-label="Command bar" placeholder="What do you want to do? e.g. Find an AI tool for creating product videos"><button class="btn" id="go">Go</button></form>
  <div class="top"><a href="/feed">Feed</a> <a href="/extension">Extension</a>
  <form method="post" action="/logout" style="margin:0"><button>Sign out</button></form></div>
</header>
<div class="layout"><nav id="tabs" aria-label="Sections"></nav><main><div class="wrap" id="view" aria-live="polite"></div></main></div>
<script>
const TABS=[["discover","Discover"],["provenance","Provenance"],["saved","Saved links"]];
const EX=["Find an AI tool for creating product videos","Find a tool to turn a paper into a LinkedIn post","Find a voiceover tool for my launch video"];
const NOTICE={{ notice|tojson }};
const $=s=>document.querySelector(s),view=$("#view"),nav=$("#tabs"),q=$("#q"),go=$("#go");
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
const fld=(l,n)=>{const b=el("label",null,l);b.append(n);return b};
const safe=u=>/^https?:\/\//i.test(u||"")?u:"#";
const api=async(u,b,m)=>{const o=b===undefined?{}:{method:m||"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)};
  const r=await fetch(u,o);if(r.status===401){location.href="/login";throw 0}
  const d=await r.json().catch(()=>({}));if(!r.ok){throw new Error(d.error||"Request failed")}return d};
let tab={{ tab|tojson }};
function fail(e){if(e===0)return;view.querySelectorAll(".note.bad").forEach(n=>n.remove());view.prepend(el("div","note bad",e.message||"Something went wrong."))}
async function act(b,fn){b.disabled=true;try{await fn()}catch(e){fail(e)}b.disabled=false}
function head(t,s){view.replaceChildren(el("h1",null,t),el("p","sub",s||""))}
function renderNav(){nav.replaceChildren(...TABS.map(([k,l])=>{const b=el("button",null,l);if(k===tab)b.setAttribute("aria-current","page");b.onclick=()=>show(k);return b}))}
function show(t){tab=t;renderNav();({discover:vDiscover,provenance:vProvenance,saved:vSaved})[t]()}

function vDiscover(){head("What are you trying to create?","Describe the outcome. Manatune finds the tools that fit it.");
  const c=el("div","chips");EX.forEach(t=>{const b=el("button",null,t);b.onclick=()=>{q.value=t;run()};c.append(b)});view.append(c)}
function results(d){const box=el("div");box.append(el("h1",null,d.outcome||"Recommended tools"));
  if(d.capabilities&&d.capabilities.length)box.append(el("p","sub","Needs: "+d.capabilities.join(", ")));
  if(!d.ai)box.append(el("div","note","Matched by keyword. Add GROQ_API_KEY for AI-ranked recommendations."));
  if(!d.tools.length){box.append(el("div","empty","No tools matched yet. Try naming the output, such as video, voice, image or writing."));return box}
  const h=el("div","row h");["Tool","What it does","Price","Commercial use","Why recommended",""].forEach(x=>h.append(el("span",null,x)));box.append(h);
  d.tools.forEach(t=>{const r=el("div","row"),n=el("div");n.append(el("div","nm",t.name),el("div","sm",t.category));
    const p=el("div");p.append(el("div",null,t.pricing||""),el("div","sm",t.free_tier||""));
    const a=el("a","use","Use tool");a.href=safe(t.url);a.target="_blank";a.rel="noopener noreferrer";
    r.append(n,el("div",null,t.description),p,el("div",null,t.commercial_use||""),el("div",null,t.why),a);box.append(r)});
  if(d.limitations)box.append(el("p","sm",d.limitations));
  box.append(el("p","sm","Pricing and licence terms change. Check each tool's own page before you commit."));return box}
async function run(){const t=q.value.trim();if(!t)return;go.disabled=true;tab="discover";renderNav();view.replaceChildren(el("p","sub","Working on it..."));
  try{view.replaceChildren(results(await api("/api/command",{q:t})))}catch(e){fail(e)}go.disabled=false}
$("#cmd").onsubmit=e=>{e.preventDefault();run()};

async function vProvenance(){head("Provenance","Records captured by the Chrome extension: where something came from, its fingerprint, and the server time.");
  view.append(el("div","note",NOTICE));
  let caps;try{caps=await api("/api/captures")}catch(e){return fail(e)}
  if(!caps.length){view.append(el("div","empty","No captures yet. Install the extension, then capture a selection, image or page."));return}
  caps.forEach(x=>{const c=el("div","card"),t=el("div","sp"),st=el("span","pill");
    t.append(el("div","nm",x.title),el("span","pill",x.kind));
    const u=el("a",null,x.url);u.href=safe(x.url);u.target="_blank";u.rel="noopener noreferrer";
    const acts=el("div","sp");acts.style.justifyContent="flex-start";
    const v=el("button","btn ghost","Check record"),d=el("a","btn ghost","Download JSON");d.href="/api/captures/"+x.id+"?download=1";d.style.textDecoration="none";
    v.onclick=()=>act(v,async()=>{const r=await api("/api/captures/"+x.id+"/verify");st.textContent=r.intact?"Record unchanged":"Record does NOT match";st.className="pill "+(r.intact?"ok":"bad")});
    acts.append(v,d,st);
    c.append(t,u,el("div","sm","Author: "+x.author+" | Licence: "+x.licence+" | Recorded "+x.server_ts),el("div","mono","SHA-256 ("+x.hash_basis+"): "+x.sha256),acts);view.append(c)})}

async function vSaved(){head("Saved links","Links you saved to your profile. Manatune stores the link and a citation, never the content.");
  const u=el("input");u.placeholder="https://";const ti=el("input");ti.maxLength=200;const no=el("textarea");no.rows=2;no.maxLength=500;
  const b=el("button","btn","Save link");
  b.onclick=()=>act(b,async()=>{await api("/api/reposts",{url:u.value,title:ti.value,note:no.value});vSaved()});
  view.append(fld("Link",u),fld("Title (optional)",ti),fld("Note (optional)",no),b);
  let s;try{s=await api("/api/state")}catch(e){return fail(e)}
  const mine=s.reposts.filter(p=>p.mine);
  if(!mine.length){view.append(el("div","empty","Nothing saved yet."));return}
  const lst=el("div");lst.style.marginTop="18px";
  mine.forEach(p=>{const m=p.meta||{},c=el("div","card"),a=el("a",null,m.title||m.source_url);a.href=safe(m.source_url);a.target="_blank";a.rel="noopener noreferrer";
    c.append(a,el("div","sm",(m.platform||"")+" | saved "+(p.server_ts||"")),el("div","mono","SHA-256: "+(p.hash||"")));lst.append(c)});view.append(lst)}

renderNav();show(tab);
</script>
</body>
</html>
''',
    "advocate_home.html": r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Manatune: advocate portal</title>
<style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f3f5f9;color:#11151b;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;padding:16px}
@media (prefers-color-scheme:dark){body{background:#0f1114;color:#fff}.c{background:#181b20!important;border-color:#262b33!important}}
.c{max-width:420px;background:#fff;border:1px solid #d9dee7;border-radius:10px;padding:20px}
button{background:#1f7ae8;color:#fff;border:0;border-radius:20px;padding:9px 18px;font-weight:700;cursor:pointer}
</style>
</head>
<body><div class="c"><h2 style="margin-top:0">Hello, {{ me.name }}</h2>
<p>The IP advocate portal is being built. Signing in works; filing requests will appear here once it is ready.</p>
<form method="post" action="/logout"><button>Sign out</button></form></div></body>
</html>
''',
}


# ======================= AI browser: discovery =======================
STOP = set("a an the to for of and or i want my me is in on with this that how create find tool tools ai use".split())


class AIProvider:  # add another class + PROVIDERS entry to swap providers
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


# ======================= app =======================
def _db_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///manatune.db")
    for prefix in ("postgres://", "postgresql://"):  # Render gives either; pin the psycopg2 driver explicitly
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


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="creator")  # creator | advocate
    pw = db.Column(db.String(255), nullable=False)  # unused legacy column (NOT NULL in existing databases)


class Record(db.Model):  # generic store; kind="repost" for saved links
    __tablename__ = "records"
    id = db.Column(db.String(64), primary_key=True)
    kind = db.Column(db.String(20), index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    data = db.Column(db.Text, nullable=False)
    ts = db.Column(db.DateTime, default=datetime.utcnow)


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


CAPTURE_NOTICE = ("A capture record shows that this page address, title and fingerprint were recorded by your Manatune "
                  "account at the server time shown. It is evidence only: it is not proof of authorship, copyright "
                  "ownership or registration, and it is not legal advice. \"Check record\" confirms the stored fields "
                  "still match their fingerprint; keep your own downloaded copy as an independent reference.")
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


# ======================= helpers =======================
def _int(k, d):
    try:
        return int(os.environ.get(k, d))
    except ValueError:
        return d


def err(m, c):
    return jsonify(error=m), c


def iso(d):
    return d.isoformat(timespec="seconds") + "Z"


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


_hits = {}


def rate_ok(key, n=20):  # per-worker limiter: n calls per minute per key
    now = time.time()
    q = [t for t in _hits.get(key, []) if now - t < 60]
    ok = len(q) < n
    if ok:
        q.append(now)
    _hits[key] = q
    return ok


def creator_only(f):  # website endpoints for creators (session login)
    @wraps(f)
    @login_required
    def wrapper(*a, **k):
        if current_user.role != "creator":
            return err("This is for creator accounts.", 403)
        return f(*a, **k)
    return wrapper


# ======================= discovery =======================
def ensure_seed():
    if Tool.query.count() == 0:
        for n, c, u, cat, d, caps, pr, ft, cu, api, pv in SEED:
            db.session.add(Tool(name=n, company=c, url=u, category=cat, description=d, capabilities=json.dumps(caps),
                                pricing=pr, free_tier=ft, commercial_use=cu, api=api, privacy=pv))
        db.session.commit()


def candidates(q, n=6):
    words = {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", q.lower())} - STOP
    scored = []
    for t in Tool.query.all():
        hay = " ".join([t.name, t.category or "", t.description or "", t.capabilities or ""]).lower()
        scored.append((sum(2 if w in (t.category or "") else 1 for w in words if w in hay), t))
    scored.sort(key=lambda x: -x[0])
    return [t for s, t in scored if s > 0][:n]


def discover(q):
    ts = candidates(q)
    out = {"outcome": q, "capabilities": [], "limitations": "", "ai": False}
    why, p = {}, provider()
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
    out["tools"] = [dict(t.to_dict(), why=why.get(t.id) or "Matches your request: " + (t.description or "")) for t in ts]
    return out


@app.post("/api/command")
@creator_only
def command():
    q = ((request.get_json(silent=True) or {}).get("q") or "").strip()[:1000]
    if not q:
        return err("Type what you want to do.", 400)
    if not rate_ok(("cmd", current_user.id)):
        return err("Slow down a little and try again.", 429)
    ensure_seed()
    return jsonify(discover(q))


# ======================= provenance: capture records =======================
def _tok_hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


def record_hash(c):
    """Fingerprint of every stored field plus the server time. Recomputed by 'Check record'."""
    return hashlib.sha256(json.dumps([c.id, c.user_id, c.kind, c.url, c.target_url, c.title, c.author, c.licence,
                                      c.sha256, c.hash_basis, iso(c.created)]).encode()).hexdigest()


def cap_json(c, detail=False):
    d = dict(id=c.id, kind=c.kind, url=c.url, target_url=c.target_url, title=c.title or "UNKNOWN", author=c.author or "UNKNOWN",
             licence=c.licence or "UNKNOWN", sha256=c.sha256, hash_basis=c.hash_basis, size=c.size, server_ts=iso(c.created))
    if detail:
        d.update(client_ts_claimed=c.client_ts or "UNKNOWN", record_sha256=c.record_sha256, notice=CAPTURE_NOTICE)
    return d


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


# ---- website side (session login): tokens, capture records, extension download ----
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


def _mine_capture(cid):
    return Capture.query.filter_by(id=cid, user_id=current_user.id).first()  # other users' ids behave like missing ones


@app.get("/api/captures/<cid>")
@creator_only
def capture_get(cid):
    c = _mine_capture(cid)
    if not c:
        return err("not found", 404)
    body = cap_json(c, detail=True)
    if request.args.get("download") == "1":
        return Response(json.dumps(body, indent=2), mimetype="application/json",
                        headers={"Content-Disposition": 'attachment; filename="capture-%s.json"' % c.id[:8]})
    return jsonify(body)


@app.get("/api/captures/<cid>/verify")
@creator_only
def capture_verify(cid):
    c = _mine_capture(cid)
    if not c:
        return err("not found", 404)
    now = record_hash(c)
    return jsonify(intact=hmac.compare_digest(now, c.record_sha256 or ""), stored=c.record_sha256, recomputed=now,
                   note="This checks the stored fields against their fingerprint. It is not proof of authorship.")


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
            with open(p, "rb") as fh:
                data = fh.read()
            if name.endswith((".json", ".js")):
                data = data.replace(b"__MANATUNE_URL__", o.encode())
            z.writestr(name, data)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip", as_attachment=True, download_name="manatune-extension.zip")


# ---- saved links ("reposts"): a link plus a citation, nothing downloaded, copied or hosted ----
def save_link(user, b, via):
    url = _web_url(b.get("url"))
    if not url:
        return err("Only full http:// or https:// links can be saved.", 400)
    pv = b.get("preview") if isinstance(b.get("preview"), dict) else {}
    host = (urlsplit(url).hostname or "").replace("www.", "", 1)
    meta = {"source_url": url, "platform": host[:80], "title": _clean(b.get("title"), 200) or host,
            "reposted_by": user.name, "reposted_at": iso(datetime.utcnow()), "relationship": "Embed",
            "note": _clean(b.get("note"), 500), "preview_image": _web_url(pv.get("image"), 500),  # hotlinked by the browser only
            "preview_text": _clean(pv.get("description"), 300), "via": via}
    rid = "x" + hashlib.sha256(("%d|%s" % (user.id, url)).encode()).hexdigest()[:31]  # one saved link per URL per user
    data = {"meta": meta, "hash": hashlib.sha256((json.dumps(meta, sort_keys=True) + url).encode()).hexdigest(),
            "likes": 0, "liked": False, "server_ts": meta["reposted_at"]}
    r = db.session.get(Record, rid)
    if r is None:
        db.session.add(Record(id=rid, kind="repost", owner_id=user.id, data=json.dumps(data)))
        dup = False
    elif r.owner_id == user.id and r.kind == "repost":
        old = json.loads(r.data)
        old["meta"]["note"], dup = meta["note"], True  # saving again only updates the note
        r.data = json.dumps(old)
    else:
        return err("forbidden", 403)
    db.session.commit()
    return jsonify(ok=True, id=rid, duplicate=dup, source_url=url, title=meta["title"]), (200 if dup else 201)


@app.post("/api/reposts")
@creator_only
def repost_web():
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        return err("Cross-site requests are not allowed.", 403)
    return save_link(current_user, request.get_json(silent=True) or {}, "web")


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
    c = Capture(id=uuid.uuid4().hex, user_id=g.ext_user.id, kind=kind, url=url, target_url=target if kind == "image" else None,
                title=_clean(b.get("title"), 300), author=_clean(b.get("author"), 300), licence=_clean(b.get("licence"), 500),
                sha256=digest, hash_basis=basis, size=size, client_ts=_clean(b.get("client_ts"), 40), created=datetime.utcnow())
    c.record_sha256 = record_hash(c)
    db.session.add(c)
    db.session.commit()
    return jsonify(cap_json(c, detail=True)), 201


@app.post("/api/ext/repost")
@token_required
def ext_repost():
    return save_link(g.ext_user, request.get_json(silent=True) or {}, "extension")


# ======================= social module (Feature 2; unchanged for now) =======================
S = social.register(app, db, User, Record, dict(err=err, rate_ok=rate_ok, int=_int, clean=_clean, iso=iso, web_url=_web_url))
TEMPLATES.update(social.TEMPLATES)  # the Jinja DictLoader reads this same dict

with app.app_context():
    for attempt in range(6):  # the database can take a moment to accept connections on boot
        try:
            db.create_all()
            break
        except OperationalError:
            if attempt == 5:
                raise
            time.sleep(3)
    try:
        S.backfill()  # give existing creators a profile handle
    except Exception:
        db.session.rollback()
        app.logger.exception("Profile backfill skipped")


@app.get("/health")
@app.get("/healthz")
def health():
    return jsonify(status="ok")


@lm.user_loader
def load_user(i):
    return db.session.get(User, int(i))


@lm.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return jsonify(error="login required"), 401
    return redirect("/login")


# ---------------- pages ----------------
def _page(tab="discover"):
    me = {"name": current_user.name, "role": current_user.role}
    if current_user.role == "advocate":
        return render_template("advocate_home.html", me=me)
    return render_template("workspace.html", me=me, tab=tab, notice=CAPTURE_NOTICE)


@app.get("/")
@login_required
def index():
    return _page("discover")


@app.get("/provenance")
@login_required
def provenance_page():
    return _page("provenance")


@app.get("/saved")
@login_required
def saved_page():
    return _page("saved")


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
@app.get("/api/state")
@login_required
def state():
    """Saved links visible to this person. Taken-down posts are gone; posts awaiting review show only to their owner."""
    rows = Record.query.filter_by(kind="repost").order_by(Record.ts.desc()).limit(100).all()
    posts = []
    for r in S.visible(rows, current_user.id):
        d = json.loads(r.data)
        d["id"], d["mine"] = r.id, r.owner_id == current_user.id
        posts.append(d)
    return jsonify(reposts=posts)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
