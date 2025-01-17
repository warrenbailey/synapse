# Copyright 2014-2016 OpenMarket Ltd
# Copyright 2020-2021 The Matrix.org Foundation C.I.C.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from typing import TYPE_CHECKING

from synapse.http.server import (
    DirectServeJsonResource,
    set_corp_headers,
    set_cors_headers,
)
from synapse.http.servlet import parse_boolean
from synapse.http.site import SynapseRequest
from synapse.media._base import parse_media_id, respond_404

if TYPE_CHECKING:
    from synapse.media.media_repository import MediaRepository
    from synapse.server import HomeServer

logger = logging.getLogger(__name__)


class DownloadResource(DirectServeJsonResource):
    isLeaf = True

    def __init__(self, hs: "HomeServer", media_repo: "MediaRepository"):
        super().__init__()
        self.media_repo = media_repo
        self._is_mine_server_name = hs.is_mine_server_name

    async def _async_render_GET(self, request: SynapseRequest) -> None:
        set_cors_headers(request)
        set_corp_headers(request)
        request.setHeader(
            b"Content-Security-Policy",
            b"sandbox;"
            b" default-src 'none';"
            b" script-src 'none';"
            b" plugin-types application/pdf;"
            b" style-src 'unsafe-inline';"
            b" media-src 'self';"
            b" object-src 'self';",
        )
        # Limited non-standard form of CSP for IE11
        request.setHeader(b"X-Content-Security-Policy", b"sandbox;")
        request.setHeader(
            b"Referrer-Policy",
            b"no-referrer",
        )
        server_name, media_id, name = parse_media_id(request)
        if self._is_mine_server_name(server_name):
            await self.media_repo.get_local_media(request, media_id, name)
        else:
            allow_remote = parse_boolean(request, "allow_remote", default=True)
            if not allow_remote:
                logger.info(
                    "Rejecting request for remote media %s/%s due to allow_remote",
                    server_name,
                    media_id,
                )
                respond_404(request)
                return

            await self.media_repo.get_remote_media(request, server_name, media_id, name)
