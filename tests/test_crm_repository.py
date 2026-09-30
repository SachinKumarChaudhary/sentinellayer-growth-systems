from sentinellayer_growth_engine.crm.repository import CRMRepository


class Cursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return self.rows.pop(0)


class Connection:
    def __init__(self, rows):
        self.cursor_obj = Cursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj


def test_first_account_transition_initializes_from_new():
    connection = Connection([
        None,
        {"id": 2},
        {
            "account_id": 2,
            "state": "QUALIFIED",
            "version": 1,
            "updated_at": "2026-09-30T00:00:00Z",
        },
    ])
    repo = CRMRepository(lambda: connection)

    result = repo.transition_account_state(
        account_id=2,
        to_state="QUALIFIED",
        expected_version=0,
    )

    assert result["account_id"] == 2
    assert result["state"] == "QUALIFIED"
    assert result["version"] == 1
    assert any("insert into crm.account_state" in sql.lower() for sql, _ in connection.cursor_obj.calls)
