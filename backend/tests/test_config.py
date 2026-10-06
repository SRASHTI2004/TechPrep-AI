import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@ep-x.neon.tech/db?sslmode=require",
        "postgres://u:p@ep-x.neon.tech/db?sslmode=require",
        "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require",
    ],
)
def test_database_url_uses_psycopg_driver(url):
    settings = Settings(database_url=url)
    assert settings.database_url == "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"
