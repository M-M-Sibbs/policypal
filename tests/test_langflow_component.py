"""The Langflow component (langflow/policypal_component.py) forwards a Chat
Input message to POST /chat and formats the cited answer.

Langflow itself is a large install, so these tests replace the `lfx` classes
the component imports with small stand-ins and route its HTTP calls to the
Flask test client. They check the component's contract with PolicyPal, not
Langflow's UI.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

COMPONENT = Path(__file__).resolve().parents[1] / "langflow" / "policypal_component.py"


class _Message:
    def __init__(self, text="", session_id=""):
        self.text = text
        self.session_id = session_id


class _Data:
    def __init__(self, data=None):
        self.data = data or {}


class _Input:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _Component:
    pass


def _install_lfx_stubs(monkeypatch):
    modules = {
        "lfx": types.ModuleType("lfx"),
        "lfx.custom": types.ModuleType("lfx.custom"),
        "lfx.custom.custom_component": types.ModuleType("lfx.custom.custom_component"),
        "lfx.custom.custom_component.component": types.ModuleType("lfx.custom.custom_component.component"),
        "lfx.io": types.ModuleType("lfx.io"),
        "lfx.schema": types.ModuleType("lfx.schema"),
        "lfx.schema.data": types.ModuleType("lfx.schema.data"),
        "lfx.schema.message": types.ModuleType("lfx.schema.message"),
    }
    modules["lfx.custom.custom_component.component"].Component = _Component
    for name in ("IntInput", "MessageInput", "MessageTextInput", "Output"):
        setattr(modules["lfx.io"], name, _Input)
    modules["lfx.schema.data"].Data = _Data
    modules["lfx.schema.message"].Message = _Message
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


class _FakeResponse:
    def __init__(self, flask_response):
        self.status_code = flask_response.status_code
        self._json = flask_response.get_json()

    def json(self):
        if self._json is None:
            raise ValueError("not json")
        return self._json


def _fake_async_client(flask_client, calls):
    class FakeAsyncClient:
        def __init__(self, timeout=None):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            calls.append((url, json))
            path = "/" + url.split("://", 1)[-1].split("/", 1)[1]
            return _FakeResponse(flask_client.post(path, json=json))

    return FakeAsyncClient


@pytest.fixture
def component_module(monkeypatch):
    _install_lfx_stubs(monkeypatch)
    spec = importlib.util.spec_from_file_location("policypal_component", COMPONENT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make(component_module, client, question, monkeypatch, calls):
    monkeypatch.setattr(component_module.httpx, "AsyncClient", _fake_async_client(client, calls))
    comp = component_module.PolicyPalRAG()
    comp.input_value = _Message(question, session_id="sess-1")
    comp.api_url = "http://localhost:5000/"
    comp.timeout = 30
    comp._result = None
    return comp


def test_component_declares_langflow_inputs(component_module):
    names = [i.name for i in component_module.PolicyPalRAG.inputs]
    assert names == ["input_value", "api_url", "timeout"]
    assert {o.name for o in component_module.PolicyPalRAG.outputs} == {"answer", "citations"}


def test_component_returns_cited_answer(component_module, client, monkeypatch):
    calls = []
    comp = _make(component_module, client, "How many unused PTO days can I carry over?", monkeypatch, calls)
    message = asyncio.run(comp.answer_response())
    assert calls[0] == ("http://localhost:5000/chat", {"question": "How many unused PTO days can I carry over?", "session_id": "sess-1"})
    assert "5" in message.text and "Sources:" in message.text
    assert "Paid Time Off (PTO)" in message.text and "http://localhost:5000/sources/POL-02" in message.text
    assert comp.status == "answered"
    data = asyncio.run(comp.citations_data())
    assert data[0].data["document_id"] == "POL-02"
    assert len(calls) == 1  # both outputs share one API call


def test_component_passes_on_refusals(component_module, client, monkeypatch):
    comp = _make(component_module, client, "What is the capital of France?", monkeypatch, [])
    message = asyncio.run(comp.answer_response())
    assert message.text == "I can only answer about our policies."
    assert comp.status == "out_of_scope"
    assert asyncio.run(comp.citations_data()) == []


def test_component_reports_api_errors(component_module, client, monkeypatch):
    comp = _make(component_module, client, "   ", monkeypatch, [])
    message = asyncio.run(comp.answer_response())
    assert message.text == "Please enter a question."
    assert comp.status == "invalid_request"
