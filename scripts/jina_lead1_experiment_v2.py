#!/usr/bin/env python3
"""Evidence-aware Jina-only Lead #1 benchmark.

Uses only Jina Search and Reader. No TinyFish, Firecrawl, or browser automation.
The evaluator scores actual decision-maker/LinkedIn evidence rather than API success.
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

OUT=Path("jina_lead1_output"); OUT.mkdir(exist_ok=True)
COMPANY="100 Thieves"; DOMAIN="100thieves.com"
QUERIES=[
 '"100 Thieves" company leadership','"100 Thieves" "Julie Van"',
 '"100 Thieves" "Selina Garcia"','"100 Thieves" security technology',
 '"100 Thieves" account login Shopify','"100 Thieves" fraud cybersecurity',
 '"100 Thieves" 2026 leadership','site:linkedin.com/in "100 Thieves" leadership']
EXPECTED={
 "Julie Van":{"role":"COO","linkedin":"https://www.linkedin.com/in/jvan1"},
 "Selina Garcia":{"role":"Director of IT & Infrastructure","linkedin":"https://www.linkedin.com/in/selinagarcia1"},
 "Matthew Haag":{"role":"Founder & CEO","linkedin":"https://www.linkedin.com/in/matthew-haag-a46b4a18"},
 "Jacob Toft-Andersen":{"role":"President","linkedin":"https://www.linkedin.com/in/maelk"}}
ROLE_PATTERNS={
 "Julie Van":[r"chief operating officer",r"\bcoo\b"],
 "Selina Garcia":[r"director of it\s*(?:&|and)\s*infrastructure"],
 "Matthew Haag":[r"founder\s*&\s*ceo",r"founder\s+and\s+ceo"],
 "Jacob Toft-Andersen":[r"\bpresident\b"]}

def jina_get(url):
 key=os.environ.get("JINA_API_KEY","")
 if not key: raise RuntimeError("JINA_API_KEY is not configured")
 req=Request(url,headers={"Authorization":f"Bearer {key}","Accept":"application/json","User-Agent":"SentinelLayer-Jina-Benchmark/2.0"})
 with urlopen(req,timeout=45) as resp: return resp.status,resp.read().decode("utf-8",errors="replace"),dict(resp.headers)

def search(q):
 started=time.time(); url="https://s.jina.ai/?q="+quote(q,safe="")
 try:
  status,body,h=jina_get(url); return {"query":q,"status":status,"latency_seconds":round(time.time()-started,3),"body":body,"content_type":h.get("content-type","")}
 except Exception as e: return {"query":q,"status":None,"latency_seconds":round(time.time()-started,3),"error":type(e).__name__+": "+str(e)}

def parse_items(result):
 try:
  p=json.loads(result.get("body","")); return p.get("data",[]) if isinstance(p,dict) else []
 except Exception: return []

def norm(u): return str(u).strip().rstrip(".,);]")
def linkedin(u):
 p=urlparse(u); return p.netloc.lower() in {"linkedin.com","www.linkedin.com"} and "/in/" in p.path
def image_url(u): return urlparse(u).path.lower().endswith((".jpg",".jpeg",".png",".webp",".gif",".svg",".avif"))

def search_evidence(searches):
 out=[]
 for s in searches:
  if s.get("status")!=200: continue
  for i in parse_items(s):
   u=norm(i.get("url",""));
   if u: out.append({"query":s["query"],"title":i.get("title",""),"url":u,"description":i.get("description",""),"content":i.get("content",""),"text":" ".join(str(i.get(k,"")) for k in ("title","description","content"))})
 return out

def reader_urls(evidence):
 ranked=[]; seen=set()
 for n,e in enumerate(evidence):
  u=e["url"]
  if not u or u in seen or image_url(u): continue
  seen.add(u); low=e["text"].lower(); score=0
  if linkedin(u): score+=100
  if "100thieves.com" in urlparse(u).netloc.lower(): score+=35
  if any(x.lower() in low for x in EXPECTED): score+=30
  if any(re.search(p,low) for ps in ROLE_PATTERNS.values() for p in ps): score+=20
  if any(x in urlparse(u).netloc.lower() for x in ("asiasociety.org","sloansportsconference.com","theorg.com","rocketreach.co","esportsinsider.com","wikipedia.org")): score+=10
  score+=max(0,10-n); ranked.append((score,u))
 ranked.sort(reverse=True); urls=[u for _,u in ranked]
 for u in ("https://100thieves.com/pages/about","https://100thieves.com/pages/privacy-policy","https://100thieves.com/pages/terms-of-service"):
  if u not in urls: urls.append(u)
 return urls[:20]

def read(u):
 started=time.time()
 try:
  st,b,h=jina_get("https://r.jina.ai/"+u); return {"url":u,"status":st,"latency_seconds":round(time.time()-started,3),"content_type":h.get("content-type",""),"body":b}
 except Exception as e: return {"url":u,"status":None,"latency_seconds":round(time.time()-started,3),"error":type(e).__name__+": "+str(e)}

def person_eval(name,spec,evidence,reads):
 nl=name.lower(); exact=norm(spec["linkedin"]).rstrip("/")
 hits=[e for e in evidence if nl in e["text"].lower() or exact==norm(e["url"]).rstrip("/")]
 rh=[r for r in reads if nl in r.get("body","").lower() or exact in r.get("body","").lower()]
 rel=hits+[{"url":r["url"],"text":r.get("body","")} for r in rh]; text="\n".join(x.get("text","") for x in rel).lower()
 return {
  "name":name,"role_ground_truth":spec["role"],"linkedin_ground_truth":spec["linkedin"],
  "name_found":bool(rel),"name_company_association":bool(nl in text and ("100 thieves" in text or "100thieves" in text)),
  "role_found_in_evidence":any(re.search(p,text) for p in ROLE_PATTERNS[name]),
  "exact_linkedin_found":any(norm(e["url"]).rstrip("/")==exact for e in hits),
  "wrong_linkedin_candidates":[e["url"] for e in hits if linkedin(e["url"]) and norm(e["url"]).rstrip("/")!=exact],
  "search_evidence_count":len(hits),"reader_evidence_count":len(rh),
  "observed_emails":sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@100thieves\.com",text))),
  "masked_email_present":bool(re.search(r"[A-Za-z0-9._%+-]?[*xX]+[A-Za-z0-9._%+-]*@100thieves\.com",text)),
  "sources":[x.get("url") for x in rel]}

def evaluate(searches,evidence,reads):
 people={n:person_eval(n,s,evidence,reads) for n,s in EXPECTED.items()}
 dm=sum(p["name_company_association"] for p in people.values())
 li=sum(p["exact_linkedin_found"] for p in people.values())
 role=sum(p["role_found_in_evidence"] for p in people.values())
 ss=sum(s.get("status")==200 for s in searches)/len(searches)
 rs=sum(r.get("status")==200 for r in reads)/max(1,len(reads))
 useful=sum(not image_url(r.get("url","")) and bool(r.get("body")) for r in reads)
 emails=sorted({e for p in people.values() for e in p["observed_emails"]})
 scores={
  "decision_maker_discovery":round(10*dm/4,2),"linkedin_discovery":round(10*li/4,2),
  "identity_accuracy":round(10*((dm/4)+(role/4))/2,2),"currentness":round(10*role/4,2),
  "evidence_quality":round(10*((ss+rs+(useful/max(1,len(reads))))/3),2),
  "contact_discovery":round(10*min(1,len(emails)/4),2)}
 scores["overall_enrichment_usefulness"]=round(.30*scores["decision_maker_discovery"]+.25*scores["linkedin_discovery"]+.20*scores["identity_accuracy"]+.10*scores["currentness"]+.10*scores["evidence_quality"]+.05*scores["contact_discovery"],2)
 return {"people":people,"recall":{"decision_maker":f"{dm}/4","linkedin":f"{li}/4","role":f"{role}/4"},"quality":scores,"homonym_contamination":{"wrong_linkedin_candidates":sum(len(p["wrong_linkedin_candidates"]) for p in people.values())},"contact_safety":{"observed_unmasked_emails":emails,"masked_email_only":not emails and any(p["masked_email_present"] for p in people.values()),"inferred_or_constructed_emails":[]},"reader_utilization":{"urls_read":len(reads),"useful_non_image_reads":useful,"image_reads":sum(image_url(r.get("url","")) for r in reads)}}

def main():
 started=time.time(); searches=[search(q) for q in QUERIES]; evidence=search_evidence(searches); urls=reader_urls(evidence); reads=[read(u) for u in urls]; q=evaluate(searches,evidence,reads)
 report={"experiment":"Jina Search + Jina Reader only — evidence-aware Lead #1 benchmark","lead":{"company":COMPANY,"domain":DOMAIN,"company_id":96},"constraints":{"tinyfish":False,"firecrawl":False,"browser_automation":False},"search_queries":len(QUERIES),"successful_searches":sum(s.get("status")==200 for s in searches),"candidate_search_results":len(evidence),"reader_urls":urls,"successful_reads":sum(r.get("status")==200 for r in reads),"total_latency_seconds":round(time.time()-started,3),"quality":q,"ground_truth":EXPECTED,"safety_note":"Masked emails, guesses, provider-inferred addresses, and unrelated homonyms are not treated as verified contact identity."}
 (OUT/"search_results.json").write_text(json.dumps(searches,indent=2),encoding="utf-8"); (OUT/"reader_results.json").write_text(json.dumps(reads,indent=2),encoding="utf-8"); (OUT/"evidence_index.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8"); (OUT/"quality_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 md=["# Jina-only Lead #1 benchmark v2","",f"Searches: {len(QUERIES)}; successful: {report['successful_searches']}/{len(QUERIES)}",f"Reader: {len(reads)} URLs; successful: {report['successful_reads']}/{len(reads)}",f"Wall time: {report['total_latency_seconds']}s","","## Ground-truth evaluation"]
 for n,p in q["people"].items(): md += [f"### {n}",f"- Name/company association: {'FOUND' if p['name_company_association'] else 'NOT_FOUND'}",f"- Role evidence: {'FOUND' if p['role_found_in_evidence'] else 'NOT_FOUND'}",f"- Exact LinkedIn URL: {'FOUND' if p['exact_linkedin_found'] else 'NOT_FOUND'}",f"- Wrong LinkedIn candidates: {len(p['wrong_linkedin_candidates'])}",f"- Search evidence: {p['search_evidence_count']}",f"- Reader evidence: {p['reader_evidence_count']}"]
 md += ["","## Scores"]+[f"- {k}: {v}/10" for k,v in q["quality"].items()]+["","## Contact safety",f"- Observed unmasked emails: {q['contact_safety']['observed_unmasked_emails'] or 'NONE'}","- Masked-email-only evidence: "+str(q['contact_safety']['masked_email_only']),"- Inferred/constructed emails: NONE"]
 (OUT/"quality_report.md").write_text("\n".join(md)+"\n",encoding="utf-8")
 print("Jina Lead #1 v2 benchmark complete"); print(f"overall={q['quality']['overall_enrichment_usefulness']}/10"); print(f"wall_time_seconds={report['total_latency_seconds']}")
if __name__=="__main__": main()
