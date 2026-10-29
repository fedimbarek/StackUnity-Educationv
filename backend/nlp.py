"""Traducteur intelligent  question en français  ->  requête SPARQL  (NLP/TALN, sans API de LLM).

Pipeline (chaque étape est restituée dans la « trace » renvoyée au front) :
  1. Analyse linguistique : tokenisation + lemmatisation + POS avec spaCy (fr_core_news_sm) ;
     racinisation (stemming) avec NLTK SnowballStemmer('french'). Si l'un des deux est absent, un repli
     léger est utilisé, de sorte que le module reste exécutable (la trace indique les outils réellement actifs).
  2. Lexique construit à partir de l'ontologie : labels + noms camelCase des classes, propriétés et individus,
     plus quelques synonymes métier (étudiant -> Apprenant, prof -> Enseignant, ...).
  3. Liaison d'entités (entity linking) : plus long n-gramme de racines trouvé dans le lexique,
     avec tolérance aux fautes (similarité difflib >= 0.86).
  4. Détection d'intention par règles linguistiques : COUNT (combien), ASK (existe / y a-t-il), DESCRIBE (que sais-tu sur...),
     SUPERLATIF (le plus / le moins / maximum), regroupement (par / chaque), négation (sans / aucun / non).
  5. Extraction des contraintes : comparateurs + nombres (plus de 20, supérieur à 3, entre 2 et 5), booléens (gratuit, rémunéré).
  6. Génération SPARQL guidée par le schéma : domaines / portées des propriétés et hiérarchie des classes
     pour trouver le chemin entre les entités citées ; classes définies (equivalentClass) dépliées.
  7. Validation (rdflib.prepareQuery) puis exécution : faite par ai.py via store.run_readonly.
"""
import re, difflib, unicodedata

# ----------------------------------------------------------------------------- outils NLP (optionnels)
try:
    import spacy
    _NLP = spacy.load("fr_core_news_sm", disable=["ner", "parser"])
except Exception:                                   # spaCy ou modèle absent
    _NLP = None
try:
    from nltk.stem.snowball import FrenchStemmer
    _SNOWBALL = FrenchStemmer().stem
except Exception:                                   # NLTK absent
    _SNOWBALL = None


def tools():
    return {"spacy": "fr_core_news_sm (tokenisation, lemmatisation, POS)" if _NLP else None,
            "nltk": "SnowballStemmer('french')" if _SNOWBALL else None,
            "difflib": "similarité de chaînes (tolérance aux fautes)"}


def unaccent(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def camel_split(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)

def light_stem(w):
    """Repli quand NLTK est absent : retire pluriel et terminaisons verbales courantes (appliqué des deux côtés)."""
    if len(w) > 3 and w[-1] in "sx":
        w = w[:-1]
    if len(w) > 6 and w.endswith("ent"):
        w = w[:-3]
    elif len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w

def stem(w):
    return _SNOWBALL(w) if _SNOWBALL else light_stem(w)

STOP = set("""le la les l un une des du de d au aux en et ou a est sont etre ce cet cette ces c que qu qui quoi quel quels quelle quelles
dans pour sur avec y il elle ils elles me m moi te t tu toi se s son sa ses leur leurs nous vous ont ai as avez avons avoir sais sait
donne donner liste lister affiche afficher montre montrer trouve trouver cherche chercher peux peut dis svp stp il y ya tous toutes tout
toute chaque voir veux voudrais souhaite saurais quelles est ce qu on mon ma mes ton ta tes notre nos votre vos plus moins par sans non
pas ni aucun aucune combien existe existent entre egal egale exactement superieur superieure inferieur inferieure depasse depassent
au apres avant comme ainsi alors donc mais car ou ni plusieurs""".split())

NUM_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)?|[^\W\d_]+", re.UNICODE)


