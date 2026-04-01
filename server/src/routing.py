from src.kit.routing import (
    AutoCommitAPIRoute,
    IncludedInSchemaAPIRoute,
    get_api_router_class,
)


class APIRoute(AutoCommitAPIRoute, IncludedInSchemaAPIRoute):
    pass


APIRouter = get_api_router_class(APIRoute)

__all__ = ["APIRouter"]
