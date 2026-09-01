# Dependency Rules

## Dependency principle
A system may depend on another system's documented public contract. It must not depend on private implementation modules, undocumented side effects, another system's worker state, or internal database tables without an explicit contract.

## Lifecycle
Platform contracts → Intelligence → Campaign → Mail → Tracking / Conversation → Sales → Analytics.
Operations provides runtime capabilities across systems.

Campaign → RenderedSendTreatment → Mail is a contract boundary. Mail validates and executes; it does not interpret campaign strategy.

Analytics consumes canonical events/outcomes and is never the operational source of truth.

## Breaking changes
1. Identify producer and consumer.
2. Assess compatibility.
3. Decide schema/version strategy.
4. Update producer and consumer.
5. Add integration coverage.
6. Run the full CI gate.

## Database
Domain systems own their domain tables and migrations. Platform owns shared database primitives and cross-system conventions; it does not own every domain table.
