"""
Email backends for the cold-email-drafter skill.

Each backend implements the EmailBackend interface (see base.py) so the
daily send path (send_batch.py) never has to know which provider is
behind it. Adding a new provider = generating a new backend module here
via inspect_mcp.py, then pointing PROVIDER at it. Nothing else changes.
"""
