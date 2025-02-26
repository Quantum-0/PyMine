# A flexible and fast Minecraft server software written completely in Python.
# Copyright (C) 2021 PyMine

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import sys
import os

from pymine.util.immutable import make_immutable
from pymine.types.registry import Registry

__all__ = ("BLOCK_STATES",)


def reversed_bs_data(bs_data):
    reverse_data = {}

    for k, block in bs_data.items():
        for sv in block["states"]:
            reverse_data[sv["id"]] = {"name": k, "properties": sv.get("properties", {})}

    return make_immutable(reverse_data)


if "sphinx" in sys.modules:
    os.chdir(os.path.join(os.path.dirname(__file__), "../.."))

with open(os.path.join("pymine", "data", "blocks.json"), "r") as block_data:
    bs_data = make_immutable(json.load(block_data))

BLOCK_STATES = Registry(bs_data, reversed_bs_data(bs_data))
