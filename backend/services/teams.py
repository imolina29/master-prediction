import json
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

MAPPINGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "team_mappings.json"


class TeamNormalizer:
    def __init__(self, mappings_path: Path = MAPPINGS_PATH):
        data = json.loads(mappings_path.read_text(encoding="utf-8"))
        self._alias_to_canonical: dict[str, str] = data.get("aliases", {})
        self._metadata: dict[str, dict] = data.get("canonical_metadata", {})

        self._canonical_to_aliases: dict[str, list[str]] = defaultdict(list)
        for alias, canonical in self._alias_to_canonical.items():
            self._canonical_to_aliases[canonical].append(alias)

    def normalize(self, name: str) -> str:
        return self._alias_to_canonical.get(name, name)

    def get_aliases(self, canonical_name: str) -> list[str]:
        return self._canonical_to_aliases.get(canonical_name, [])

    def get_metadata(self, canonical_name: str) -> dict | None:
        return self._metadata.get(canonical_name)

    def all_canonical(self) -> set[str]:
        canonical = set(self._alias_to_canonical.values())
        canonical.update(self._metadata.keys())
        return canonical
