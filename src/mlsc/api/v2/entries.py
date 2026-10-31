from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field, RootModel

from mlsc.api.v2.errors import READ_ERRORS, WRITE_ERRORS, Problem, Usage
from mlsc.api.v2.lookup import require_patch
from mlsc.api.v2.security import api_login_required
from mlsc.color_registry import COLOUR, GRADIENT
from mlsc.webserver.executer import Executer

REFRESH_ERRORS = {"500": Problem}
CONFLICT_ERRORS = {"409": Problem}


class EntryPath(BaseModel):
    name: str = Field(description="Name of the entry, URL-encoded. Matched case-insensitively.")


class UsageListOut(RootModel[list[Usage]]):
    pass


class ColourCreate(BaseModel):
    name: str = Field(description="1-32 letters, digits, spaces, `-` or `_`; unique among the colours regardless of case.")
    rgb: list[int] = Field(description="`[r, g, b]`, each 0-255.")


class ColourUpdate(BaseModel):
    name: str | None = Field(default=None, description="Renames the entry and every usage of it.")
    rgb: list[int] | None = None


class ColourOut(BaseModel):
    name: str
    rgb: list[int]
    predefined: bool = Field(description="Predefined entries are read-only; duplicate one to edit a copy.")


class ColourListOut(RootModel[list[ColourOut]]):
    pass


class GradientCreate(BaseModel):
    name: str = Field(description="1-32 letters, digits, spaces, `-` or `_`; unique among the gradients regardless of case.")
    stops: list[list[int]] = Field(description="2-16 stops, each `[r, g, b]` with 0-255 per channel.")


class GradientUpdate(BaseModel):
    name: str | None = Field(default=None, description="Renames the entry and every usage of it.")
    stops: list[list[int]] | None = None


class GradientOut(BaseModel):
    name: str
    stops: list[list[int]]
    predefined: bool = Field(description="Predefined entries are read-only; duplicate one to edit a copy.")


class GradientListOut(RootModel[list[GradientOut]]):
    pass


def _blueprint(kind, plural, field, create_model, update_model, out_model, list_model):
    """Build the blueprint of the colours or the gradients; both collections behave the same."""
    tag = Tag(name=plural.capitalize(), description=f"The named {plural} that effects can use")
    api = APIBlueprint(f"{plural}_api_v2", __name__, url_prefix=f"/api/v2/{plural}", abp_tags=[tag])
    def entries():
        return Executer.instance.entry_executer

    @api.get("", summary=f"List the {plural}", responses={"200": list_model, "401": Problem})
    @api_login_required
    def list_entries():
        return entries().list_entries(kind)

    @api.post("", summary=f"Create a {kind}", responses={"201": out_model, **WRITE_ERRORS, **CONFLICT_ERRORS, **REFRESH_ERRORS})
    @api_login_required
    def create_entry(body: create_model):
        return entries().create_entry(kind, body.name, getattr(body, field)), 201

    @api.get("/<name>", summary=f"Get a {kind}", responses={"200": out_model, **READ_ERRORS})
    @api_login_required
    def get_entry(path: EntryPath):
        return entries().get_entry(kind, path.name)

    @api.patch("/<name>", summary=f"Edit or rename a {kind}", responses={"200": out_model, **WRITE_ERRORS, **CONFLICT_ERRORS, **REFRESH_ERRORS})
    @api_login_required
    def update_entry(path: EntryPath, body: update_model):
        """Rewrite every usage on a rename, which restarts the devices that use the entry. Predefined entries answer `PredefinedEntryReadOnly`."""
        patch = require_patch(body.model_dump(exclude_unset=True))
        return entries().update_entry(kind, path.name, patch.get("name"), patch.get(field))

    @api.delete("/<name>", summary=f"Delete a {kind}", responses={"204": None, **READ_ERRORS, **CONFLICT_ERRORS})
    @api_login_required
    def delete_entry(path: EntryPath):
        """Blocked with `EntryInUse` (its `usages` member lists where) while an effect setting still uses the entry."""
        entries().delete_entry(kind, path.name)
        return "", 204

    @api.post("/<name>/duplicate", summary=f"Copy a {kind}", responses={"201": out_model, **READ_ERRORS, "415": Problem, **REFRESH_ERRORS})
    @api_login_required
    def duplicate_entry(path: EntryPath):
        """Name the copy `<name> (copy)`, `<name> (copy 2)` and so on, shortened to 32 characters."""
        return entries().duplicate_entry(kind, path.name), 201

    @api.get("/<name>/usages", summary=f"List where a {kind} is used", responses={"200": UsageListOut, **READ_ERRORS})
    @api_login_required
    def list_usages(path: EntryPath):
        return entries().get_usages(kind, path.name)

    return api


colors_api = _blueprint(COLOUR, "colors", "rgb", ColourCreate, ColourUpdate, ColourOut, ColourListOut)
gradients_api = _blueprint(GRADIENT, "gradients", "stops", GradientCreate, GradientUpdate, GradientOut, GradientListOut)