def analyse(text):
    """Texte -> liste de tokens {text, norm, lemma, pos, key, skey, stop, num}.
    key = racine du lemme, skey = racine de la forme de surface (second essai lors de la liaison)."""
    text = text.replace("’", "'")
    raw = []
    if _NLP:
        for t in _NLP(text):
            if t.is_punct or t.is_space:
                continue
            parts = TOKEN_RE.findall(t.text)
            for p in parts:
                raw.append((p, (t.lemma_ or p) if len(parts) == 1 else p, t.pos_))
    else:
        raw = [(w, w, "") for w in TOKEN_RE.findall(text)]
    out = []
    for w, lemma, pos in raw:
        norm, ln = unaccent(w.lower()), unaccent(lemma.lower())
        if not TOKEN_RE.fullmatch(ln):
            ln = norm
        num = bool(NUM_RE.match(norm))
        out.append(dict(text=w, norm=norm, lemma=ln, pos=pos, key=stem(ln), skey=stem(norm),
                        stop=(norm in STOP or (len(norm) == 1 and not num)), num=num,
                        value=float(norm.replace(",", ".")) if num else None))
    return out


# ----------------------------------------------------------------------------- schéma
class Schema:
    """Vue minimale de l'ontologie (classes, propriétés, individus) — indépendante de rdflib pour être testable."""
    def __init__(self, classes, props, individuals, defined=None, inverse=None):
        self.classes, self.props, self.inds = classes, props, individuals
        self.inverse = inverse or {}      # propriété -> propriété inverse (owl:inverseOf, dans les deux sens)
        self.defined = defined or {}      # classe définie -> (parent, propriété, classe_cible)
        self._anc = {}

    @classmethod
    def from_ontology(cls):
        from store import sparql, props as store_props
        classes = {}
        for r in sparql("""SELECT ?c ?l ?p WHERE { ?c a owl:Class . FILTER(isIRI(?c)) OPTIONAL { ?c rdfs:label ?l }
                           OPTIONAL { ?c rdfs:subClassOf ?p . FILTER(isIRI(?p)) } }"""):
            if r["c"].startswith("http"):
                continue
            d = classes.setdefault(r["c"], dict(label=r.get("l", ""), parents=[]))
            if r.get("p") and not r["p"].startswith("http"):
                d["parents"].append(r["p"])
        props = {n: dict(kind=m["kind"], label=m["label"], domain=m["domain"], range=m["range"]) for n, m in store_props().items()}
        inds = {}
        for r in sparql("SELECT ?i ?l ?t WHERE { ?i a owl:NamedIndividual , ?t . OPTIONAL { ?i rdfs:label ?l } FILTER(?t != owl:NamedIndividual && isIRI(?t)) }"):
            if r["t"].startswith("http"):
                continue
            d = inds.setdefault(r["i"], dict(label=r.get("l", r["i"]), types=[]))
            d["types"].append(r["t"])
        defined = {}
        for r in sparql("""SELECT ?c ?prop ?f WHERE { ?c owl:equivalentClass ?e . ?e owl:intersectionOf/rdf:rest*/rdf:first ?r .
                           ?r owl:onProperty ?prop ; owl:someValuesFrom ?f }"""):
            parent = (classes.get(r["c"], {}).get("parents") or [None])[0]
            if parent:
                defined[r["c"]] = (parent, r["prop"], r["f"])
        inverse = {}
        for r in sparql("SELECT ?a ?b WHERE { ?a owl:inverseOf ?b }"):
            if not r["a"].startswith("http") and not r["b"].startswith("http"):
                inverse[r["a"]], inverse[r["b"]] = r["b"], r["a"]
        return cls(classes, props, inds, defined, inverse)

    def ancestors(self, c):
        if c not in self._anc:
            seen, todo = set(), [c]
            while todo:
                x = todo.pop()
                if x not in seen:
                    seen.add(x)
                    todo += self.classes.get(x, {}).get("parents", [])
            self._anc[c] = seen
        return self._anc[c]

    def sub(self, a, b):                       # a est (sous-)classe de b
        return b in self.ancestors(a)

    def fit(self, a, b):                       # 2 = identiques, 1 = a plus précis que b, 0 = b plus précis que a, -1 = incompatibles
        if a == b: return 2
        if self.sub(a, b): return 1
        if self.sub(b, a): return 0
        return -1

    def link(self, a, b, prefer=()):
        """Meilleure propriété objet reliant la classe a à la classe b -> (propriété, 'fwd'|'rev') ou None."""
        best = None
        for n, p in self.props.items():
            if p["kind"] != "object" or not p["domain"] or not p["range"]:
                continue
            for d, (x, y) in (("fwd", (a, b)), ("rev", (b, a))):
                f1, f2 = self.fit(x, p["domain"]), self.fit(y, p["range"])
                if f1 < 0 or f2 < 0:
                    continue
                score = f1 + f2 + (3 if n in prefer else 0)
                if best is None or score > best[0]:
                    best = (score, n, d)
        return (best[1], best[2]) if best else None


