"""
NLP -> SPARQL pour la partie BOURSES + INSCRIPTIONS (fichier autonome).
Lit backend/ontology/formation_.ttl. Aucun LLM.
"""
import os, re, unicodedata, difflib
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL, BNode
from rdflib.collection import Collection
from rdflib.plugins.sparql import prepareQuery

TTL_PATH = os.environ.get(
    "ONTO_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ontology", "formation_.ttl"))

ROOTS = ["Bourse", "Inscription"]

SYNONYMS = {
    "etudiant": "Apprenant", "eleve": "Apprenant", "beneficiaire": "Apprenant",
    "aide": "Bourse", "subvention": "Bourse",
    "candidature": "Inscription",
}

EXAMPLES = [
    "Quelles bourses existent ?",
    "Combien d'inscriptions y a-t-il ?",
    "Quels apprenants ont une bourse ?",
    "Quels apprenants n'ont aucune bourse ?",
    "Combien d'inscriptions par apprenant ?",
    "Quelle bourse a le plus de bénéficiaires ?",
    "Existe-t-il un apprenant boursier ?",
    "Quelles bourses ont un montant supérieur à 500 ?",
]

try:
    from nltk.stem.snowball import SnowballStemmer
    _sb = SnowballStemmer("french")
    def stem(w): return _sb.stem(w)
    STEMMER = "NLTK Snowball"
except Exception:
    def stem(w):
        for suf in ("ements", "ement", "ations", "ation", "eaux", "aux", "es", "s", "x"):
            if len(w) > len(suf) + 3 and w.endswith(suf):
                return w[: -len(suf)]
        return w
    STEMMER = "repli simple"

