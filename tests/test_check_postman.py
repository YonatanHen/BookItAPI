from scripts.check_postman import main


def test_postman_collection_covers_every_route():
    assert main() == 0
