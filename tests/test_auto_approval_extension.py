# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Vladimir Timofeenko <vladimir@vtimofeenko.com>
# All rights reserved.
#
import pytest

from auto_approve_connect_ext.extension import AutoApprovalExtensionExtension


@pytest.mark.asyncio
async def test_process_asset_purchase_request(
    async_client_factory,
    response_factory,
    logger,
):
    config = {}
    request = {"id": 1}
    responses = [
        response_factory(count=100),
        response_factory(value=[{"id": "item-1", "value": "value1"}]),
    ]
    client = await async_client_factory(responses)
    ext = AutoApprovalExtensionExtension(client, logger, config)
    result = await ext.process_asset_purchase_request(request)
    assert result.status == "success"
