"""Tests for GraphQL subscriptions over Server-Sent Events.

Implements the graphql-sse protocol's "distinct connections mode":
https://github.com/enisdenjo/graphql-sse/blob/master/PROTOCOL.md
"""
import asyncio
import json
from typing import AsyncGenerator

import pytest

from graphql import (
    GraphQLArgument,
    GraphQLField,
    GraphQLInt,
    GraphQLObjectType,
    GraphQLSchema,
    GraphQLString,
)

from graphql_http import GraphQLHTTP

SSE_HEADERS = {"Accept": "text/event-stream"}


def is_graphql_api_installed():
    try:
        import graphql_api

        assert graphql_api
    except ImportError:
        return False

    return True


def parse_sse_events(text):
    """Parse an SSE body into (event, data) tuples, skipping comment lines."""
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        event_name = None
        data_lines = []
        has_fields = False
        for line in block.split("\n"):
            if line.startswith(":"):
                continue
            has_fields = True
            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].lstrip())
        if has_fields:
            events.append((event_name, "\n".join(data_lines)))
    return events


def build_schema():
    """Schema with query, mutation and several subscription fields."""

    async def subscribe_countdown(root, info, start=2):
        for i in range(start, -1, -1):
            yield i

    async def subscribe_failing(root, info):
        yield 1
        raise RuntimeError("source blew up")

    async def subscribe_broken(root, info):
        # Coroutine (not async generator): subscribe() fails before a
        # source stream exists.
        raise RuntimeError("subscribe blew up")

    async def subscribe_slowly(root, info):
        yield 1
        await asyncio.sleep(0.2)
        yield 2

    def resolve_flaky(event, info, **kwargs):
        if event == 1:
            raise RuntimeError("flaky resolver")
        return event

    return GraphQLSchema(
        query=GraphQLObjectType(
            "Query",
            {"hello": GraphQLField(
                GraphQLString, resolve=lambda *_: "world")},
        ),
        mutation=GraphQLObjectType(
            "Mutation",
            {"setValue": GraphQLField(
                GraphQLString, resolve=lambda *_: "set")},
        ),
        subscription=GraphQLObjectType(
            "Subscription",
            {
                "countdown": GraphQLField(
                    GraphQLInt,
                    args={"start": GraphQLArgument(GraphQLInt)},
                    subscribe=subscribe_countdown,
                    resolve=lambda event, info, **kwargs: event,
                ),
                "failing": GraphQLField(
                    GraphQLInt,
                    subscribe=subscribe_failing,
                    resolve=lambda event, info: event,
                ),
                "broken": GraphQLField(
                    GraphQLInt,
                    subscribe=subscribe_broken,
                    resolve=lambda event, info: event,
                ),
                "flaky": GraphQLField(
                    GraphQLInt,
                    args={"start": GraphQLArgument(GraphQLInt)},
                    subscribe=subscribe_countdown,
                    resolve=resolve_flaky,
                ),
                "slow": GraphQLField(
                    GraphQLInt,
                    subscribe=subscribe_slowly,
                    resolve=lambda event, info: event,
                ),
            },
        ),
    )


