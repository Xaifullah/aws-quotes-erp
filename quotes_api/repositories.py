import os

from quotes_api.interfaces import PipelineStatusRepository, QuoteRepository

# DATA_BACKEND=postgres (phase 6 default) or s3 (legacy rollback path). Imports are
# lazy so an S3-only deployment doesn't need pg8000 and vice versa.
DATA_BACKEND = os.environ.get("DATA_BACKEND", "postgres").lower()


def build_quote_repository() -> QuoteRepository:
    if DATA_BACKEND == "s3":
        from quotes_api.s3_quote_repository import S3QuoteRepository

        return S3QuoteRepository(bucket=os.environ["QUOTES_BUCKET"])

    from db.connection import run_with_reconnect
    from quotes_api.postgres_quote_repository import PostgresQuoteRepository

    return PostgresQuoteRepository(run_query=run_with_reconnect)


def build_status_repository() -> PipelineStatusRepository:
    if DATA_BACKEND == "s3":
        from quotes_api.s3_pipeline_status_repository import S3PipelineStatusRepository

        return S3PipelineStatusRepository(bucket=os.environ["QUOTES_BUCKET"])

    from db.connection import run_with_reconnect
    from quotes_api.postgres_pipeline_status_repository import PostgresPipelineStatusRepository

    return PostgresPipelineStatusRepository(run_query=run_with_reconnect)
