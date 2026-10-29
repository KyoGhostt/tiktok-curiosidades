"""Diagnóstico: mostra campos da API do Buffer (edição de post e métricas)."""
import json
import buffer_post as bp

def t(name):
    q = """query($n:String!){__type(name:$n){name kind fields{name args{name type{name kind ofType{name kind ofType{name kind}}}} type{name kind ofType{name kind}}}
      inputFields{name type{name kind ofType{name kind ofType{name kind}}}}}}"""
    return bp.gql(q, {"n": name})["__type"]

def show(name):
    x = t(name)
    if not x: print(name, "-> não existe"); return
    print("==", name, x["kind"])
    for f in (x.get("fields") or []):
        print("  ", f["name"], [a["name"] for a in f["args"]])
    for f in (x.get("inputFields") or []):
        ty = f["type"]; print("  in:", f["name"], ty.get("name") or (ty.get("ofType") or {}).get("name"))

m = t("Mutation")
print("Mutations:", [f["name"] for f in m["fields"]])
for f in m["fields"]:
    if "ost" in f["name"] and ("dit" in f["name"] or "pdate" in f["name"] or "esched" in f["name"]):
        print(f["name"], [(a["name"], a["type"].get("name") or a["type"]["ofType"]["name"]) for a in f["args"]])
for n in ("Post", "EditPostInput", "UpdatePostInput", "PostMetric", "Metric"):
    show(n)