class TestSSESubscriptions:
    """Streaming behavior of subscription operations over SSE."""

    @pytest.fixture
    def schema(self):
        return build_schema()

    @pytest.fixture
    def server(self, schema):
        return GraphQLHTTP(schema=schema)

    @pytest.fixture
    def client(self, server):
        return server.client()

    def test_subscription_streams_next_events_then_complete(self, client):
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 2) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")

        events = parse_sse_events(response.text)
        assert [(e, json.loads(d)) for e, d in events[:-1]] == [
            ("next", {"data": {"countdown": 2}}),
            ("next", {"data": {"countdown": 1}}),
            ("next", {"data": {"countdown": 0}}),
        ]
        assert events[-1] == ("complete", "")

    def test_complete_event_has_empty_data_field(self, client):
        """The spec requires an empty `data:` field on the complete event."""
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 0) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert response.text.endswith("event: complete\ndata: \n\n")

    def test_subscription_via_get(self, client):
        response = client.get(
            "/graphql?query=subscription{countdown(start:1)}",
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")
        events = parse_sse_events(response.text)
        assert [(e, json.loads(d)) for e, d in events[:-1]] == [
            ("next", {"data": {"countdown": 1}}),
            ("next", {"data": {"countdown": 0}}),
        ]
        assert events[-1] == ("complete", "")

    def test_subscription_streaming_incrementally(self, client):
        """Events are consumable through the streaming client interface."""
        with client.stream(
            "POST",
            "/graphql",
            json={"query": "subscription { countdown(start: 1) }"},
            headers=SSE_HEADERS,
        ) as response:
            lines = list(response.iter_lines())

        assert lines == [
            "event: next",
            'data: {"data":{"countdown":1}}',
            "",
            "event: next",
            'data: {"data":{"countdown":0}}',
            "",
            "event: complete",
            "data: ",
            "",
        ]

    def test_query_over_sse_single_next_then_complete(self, client):
        response = client.post(
            "/graphql",
            json={"query": "{ hello }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")
        events = parse_sse_events(response.text)
        assert [(e, json.loads(d)) for e, d in events[:-1]] == [
            ("next", {"data": {"hello": "world"}}),
        ]
        assert events[-1] == ("complete", "")

    def test_mutation_over_sse_single_next_then_complete(self, client):
        response = client.post(
            "/graphql",
            json={"query": "mutation { setValue }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)
        assert [(e, json.loads(d)) for e, d in events[:-1]] == [
            ("next", {"data": {"setValue": "set"}}),
        ]
        assert events[-1] == ("complete", "")

    def test_subscription_without_sse_accept_rejected(self, client):
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown }"},
        )

        assert response.status_code == 406
        assert response.headers["content-type"].startswith(
            "application/json")
        result = response.json()
        assert "errors" in result
        assert "text/event-stream" in result["errors"][0]["message"]

    def test_invalid_subscription_without_sse_accept_reports_validation(
        self, client
    ):
        """An invalid document surfaces its validation errors instead of a
        406 that would mask them."""
        response = client.post(
            "/graphql",
            json={"query": "subscription { doesNotExist }"},
        )

        assert response.headers["content-type"].startswith(
            "application/json")
        result = response.json()
        assert "doesNotExist" in result["errors"][0]["message"]

    def test_accept_with_q0_is_not_sse_capable(self, client):
        """`text/event-stream;q=0` is an explicit refusal per RFC 9110."""
        headers = {"Accept": "application/json, text/event-stream;q=0"}

        response = client.post(
            "/graphql", json={"query": "{ hello }"}, headers=headers)
        assert response.headers["content-type"].startswith(
            "application/json")
        assert response.json() == {"data": {"hello": "world"}}

        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown }"},
            headers=headers,
        )
        assert response.status_code == 406

    def test_accept_with_positive_q_is_sse_capable(self, client):
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 0) }"},
            headers={"Accept": "text/event-stream;q=0.5, application/json"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")

    def assert_sse_error_events(self, response, message_fragment):
        """Per the graphql-sse spec, pre-execution errors MUST arrive over
        an accepted 200 text/event-stream response as a `next` event
        carrying the errors, followed by `complete`."""
        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")
        events = parse_sse_events(response.text)
        assert [e for e, _ in events] == ["next", "complete"]
        payload = json.loads(events[0][1])
        assert "errors" in payload
        assert message_fragment in payload["errors"][0]["message"]

    def test_subscription_validation_error_streams_next_with_errors(
        self, client
    ):
        response = client.post(
            "/graphql",
            json={"query": "subscription { doesNotExist }"},
            headers=SSE_HEADERS,
        )

        self.assert_sse_error_events(response, "doesNotExist")

    def test_query_validation_error_streams_next_with_errors(self, client):
        """Any request with an SSE Accept header reports validation errors
        over the stream, not just subscriptions."""
        response = client.post(
            "/graphql",
            json={"query": "{ doesNotExist }"},
            headers=SSE_HEADERS,
        )

        self.assert_sse_error_events(response, "doesNotExist")

    def test_parse_error_streams_next_with_errors(self, client):
        response = client.post(
            "/graphql",
            json={"query": "subscription {"},
            headers=SSE_HEADERS,
        )

        self.assert_sse_error_events(response, "Syntax Error")

    def test_missing_query_streams_next_with_errors(self, client):
        response = client.post(
            "/graphql", json={}, headers=SSE_HEADERS)

        self.assert_sse_error_events(response, "Must provide query string")

    def test_subscribe_phase_error_streams_next_with_errors(self, client):
        """A subscribe() failure before a source stream exists is also
        tunneled through the accepted SSE connection."""
        response = client.post(
            "/graphql",
            json={"query": "subscription { broken }"},
            headers=SSE_HEADERS,
        )

        self.assert_sse_error_events(response, "subscribe blew up")

    def test_resolver_error_rides_inside_next_event(self, client):
        """Per-event resolver errors are standard GraphQL errors in `next`."""
        response = client.post(
            "/graphql",
            json={"query": "subscription { flaky(start: 2) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)
        payloads = [json.loads(d) for e, d in events if e == "next"]
        assert len(payloads) == 3
        assert payloads[0] == {"data": {"flaky": 2}}
        assert "errors" in payloads[1]
        assert "flaky resolver" in payloads[1]["errors"][0]["message"]
        assert payloads[2] == {"data": {"flaky": 0}}
        assert events[-1] == ("complete", "")

    def test_fatal_source_error_emits_final_next_then_complete(self, client):
        """A crashing source ends the stream with an error `next` + complete."""
        response = client.post(
            "/graphql",
            json={"query": "subscription { failing }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)
        payloads = [json.loads(d) for e, d in events if e == "next"]
        assert payloads[0] == {"data": {"failing": 1}}
        assert "errors" in payloads[1]
        assert "source blew up" in payloads[1]["errors"][0]["message"]
        assert events[-1] == ("complete", "")

    def test_keepalive_pings_while_idle(self, schema):
        server = GraphQLHTTP(schema=schema, sse_keepalive_interval=0.05)
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "subscription { slow }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert ": ping" in response.text
        events = parse_sse_events(response.text)
        assert [(e, json.loads(d)) for e, d in events[:-1]] == [
            ("next", {"data": {"slow": 1}}),
            ("next", {"data": {"slow": 2}}),
        ]
        assert events[-1] == ("complete", "")

    def test_keepalive_interval_default(self, server):
        assert server.sse_keepalive_interval == 15.0

    def test_keepalive_none_disables_pings(self, schema):
        server = GraphQLHTTP(schema=schema, sse_keepalive_interval=None)
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "subscription { slow }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert ": ping" not in response.text
        events = parse_sse_events(response.text)
        assert events[-1] == ("complete", "")

    @pytest.mark.parametrize("interval", [0, -1, -0.5])
    def test_keepalive_interval_must_be_positive(self, schema, interval):
        with pytest.raises(ValueError, match="sse_keepalive_interval"):
            GraphQLHTTP(schema=schema, sse_keepalive_interval=interval)

    def test_regular_json_requests_unaffected(self, client):
        """A schema with subscriptions still serves plain JSON as before."""
        response = client.post("/graphql", json={"query": "{ hello }"})

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "application/json")
        assert response.json() == {"data": {"hello": "world"}}


class TestSSEMiddlewareAndExecutionContext:
    """Subscription events run through the same middleware chain and
    execution context class as queries and mutations."""

    def test_subscription_events_run_through_middleware(self):
        def doubler(next_, root, info, **args):
            value = next_(root, info, **args)
            return value * 2 if isinstance(value, int) else value

        server = GraphQLHTTP(schema=build_schema(), middleware=[doubler])
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 1) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        events = parse_sse_events(response.text)
        assert [json.loads(d) for e, d in events if e == "next"] == [
            {"data": {"countdown": 2}},
            {"data": {"countdown": 0}},
        ]

    def test_middleware_applies_to_queries_and_subscriptions_alike(self):
        seen = []

        def observe(next_, root, info, **args):
            seen.append(info.field_name)
            return next_(root, info, **args)

        server = GraphQLHTTP(schema=build_schema(), middleware=[observe])
        client = server.client()

        client.post("/graphql", json={"query": "{ hello }"})
        client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 0) }"},
            headers=SSE_HEADERS,
        )

        assert seen == ["hello", "countdown"]

    def test_subscription_events_use_execution_context_class(self):
        from graphql.execution.execute import ExecutionContext

        class CountingContext(ExecutionContext):
            built = 0

            @classmethod
            def build(cls, *args, **kwargs):
                CountingContext.built += 1
                return super().build(*args, **kwargs)

        server = GraphQLHTTP(
            schema=build_schema(),
            execution_context_class=CountingContext,
        )
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 2) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        # One build per streamed event (3 events for start: 2).
        assert CountingContext.built == 3


