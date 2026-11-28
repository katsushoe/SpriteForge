import os
import uuid

from spriteforge_mcp.security import TEST_NAMESPACE_ENV

# Isolate the session-wide mutexes (inherited by spawned daemons) from a user's running
# SpriteForge so the suite can run while the real daemon or tray is active.
os.environ[TEST_NAMESPACE_ENV] = uuid.uuid4().hex
