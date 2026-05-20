import logging

from backend.etl.understat import LEAGUE_MAP, fetch_league_season
from backend.services.teams import TeamNormalizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")


def main():
    normalizer = TeamNormalizer()
    unmapped: dict[str, set[str]] = {}

    for league, division in LEAGUE_MAP.items():
        logging.info("Checking %s 2024...", league)
        data = fetch_league_season(league, 2024)
        for match in data["dates"]:
            for side in ["h", "a"]:
                name = match[side]["title"]
                canonical = normalizer.normalize(name)
                if canonical == name and name not in normalizer.all_canonical():
                    if league not in unmapped:
                        unmapped[league] = set()
                    unmapped[league].add(name)

    if unmapped:
        print("\n=== UNMAPPED TEAM NAMES ===")
        for league, names in sorted(unmapped.items()):
            print(f"\n{league}:")
            for name in sorted(names):
                print(f'  "{name}": "<canonical_name>",')
    else:
        print("\nAll team names are mapped!")


if __name__ == "__main__":
    main()