class TestSSEStreamLimits:
    """Concurrent subscription streams are capped by sse_max_streams."""

    def test_max_streams_default(self):
        server = GraphQLHTTP(schema=build_schema())
        assert server.sse_max_streams == 100

    @pytest.mark.parametrize("limit", [0, -1])
    def test_max_streams_must_be_positive(self, limit):
        with pytest.raises(ValueError, match="sse_max_streams"):
            GraphQLHTTP(schema=build_schema(), sse_max_streams=limit)

    def test_subscription_rejected_when_at_capacity(self):
        server = GraphQLHTTP(schema=build_schema(), sse_max_streams=1)
        client = server.client()

        server._sse_open_streams = 1  # simulate one open stream
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 0) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 429
        assert response.headers["content-type"].startswith(
            "application/json")
        assert "concurrent" in response.json()["errors"][0]["message"]

    def test_slot_released_after_stream_completes(self):
        server = GraphQLHTTP(schema=build_schema(), sse_max_streams=1)
        client = server.client()

        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 1) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert server._sse_open_streams == 0

        # The freed slot is usable again.
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 0) }"},
            headers=SSE_HEADERS,
        )
        assert response.status_code == 200

    def test_queries_over_sse_are_not_capped(self):
        """Only long-lived subscription streams consume slots; buffered
        query/mutation SSE responses do not."""
        server = GraphQLHTTP(schema=build_schema(), sse_max_streams=1)
        client = server.client()

        server._sse_open_streams = 1
        response = client.post(
            "/graphql", json={"query": "{ hello }"}, headers=SSE_HEADERS)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")

    def test_unlimited_when_none(self):
        server = GraphQLHTTP(schema=build_schema(), sse_max_streams=None)
        client = server.client()

        server._sse_open_streams = 10_000
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 0) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200