SYNONYMS = {"etudiant": "Apprenant", "eleve": "Apprenant", "apprenti": "Apprenant", "prof": "Enseignant", "professeur": "Enseignant",
            "cours": "Matiere", "module": "Matiere", "filiere": "Formation", "cursus": "Formation", "parcours": "Formation",
            "societe": "Entreprise", "employeur": "Entreprise", "faculte": "Departement", "doyen": "Enseignant",
            "medecin": "Medecin", "psy": "Psychologue", "association": "Club", "bourse": "Bourse"}


class Lexicon:
    def __init__(self, schema):
        self.e, self.by_size, self.partial_keys = {}, {}, set()
        S = schema
        for n, c in S.classes.items():
            self._add(c["label"], "class", n); self._add(camel_split(n), "class", n)
        for n, p in S.props.items():
            k = "object" if p["kind"] == "object" else "data"
            self._add(p["label"], k, n); self._add(camel_split(n), k, n)
        for n, i in S.inds.items():
            self._add(i["label"], "individual", n); self._add(camel_split(n), "individual", n)
        for syn, target in SYNONYMS.items():
            if target in S.classes:
                self._add(syn, "class", target)
        for n, i in S.inds.items():              # prénom / nom seuls (si non ambigus avec le reste du lexique)
            toks = [t for t in analyse(i["label"]) if not t["stop"] and not t["num"]]
            if len(toks) >= 2:
                for t in toks:
                    if len(t["norm"]) >= 4 and (t["key"],) not in self.e:
                        self.e.setdefault((t["key"],), set()).add(("individual", n))
                        self.partial_keys.add((t["key"],))
        for k in self.e:
            if k not in self.partial_keys:
                self.by_size.setdefault(len(k), {})[" ".join(k)] = k
        # index partiel : racine -> propriétés de données qui la contiennent (pour « plus de 20 membres »)
        self.partial = {}
        for n, p in S.props.items():
            if p["kind"] == "data":
                for t in analyse(p["label"]) + analyse(camel_split(n)):
                    if not t["stop"] and not t["num"]:
                        self.partial.setdefault(t["key"], set()).add(n)

    def _add(self, text, kind, name):
        if not text:
            return
        toks = [t for t in analyse(text) if not t["stop"] and not t["num"]]
        if toks:
            for key in {tuple(t["key"] for t in toks), tuple(t["skey"] for t in toks)}:
                self.e.setdefault(key, set()).add((kind, name))

    def link(self, content):
        """content : [(index, token)] sans mots vides -> mentions triées par position."""
        n, used, found = len(content), [False] * len(content), []
        for size in range(min(5, n), 0, -1):
            for s in range(n - size + 1):
                if any(used[s:s + size]):
                    continue
                seg = content[s:s + size]
                key, skey = tuple(t["key"] for _, t in seg), tuple(t["skey"] for _, t in seg)
                hits, fuzzy = self.e.get(key) or self.e.get(skey), False
                joined = " ".join(key)
                if not hits and len(joined) >= 6:
                    close = difflib.get_close_matches(joined, list(self.by_size.get(size, {})), n=1, cutoff=0.88)
                    if close and close[0][:1] == joined[:1]:
                        hits, fuzzy = self.e[self.by_size[size][close[0]]], True
                if not hits:
                    continue
                order = {"class": 0, "object": 1, "data": 2, "individual": 3}
                alts = sorted(hits, key=lambda h: (order[h[0]], h[1]))
                for j in range(s, s + size):
                    used[j] = True
                found.append(dict(kind=alts[0][0], name=alts[0][1], start=seg[0][0], end=seg[-1][0], fuzzy=fuzzy,
                                  text=" ".join(t["text"] for _, t in seg), alts=[f"{k}:{x}" for k, x in alts[1:4]]))
        return sorted(found, key=lambda m: m["start"])


