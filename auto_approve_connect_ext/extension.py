# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Vladimir Timofeenko <vladimir@vtimofeenko.com>
# All rights reserved.
#
from connect.eaas.extension import Extension, ProcessingResponse, CustomEventResponse
from uuid import uuid4

from threading import Thread


class AutoApprovalExtensionExtension(Extension):
    async def _set_license_on_request(self, request_id: str):
        license_key = uuid4()
        self.logger.info(f"Generated license key {license_key} for request {request_id}")
        await self.client.requests[request_id].update(
            payload={"asset": {"params": [{"id": "volume_license", "value": str(license_key)}]}}
        )

    async def process_asset_purchase_request(self, request):
        self.logger.info(f"Obtained request with id {request['id']}")
        # generate a random uuid to server as the license
        request_id = request["id"]
        await self._set_license_on_request(request_id)
        await self.client.requests[request_id]("approve").post({"template_id": "TL-843-435-779"})

        return ProcessingResponse.done()
