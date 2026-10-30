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
        header = re.match(r":(\w+)\s+(?:a|rdf:type)\s+([^;.]+)", b)
        if not header:
            continue
        name, types = header.groups()
        if re.search(r"\bowl:Class\b", types):
            parents = re.findall(r"rdfs:subClassOf\s+((?::\w+(?:\s*,\s*(?=:))?\s*)+)", b)
            ps = re.findall(r":(\w+)", parents[0]) if parents else []
            lab = re.search(r'rdfs:label "([^"]*)"', b)
            classes[name] = dict(label=lab.group(1) if lab else "", parents=ps)
            continue
        prop = re.search(r"\bowl:(Object|Datatype)Property\b", types)
        if prop:
            d, r = re.search(r"rdfs:domain :(\w+)", b), re.search(r"rdfs:range (?:xsd:|:)(\w+)", b)
            lab = re.search(r'rdfs:label "([^"]*)"', b)
            props[name] = dict(kind="object" if prop.group(1) == "Object" else "data", label=lab.group(1) if lab else "",
                                     domain=d.group(1) if d else None, range=r.group(1) if r else None)
            continue
        if "owl:NamedIndividual" in types:
            lab = re.search(r'rdfs:label "([^"]*)"', b)
            types = re.findall(r":(\w+)", types)
            inds[name] = dict(label=lab.group(1) if lab else name, types=types)
    inverse = {}
    for block in re.split(r"\n\n+", t):
        header = re.match(r":(\w+)\s+(?:a|rdf:type)\s+([^;.]+)", block.strip())
        inverse_prop = re.search(r"owl:inverseOf\s+:([\w]+)", block)
        if header and "owl:ObjectProperty" in header.group(2) and inverse_prop:
            inverse[header.group(1)] = inverse_prop.group(1)
            inverse[inverse_prop.group(1)] = header.group(1)
    defined = {"Boursier": ("Apprenant", "beneficieDeBourse", "Bourse")} if "Boursier" in classes else {}
    return Schema(classes, props, inds, defined, inverse)
