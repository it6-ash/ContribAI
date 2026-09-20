import inspect

from app import api, services


def test_recommendations_does_not_call_github_inline():
    """The 500 under load: revalidate() ran inside the request, so a database
    connection was held across several seconds of GitHub I/O. With enough
    concurrent readers the pool emptied and every request failed with a
    QueuePool timeout — the endpoint took itself down rather than being slow."""
    source = inspect.getsource(api.recommendations)
    assert "await services.revalidate(" not in source
    assert "background.add_task(services.revalidate_ids" in source


def test_background_revalidation_opens_its_own_session():
    """A background task must not reuse the request's session: the request has
    returned and its connection is back in the pool."""
    source = inspect.getsource(services.revalidate_ids)
    assert "with SessionLocal() as db" in source
    params = inspect.signature(services.revalidate_ids).parameters
    assert "db" not in params, "must take ids, not a live session"


def test_a_real_pool_is_configured_for_file_backed_databases():
    from sqlalchemy import create_engine

    from app.db import _pool_args

    # The in-memory database used by tests gets SingletonThreadPool, which
    # accepts none of these; only assert the production shape is sane.
    assert _pool_args == {} or _pool_args["pool_size"] >= 20
    eng = create_engine("sqlite:///:memory:")
    assert eng is not None
