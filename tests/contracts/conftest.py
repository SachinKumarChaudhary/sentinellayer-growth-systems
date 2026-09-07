from __future__ import annotations


def pytest_collection_modifyitems(config, items) -> None:
    del config
    for item in items:
        module = item.module
        if not hasattr(module, "contract_fixtures"):
            continue
        if getattr(module, "_conversation_analysis_fixture_patched", False):
            continue

        original = module.contract_fixtures

        def contract_fixtures_with_conversation_analysis(original=original):
            fixtures = original()
            fixtures["conversation_analysis"] = {
                "schema_version": "1.0",
                "primary_intent": "objection",
                "secondary_intents": ["interested"],
                "objections": [
                    {
                        "type": "already_have_solution",
                        "evidence": "We already use another platform.",
                        "confidence": 0.94,
                    }
                ],
                "explicit_opt_out": False,
                "timing_signal": "later",
                "questions": [],
                "evidence": [
                    {
                        "text": "We already use another platform.",
                        "reason": "existing solution",
                    }
                ],
                "confidence": 0.91,
            }
            return fixtures

        module.contract_fixtures = contract_fixtures_with_conversation_analysis
        module._conversation_analysis_fixture_patched = True
