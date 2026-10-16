"""SERA v0.9 — generate fully offline, source-locked browser review workspaces.

Each HTML file embeds ONLY its own blank review form + lexical cue hints.
No analyst event suggestions, outside assets, server APIs, authentication
pretence, local persistent storage, or model requests. Editing happens
in browser memory; export is JSON compatible with v0.8 validator.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.sera.sentence_review_packet_v07 import (
    generate_mara_packet, validate_review_packet,
)
from experiments.sera.mara_s1_v04_audit import PATH
from experiments.sera.review_adjudication_v08 import (
    blank_annotation, validate_annotation,
)

TITLE = "SERA Mara S1 — Blind Review Workspace"
HTML = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>__TITLE__</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#18263c;background:#eef2f7}
*{box-sizing:border-box}body{margin:0}header{background:#142945;color:white;padding:20px max(20px,calc((100vw - 1180px)/2))}
header h1{margin:0 0 6px;font-size:21px}header p{margin:0;color:#d3deed}
main{max-width:1180px;margin:20px auto;padding:0 16px 28px}
.notice{border-left:4px solid #e4a734;background:#fff9e9;padding:12px 16px;margin-bottom:16px}
.layout{display:grid;grid-template-columns:240px minmax(0,1fr);gap:18px}
aside,.pane{background:white;border:1px solid #d7dfeb;border-radius:12px;padding:16px}
aside{align-self:start;max-height:80vh;overflow:auto;position:sticky;top:12px}
aside h2{font-size:15px;margin:0 0 12px}.nav{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}
.nav button{padding:9px 2px;border-radius:8px;border:1px solid #b5c3d4;background:#f0f4f9;color:#253d54}
.nav button.active{background:#163c62;color:white}.nav button.done{border-color:#287a66}
.nav button.partial{border-color:#e6a732}
article h2{font-size:21px;margin:4px 0 12px}
.quote{background:#f4f7fb;border-radius:8px;padding:16px;font-size:17px;line-height:1.7;white-space:pre-wrap}
small,.muted{color:#546780}label{display:block;font-weight:600;font-size:13px;margin:10px 0 5px}
select,input,textarea{width:100%;padding:9px 11px;font:inherit;background:white;border:1px solid #aab9ce;border-radius:7px;color:#14243a}
textarea{min-height:70px;resize:vertical}
.field-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.entity{border:1px solid #d7dfeb;border-radius:9px;padding:11px;margin:9px 0}
.entity strong{font-size:14px}
.events{margin:12px 0;padding:12px;border:1px solid #cdd7e4;border-radius:9px}
.event{padding:8px;background:#f5f8fc;margin:8px 0;border-radius:8px}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
button{cursor:pointer;font:inherit;border:0;border-radius:7px;padding:10px 13px;background:#1f567f;color:white}
button.secondary{background:#e5edf5;color:#233d57}
button.danger{background:#a73d3d}button:disabled{opacity:.5;cursor:not-allowed}
.status{margin:10px 0;padding:9px 12px;background:#edf4fb;border-radius:7px;font-size:13px}
.pill{display:inline-block;background:#dbeaf5;color:#1a4770;padding:2px 8px;border-radius:12px;font-size:12px}
.footer{margin-top:20px;font-size:13px;color:#435a70}
#fileInput{display:none}
@media(max-width:730px){.layout{grid-template-columns:1fr}aside{position:static;max-height:none}.field-grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header><h1>__TITLE__</h1><p>Bağımsız cümle ve olay incelemesi · Tamamen çevrimdışı · Kanonik onay DEĞİL</p></header>
<main>
<div class="notice"><strong>Önemli:</strong> Bu çalışma sayfası gerçek insan kimliğini doğrulamaz; kararların doğruluğunu da garanti etmez. İlerleme yalnızca tarayıcı belleğindedir; çıkmadan önce JSON olarak dışa aktarın. Başka değerlendiricinin cevaplarını görmeyin.</div>
<div class="actions" style="margin:0 0 16px">
<button id="exportBtn" type="button">JSON değerlendirmeyi indir</button>
<button id="importBtn" class="secondary" type="button">Önceki JSON'u içe aktar</button>
<input id="fileInput" type="file" accept=".json,application/json">
</div>
<div class="layout">
<aside><h2>Cümleler <span id="progress" class="pill"></span></h2><div id="navigation" class="nav" aria-label="Cümle seçici"></div>
<p class="footer">Yeşil: gözden geçirilmiş · Sarı: yarım · Gri: incelenmemiş.</p></aside>
<section class="pane" id="workspace">
<article>
<div id="sentenceMeta" class="muted"></div>
<h2 id="sentenceTitle">Cümle</h2>
<div id="sentenceQuote" class="quote"></div>
<p id="cueNotice" class="muted"></p>
<label for="disposition">Cümlenin genel sınıfı</label>
<select id="disposition"></select>
<div id="entityList"></div>
<h3>Olaylar ve kaynak kanıtı</h3>
<p class="muted">Tek bir cümlede birden fazla olay olabilir. Her olay için metinden birebir bir ifade seçin. Birden fazla cümleye yayılan olayda aynı event_id'yi tekrar kullanın.</p>
<div id="eventList"></div>
<div class="events">
<div class="field-grid">
<div><label for="eventId">Olay kimliği</label><input id="eventId" placeholder="ör. ev_01_watch_case"></div>
<div><label for="eventType">Olay türü</label><select id="eventType"></select></div>
<div><label for="eventEpistemic">Bilginin türü</label><select id="eventEpistemic"></select></div>
<div><label for="eventEffect">Durum etkisi</label><select id="eventEffect"></select></div>
<div><label for="eventQuote">Cümleden birebir alıntı</label><input id="eventQuote" placeholder="ör. closed the case"></div>
<div><label for="eventOccurrence">Alıntının kaçıncı geçişi (1'den)</label><input id="eventOccurrence" type="number" min="1" step="1" value="1"></div>
</div>
<label for="eventRefs">İlgili nesne / karakter kimlikleri (virgülle)</label>
<input id="eventRefs" placeholder="vane, vane_watch">
<label for="eventReason">Olayın neden bu şekilde sınıflandırıldığı</label>
<textarea id="eventReason" rows="2" placeholder="Metin kanıtını ve iddia/gerçek ayrımını açıklayın"></textarea>
<div class="actions"><button id="addEvent" type="button">Olayı ekle</button><button id="clearEvent" type="button" class="secondary">Alanları temizle</button></div>
</div>
<label for="rowNotes">İnceleme notları / eksik olabilecek nesneler</label>
<textarea id="rowNotes" placeholder="Çözülemeyen nesneleri, zamirleri, bağlamı buraya not edin"></textarea>
<div class="status" id="statusText" role="status"></div>
<div class="actions"><button class="secondary" id="prev" type="button">← Önceki</button><button id="next" type="button">Sonraki →</button></div>
</article>
</section>
</div>
<p class="footer">SERA v0.9 · Tamamen istemci tarafı çalışma · Harici bağlantı/API/veri kaydı yok · Elde edilen JSON mutlaka Python v0.8 validator ve güvenilir hakem tarafından ayrıca kontrol edilmelidir.</p>
</main>
<script id="reviewForm" type="application/json">__FORM_JSON__</script>
<script id="reviewCues" type="application/json">__CUES_JSON__</script>
<script>
"use strict";
let form = JSON.parse(document.getElementById("reviewForm").textContent);
const cues = JSON.parse(document.getElementById("reviewCues").textContent);
const initialMeta = Object.freeze({
 schema:form.schema, scene_key:form.scene_key,
 prose_sha256:form.prose_sha256, source_packet_sha256:form.source_packet_sha256,
 reviewer_alias:form.reviewer_alias
});
let current = 0;
const byId = id => document.getElementById(id);
const DISPOSITIONS=["UNREVIEWED","STATE_EVENT","KNOWLEDGE_EVENT","CLAIM_ONLY","NO_TRACKED_CHANGE","TEXTURE","AMBIGUOUS"];
const ENTITY=["UNREVIEWED","PHYSICALLY_PRESENT","MENTIONED_ONLY","REPORTED_ONLY","NOT_ENTITY","AMBIGUOUS"];
const TYPES=["OBSERVE","DISCOVER","COMMUNICATE","WRITE","OPEN","CLOSE","MOVE","TRANSFER","CHANGE_STATE","KNOWLEDGE_UPDATE","CLAIM_MENTION","UNMAPPED"];
const EPISTEMIC=["OBSERVED_ACTION","REPORTED_CLAIM","NARRATOR_ASSERTION","HYPOTHESIS","NEGATED","UNCERTAIN"];
const EFFECTS=["NONE","OBJECT","DOCUMENT","CHARACTER_KNOWLEDGE","WORLD","UNKNOWN"];
function element(tag,parent,text,cls){
 const node=document.createElement(tag);
 if(cls)node.className=cls;
 if(text!==undefined&&text!==null)node.textContent=String(text);
 if(parent)parent.appendChild(node);
 return node;
}
function fillOptions(select, values, value){
 select.replaceChildren();
 for(const v of values){const opt=element("option",select,v);opt.value=v;}
 select.value=value || values[0];
}
function message(text,problem=false){
 const node=byId("statusText"); node.textContent=text;
 node.style.background=problem?"#ffebeb":"#edf4fb";
}
function rowComplete(row){
 return row.disposition!=="UNREVIEWED" &&
 row.entity_decisions.every(x=>x.decision!=="UNREVIEWED"&&x.reason.trim()) &&
 (!["STATE_EVENT","KNOWLEDGE_EVENT"].includes(row.disposition)||row.events.length>0);
}
function refreshNav(){
 const nav=byId("navigation");nav.replaceChildren();
 const finished=form.rows.filter(rowComplete).length;
 byId("progress").textContent=finished+"/"+form.rows.length;
 form.rows.forEach((row,i)=>{
  const btn=element("button",nav,String(i+1));
  btn.type="button";btn.title=row.sentence_id;
  btn.className=(i===current?"active ":"")+(rowComplete(row)?"done":row.disposition==="UNREVIEWED"?"":"partial");
  btn.addEventListener("click",()=>{current=i;render();});
 });
}
function quoteOffsets(sentence,phrase,occurrence){
 if(!phrase)return null;
 const hay=Array.from(sentence.quote), term=Array.from(phrase);
 const matches=[];
 for(let i=0;i+term.length<=hay.length;i++){
  let yes=true;
  for(let j=0;j<term.length;j++){if(hay[i+j]!==term[j]){yes=false;break;}}
  if(yes)matches.push(i);
 }
 if(!Number.isSafeInteger(occurrence)||occurrence<1||occurrence>matches.length)
   return null;
 const start=sentence.start+matches[occurrence-1];
 return {start,end:start+term.length,quote:phrase};
}
function resetEvent(){
 ["eventId","eventQuote","eventRefs","eventReason"].forEach(id=>byId(id).value="");
 byId("eventOccurrence").value="1";
 fillOptions(byId("eventType"),TYPES,"OBSERVE");
 fillOptions(byId("eventEpistemic"),EPISTEMIC,"OBSERVED_ACTION");
 fillOptions(byId("eventEffect"),EFFECTS,"NONE");
}
function renderEvents(row){
 const target=byId("eventList");target.replaceChildren();
 row.events.forEach((evt,i)=>{
  const node=element("div",target,null,"event");
  element("strong",node,evt.event_id+" — "+evt.event_type);
  element("div",node,"“"+evt.quote+"” · "+evt.epistemic+" · "+evt.effect);
  element("div",node,"Refs: "+evt.entity_refs.join(", ")+" · "+evt.reason,"muted");
  const remove=element("button",node,"Olayı sil","danger");
  remove.type="button";
  remove.addEventListener("click",()=>{row.events.splice(i,1);renderEvents(row);refreshNav();message("Olay silindi; JSON kaydettiğinizde güncel form aktarılır.");});
 });
 if(!row.events.length)element("p",target,"Henüz olay eklenmedi.","muted");
}
function render(){
 const row=form.rows[current];
 byId("sentenceMeta").textContent=row.sentence_id+" · "+row.start+"–"+row.end+" · "+form.reviewer_alias;
 byId("sentenceTitle").textContent="Cümle "+(current+1)+" / "+form.rows.length;
 byId("sentenceQuote").textContent=row.quote;
 const cue=cues[row.sentence_id]||[];
 byId("cueNotice").textContent="Bağımsız sözcük/eylem ipuçları: "+(cue.join(", ")||"Yok (bu, olay olmadığı anlamına gelmez)");
 fillOptions(byId("disposition"),DISPOSITIONS,row.disposition);
 byId("disposition").onchange=e=>{
  if(e.target.value==="UNREVIEWED" && row.disposition!=="UNREVIEWED"){
   if(!confirm("Bu cümledeki bütün işaretlemeleri sıfırlamak istiyor musunuz?")){
    e.target.value=row.disposition;return;
   }
   row.events=[];
   row.entity_decisions.forEach(x=>{x.decision="UNREVIEWED";x.reason="";});
  }
  row.disposition=e.target.value;render();
 };
 const list=byId("entityList");list.replaceChildren();
 element("h3",list,"Karakter / nesne adayları");
 if(!row.entity_decisions.length)element("p",list,"Tarayıcı bu cümle için aday bulamadı. Eksik olanları inceleme notuna yazın.","muted");
 row.entity_decisions.forEach(ent=>{
  const node=element("div",list,null,"entity");
  element("strong",node,ent.ref+" — “"+ent.quote+"”");
  const group=element("div",node,null,"field-grid");
  const col1=element("div",group); const col2=element("div",group);
  element("label",col1,"Varlık kararı");
  const select=element("select",col1);fillOptions(select,ENTITY,ent.decision);
  select.onchange=e=>{ent.decision=e.target.value;refreshNav();};
  element("label",col2,"Kararın gerekçesi");
  const input=element("input",col2);input.value=ent.reason;
  input.placeholder="Metindeki kanıta dayalı gerekçe";
  input.oninput=e=>{ent.reason=e.target.value;refreshNav();};
 });
 byId("rowNotes").value=row.notes;
 byId("rowNotes").oninput=e=>{row.notes=e.target.value;};
 renderEvents(row);
 byId("prev").disabled=current===0;
 byId("next").disabled=current===form.rows.length-1;
 resetEvent();refreshNav();
 message("Bu form yerel tarayıcı belleğinde. Cümlenin doğru yorumlandığı otomatik garanti edilmez.");
}
byId("addEvent").addEventListener("click",()=>{
 const row=form.rows[current],type=byId("eventType").value;
 if(["UNREVIEWED","TEXTURE","NO_TRACKED_CHANGE"].includes(row.disposition)){
  message("Olay eklemeden önce cümle sınıfını STATE_EVENT / KNOWLEDGE_EVENT / CLAIM_ONLY / AMBIGUOUS olarak seçin.",true);return;
 }
 const id=byId("eventId").value.trim(),phrase=byId("eventQuote").value;
 const occ=Number(byId("eventOccurrence").value);
 const evidence=quoteOffsets(row,phrase,occ);
 const reason=byId("eventReason").value.trim();
 const refs=byId("eventRefs").value.split(",").map(x=>x.trim()).filter(Boolean);
 if(!id||!reason||!evidence||new Set(refs).size!==refs.length||
 row.events.some(x=>x.event_id===id)){
  message("Benzersiz olay kimliği, metinde birebir bulunan alıntı, geçerli geçiş numarası ve gerekçe gereklidir.",true);return;
 }
 row.events.push({
  event_id:id,event_type:type,start:evidence.start,end:evidence.end,
  quote:evidence.quote,epistemic:byId("eventEpistemic").value,
  effect:byId("eventEffect").value,entity_refs:refs,reason
 });
 renderEvents(row);refreshNav();resetEvent();
 message("Olay yalnızca tarayıcıdaki formda eklendi. Kanonik onay verilmedi.");
});
byId("clearEvent").onclick=resetEvent;
byId("prev").onclick=()=>{if(current>0){current--;render();}};
byId("next").onclick=()=>{if(current<form.rows.length-1){current++;render();}};
byId("exportBtn").onclick=()=>{
 const raw=JSON.stringify(form,null,2)+"\n";
 const blob=new Blob([raw],{type:"application/json"});
 const url=URL.createObjectURL(blob);
 const anchor=document.createElement("a");anchor.href=url;
 anchor.download="sera-"+form.reviewer_alias+"-NOT_GOLD.json";
 document.body.appendChild(anchor);anchor.click();anchor.remove();
 URL.revokeObjectURL(url);
 message("JSON indirildi. Bu veri insan kimliğini veya GOLD onayını kanıtlamaz.");
};
byId("importBtn").onclick=()=>byId("fileInput").click();
byId("fileInput").onchange=async e=>{
 const file=e.target.files[0];if(!file)return;
 try{
  const imported=JSON.parse(await file.text());
  if(!imported||typeof imported!=="object"||
   ["schema","scene_key","prose_sha256","source_packet_sha256","reviewer_alias"]
   .some(k=>imported[k]!==initialMeta[k])||
   imported.review_source!=="CLAIMED_HUMAN_UNATTESTED"||
   imported.gold_status!=="NOT_GOLD"||
   imported.status!=="IN_PROGRESS"||
   imported.canonical_commit_authorized!==false||
   !Array.isArray(imported.rows)||imported.rows.length!==form.rows.length)
    throw Error("Kaynak/rol/sözleşme uyuşmuyor.");
  for(let i=0;i<form.rows.length;i++){
   const a=form.rows[i],b=imported.rows[i];
   if(!b||b.sentence_id!==a.sentence_id||
     b.start!==a.start||b.end!==a.end||b.quote!==a.quote||
     !Array.isArray(b.entity_decisions)||
     b.entity_decisions.length!==a.entity_decisions.length||
     !Array.isArray(b.events))throw Error("Cümle kimliği veya metni farklı.");
   for(let j=0;j<a.entity_decisions.length;j++){
    const p=a.entity_decisions[j],q=b.entity_decisions[j];
    if(!q||["ref","start","end","quote"].some(k=>p[k]!==q[k]))
      throw Error("Nesne kanıtı değiştirildi.");
   }
  }
  form=imported;current=0;render();
  message("Kaynakla eşleşen taslak yüklendi. Nihai doğrulama Python ile yapılmalıdır.");
 }catch(error){message("JSON alınamadı: "+error.message,true);}
 finally{e.target.value="";}
};
render();
</script>
</body>
</html>
"""


