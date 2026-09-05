# Conversation → Sales bridge

Only `interested` and `question` classifications create human sales tasks. Negative, unsubscribe, out-of-office and defer classifications stay inside their policy paths and do not create a sales task.

The bridge creates a validated SalesHandoff containing account/person identity, trigger, priority, latest reply, conversation context and recommended action. A durable Sales task store owns idempotent persistence.