#!/usr/bin/env python3
"""Emit docs/operating-stack.html from a stack dataset.

The page renders itself from its own embedded payload at load, so the JSON an
agent parses and the page a human reads can never disagree. Regenerate after
editing the dataset; never hand-edit the HTML.

    python3 scripts/build_operating_stack.py --data <stack-data.json> -o docs/operating-stack.html
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Toolkit plugin ids are read from the marketplace so the two cannot drift.
def toolkit_ids(root: Path) -> set[str]:
    mk = root / ".claude-plugin" / "marketplace.json"
    if not mk.exists():
        return set()
    return {p["name"] for p in json.loads(mk.read_text())["plugins"]}


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>RossLabs Operating Stack</title>
<meta name="description" content="How the RossLabs toolkit plugins fit together: five layers, left to right, following data flow.">
<!--
  MACHINE-READABLE VIEW. Self-contained: no build step to VIEW, no server, no
  external data. Open with any browser (file:// works) or read as plain text.

  AGENTS: the dataset behind every section is embedded as JSON between the
  markers STACK-DATA-BEGIN and STACK-DATA-END near the end of the body. Split
  rather than regex, so this example contains no comment-closing sequence:

      import json
      s = open("operating-stack.html").read()
      raw = s.split("STACK-DATA-BEGIN")[-1].split("STACK-DATA-END")[0]
      d = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
      print([l["name"] for l in d["layers"]], len(d["inventory"]))

  Take the LAST match, never the first: these marker names also appear in this
  comment, so a first-match extractor reads the documentation instead of the data.

  The page RENDERS FROM that payload at load. Counts shown on screen are computed
  from it, so page and data cannot drift. Regenerate with
  scripts/build_operating_stack.py; do not hand-edit this file.
-->
<style>
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0}
img,svg{max-width:100%}
[hidden]{display:none!important}

/* RossLabs tokens. Geist Sans needs ss03/ss05/ss09; Geist Mono needs NONE —
   ss09 runs backwards there and would un-slash the zero. */
:root{
  --paper:#ffffff; --sunk:#f4f5f7; --ink:#14161a; --ink-2:#3d434d; --muted:#5b6270;
  --line:#e2e5ea; --line-2:#ccd1da; --accent:#1f4fd8; --accent-soft:#e8edfd;
  --ok:#186a3b; --warn:#8a5a12; --stop:#a3243c;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --paper:#0e1013; --sunk:#161a1f; --ink:#e9ecf1; --ink-2:#bcc3ce; --muted:#8b93a1;
  --line:#242931; --line-2:#333a45; --accent:#7d9cff; --accent-soft:#18213a;
  --ok:#5fbf92; --warn:#d9a441; --stop:#f0788f;
}}
:root[data-theme="dark"]{
  --paper:#0e1013; --sunk:#161a1f; --ink:#e9ecf1; --ink-2:#bcc3ce; --muted:#8b93a1;
  --line:#242931; --line-2:#333a45; --accent:#7d9cff; --accent-soft:#18213a;
  --ok:#5fbf92; --warn:#d9a441; --stop:#f0788f;
}
@font-face{font-family:"GeistLocal";src:local("Geist"),local("Geist Regular");font-weight:400;font-display:swap}
@font-face{font-family:"GeistLocal";src:local("Geist Medium");font-weight:500;font-display:swap}
@font-face{font-family:"GeistLocal";src:local("Geist SemiBold");font-weight:600;font-display:swap}
@font-face{font-family:"GeistMonoLocal";src:local("Geist Mono"),local("GeistMono-Regular");font-weight:400;font-display:swap}

body{background:var(--paper);color:var(--ink);
  font-family:"GeistLocal",-apple-system,"Helvetica Neue",Arial,sans-serif;
  font-feature-settings:"ss03","ss05","ss09";
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.mono{font-family:"GeistMonoLocal",ui-monospace,SFMono-Regular,Menlo,monospace;font-feature-settings:normal}
.wrap{max-width:1180px;margin:0 auto;padding:36px 22px 80px}
h1{font-size:clamp(25px,3.4vw,36px);line-height:1.1;letter-spacing:-.02em;margin:0;font-weight:600;text-wrap:balance}
h2{font-size:19px;margin:0;font-weight:600;letter-spacing:-.01em}
p{margin:0}
a{color:var(--accent)}

.mast{border-bottom:1px solid var(--line-2);padding-bottom:18px;margin-bottom:8px}
.eyebrow{font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:9px}
.lede{color:var(--ink-2);max-width:66ch;margin-top:11px}
.asof{font-size:11.5px;color:var(--muted);margin-top:9px;letter-spacing:.04em}
.facts{display:flex;gap:22px;flex-wrap:wrap;margin-top:14px;
  font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;font-size:11.5px;color:var(--muted)}
.facts b{display:block;color:var(--ink);font-size:15px;font-weight:500}

.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:14px 0 18px}
.btn{font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;font-size:11.5px;
  min-height:44px;padding:6px 13px;border-radius:7px;border:1px solid var(--line-2);
  background:transparent;color:var(--ink-2);cursor:pointer;letter-spacing:.03em}
.btn:hover{border-color:var(--accent);color:var(--ink)}
.btn[aria-pressed="true"]{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.btn:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.hint{font-size:12px;color:var(--muted)}

/* the flow: five layers, left to right */
.flowline{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
  font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:11px;color:var(--muted);margin-bottom:10px}
.flowline i{font-style:normal;color:var(--accent)}
#board{position:relative}
.layers{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;position:relative;z-index:1}
.layer{background:var(--sunk);border:1px solid var(--line);border-radius:11px;padding:13px;
  display:flex;flex-direction:column;gap:9px;min-width:0}
.lhead .n{font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.lhead b{display:block;font-size:14px;font-weight:600;margin-top:2px}
.lhead .axis{display:block;font-size:11.5px;color:var(--accent);margin-top:2px}
.lhead .def{display:block;font-size:11.5px;color:var(--muted);line-height:1.45;margin-top:5px}
.seg{border-top:1px dashed var(--line-2);padding-top:8px}
.seg .sname{font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2);margin-bottom:5px}
.nodes{display:flex;flex-direction:column;gap:5px}
.node{text-align:left;width:100%;background:var(--paper);border:1px solid var(--line);border-radius:7px;
  padding:7px 9px;cursor:pointer;font:inherit;color:inherit;min-height:44px}
.node:hover{border-color:var(--accent)}
.node:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.node[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent)}
.node .nm{display:block;font-size:12.5px;font-weight:500;line-height:1.3}
.node .meta{display:block;font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:9.5px;letter-spacing:.05em;color:var(--muted);margin-top:2px}
.node.tk{border-left:3px solid var(--accent)}
.node.dim{opacity:.32}
.deg{float:right;font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:9.5px;color:var(--accent)}
#wires{position:absolute;inset:0;z-index:0;pointer-events:none}

/* pop-out detail */
.detail{border:1px solid var(--line-2);border-radius:11px;background:var(--sunk);padding:16px 18px;margin-top:14px}
.detail .dh{display:flex;justify-content:space-between;gap:12px;align-items:baseline;flex-wrap:wrap}
.detail h3{margin:0;font-size:17px;font-weight:600}
.detail .tags{font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:10.5px;color:var(--muted);letter-spacing:.05em}
.detail .use{margin-top:8px;color:var(--ink-2);max-width:70ch}
.detail ul{margin:12px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:7px}
.detail li{border-top:1px solid var(--line);padding-top:7px;font-size:13px}
.detail .rel{color:var(--accent);font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;font-size:11.5px}
.detail .ev{display:block;color:var(--muted);font-size:11.5px;line-height:1.45;margin-top:2px}
.detail .empty{color:var(--muted);font-size:13px;margin-top:10px}

section{margin-top:40px}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:11px}
table{border-collapse:collapse;width:100%;font-size:13px}
@media (min-width:680px){table{min-width:640px}}
th{text-align:left;background:var(--sunk);border-bottom:1px solid var(--line-2);padding:9px 12px;
  font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:500}
td{padding:9px 12px;border-top:1px solid var(--line);vertical-align:top}
footer{margin-top:52px;padding-top:16px;border-top:1px solid var(--line);
  font-family:"GeistMonoLocal",ui-monospace,Menlo,monospace;font-feature-settings:normal;
  font-size:11px;color:var(--muted);display:flex;gap:18px;flex-wrap:wrap;justify-content:space-between}
@media (max-width:900px){.layers{grid-template-columns:repeat(2,minmax(0,1fr))}#wires{display:none}}
@media (max-width:560px){.layers{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <div class="eyebrow">RossLabs AI Toolkit</div>
  <h1>The operating stack</h1>
  <p class="asof mono">Snapshot as of <time datetime="__ASOF__">__ASOF__</time></p>
  <p class="lede" id="lede"></p>
  <div class="facts" id="facts"></div>
</header>

<div class="flowline" id="flowline"></div>

<div class="controls">
  <button class="btn" id="wireToggle" aria-pressed="false">connections: off</button>
  <button class="btn" id="tkToggle" aria-pressed="false">toolkit plugins only</button>
  <button class="btn" id="clearBtn">clear selection</button>
  <span class="hint">Connections are off by default because 30 wires at once are unreadable. Select any component to pop out its detail and see only its links.</span>
</div>

<div id="board"><svg id="wires" aria-hidden="true"></svg><div class="layers" id="layers"></div></div>
<div class="detail" id="detail"></div>

<section>
  <h2>Every recorded connection</h2>
  <p class="lede" style="margin-bottom:12px">Each row carries the evidence string it was read from. A component with no row has no recorded connection, which is a gap in the record rather than a claim of independence.</p>
  <div class="tblwrap"><table>
    <thead><tr><th>From</th><th>Relation</th><th>To</th><th>When</th><th>Read from</th></tr></thead>
    <tbody id="edgeRows"></tbody>
  </table></div>
</section>

<footer>
  <span>Generated by scripts/build_operating_stack.py &middot; do not hand-edit</span>
  <span id="asof"></span>
</footer>
</div>
"""