def render_html(*, packet: dict, reviewer_alias: str) -> str:
    form = blank_annotation(packet, reviewer_alias=reviewer_alias)
    validate_annotation(packet=packet, annotation=form)
    cues = {}
    for sentence in packet["sentences"]:
        sid = sentence["sentence_id"]
        cues[sid] = sorted({
            x["family"] + ":" + x["quote"]
            for x in sentence["cue_hints"]
        })
    # Never include prior event_suggestions / suggested_event_ids.
    # Safe inside JSON script tags: literal '<' cannot terminate script text.
    data = json.dumps(form, ensure_ascii=False).replace("<", "\\u003c")
    cue_data = json.dumps(cues, ensure_ascii=False).replace("<", "\\u003c")
    page = (HTML.replace("__TITLE__", TITLE)
            .replace("__FORM_JSON__", data)
            .replace("__CUES_JSON__", cue_data))
    if any(x in page for x in ("ANALYST_CANDIDATE_NOT_ADJUDICATED",
                                '"event_suggestions"', '"suggested_event_ids"')):
        raise RuntimeError("BLIND_UI_ANALYST_CANDIDATE_LEAK")
    return page


def export_mara_browser_forms(directory: Path) -> dict:
    packet = generate_mara_packet()
    prose = json.loads(PATH.read_text(encoding="utf-8"))["prose"]
    validate_review_packet(prose=prose, packet=packet)
    directory.mkdir(parents=True, exist_ok=True)
    filenames = []
    for alias in ("reviewer_A_unverified", "reviewer_B_unverified"):
        page = render_html(packet=packet, reviewer_alias=alias)
        target = directory / (alias + ".html")
        target.write_text(page, encoding="utf-8")
        filenames.append(target.name)
    return {
        "protocol": "sera.review-browser-export.v0.9",
        "source_sha256": packet["prose_sha256"],
        "packet_sha256": packet["packet_sha256"],
        "sentence_count": len(packet["sentences"]),
        "files": filenames,
        "offline_only": True,
        "reviewers_authenticated": False,
        "prior_analyst_labels_exposed": False,
        "gold_qualified": False,
        "llm_calls": 0,
        "canonical_commit_authorized": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(
        export_mara_browser_forms(args.output_dir),
        ensure_ascii=False, indent=2,
    ))
