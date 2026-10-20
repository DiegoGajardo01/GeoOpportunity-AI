import json
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from geoopportunity.config import Settings, get_settings
from geoopportunity.inference.contracts import ModelInfo


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        })


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger('geoopportunity')
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title='GeoOpportunity AI', description='Territorial analysis and separate commercial sales ML')

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger('geoopportunity').exception('unhandled_request_error')
        return JSONResponse(status_code=500, content={'detail': 'Internal server error'})

    @app.get('/health')
    def health() -> dict[str, str]:
        return {'status': 'ok'}

    @app.get('/model/info', response_model=ModelInfo)
    def model_info() -> ModelInfo:
        return ModelInfo()

    return app


app = create_app()
