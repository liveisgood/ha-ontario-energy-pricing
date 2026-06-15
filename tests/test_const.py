"""Unit tests for const.py - location to zone mapping."""

import logging

logging.basicConfig(level=logging.WARNING)

# Load the const module directly
with open('/home/dmalloc/pidev/custom_components/ontario_energy_pricing/const.py', 'r') as f:
    code = f.read()

namespace = {'logging': logging}
exec(code, namespace)

get_zone_from_location = namespace['get_zone_from_location']
LOCATION_TO_ZONE = namespace['LOCATION_TO_ZONE']
LOCATION_OPTIONS = namespace['LOCATION_OPTIONS']


def test_known_locations_map_to_correct_zone():
    """Test that known Ontario cities map to their correct IESO zones."""
    test_cases = {
        # TORONTO zone
        "oakville": "TORONTO",
        "oakville, ontario": "TORONTO",
        "Oakville, Ontario": "TORONTO",
        "toronto": "TORONTO",
        "Toronto": "TORONTO",
        "mississauga": "TORONTO",
        "brampton": "TORONTO",
        "markham": "TORONTO",
        "vaughan": "TORONTO",
        "richmond hill": "TORONTO",
        "ajax": "TORONTO",
        "pickering": "TORONTO",
        "whitby": "TORONTO",
        "oshawa": "TORONTO",
        "burlington": "TORONTO",
        "hamilton": "TORONTO",
        "caledon": "TORONTO",
        "king": "TORONTO",
        "aurora": "TORONTO",
        "newmarket": "TORONTO",
        "east guilimbury": "TORONTO",
        "georgina": "TORONTO",
        # OTTAWA zone
        "ottawa": "OTTAWA",
        "kanata": "OTTAWA",
        "orleans": "OTTAWA",
        "nepean": "OTTAWA",
        "barrhaven": "OTTAWA",
        "stittsville": "OTTAWA",
        # NIAGARA zone
        "niagara falls": "NIAGARA",
        "st. catharines": "NIAGARA",
        "welland": "NIAGARA",
        "fort erie": "NIAGARA",
        "niagara-on-the-lake": "NIAGARA",
        "grimsby": "NIAGARA",
        # SOUTHWEST zone
        "london": "SOUTHWEST",
        "London": "SOUTHWEST",
        "kitchener": "SOUTHWEST",
        "waterloo": "SOUTHWEST",
        "cambridge": "SOUTHWEST",
        "guelph": "SOUTHWEST",
        "windsor": "SOUTHWEST",
        "sarnia": "SOUTHWEST",
        "stratford": "SOUTHWEST",
        "woodstock": "SOUTHWEST",
        "chatham": "SOUTHWEST",
        "leamington": "SOUTHWEST",
        # EAST zone
        "kingston": "EAST",
        "belleville": "EAST",
        "peterborough": "EAST",
        "cobourg": "EAST",
        "port hope": "EAST",
        "brockville": "EAST",
        "cornwall": "EAST",
        # ESSA zone
        "barrie": "ESSA",
        "orillia": "ESSA",
        "midland": "ESSA",
        "collingwood": "ESSA",
        "wasaga beach": "ESSA",
        "innisfil": "ESSA",
        # NORTHEAST zone
        "sudbury": "NORTHEAST",
        "north bay": "NORTHEAST",
        "timmins": "NORTHEAST",
        "sault ste. marie": "NORTHEAST",
        # NORTHWEST zone
        "thunder bay": "NORTHWEST",
        "kenora": "NORTHWEST",
        "dryden": "NORTHWEST",
        # WEST zone
        "owen sound": "WEST",
        "blue mountains": "WEST",
        "meaford": "WEST",
    }

    for location, expected_zone in test_cases.items():
        result = get_zone_from_location(location)
        assert result == expected_zone, f"Failed for '{location}': expected {expected_zone}, got {result}"


def test_unknown_location_defaults_to_toronto():
    """Test that unknown locations default to TORONTO zone."""
    result = get_zone_from_location("Somewhere Unknown")
    assert result == "TORONTO"


def test_empty_location_defaults_to_toronto():
    """Test that empty/None location defaults to TORONTO."""
    assert get_zone_from_location("") == "TORONTO"
    assert get_zone_from_location(None) == "TORONTO"


def test_case_insensitive():
    """Test that location matching is case-insensitive."""
    assert get_zone_from_location("TORONTO") == "TORONTO"
    assert get_zone_from_location("toronto") == "TORONTO"
    assert get_zone_from_location("Toronto") == "TORONTO"
    assert get_zone_from_location("ToRoNtO") == "TORONTO"


def test_whitespace_handling():
    """Test that extra whitespace is handled."""
    assert get_zone_from_location("  oakville  ") == "TORONTO"
    assert get_zone_from_location("oakville , ontario") == "TORONTO"


def test_location_options_includes_all_mapped():
    """Test that LOCATION_OPTIONS includes all keys from LOCATION_TO_ZONE."""
    assert set(LOCATION_OPTIONS) == set(LOCATION_TO_ZONE.keys())
    assert LOCATION_OPTIONS == sorted(LOCATION_TO_ZONE.keys())


def test_no_ontario_on_substring_bug():
    """Regression test for the 'on' substring bug.

    Previously 'Toronto' -> 'Tronto' -> unknown -> TORONTO (wrong zone logic)
    and 'London' -> 'Ldon' -> unknown -> TORONTO (wrong zone).
    """
    # These cities contain "on" as substring but should NOT be corrupted
    assert get_zone_from_location("Toronto") == "TORONTO"
    assert get_zone_from_location("London") == "SOUTHWEST"
    assert get_zone_from_location("Hamilton") == "TORONTO"
    assert get_zone_from_location("Kingston") == "EAST"
    # Simcoe not in mapping, just verify it doesn't crash
    get_zone_from_location("Simcoe")


if __name__ == "__main__":
    # Run tests
    test_known_locations_map_to_correct_zone()
    print("✅ test_known_locations_map_to_correct_zone passed")

    test_unknown_location_defaults_to_toronto()
    print("✅ test_unknown_location_defaults_to_toronto passed")

    test_empty_location_defaults_to_toronto()
    print("✅ test_empty_location_defaults_to_toronto passed")

    test_case_insensitive()
    print("✅ test_case_insensitive passed")

    test_whitespace_handling()
    print("✅ test_whitespace_handling passed")

    test_location_options_includes_all_mapped()
    print("✅ test_location_options_includes_all_mapped passed")

    test_no_ontario_on_substring_bug()
    print("✅ test_no_ontario_on_substring_bug passed")

    print("\n🎉 All tests passed!")