class TestSSEAuthentication:
    """SSE requests go through the same auth enforcement as regular POSTs."""

    @pytest.fixture
    def auth_server(self):
        return GraphQLHTTP(
            schema=build_schema(),
            auth_enabled=True,
            auth_jwks_uri="https://example.com/.well-known/jwks.json",
            auth_issuer="https://example.com/",
            auth_audience="test-audience",
        )

    @pytest.fixture
    def client(self, auth_server):
        return auth_server.client()

    def test_unauthenticated_subscription_rejected(self, client):
        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 401
        assert response.headers["content-type"].startswith(
            "application/json")
        result = response.json()
        assert "errors" in result
        assert "Authorization header is missing" in result[
            "errors"][0]["message"]

    def test_introspection_bypass_does_not_cover_subscriptions(self, client):
        """A subscription document must never classify as introspection,
        even when it only selects dunder fields."""
        for query in (
            "subscription { countdown }",
            "subscription Named { countdown }",
            "subscription { __typename }",
        ):
            response = client.post(
                "/graphql", json={"query": query}, headers=SSE_HEADERS)
            assert response.status_code == 401, query

    def test_introspection_bypass_still_works_for_queries(self, client):
        response = client.post(
            "/graphql", json={"query": "{ __typename }"})

        assert response.status_code == 200
        assert response.json() == {"data": {"__typename": "Query"}}

    def test_is_introspection_only_rejects_subscription_documents(self):
        from graphql_http.introspection import is_introspection_only

        assert is_introspection_only({"query": "{ __typename }"}) is True
        assert is_introspection_only(
            {"query": "subscription { countdown }"}) is False
        assert is_introspection_only(
            {"query": "subscription Named { __typename }"}) is False

    def test_string_fallback_rejects_named_operations(self):
        from graphql_http.introspection import _check_introspection_string

        assert _check_introspection_string("{ __typename }") is True
        assert _check_introspection_string(
            "subscription Named { __typename }") is False
        assert _check_introspection_string(
            "mutation Named { __typename }") is False


