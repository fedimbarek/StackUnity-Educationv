"""Construit un nlp.Schema en lisant le .ttl avec des regex (permet de tester sans rdflib)."""
import re, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nlp import Schema

def load(path=None):
    path = path or os.path.join(os.path.dirname(__file__), "..", "ontology", "formation_.ttl")
    t = open(path, encoding="utf-8").read().replace("\r", "")
    classes, props, inds = {}, {}, {}
    for b in re.split(r"\n\n+", t):
        b = re.sub(r"^(###.*\n)+", "", b.strip())
        m = re.match(r":(\w+) rdf:type owl:Class", b)
        if m:
            parents = re.findall(r"rdfs:subClassOf\s+((?::\w+(?:\s*,\s*(?=:))?\s*)+)", b)
            ps = re.findall(r":(\w+)", parents[0]) if parents else []
            lab = re.search(r'rdfs:label "([^"]*)"', b)
            classes[m.group(1)] = dict(label=lab.group(1) if lab else "", parents=ps)
            continue
        m = re.match(r":(\w+) rdf:type owl:(Object|Datatype)Property", b)
        if m:
            d, r = re.search(r"rdfs:domain :(\w+)", b), re.search(r"rdfs:range (?:xsd:|:)(\w+)", b)
            lab = re.search(r'rdfs:label "([^"]*)"', b)
            props[m.group(1)] = dict(kind="object" if m.group(2) == "Object" else "data", label=lab.group(1) if lab else "",
                                     domain=d.group(1) if d else None, range=r.group(1) if r else None)
            continue
        m = re.match(r":(\w+) rdf:type owl:NamedIndividual\s*,\s*:(\w+)", b)
        if m:
            lab = re.search(r'rdfs:label "([^"]*)"', b)
            inds[m.group(1)] = dict(label=lab.group(1) if lab else m.group(1), types=[m.group(2)])
    inverse = {}
    for a, b in re.findall(r":(\w+) rdf:type owl:ObjectProperty ;\s*owl:inverseOf :(\w+)", t):
        inverse[a], inverse[b] = b, a
    defined = {"Boursier": ("Apprenant", "beneficieDeBourse", "Bourse")} if "Boursier" in classes else {}
    return Schema(classes, props, inds, defined, inverse)
