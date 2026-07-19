"""
Pytest loads this file automatically before collecting any test module.

We stub out `google.generativeai` here so that `backend.gemini_client`
can be imported without pulling in the real SDK's dependency chain
(grpc / cryptography / cffi). Every test in this suite already mocks
Gemini calls directly (via unittest.mock.patch on gemini_client.model),
so the real SDK is never actually needed to run the test suite —
only to run the live app.

This exists specifically to work around environments (seen on some
Windows setups) where the real google-generativeai import chain fails
with unrelated binary/DLL errors (pydantic_core, cygrpc, cffi, etc.)
that have nothing to do with this project's own code.
"""
import sys
import types

if "google.generativeai" not in sys.modules:
    genai_stub = types.ModuleType("google.generativeai")

    class _FakeGenerativeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, *args, **kwargs):
            raise RuntimeError(
                "Real Gemini calls are not available under the test stub. "
                "Patch gemini_client.model.generate_content with unittest.mock."
            )

    genai_stub.configure = lambda *args, **kwargs: None
    genai_stub.GenerativeModel = _FakeGenerativeModel

    sys.modules["google.generativeai"] = genai_stub

    try:
        import google as _google_pkg
        _google_pkg.generativeai = genai_stub
    except ImportError:
        pass