class TestSSEDisconnectCleanup:
    """A client disconnect must promptly close the source generator,
    including async cleanup in its ``finally`` block."""

    def build_server(self, state, cleanup_sleep=0.0):
        async def subscribe_forever(root, info):
            try:
                counter = 0
                while True:
                    yield counter
                    counter += 1
                    await asyncio.sleep(0.01)
            finally:
                state["finally_entered"] = True
                if cleanup_sleep:
                    # Async cleanup, e.g. `await pubsub.unsubscribe()`.
                    await asyncio.sleep(cleanup_sleep)
                state["closed"] = True

        schema = GraphQLSchema(
            query=GraphQLObjectType(
                "Query",
                {"hello": GraphQLField(
                    GraphQLString, resolve=lambda *_: "world")},
            ),
            subscription=GraphQLObjectType(
                "Subscription",
                {
                    "counter": GraphQLField(
                        GraphQLInt,
                        subscribe=subscribe_forever,
                        resolve=lambda event, info: event,
                    )
                },
            ),
        )
        return GraphQLHTTP(schema=schema)

    @staticmethod
    def make_scope(body, spec_version="2.0"):
        return {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": spec_version},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/graphql",
            "raw_path": b"/graphql",
            "root_path": "",
            "query_string": b"",
            "headers": [
                (b"host", b"testserver"),
                (b"accept", b"text/event-stream"),
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

    @pytest.mark.asyncio
    async def test_disconnect_closes_source_generator(self):
        state = {"closed": False}
        server = self.build_server(state)

        body = json.dumps({"query": "subscription { counter }"}).encode()
        scope = self.make_scope(body)

        request_messages = [
            {"type": "http.request", "body": body, "more_body": False}
        ]
        disconnected = asyncio.Event()
        chunks = []

        async def receive():
            if request_messages:
                return request_messages.pop(0)
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            if message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

        task = asyncio.create_task(server.app(scope, receive, send))

        # Wait for the stream to start producing events
        for _ in range(200):
            if any(b"event: next" in chunk for chunk in chunks):
                break
            await asyncio.sleep(0.01)
        else:
            task.cancel()
            pytest.fail("subscription stream never produced an event")

        assert state["closed"] is False

        # Simulate the client dropping the connection
        disconnected.set()
        await asyncio.wait_for(task, timeout=2)

        # Allow pending cancellation callbacks to settle
        for _ in range(20):
            if state["closed"]:
                break
            await asyncio.sleep(0.01)

        assert state["closed"] is True
        assert server._sse_open_streams == 0

    @pytest.mark.asyncio
    async def test_disconnect_mid_send_does_not_interrupt_async_cleanup(self):
        """A disconnect landing while send() is in flight (stalled client)
        must not cancel awaits inside the source generator's finally —
        Starlette's disconnect cancel scope re-delivers CancelledError at
        every checkpoint unless teardown is shielded."""
        state = {"finally_entered": False, "closed": False}
        server = self.build_server(state, cleanup_sleep=0.05)

        body = json.dumps({"query": "subscription { counter }"}).encode()
        # uvicorn advertises spec_version 2.3
        scope = self.make_scope(body, spec_version="2.3")

        request_messages = [
            {"type": "http.request", "body": body, "more_body": False}
        ]
        disconnected = asyncio.Event()
        send_stalled = asyncio.Event()
        next_events_seen = 0

        async def receive():
            if request_messages:
                return request_messages.pop(0)
            await disconnected.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            nonlocal next_events_seen
            if message["type"] == "http.response.body":
                if b"event: next" in message.get("body", b""):
                    next_events_seen += 1
                    if next_events_seen >= 2:
                        # Simulate a stalled client: send never completes.
                        send_stalled.set()
                        await asyncio.Event().wait()

        task = asyncio.create_task(server.app(scope, receive, send))
        await asyncio.wait_for(send_stalled.wait(), timeout=5)

        # Client drops while the server is blocked in send()
        disconnected.set()
        await asyncio.wait_for(task, timeout=5)

        for _ in range(40):
            if state["closed"]:
                break
            await asyncio.sleep(0.01)

        assert state["finally_entered"] is True
        assert state["closed"] is True
        assert server._sse_open_streams == 0


@pytest.mark.skipif(
    not is_graphql_api_installed(), reason="GraphQL-API is not installed"
)
class TestGraphQLAPISSESubscriptions:
    """End-to-end SSE subscriptions through GraphQLHTTP.from_api."""

    def build_server(self):
        from graphql_api import GraphQLAPI

        api = GraphQLAPI()

        @api.type(is_root_type=True)
        class Root:
            @api.field
            def hello(self) -> str:
                return "world"

            @api.field
            async def countdown(
                self, start: int = 2
            ) -> AsyncGenerator[int, None]:
                for i in range(start, -1, -1):
                    yield i

        return GraphQLHTTP.from_api(api)

    def test_subscription_end_to_end(self):
        client = self.build_server().client()

        response = client.post(
            "/graphql",
            json={"query": "subscription { countdown(start: 3) }"},
            headers=SSE_HEADERS,
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith(
            "text/event-stream")
        events = parse_sse_events(response.text)
        assert [(e, json.loads(d)) for e, d in events[:-1]] == [
            ("next", {"data": {"countdown": i}}) for i in (3, 2, 1, 0)
        ]
        assert events[-1] == ("complete", "")

    def test_query_still_served_as_json(self):
        client = self.build_server().client()

        response = client.post("/graphql", json={"query": "{ hello }"})

        assert response.status_code == 200
        assert response.json() == {"data": {"hello": "world"}}

    def test_subscription_without_sse_accept_rejected(self):
        client = self.build_server().client()

        response = client.post(
            "/graphql", json={"query": "subscription { countdown }"})

        assert response.status_code == 406
        assert "text/event-stream" in response.json()[
            "errors"][0]["message"]
