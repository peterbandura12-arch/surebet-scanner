"""Text normalisation used by the event matching engine."""
from __future__ import annotations

import re
import unicodedata

_TEAM_ABBREVIATIONS = {
    "manchester city": ["man city", "manchester c", "man c", "mcity"],
    "manchester united": ["man united", "man utd", "manchester u", "man u"],
    "newcastle united": ["newcastle"],
    "wolverhampton wanderers": ["wolves", "wolverhampton"],
    "tottenham hotspur": ["tottenham", "spurs"],
    "west ham united": ["west ham"],
    "paris saint germain": ["paris sg", "paris saint-germain", "psg", "paris"],
    "real madrid": ["real m", "r madrid"],
    "atletico madrid": ["atletico", "atl madrid", "atletico m"],
    "bayern munich": ["bayern", "bayern munchen", "fc bayern"],
    "borussia dortmund": ["dortmund", "bvb"],
    "internazionale": ["inter", "inter milan"],
    "fc barcelona": ["barcelona", "barca", "fc barca"],
    "as monaco": ["monaco"],
    "milan": ["ac milan"],
    "rb leipzig": ["leipzig", "rasenballsport leipzig"],
    "la lakers": ["los angeles lakers", "lakers"],
    "ny rangers": ["new york rangers"],
    "golden state warriors": ["gs warriors", "warriors"],
    "vegas golden knights": ["vegas knights", "golden knights"],
    "boston celtics": ["celtics"],
    "denver nuggets": ["nuggets"],
    "miami heat": ["heat"],
    "dallas mavericks": ["mavericks", "mavs"],
    "as roma": ["roma"],
    "everton": ["everton fc"],
    "sevilla": ["sevilla fc", "sevilla cf"],
    "real betis": ["betis", "real betis balompie"],
    "athletic bilbao": ["athletic club"],
    "valencia": ["valencia cf"],
    "villarreal": ["villarreal cf"],
    "bayer leverkusen": ["leverkusen", "bayer 04 leverkusen", "bayer 04"],
    "boston bruins": ["bruins"],
    "toronto maple leafs": ["maple leafs", "leafs"],
    "colorado avalanche": ["avalanche"],
    "edmonton oilers": ["oilers"],
    "fenerbahce": ["fenerbahce sk"],
    "anadolu efes": ["efes"],
    "panathinaikos": ["panathinaikos bc"],
    "olympiacos": ["olympiacos bc"],
}

_STOPWORDS = {"fc", "cf", "sc", "afc", "ac", "as", "ss", "ssd", "club", "de",
              "the", "1", "ii", "if", "bk", "sk", "fk", "cd", "ca", "ud",
              "cp", "sd", "ec", "vfl", "vfb", "tsv", "sv"}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


def normalize_team_name(name: str) -> str:
    if not name:
        return ""
    s = strip_accents(name).lower()
    s = s.replace("-", " ").replace("_", " ").replace(".", " ")
    s = re.sub(r"\((?:[^)]*)\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    tokens = [t for t in s.split() if t and t not in _STOPWORDS]
    expanded = [{"utd": "united", "st": "saint"}.get(t, t) for t in tokens]
    return " ".join(expanded)


def canonical_participant(name: str) -> str:
    """Resolve well-known abbreviations to a canonical team name."""
    n = strip_accents(name).lower().strip()
    for canonical, variants in _TEAM_ABBREVIATIONS.items():
        if n == canonical or n in variants:
            return canonical
    return normalize_team_name(name)


def participant_tokens(name: str) -> set[str]:
    c = canonical_participant(name)
    return {t for t in c.split() if len(t) > 1}
