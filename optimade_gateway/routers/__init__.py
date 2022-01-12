"""Routers for the OPTIMADE Gateway."""
import importlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Any, Generator, List, Set

    from fastapi import APIRouter


class Routers:
    """A class that can retrieve all routers.

    The class also implements a method to return the routers of each submodule lazily.
    """

    NON_ROUTER_SUBMODULES = ("utils", "__init__", "callback")

    _submodules: "Set[str]" = set()

    def __setattr__(self, name: str, value: "Any") -> None:
        """Do not allow users to set attributes."""
        raise AttributeError("Setting attributes on a Routers object is not allowed.")

    @staticmethod
    def _get_submodule(name: str) -> "ModuleType":
        """Retrieve and import a `routers` submodule."""
        return importlib.import_module(f"optimade_gateway.routers.{name}")

    def available_submodules(self) -> "List[str]":
        """Return list of available `routers` submodule names."""
        if self._submodules:
            return sorted(self._submodules)

        self_dir = Path(__file__).resolve().parent
        for filename in self_dir.glob("*.py"):
            if filename.is_dir():
                continue
            if filename.stem in self.NON_ROUTER_SUBMODULES:
                continue
            self._submodules.add(filename.stem)

        return sorted(self._submodules)

    def routers(self) -> "Generator[APIRouter, None, None]":
        """Return FastAPI `APIRouters`."""
        for name in self.available_submodules():
            submodule = self._get_submodule(name)
            if hasattr(submodule, "ROUTER"):
                yield getattr(submodule, "ROUTER")
            else:
                raise AttributeError(
                    f"No FastAPI APIRouter found in the {name} submodule."
                )


ROUTERS = Routers()
