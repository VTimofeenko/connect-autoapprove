# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Vladimir Timofeenko <vladimir@vtimofeenko.com>
# All rights reserved.
#
from uuid import uuid4

from connect.eaas.extension import Extension, ProcessingResponse, CustomEventResponse


class AutoApprovalExtensionExtension(Extension):
    async def _set_license_on_request(self, request_id: str):
        license_key = uuid4()
        self.logger.info(f"Generated license key {license_key} for request {request_id}")
        await self.client.requests[request_id].update(
            payload={"asset": {"params": [{"id": "volume_license", "value": str(license_key)}]}}
        )

    async def _get_single_product_fulfillment_template(self, product_id: str) -> str:
        """Check the list of templates, if there are more than one - raise ValueError, otherwise - return the single
        template"""

        async def get_product_fulfillment_templates():
            # see connect-python-openapi-client/issues/27
            templates = []
            async for template in self.client.products[product_id].templates.all():
                if template.get("type") == "fulfillment":
                    templates.append(template["id"])
            return templates

        templates = await get_product_fulfillment_templates()

        if len(templates) == 1:
            return templates[0]
        elif len(templates) == 1:
            raise ValueError("No fulfillment templates found in the product, please create one")
        else:
            raise ValueError(f"Got multiple templates, will not try to guess which one to use: {templates}")

    async def process_asset_purchase_request(self, request):
        self.logger.info(f"Obtained request with id {request['id']}")
        # generate a random uuid to server as the license
        request_id = request["id"]
        product_id = request["asset"]["product"]["id"]
        self.logger.info(f"My product id is {product_id}")

        await self._set_license_on_request(request_id)

        template_id = await self._get_single_product_fulfillment_template(product_id)

        await self.client.requests[request_id]("approve").post({"template_id": template_id})
        return ProcessingResponse.done()

    async def process_asset_cancel_request(self, request):
        """Cancels the request."""
        self.logger.info(f"Obtained cancellation request with id {request['id']}")
        request_id = request["id"]
        product_id = request["asset"]["product"]["id"]

        # Connect needs a template for canceling as well
        template_id = await self._get_single_product_fulfillment_template(product_id)

        await self.client.requests[request_id]("approve").post({"template_id": template_id})

        return ProcessingResponse.done()

    async def process_asset_change_request(self, request):
        """Cancels the request."""
        self.logger.info(f"Obtained change request with id {request['id']}")
        request_id = request["id"]
        product_id = request["asset"]["product"]["id"]

        # Connect needs a template for canceling as well
        template_id = await self._get_single_product_fulfillment_template(product_id)

        await self.client.requests[request_id]("approve").post({"template_id": template_id})

        return ProcessingResponse.done()