SCRIPT = r"""
<script>
const DATA = JSON.parse(document.getElementById("stack-data").textContent);
const TK = new Set(DATA.toolkitPlugins || []);
const BY = Object.fromEntries(DATA.inventory.map(r => [r.id, r]));
const REL = {hosts:"runs inside","dispatches":"hands work to","routes-model-via":"picks its model via",
  "verifies-with":"is checked by",reads:"reads",writes:"writes to","ships-to":"deploys to",
  "backed-by":"is backed by","companion-of":"is the daemon for",supersedes:"replaces"};
const esc = t => String(t).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const nm = id => BY[id] ? BY[id].name : id;
const degree = id => DATA.edges.filter(e => e.from === id || e.to === id).length;

document.getElementById("lede").textContent = DATA.flow;
document.getElementById("asof").textContent = "as of " + DATA.dateCreated;
const placed = DATA.layers.reduce((n,l)=>n+l.members.length,0);
document.getElementById("facts").innerHTML =
  [["Layers",DATA.layers.length],["Components placed",placed],["Connections",DATA.edges.length],
   ["Toolkit plugins here",DATA.layers.flatMap(l=>l.members).filter(i=>TK.has(i)).length]]
  .map(([k,v])=>`<div>${k}<b>${v}</b></div>`).join("");
document.getElementById("flowline").innerHTML =
  DATA.layers.map(l=>`<span>${esc(l.name)}</span>`).join('<i>&rarr;</i>');

function nodeHTML(id){
  const r = BY[id]; if(!r) return "";
  const bits = [r.kind==="own-product"?"own product":r.kind==="own-tool"?"own tool":"third-party"];
  if(r.scope) bits.push(r.scope);
  if(r.status && r.status!=="current") bits.push(r.status);
  const d = degree(id);
  return `<button class="node${TK.has(id)?" tk":""}" data-id="${id}" aria-pressed="false">
    <span class="nm">${esc(r.name)}${d?`<span class="deg">${d}</span>`:""}</span>
    <span class="meta">${esc(bits.join(" · "))}</span></button>`;
}
document.getElementById("layers").innerHTML = DATA.layers.map(L => {
  const head = `<div class="lhead"><span class="n">Layer ${L.n}</span><b>${esc(L.name)}</b>
    <span class="axis">${esc(L.axis||"")}</span><span class="def">${esc(L.definition)}</span></div>`;
  const body = L.segments
    ? L.segments.map(s=>`<div class="seg"><div class="sname">${esc(s.name)}</div>
        <div class="nodes">${s.members.map(nodeHTML).join("")}</div></div>`).join("")
    : `<div class="nodes">${L.members.map(nodeHTML).join("")}</div>`;
  return `<div class="layer">${head}${body}</div>`;
}).join("");

document.getElementById("edgeRows").innerHTML = DATA.edges.map(e =>
  `<tr><td>${esc(nm(e.from))}</td><td class="rel">${esc(REL[e.rel]||e.rel)}</td>
   <td>${esc(nm(e.to))}</td><td>${esc(e.when||"")}</td><td>${esc(e.evidence)}</td></tr>`).join("");

const detail = document.getElementById("detail");
function showDetail(id){
  if(!id){ detail.innerHTML = `<p class="empty">Select a component to see what it is, what it does, and everything it connects to.</p>`; return; }
  const r = BY[id], mine = DATA.edges.filter(e=>e.from===id||e.to===id);
  const tags = [r.kind==="own-product"?"own product":r.kind==="own-tool"?"own tool":"third-party",
    r.category, r.scope, r.status, TK.has(id)?"in the toolkit":null].filter(Boolean).join(" · ");
  detail.innerHTML = `<div class="dh"><h3>${esc(r.name)}</h3><span class="tags">${esc(tags)}</span></div>
    <p class="use">${esc(r.use)}</p>` + (mine.length
      ? `<ul>${mine.map(e=>{const out=e.from===id;
          return `<li><span class="rel">${out?"&rarr;":"&larr;"} ${esc(REL[e.rel]||e.rel)}</span>
            ${esc(nm(out?e.to:e.from))}${e.when?` <span class="tags">when: ${esc(e.when)}</span>`:""}
            <span class="ev">${esc(e.evidence)}</span></li>`}).join("")}</ul>`
      : `<p class="empty">No recorded connection. That is a gap in the record, not a claim of independence.</p>`);
}
showDetail(null);

let sel = null, wires = false, tkOnly = false;
const svg = document.getElementById("wires");
function linked(id){ const s=new Set([id]);
  DATA.edges.forEach(e=>{ if(e.from===id) s.add(e.to); if(e.to===id) s.add(e.from); }); return s; }
function paint(){
  const keep = sel ? linked(sel) : null;
  document.querySelectorAll(".node").forEach(n=>{
    const id=n.dataset.id;
    n.setAttribute("aria-pressed", String(id===sel));
    n.classList.toggle("dim", (keep && !keep.has(id)) || (tkOnly && !TK.has(id)));
  });
  drawWires();
}
function drawWires(){
  svg.innerHTML="";
  if(!wires && !sel) return;
  const board=document.getElementById("board").getBoundingClientRect();
  svg.setAttribute("viewBox",`0 0 ${board.width} ${board.height}`);
  svg.setAttribute("width",board.width); svg.setAttribute("height",board.height);
  const pos={};
  document.querySelectorAll(".node").forEach(n=>{const b=n.getBoundingClientRect();
    pos[n.dataset.id]={x:b.left-board.left+b.width/2,y:b.top-board.top+b.height/2};});
  const show = DATA.edges.filter(e => sel ? (e.from===sel||e.to===sel) : true);
  svg.innerHTML = show.map(e=>{const a=pos[e.from],b=pos[e.to]; if(!a||!b) return "";
    const mx=(a.x+b.x)/2;
    return `<path d="M${a.x} ${a.y} C ${mx} ${a.y} ${mx} ${b.y} ${b.x} ${b.y}"
      fill="none" stroke="var(--accent)" stroke-width="1.2" opacity="${sel?0.85:0.28}">
      <title>${esc(nm(e.from))} ${esc(REL[e.rel]||e.rel)} ${esc(nm(e.to))}</title></path>`;}).join("");
}
document.getElementById("layers").addEventListener("click", ev=>{
  const n=ev.target.closest(".node"); if(!n) return;
  sel = (sel===n.dataset.id) ? null : n.dataset.id;
  showDetail(sel); paint();
});
const wt=document.getElementById("wireToggle");
wt.addEventListener("click",()=>{wires=!wires;wt.setAttribute("aria-pressed",String(wires));
  wt.textContent="connections: "+(wires?"on":"off");paint();});
const tt=document.getElementById("tkToggle");
tt.addEventListener("click",()=>{tkOnly=!tkOnly;tt.setAttribute("aria-pressed",String(tkOnly));paint();});
document.getElementById("clearBtn").addEventListener("click",()=>{sel=null;showDetail(null);paint();});
addEventListener("resize",drawWires);
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--out", type=Path, required=True)
    a = ap.parse_args()

    d = json.loads(a.data.read_text())
    root = Path(__file__).resolve().parent.parent
    d["toolkitPlugins"] = sorted(toolkit_ids(root))
    payload = json.dumps(d, indent=1, ensure_ascii=False)

    head = HEAD.replace("__ASOF__", d.get("dateCreated", ""))
    html = (head
            + "\n<!--STACK-DATA-BEGIN-->\n"
            + '<script type="application/json" id="stack-data">\n'
            + payload + "\n</script>\n<!--STACK-DATA-END-->\n"
            + SCRIPT)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(html, encoding="utf-8")
    print(f"wrote {a.out} ({len(html)} bytes); toolkit plugins tagged: {len(d['toolkitPlugins'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
