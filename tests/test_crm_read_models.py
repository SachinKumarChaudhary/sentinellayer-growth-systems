from sentinellayer_growth_engine.crm.read_models import CRMReadModelRepository


class Cursor:
    def __init__(self, results):
        self.results = list(results)
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append((sql, params))

    def fetchone(self):
        return self.results.pop(0)

    def fetchall(self):
        return self.results.pop(0)


class Connection:
    def __init__(self, results):
        self.cursor_obj = Cursor(results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj


# Support psycopg-style `with conn.cursor() as cur:` in repository tests.
Cursor.__enter__ = lambda self: self
Cursor.__exit__ = lambda self, exc_type, exc, tb: False


def test_list_accounts_returns_cursor_metadata():
    conn = Connection([
        [
            {"id": 1, "name": "Alpha", "domain": "alpha.example", "state": "NEW",
             "owner_user_id": None, "version": 0, "last_activity_at": None,
             "next_action_at": None},
            {"id": 2, "name": "Beta", "domain": "beta.example", "state": "WORKING",
             "owner_user_id": None, "version": 1, "last_activity_at": None,
             "next_action_at": None},
            {"id": 3, "name": "Gamma", "domain": "gamma.example", "state": "NEW",
             "owner_user_id": None, "version": 0, "last_activity_at": None,
             "next_action_at": None},
        ]
    ])
    repo = CRMReadModelRepository(lambda: conn)

    result = repo.list_accounts(limit=2)

    assert [row["id"] for row in result["data"]] == [1, 2]
    assert result["meta"] == {"next_cursor": 2, "has_more": True}


def test_account_360_assembles_core_sections():
    conn = Connection([
        {
            "id": 1, "name": "Alpha", "domain": "alpha.example",
            "website": None, "company_linkedin": None, "country": None, "city": None,
            "segment": None, "revenue_est": None, "visits_est": None,
            "state": "NEW", "owner_user_id": None, "version": 0,
        },
        [{"decision_maker_id": "dm-1", "full_name": "Ada", "title": "CISO",
          "role_family": "security", "role_priority": 1, "status": "active",
          "contact_methods": []}],
        [{"sales_task_id": "task-1", "canonical_person_id": None,
          "trigger_type": "follow_up", "priority": "P2",
          "recommended_action": "follow up", "why_now": [], "status": "open",
          "due_at": None, "assigned_to": None, "created_at": None, "updated_at": None}],
        [{"note_id": "note-1", "decision_maker_id": None, "body": "Context",
          "author_user_id": "user-1", "created_at": None, "updated_at": None}],
        None,
        [],
        [],
        [{"occurred_at": None, "event_type": "state_changed",
          "event_id": "h-1", "channel": None, "touchpoint_type": "state_changed",
          "summary": "∅ → NEW", "person_id": None}],
    ])
    repo = CRMReadModelRepository(lambda: conn)

    result = repo.get_account_360(account_id=1)

    assert result["account"]["id"] == 1
    assert result["contacts"][0]["full_name"] == "Ada"
    assert result["open_tasks"][0]["sales_task_id"] == "task-1"
    assert result["notes"][0]["body"] == "Context"
    assert result["timeline"][0]["event_type"] == "state_changed"


def test_search_accounts_rejects_blank_query():
    repo = CRMReadModelRepository(lambda: Connection([]))

    try:
        repo.search_accounts(query=" ")
    except ValueError as exc:
        assert "search query" in str(exc)
    else:
        raise AssertionError("blank query must be rejected")


def test_pipeline_summary_uses_state_order():
    conn = Connection([[{"state": "NEW", "account_count": 5}, {"state": "WORKING", "account_count": 2}]])
    repo = CRMReadModelRepository(lambda: conn)
    result = repo.pipeline_summary()
    assert result["data"][0]["state"] == "NEW"
    assert result["meta"]["total_accounts"] == 7


def test_contacts_returns_cursor_metadata():
    conn = Connection([[
        {"decision_maker_id": "11111111-1111-4111-8111-111111111111", "company_id": 1,
         "company_name": "Alpha", "domain": "alpha.example", "full_name": "Ada",
         "title": "CISO", "role_family": "security", "role_priority": 1,
         "research_status": "validated", "state": "NOT_CONTACTED",
         "owner_user_id": None, "version": 0, "contact_methods": []},
        {"decision_maker_id": "22222222-2222-4222-8222-222222222222", "company_id": 2,
         "company_name": "Beta", "domain": "beta.example", "full_name": "Bob",
         "title": "CISO", "role_family": "security", "role_priority": 2,
         "research_status": "validated", "state": "CONTACTED",
         "owner_user_id": None, "version": 1, "contact_methods": []},
    ]])
    repo = CRMReadModelRepository(lambda: conn)
    result = repo.list_contacts(limit=1)
    assert len(result["data"]) == 1
    assert result["meta"]["has_more"] is True
