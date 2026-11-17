"""Typed FastAPI response metadata shared by route families."""

from dataclasses import dataclass
from types import UnionType

from pydantic import BaseModel
from typing_extensions import TypedDict

from app.shared.types.base_types import JsonObject

type ResponseModel = type[BaseModel] | UnionType


class ModelResponseMetadata(TypedDict, total=True, closed=True):
    """FastAPI response metadata carrying one schema model or model union."""

    model: ResponseModel


class ContentResponseMetadata(TypedDict, total=True, closed=True):
    """FastAPI response metadata carrying a custom documented content schema."""

    description: str
    content: JsonObject


type ResponseMetadataValue = ResponseModel | str | JsonObject
type ResponseModels = dict[int | str, dict[str, ResponseMetadataValue]]
type ResponseDefinition = ResponseModelDefinition | ContentResponseDefinition


@dataclass(frozen=True, slots=True, kw_only=True)
class ResponseModelDefinition:
    """One documented HTTP response status and its Pydantic model."""

    status_code: int | str
    model: ResponseModel

    def to_dict(self) -> ModelResponseMetadata:
        """Build FastAPI's typed model metadata shape.

        Args:
            None.
        Return:
            Closed FastAPI model response metadata.
        """
        result = ModelResponseMetadata(model=self.model)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ContentResponseDefinition:
    """One documented HTTP response status with explicit OpenAPI content."""

    status_code: int | str
    description: str
    content: JsonObject

    def to_dict(self) -> ContentResponseMetadata:
        """Build FastAPI's typed custom-content metadata shape.

        Args:
            None.
        Return:
            Closed FastAPI description and content metadata.
        """
        result = ContentResponseMetadata(
            description=self.description,
            content=self.content,
        )
        return result


def build_response_models(
    definitions: tuple[ResponseDefinition, ...],
) -> ResponseModels:
    """Build a FastAPI response map from closed typed response definitions.

    Args:
        definitions: Distinct status definitions for one route family.
    Return:
        Status-keyed FastAPI response metadata.
    """
    result: ResponseModels = {}
    for definition in definitions:
        metadata = dict(definition.to_dict())
        result[definition.status_code] = metadata
    return result
