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

from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import aiohttp
import uuid

from pymine.net.packets.login.set_comp import LoginSetCompression
from pymine.types.stream import EncryptedStream, Stream
import pymine.net.packets.login.login as login_packets
from pymine.api.errors import StopHandling
import pymine.util.encryption as encryption
from pymine.types.packet import Packet
from pymine.types.buffer import Buffer
from pymine.logic.join import join
from pymine.server import server


@server.api.register.on_packet("login", 0x00)
async def login_start(stream: Stream, packet: Packet) -> None:
    if server.conf["online_mode"]:  # Online mode is enabled, so we request encryption
        lc = server.cache.login[stream.remote] = {"username": packet.username, "verify": None}

        packet = login_packets.LoginEncryptionRequest(
            server.secrets.rsa_public.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        lc["verify"] = packet.verify_token

        await server.send_packet(stream, packet, -1)
    else:  # No need for encryption since online mode is off, just send login success
        if server.comp_thresh > 0:  # Send set compression packet if needed
            await server.send_packet(stream, LoginSetCompression(server.comp_thresh), -1)

        # This should be only generated if the player name isn't found in the world data, but no way to do that rn
        uuid_ = uuid.uuid4()

        await server.send_packet(stream, login_packets.LoginSuccess(uuid_, packet.username))

        server.cache.states[stream.remote] = 3  # Update state to play
        await join(stream, uuid_, packet.username, [])


@server.api.register.on_packet("login", 0x01)
async def encrypted_login(stream: Stream, packet: Packet) -> Stream:
    shared_key, auth, props = await server_auth(
        packet, stream.remote, server.cache.login[stream.remote]
    )

    del server.cache.login[stream.remote]  # No longer needed

    if not auth:  # If authentication failed, disconnect client
        await server.send_packet(
            stream, login_packets.LoginDisconnect("Failed to authenticate your connection.")
        )
        raise StopHandling

    # Generate a cipher for that client using the shared key from the client
    cipher = encryption.gen_aes_cipher(shared_key)

    # Replace stream with one which auto decrypts + encrypts data when reading/writing
    stream = EncryptedStream(stream, cipher)

    if server.comp_thresh > 0:  # Send set compression packet if needed
        await server.send_packet(stream, LoginSetCompression(server.comp_thresh), -1)

    # Send LoginSuccess packet, tells client they've logged in succesfully
    await server.send_packet(stream, login_packets.LoginSuccess(*auth))

    server.cache.states[stream.remote] = 3  # Update state to play
    await join(stream, *auth, props)

    return stream


# Verifies that the shared key and token are the same, and does other authentication methods
# Returns the decrypted shared key and the client's username and uuid
async def server_auth(
    packet: login_packets.LoginEncryptionResponse, remote: tuple, cache: dict
) -> tuple:
    if server.secrets.rsa_private.decrypt(packet.verify_token, PKCS1v15()) == cache["verify"]:
        decrypted_shared_key = server.secrets.rsa_private.decrypt(packet.shared_key, PKCS1v15())

        resp = await server.aiohttp.get(
            "https://sessionserver.mojang.com/session/minecraft/hasJoined",
            params={
                "username": cache["username"],
                "serverId": encryption.gen_verify_hash(
                    decrypted_shared_key,
                    server.secrets.rsa_public.public_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ),
                ),
            },
        )

        jj = await resp.json()

        if jj is not None:
            return decrypted_shared_key, (uuid.UUID(jj["id"]), jj["name"]), jj["properties"]

    return False, False, None
