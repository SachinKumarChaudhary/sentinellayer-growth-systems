from sentinellayer_growth_engine.cli import build_parser


def test_parser_exposes_health_and_status_commands():
    parser = build_parser()
    assert parser.parse_args(["health"]).command == "health"
    assert parser.parse_args(["status"]).command == "status"
