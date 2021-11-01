# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Vladimir Timofeenko <vladimir@vtimofeenko.com>
# All rights reserved.
#
from connect.eaas.extension import Extension, ProcessingResponse, CustomEventResponse
from uuid import uuid4
from toolz import compose, pluck

from threading import Thread


class AutoApprovalExtensionExtension(Extension):
    async def _set_license_on_request(self, request_id: str):
        license_key = uuid4()
        self.logger.info(f"Generated license key {license_key} for request {request_id}")
        await self.client.requests[request_id].update(
            payload={"asset": {"params": [{"id": "volume_license", "value": str(license_key)}]}}
        )

    async def process_all_old_requests(self):
        """Kept as a reference only"""
        requests = self.client.requests
        for request_id in pluck(
            "id",
            requests.filter(asset__product__id="PRD-620-226-877")
            .filter(type="purchase")
            .filter(status="pending")
            .all(),
        ):
            self.logger.info(f"Found old stale request {request_id}, processing it")
            await self._set_license_on_request(request_id)

    async def process_asset_purchase_request(self, request):
        self.logger.info(f"Obtained request with id {request['id']}")
        # generate a random uuid to server as the license
        request_id = request["id"]
        await self._set_license_on_request(request_id)
        await self.client.requests[request_id]("approve").post({"template_id": "TL-843-435-779"})

        return ProcessingResponse.done()