# ----------------------------------------------------------------------------- traduction
GT, GE, LT, LE, EQ = ">", ">=", "<", "<=", "="


class NL2SPARQL:
    def __init__(self, schema):
        self.S, self.lex = schema, Lexicon(schema)

    # ---------------------------------------------------------------- intentions
    def intents(self, toks, mentions):
        words = [t["norm"] for t in toks]
        text = " ".join(words)
        covered = {i for m in mentions for i in range(m["start"], m["end"] + 1)}
        it = dict(ask=bool(re.search(r"\b(existe|existent|y a t il|y a il|est ce qu|y en a t il)\b", text)),
                  count="combien" in words or any(w == "nombre" and i not in covered for i, w in enumerate(words)),
                  describe=bool(re.search(r"\b(sais tu|informations?|infos?|fiche|dossier|details?|profil|decris|decrire|parle moi|qui est)\b", text)),
                  most=bool(re.search(r"\b(le|la|les) plus (eleve|elevee|elevees|eleves|grand|grande|haut|haute|important|importante|cher|chere|long|longue|fort|forte)\b|\bmaximum\b|\bmaximal|\bmeilleur", text)),
                  least=bool(re.search(r"\b(le|la|les) moins (eleve|elevee|cher|chere|long|longue|fort|forte)\b|\bminimum\b|\bminimal|\bplus (petit|petite|faible|bas|basse|court|courte)\b", text)),
                  most_count=bool(re.search(r"\b(le|la) plus de\b|\bplus grand nombre\b", text)),
                  least_count=bool(re.search(r"\b(le|la) moins de\b|\bplus petit nombre\b", text)),
                  group_at=next((i for i, w in enumerate(words) if w in ("par", "chaque")), None))
        return it

    def numbers(self, toks):
        """[(op, valeur, index_du_nombre)] — comparateurs lus dans les 4 mots précédant le nombre."""
        out, norm = [], [t["norm"] for t in toks]
        for i, t in enumerate(toks):
            if not t["num"]:
                continue
            w = norm[max(0, i - 4):i]
            if "entre" in w:
                nxt = [j for j in range(i + 1, min(len(toks), i + 4)) if toks[j]["num"]]
                if nxt:
                    out += [(GE, t["value"], i), (LE, toks[nxt[0]]["value"], i)]
                continue
            if i >= 2 and norm[i - 1] == "et" and "entre" in norm[max(0, i - 4):i - 1]:
                continue                                   # 2e borne déjà traitée
            if "au" in w and "moins" in w: op = GE
            elif "au" in w and "plus" in w: op = LE
            elif any(x in w for x in ("superieur", "superieure", "depasse", "depassent", "plus", "apres")): op = GT
            elif any(x in w for x in ("inferieur", "inferieure", "moins", "avant")): op = LT
            elif any(x in w for x in ("egal", "egale", "exactement")): op = EQ
            else: op = None
            out.append((op, t["value"], i))
        return out

    # ---------------------------------------------------------------- planification
    def translate(self, question):
        S = self.S
        toks = analyse(question)
        content = [(i, t) for i, t in enumerate(toks) if not t["stop"] and not t["num"]]
        mentions = self.lex.link(content)
        it = self.intents(toks, mentions)
        nums = self.numbers(toks)
        notes = []
        trace = dict(tools=tools(), tokens=[dict(text=t["text"], lemma=t["lemma"], pos=t["pos"], stem=t["key"]) for t in toks],
                     entities=[dict(text=m["text"], kind=m["kind"], name=m["name"], fuzzy=m["fuzzy"]) for m in mentions],
                     intent=[k for k in ("ask", "count", "describe", "most", "least", "most_count", "least_count") if it[k]]
                            + (["group_by"] if it["group_at"] is not None and it["count"] else []),
                     constraints=[f"{op or '?'} {v:g}" for op, v, _ in nums], notes=notes)

        cls = [m for m in mentions if m["kind"] == "class"]
        objs = [m for m in mentions if m["kind"] == "object"]
        datas = [m for m in mentions if m["kind"] == "data"]
        inds = [m for m in mentions if m["kind"] == "individual"]
        near_num = {m["start"] for m in mentions if m["kind"] in ("object", "data") and any(abs(m["start"] - i) <= 2 for _, _, i in nums)}

        # ---- fiche d'un individu
        if inds and (it["describe"] or not (cls or objs or datas)):
            i = inds[0]["name"]
            q = (f"SELECT ?propriete ?valeur WHERE {{\n  :{i} ?p ?v .\n  FILTER(?p != rdf:type || ?v != owl:NamedIndividual)\n"
                 f"  BIND(STRAFTER(STR(?p), \"#\") AS ?propriete)\n  BIND(COALESCE(STRAFTER(STR(?v), \"#\"), STR(?v)) AS ?valeur)\n}} ORDER BY ?propriete")
            return dict(sparql=q, kind="describe", subject=S.inds[i]["label"], trace=trace)

        # ---- cible du regroupement (mention suivant « par » / « chaque »)
        group = next((m for m in mentions if it["group_at"] is not None and m["start"] > it["group_at"]), None)

        # ---- classe principale
        main = None
        pool = [m for m in cls if m is not group] or []
        if pool:
            main = pool[0]["name"]
            for o in pool[1:]:                       # « apprenants boursiers » : la sous-classe la plus précise gagne
                if o["name"] != main and S.sub(o["name"], main):
                    main = o["name"]
        elif group and group["kind"] == "class" and objs:
            p = S.props[objs[0]["name"]]
            main = p["domain"] if S.fit(group["name"], p["range"] or "") >= 0 else p["range"]
        elif group and group["kind"] == "class" and len(cls) > 1:
            main = cls[1]["name"]
        elif cls:
            main = cls[0]["name"]
        elif objs and S.props[objs[0]["name"]]["domain"]:
            main = S.props[objs[0]["name"]]["domain"]
        elif datas and S.props[datas[0]["name"]]["domain"]:
            main = S.props[datas[0]["name"]]["domain"]
        elif inds:
            main = S.inds[inds[0]["name"]]["types"][0]
        if not main:
            return dict(sparql=None, trace=trace)

        where, filters, cols, used_props = [], [], [], set()
        n = [0]
        def v(base="v"):
            n[0] += 1
            return f"?{base}{n[0]}"
        def lbl(var, cname):                 # variable d'affichage nommée d'après la classe
            name = re.sub(r"\W", "", unaccent(cname.lower()))
            alias = f"?{name}" if f"?{name}" not in cols else v(name)
            where.append(f"{var} rdfs:label {alias} .")
            return alias
        def edge(sub, p, obj):               # arc tenant compte de owl:inverseOf (pas de raisonneur dans rdflib)
            inv = S.inverse.get(p)
            return f"{sub} (:{p}|^:{inv}) {obj} ." if inv else f"{sub} :{p} {obj} ."
        def typ(var, cname):
            return f"{var} a/rdfs:subClassOf* :{cname} ."

        main_actual = main
        if main in S.defined:               # classe définie : on déplie « parent + restriction »
            main_actual, dprop, dfill = S.defined[main]
            trace["notes"].append(f"{main} est une classe définie : {main_actual} qui a au moins un(e) {dfill} via {dprop}")
        where.append(typ("?x", main_actual))
        if main in S.defined:
            d = v("d")
            where.append(f"?x :{dprop} {d} . {typ(d, dfill)}")
        main_lbl = lbl("?x", main)
        cols.append(main_lbl)
        # nombre -> mention concernée
        neg_words = {"sans", "aucun", "aucune", "non", "pas", "ni"}
        def negated(m):
            return any(toks[j]["norm"] in neg_words for j in range(max(0, m["start"] - 2), m["start"]))

        # ---- autres classes citées : jointure par le schéma
        linked, lbl_of = {}, {}              # classe -> variable ; classe -> variable d'affichage
        for m in cls:
            c = m["name"]
            if c == main or S.fit(c, main) >= 0 or S.fit(main, c) >= 0:
                continue
            lk = S.link(main_actual, c, prefer={o["name"] for o in objs})
            if not lk:
                notes.append(f"Aucune propriété ne relie {main} à {c}")
                continue
            p, d = lk; used_props.add(p)
            k = v("k")
            arc = edge("?x", p, k) if d == "fwd" else edge(k, p, "?x")
            if negated(m):
                filters.append(f"FILTER NOT EXISTS {{ {arc} {typ(k, c)} }}")
            else:
                where.append(f"{arc} {typ(k, c)}")
                linked[c] = k
                if not it["count"] or group is m:
                    lbl_of[c] = lbl(k, c)
                    if not it["count"]:
                        cols.append(lbl_of[c])

        # ---- individus cités : contraintes
        for m in inds:
            i, types = m["name"], S.inds[m["name"]]["types"]
            best = None
            for t in types:
                lk = S.link(main_actual, t, prefer={o["name"] for o in objs})
                if lk:
                    best = lk; break
            if best:
                p, d = best; used_props.add(p)
                where.append(edge("?x", p, f":{i}") if d == "fwd" else edge(f":{i}", p, "?x"))
            else:
                where.append(f"?x ?lien :{i} .")
                notes.append(f"Lien entre {main} et {i} inconnu : recherche générique")

        # ---- propriétés objet citées isolément (colonne supplémentaire)
        for m in objs:
            p = m["name"]
            if p in used_props or used_props or m["start"] in near_num or it["most_count"] or it["least_count"]:
                continue
            meta = S.props[p]
            if meta["domain"] and S.fit(main_actual, meta["domain"]) >= 0 and not (group and m["start"] == group["start"]):
                k = v("o")
                if negated(m):
                    filters.append(f"FILTER NOT EXISTS {{ {edge('?x', p, '?any')} }}")
                else:
                    where.append(edge("?x", p, k))
                    if not it["count"]:
                        where.append(f"OPTIONAL {{ {k} rdfs:label {k}l }}")
                        cols.append(f"(COALESCE({k}l, STRAFTER(STR({k}), '#')) AS ?{p})")
                used_props.add(p)

        # ---- propriétés de données : colonnes, booléens, comparateurs, superlatifs
        def owner(prop):
            dom = S.props[prop]["domain"]
            if not dom or S.fit(main_actual, dom) >= 0:
                return "?x"
            for c, var in linked.items():
                if S.fit(c, dom) >= 0:
                    return var
            return None
        num_targets = []
        for op, val, idx in nums:
            target = next((m for m in datas if abs(m["start"] - idx) <= 4), None)
            prop = target["name"] if target else None
            if not prop:                      # « plus de 20 membres » : racine d'un mot voisin présente dans un label de propriété
                for j in (idx + 1, idx + 2, idx - 1, idx - 2, idx - 3):
                    if 0 <= j < len(toks) and not toks[j]["num"]:
                        cands = [c for c in self.lex.partial.get(toks[j]["key"], ()) if owner(c)]
                        if cands:
                            prop = sorted(cands)[0]; break
            if not prop:
                numeric = [c for c, pm in S.props.items() if pm["kind"] == "data" and pm["range"] in ("integer", "int", "decimal", "float", "double", "nonNegativeInteger")
                           and pm["domain"] and S.fit(main_actual, pm["domain"]) >= 0]
                if len(numeric) == 1:
                    prop = numeric[0]
            if not prop:
                notes.append(f"Nombre {val:g} ignoré : propriété visée non identifiée")
                continue
            num_targets.append((prop, op or EQ, val))

        order = None
        done = set()
        by_prop = {}
        for prop, op, val in num_targets:
            by_prop.setdefault(prop, []).append((op, val))
        for prop, conds in by_prop.items():
            o = owner(prop)
            if o:
                x = v("n")
                where.append(f"{o} :{prop} {x} .")
                filters += [f"FILTER({x} {op} {val:g})" for op, val in conds]
                done.add(prop)
                if not it["count"]:
                    cols.append(f"({x} AS ?{prop})")
        for m in datas:
            p = m["name"]
            if p in done or m["start"] in near_num:
                continue
            o = owner(p)
            if not o:
                notes.append(f"{p} ne s'applique pas à {main}")
                continue
            meta = S.props[p]; x = v("d")
            if meta["range"] == "boolean":
                neg = negated(m)
                where.append(f"{o} :{p} {x} ."); filters.append(f"FILTER({x} = {'false' if neg else 'true'})")
            else:
                where.append(f"{o} :{p} {x} .")
                if (it["most"] or it["least"]) and not it["count"] and order is None:
                    order = (f"{'DESC' if it['most'] else 'ASC'}({x})", 1)
                if not it["count"]:
                    cols.append(f"({x} AS ?{p})")
            done.add(p)

        # ---- ranking par nombre de relations (« le club qui a le plus de membres »)
        rank = None
        if (it["most_count"] or it["least_count"]) and not it["count"]:
            tgt = next((m for m in objs if m["start"] not in near_num), None)
            if tgt:
                p = tgt["name"]; meta = S.props[p]
                m_var = v("m")
                if meta["range"] and S.fit(main_actual, meta["range"]) >= 0:
                    where.append(edge(m_var, p, "?x"))
                else:
                    where.append(edge("?x", p, m_var))
                rank = (m_var, "DESC" if it["most_count"] else "ASC")

        # ---- composition
        body = "\n  ".join(where + filters)
        if it["ask"]:
            return dict(sparql=f"ASK {{\n  {body}\n}}", kind="ask", main=main, trace=trace)
        if rank:
            sel = f"SELECT {main_lbl} (COUNT(DISTINCT {rank[0]}) AS ?nombre)"
            q = f"{sel} WHERE {{\n  {body}\n}} GROUP BY ?x {main_lbl} ORDER BY {rank[1]}(?nombre) LIMIT 1"
            return dict(sparql=q, kind="rank", main=main, trace=trace)
        if it["count"]:
            g = None
            if group:
                if group["kind"] == "class" and group["name"] in lbl_of:
                    g = lbl_of[group["name"]]
                elif group["kind"] == "class" and S.fit(group["name"], main_actual) >= 0:
                    g = main_lbl
                elif group["kind"] == "data" and owner(group["name"]):
                    x = v("g"); where.append(f"{owner(group['name'])} :{group['name']} {x} ."); g = x
                else:
                    notes.append("Cible du regroupement non identifiée")
            body = "\n  ".join(where + filters)
            if g:
                q = f"SELECT {g} (COUNT(DISTINCT ?x) AS ?nombre) WHERE {{\n  {body}\n}} GROUP BY {g} ORDER BY DESC(?nombre) {g}"
            else:
                q = f"SELECT (COUNT(DISTINCT ?x) AS ?nombre) WHERE {{\n  {body}\n}}"
            return dict(sparql=q, kind="count", main=main, trace=trace)
        order_clause = f"ORDER BY {order[0]}" if order else f"ORDER BY {main_lbl}"
        limit = order[1] if order else 200
        q = f"SELECT DISTINCT {' '.join(cols)} WHERE {{\n  {body}\n}} {order_clause} LIMIT {limit}"
        return dict(sparql=q, kind="select", main=main, trace=trace)