_nlp = None
def _spacy():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("fr_core_news_sm")
        except Exception:
            _nlp = False
    return _nlp

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[’'`]", " ", s)

def toks(s):
    return re.findall(r"[a-z0-9]+", norm(s))

def split_camel(s):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|_", " ", s)

def local(u):
    u = str(u)
    return u.rsplit("#", 1)[-1] if "#" in u else u.rstrip("/").rsplit("/", 1)[-1]

NUM = r"(\d+(?:[.,]\d+)?)"
def _n(x): return float(x.replace(",", "."))


class Engine:
    def __init__(self, path=TTL_PATH):
        self.path, self._mtime, self.g = path, None, None
        self._load()

    def _load(self):
        m = os.path.getmtime(self.path)
        if m == self._mtime:
            return
        self._mtime = m
        g = self.g = Graph()
        g.parse(self.path, format="turtle")
        self.cls = {c for c in g.subjects(RDF.type, OWL.Class) if isinstance(c, URIRef)}
        self.oprops = {p for p in g.subjects(RDF.type, OWL.ObjectProperty) if isinstance(p, URIRef)}
        self.dprops = {p for p in g.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(p, URIRef)}
        self._anc, self._desc = {}, {}
        self.dom = {p: [d for d in g.objects(p, RDFS.domain) if isinstance(d, URIRef)] for p in self.oprops | self.dprops}
        self.rng = {p: [r for r in g.objects(p, RDFS.range) if isinstance(r, URIRef)] for p in self.oprops | self.dprops}
        self.inv = {}
        for a, b in g.subject_objects(OWL.inverseOf):
            if isinstance(a, URIRef) and isinstance(b, URIRef):
                self.inv.setdefault(a, set()).add(b); self.inv.setdefault(b, set()).add(a)
        byname = {local(c): c for c in self.cls}
        self.roots = [byname[r] for r in ROOTS if r in byname]
        self.scope_cls = set()
        for r in self.roots:
            self.scope_cls |= self.desc(r)
        self.scope_inds = {i for c in self.scope_cls for i in g.subjects(RDF.type, c) if isinstance(i, URIRef)}
        used = set()
        for i in self.scope_inds:
            used |= {p for p in g.predicates(i, None) if p in self.oprops | self.dprops}
            used |= {p for p in g.predicates(None, i) if p in self.oprops}
        self.scope_props = {p for p in self.oprops | self.dprops
                            if any(self.compat(x, c) for x in self.dom[p] + self.rng[p] for c in self.roots)} | used
        self.neigh_inds = set(self.scope_inds)
        for i in self.scope_inds:
            for o in g.objects(i, None):
                if isinstance(o, URIRef) and (o, RDF.type, None) in g:
                    self.neigh_inds.add(o)
            for s in g.subjects(None, i):
                if isinstance(s, URIRef) and (s, RDF.type, None) in g:
                    self.neigh_inds.add(s)
        self.ns = ""
        if self.roots:
            u = str(self.roots[0]); self.ns = u[: len(u) - len(local(u))]
        self._build_lexicon(byname)

    def anc(self, c):
        if c not in self._anc:
            self._anc[c] = {x for x in self.g.transitive_objects(c, RDFS.subClassOf) if isinstance(x, URIRef)}
        return self._anc[c]

    def desc(self, c):
        if c not in self._desc:
            self._desc[c] = {x for x in self.g.transitive_subjects(RDFS.subClassOf, c) if isinstance(x, URIRef)}
        return self._desc[c]

    def compat(self, a, b):
        return a == b or b in self.anc(a) or a in self.anc(b)

    def _label_forms(self, u):
        forms = {split_camel(local(u))}
        for l in self.g.objects(u, RDFS.label):
            forms.add(str(l))
        return forms

    def _build_lexicon(self, byname):
        self.lex, self.single = {}, {}
        def add(text, kind, uri, scope):
            t = tuple(stem(w) for w in toks(text))
            if t and (t not in self.lex or scope):
                self.lex[t] = (kind, uri, scope)
        for c in self.cls:
            for f in self._label_forms(c): add(f, "class", c, c in self.scope_cls)
        for p in self.oprops:
            for f in self._label_forms(p): add(f, "oprop", p, p in self.scope_props)
        for p in self.dprops:
            for f in self._label_forms(p): add(f, "dprop", p, p in self.scope_props)
        for i in self.neigh_inds:
            for f in self._label_forms(i): add(f, "ind", i, i in self.scope_inds)
        for syn, name in SYNONYMS.items():
            u = byname.get(name)
            if u:
                add(syn, "class", u, u in self.scope_cls)
        for t in self.lex:
            if len(t) == 1:
                self.single[t[0]] = self.lex[t]
        self.maxn = max((len(t) for t in self.lex), default=1)

    def f(self, u):
        s = str(u)
        if self.ns and s.startswith(self.ns) and re.fullmatch(r"[A-Za-z_][\w\-]*", s[len(self.ns):]):
            return ":" + s[len(self.ns):]
        return f"<{s}>"

    def analyse(self, question):
        self._load()
        trace = []
        text = norm(question)
        doc = _spacy()
        if doc:
            d = doc(question)
            trace.append({"etape": "1. Analyse linguistique (spaCy)",
                          "detail": [f"{t.text}/{t.lemma_}/{t.pos_}" for t in d if not t.is_punct]})
        else:
            trace.append({"etape": "1. Analyse linguistique", "detail": toks(question)})
        cons = []
        def take(rx, fn):
            nonlocal text
            for m in list(re.finditer(rx, text)):
                cons.append(fn(m))
            text = re.sub(rx, " ", text)
        take(r"entre " + NUM + r" et " + NUM, lambda m: ("BETWEEN", _n(m.group(1)), _n(m.group(2))))
        take(r"au moins " + NUM, lambda m: (">=", _n(m.group(1))))
        take(r"au plus " + NUM, lambda m: ("<=", _n(m.group(1))))
        take(r"(?:plus de|superieur\w* a|au dessus de|depasse\w*|>)\s*" + NUM, lambda m: (">", _n(m.group(1))))
        take(r"(?:moins de|inferieur\w* a|en dessous de|<)\s*" + NUM, lambda m: ("<", _n(m.group(1))))
        take(r"(?:egal\w* a|exactement)\s*" + NUM, lambda m: ("=", _n(m.group(1))))
        trace.append({"etape": "2. Contraintes numériques", "detail": [str(c) for c in cons] or ["aucune"]})

        words = toks(text)
        stems = [stem(w) for w in words]
        sup = re.search(r"\b(?:le|la|les)\s+(plus|moins)\b", text)
        low = bool(sup and sup.group(1) == "moins") or bool(re.search(r"\b(petit|bas|faible|minimum)", text))
        agg = None
        for rx, fn in ((r"\bsomme\b|montant total|total des", "SUM"), (r"\bmoyenne\b", "AVG"),
                       (r"\bmaximum\b", "MAX"), (r"\bminimum\b", "MIN")):
            if re.search(rx, text): agg = fn; break
        intent = {
            "count": bool(re.search(r"\bcombien\b|\bnombre\b", text)),
            "ask": bool(re.search(r"\bexiste\b|\by a t il\b|\bexistent? t il", text)),
            "fiche": bool(re.search(r"que sais tu|\bfiche\b|\bdetails?\b|informations? (?:sur|de)|parle moi", text)),
            "sup": bool(sup) or bool(re.search(r"\b(?:eleve|grand|haut|petit|bas|faible)\w*\b", text) and re.search(r"\b(?:le|la) plus|\bmaximum|\bminimum", text)),
            "agg": agg, "low": low,
        }
        trace.append({"etape": "3. Intention", "detail": [k for k, v in intent.items() if v and k != "low"] or ["liste"]})

        ents, i = [], 0
        while i < len(stems):
            hit = None
            for n in range(min(self.maxn, len(stems) - i), 0, -1):
                k = tuple(stems[i:i + n])
                if k in self.lex:
                    hit = (n, self.lex[k]); break
            if not hit and len(words[i]) >= 5:
                m = difflib.get_close_matches(stems[i], list(self.single), n=1, cutoff=0.85)
                if m: hit = (1, self.single[m[0]])
            if hit:
                n, (kind, uri, scope) = hit
                ents.append({"kind": kind, "uri": uri, "scope": scope, "pos": i, "len": n})
                i += n
            else:
                i += 1
        trace.append({"etape": "4. Entités reconnues",
                      "detail": [f"{e['kind']}:{local(e['uri'])}" for e in ents] or ["aucune"]})
        def first_pos(rx):
            for j, w in enumerate(words):
                if re.fullmatch(rx, w): return j
            return None
        neg_pos = first_pos(r"sans|aucune?|n|pas")
        if neg_pos is not None and words[neg_pos] in ("n", "pas") and not re.search(r"\bn (?:a|ont|est|sont|existe)|\bne\b|\bpas\b", text):
            neg_pos = None
        grp_pos = first_pos(r"par|chaque")
        return ents, cons, intent, neg_pos, grp_pos, trace

    def unfold(self, c):
        for eq in self.g.objects(c, OWL.equivalentClass):
            if isinstance(eq, BNode):
                lst = self.g.value(eq, OWL.intersectionOf)
                if lst is None: continue
                base, extra = None, []
                for m in Collection(self.g, lst):
                    if isinstance(m, URIRef): base = m
                    else:
                        p = self.g.value(m, OWL.onProperty); fil = self.g.value(m, OWL.someValuesFrom)
                        if p is not None and fil is not None: extra.append((p, fil))
                if base is not None:
                    return base, extra
        return c, []

    def link_path(self, a, b):
        paths = []
        for p in self.oprops:
            doms, rngs = self.dom[p], self.rng[p]
            if not doms or not rngs: continue
            if any(self.compat(d, a) for d in doms) and any(self.compat(r, b) for r in rngs):
                paths.append(self.f(p)); paths += ["^" + self.f(q) for q in self.inv.get(p, ())]
            if any(self.compat(d, b) for d in doms) and any(self.compat(r, a) for r in rngs):
                paths.append("^" + self.f(p)); paths += [self.f(q) for q in self.inv.get(p, ())]
        return "|".join(dict.fromkeys(paths))

    def build(self, question):
        ents, cons, it, neg_pos, grp_pos, trace = self.analyse(question)
        if not any(e["scope"] for e in ents):
            return None, trace, "Question hors de la partie Bourses / Inscriptions (aucune entité reconnue)."
        cls = [e for e in ents if e["kind"] == "class"]
        dps = [e for e in ents if e["kind"] == "dprop"]
        ops = [e for e in ents if e["kind"] == "oprop"]
        inds = [e for e in ents if e["kind"] == "ind"]

        if it["fiche"] and inds:
            I = inds[0]["uri"]
            q = (f"PREFIX : <{self.ns}>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
                 f"SELECT ?propriete ?valeur WHERE {{\n  {self.f(I)} ?p ?v .\n"
                 f"  BIND(REPLACE(STR(?p), \"^.*[#/]\", \"\") AS ?propriete)\n"
                 f"  BIND(REPLACE(STR(?v), \"^.*[#/]\", \"\") AS ?valeur)\n}} ORDER BY ?propriete")
            trace.append({"etape": "5. Génération SPARQL", "detail": ["fiche d'un individu"]})
            return q, trace, None

        main = None
        if cls:
            main = cls[0]["uri"]
        elif dps or ops:
            p = (dps or ops)[0]["uri"]
            main = next((d for d in self.dom[p]), None)
        elif inds:
            main = next(iter(self.g.objects(inds[0]["uri"], RDF.type)), None)
        if main is None:
            return None, trace, "Je n'ai pas identifié l'objet de la question."

        var_n = [0]
        def nv(prefix):
            var_n[0] += 1; return f"?{prefix}{var_n[0]}"
        P, filt, sel = [], [], ["?x", "?nom"]

        def class_pat(var, c):
            base, extra = self.unfold(c)
            t = nv("t")
            out = [f"{var} a {t} . {t} rdfs:subClassOf* {self.f(base)} ."]
            for p, fil in extra:
                o, t2 = nv("o"), nv("t")
                out.append(f"{var} {self.f(p)} {o} . {o} a {t2} . {t2} rdfs:subClassOf* {self.f(fil)} .")
            return out

        def name_of(var):
            nm = var + "nom"
            P.append(f"OPTIONAL {{ {var} rdfs:label {var}lbl }}")
            P.append(f"BIND(COALESCE(STR({var}lbl), REPLACE(STR({var}), \"^.*[#/]\", \"\")) AS {nm})")
            return nm

        P += class_pat("?x", main)
        P.append("OPTIONAL { ?x rdfs:label ?xlbl }")
        P.append('BIND(COALESCE(STR(?xlbl), REPLACE(STR(?x), "^.*[#/]", "")) AS ?nom)')

        others = [e for e in ents if e not in (cls[:1] if cls else [])
                  and not (e["kind"] == "class" and (e["uri"] == main))]
        refined = []
        for e in others:
            if e["kind"] == "class" and e["uri"] in self.desc(main):
                P.append(f"FILTER EXISTS {{ ?x a/rdfs:subClassOf* {self.f(e['uri'])} }}")
            else:
                refined.append(e)

        gvar = None
        numeric_var = None
        for e in refined:
            negated = neg_pos is not None and e["pos"] > neg_pos and not any(
                x["pos"] > neg_pos and x["pos"] < e["pos"] for x in refined if x is not e and x["kind"] != "dprop")
            blk, var = [], None
            if e["kind"] == "dprop":
                var = nv("d"); blk = [f"?x {self.f(e['uri'])} {var} ."]
                if numeric_var is None: numeric_var = var
                if not negated: sel.append(var)
            elif e["kind"] == "oprop":
                var = nv("o"); p = e["uri"]
                fwd = not self.dom[p] or any(self.compat(d, main) for d in self.dom[p])
                blk = [f"?x {'' if fwd else '^'}{self.f(p)} {var} ."]
            elif e["kind"] == "class":
                var = nv("e"); path = self.link_path(main, e["uri"])
                blk = ([f"?x ({path}) {var} ."] if path else
                       [f"{{ ?x ?pl {var} }} UNION {{ {var} ?pl ?x }}"]) + class_pat(var, e["uri"])
            elif e["kind"] == "ind":
                I = self.f(e["uri"]); pv = nv("pl")
                blk = [f"{{ ?x {pv} {I} }} UNION {{ {I} {pv} ?x }}"]
            e["var"] = var
            if negated:
                P.append("FILTER NOT EXISTS { " + " ".join(blk) + " }")
                continue
            P += blk
            if e["kind"] in ("oprop", "class") and var:
                nm = name_of(var)
                if not (it["count"] or it["agg"] or it["sup"]): sel.append(nm)
                e["nom"] = nm
            if grp_pos is not None and e["pos"] > grp_pos and gvar is None and e["kind"] != "ind":
                gvar = e.get("nom") or var

        if cons:
            if numeric_var is None:
                dp = next((p for p in self.dprops if (any(self.compat(d, main) for d in self.dom[p]) or p in self.scope_props)
                           and any(isinstance(v, Literal) and isinstance(v.toPython(), (int, float)) or
                                   (isinstance(v, Literal) and str(v.datatype).endswith(("decimal", "double", "float")))
                                   for v in self.g.objects(None, p))), None)
                if dp is None:
                    return None, trace, "Contrainte numérique sans propriété numérique reconnue."
                numeric_var = nv("d"); P.append(f"?x {self.f(dp)} {numeric_var} .")
                sel.append(numeric_var)
            for c in cons:
                if c[0] == "BETWEEN": filt.append(f"FILTER({numeric_var} >= {c[1]:g} && {numeric_var} <= {c[2]:g})")
                else: filt.append(f"FILTER({numeric_var} {c[0]} {c[1]:g})")

        body = "\n  ".join(P + filt)
        head = f"PREFIX : <{self.ns}>\nPREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
        target = next((e for e in refined if e.get("nom") and e["kind"] != "dprop"), None)
        dp_first = next((e for e in refined if e["kind"] == "dprop"), None)

        if it["ask"]:
            q = head + f"ASK {{\n  {body}\n}}"; kind = "ASK"
        elif it["sup"] and target is None and (dp_first or numeric_var):
            v = (dp_first or {}).get("var") or numeric_var
            if v not in sel: sel.append(v)
            q = head + f"SELECT DISTINCT {' '.join(sel)} WHERE {{\n  {body}\n}}\nORDER BY {'ASC' if it['low'] else 'DESC'}({v}) LIMIT 1"
            kind = "superlatif (valeur)"
        elif it["sup"] and target is not None:
            q = (head + f"SELECT ?x ?nom (COUNT(DISTINCT {target['var']}) AS ?total) WHERE {{\n  {body}\n}}\n"
                 f"GROUP BY ?x ?nom ORDER BY {'ASC' if it['low'] else 'DESC'}(?total) LIMIT 1")
            kind = "superlatif (comptage)"
        elif it["agg"] and (dp_first or numeric_var):
            v = (dp_first or {}).get("var") or numeric_var
            if gvar:
                q = head + f"SELECT {gvar} ({it['agg']}({v}) AS ?resultat) WHERE {{\n  {body}\n}}\nGROUP BY {gvar}"
            else:
                q = head + f"SELECT ({it['agg']}({v}) AS ?resultat) WHERE {{\n  {body}\n}}"
            kind = it["agg"]
        elif it["count"] or gvar:
            if gvar:
                q = head + f"SELECT {gvar} (COUNT(DISTINCT ?x) AS ?total) WHERE {{\n  {body}\n}}\nGROUP BY {gvar} ORDER BY DESC(?total)"
            else:
                q = head + f"SELECT (COUNT(DISTINCT ?x) AS ?total) WHERE {{\n  {body}\n}}"
            kind = "COUNT"
        else:
            q = head + f"SELECT DISTINCT {' '.join(dict.fromkeys(sel))} WHERE {{\n  {body}\n}}\nORDER BY ?nom LIMIT 200"
            kind = "liste"
        trace.append({"etape": "5. Génération SPARQL guidée par le schéma", "detail": [kind]})
        return q, trace, None

    def ask(self, question):
        q, trace, err = self.build(question)
        if err:
            return {"ok": False, "error": err, "trace": trace, "examples": EXAMPLES}
        try:
            pq = prepareQuery(q, initNs={"rdfs": RDFS, "owl": OWL})
            if pq.algebra.name not in ("SelectQuery", "AskQuery"):
                return {"ok": False, "error": "Seules les requêtes SELECT/ASK sont autorisées.", "sparql": q, "trace": trace}
            res = self.g.query(pq)
        except Exception as ex:
            return {"ok": False, "error": f"Requête générée invalide : {ex}", "sparql": q, "trace": trace}
        trace.append({"etape": "6. Validation + exécution (rdflib)", "detail": ["OK"]})
        if res.type == "ASK":
            return {"ok": True, "sparql": q, "trace": trace, "type": "ask", "answer": bool(res.askAnswer),
                    "columns": [], "rows": []}
        cols = [str(v) for v in res.vars]
        rows = []
        for r in res:
            rows.append([("" if v is None else (str(v.toPython()) if isinstance(v, Literal) else local(v))) for v in r])
        return {"ok": True, "sparql": q, "trace": trace, "type": "select", "columns": cols, "rows": rows[:200]}


_engine = None
def get_engine():
    global _engine
    if _engine is None:
        _engine = Engine()
    return _engine