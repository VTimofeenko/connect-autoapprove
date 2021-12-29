# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, Vladimir Timofeenko <vladimir@vtimofeenko.com>
# All rights reserved.
#
from random import choice
from typing import List, Callable
from operator import itemgetter
from faker import Faker

from connect.eaas.extension import Extension, ProcessingResponse


class AutoApprovalExtensionExtension(Extension):
    def _generate_fake_address(self) -> dict:
        """
        Generates a fake address in a format conforming with Connect schema

        Implementation note: not a staticmethod since there is a call to self.faker
        """
        fake = self.faker
        return {
            "address_line1": fake.street_address(),
            "address_line2": "",
            "city": fake.city(),
            "country": fake.country_code(),
            "postal_code": fake.postalcode(),
            "state": fake.state(),
        }

    def _generate_fake_phone(self) -> dict:
        """
        Generates a fake phone number in a format conforming with Connect schema.

        Implementation note: not a staticmethod since there is a call to self.faker
        """
        fake = self.faker
        return {
            "country_code": "+1",
            "area_code": "949",
            "phone_number": str(fake.random_int(5010000, 5019999)),
        }

    @staticmethod
    def _pick_random_choice(param: dict) -> Callable:
        """
        When called with the parameter that has constraints for choices, will return the function to return a single
        value from a random element in the choices.
        """
        if param["type"] not in {"choice", "dropdown", "subdomain"}:
            raise ValueError(f"Parameter {param['name']} not in allowed types, may be a bug")

        def _f():
            return choice(param["value_choices"])["value"]

        return _f

    @staticmethod
    def _check_random_checkboxes(param: dict) -> Callable:
        """When used with a checkbox parameter, returns list of values with randomly assigned True or False"""
        if param["type"] != "checkbox":
            raise ValueError(f"Parameter {param['name']} not in allowed types, may be a bug")

        def _f():
            return {_choice["value"]: choice((True, False)) for _choice in param["value_choices"]}

        return _f

    def _generate_random_subdomain(self, param: dict) -> Callable:
        """Generates a random subdomain by generating a random word and then picking a random domain from the choices"""
        if param["type"] != "subdomain":
            raise ValueError(f"Parameter {param['name']} not in allowed types, may be a bug")

        def _f():
            return self.faker.word() + "." + self._pick_random_choice(param)()

        return _f

    def __init__(self, *args, **kwargs):
        self.faker = Faker()
        # contains the mapping between parameter type, field ("value" or "structured_value" and
        # a callable that returns the actual value
        self.param_fake_map = {
            "text": ("value", self.faker.uuid4),
            "address": ("structured_value", self._generate_fake_address),
            "checkbox": ("structured_value", self._check_random_checkboxes),
            "choice": ("value", self._pick_random_choice),
            "domain": ("value", self.faker.safe_domain_name),
            "dropdown": ("value", self._pick_random_choice),
            "email": ("value", self.faker.safe_email),
            "object": ("value", lambda: "{}"),  # not sure how to randomize JSON
            "password": ("value", self.faker.uuid4),
            "phone": ("structured_value", self._generate_fake_phone),
            "subdomain": ("value", self._generate_random_subdomain),
            "url": ("value", self.faker.url),
        }
        super().__init__(*args, **kwargs)

    async def _fill_parameter(self, request_id: str, param: dict):
        """
        Special note on 'checkbox', 'choice', "dropdown", "subdomain":

        these parameters have constraints, so the function to pick a random choice has to be 'seeded' with the
        constraints taken from the parameter. This is implemented through partial application
        """
        parameter_id = param["id"]
        self.logger.info(f"Filling in parameter {parameter_id}")
        parameter_type = param["type"]

        value_type, random_function = self.param_fake_map[parameter_type]

        if parameter_type in {"checkbox", "choice", "dropdown", "subdomain"}:
            random_function = random_function(param)

        await self.client.requests[request_id].update(
            payload={"asset": {"params": [{"id": parameter_id, value_type: random_function()}]}}
        )

    async def _get_single_product_fulfillment_template(self, product_id: str) -> str:
        """Check the list of templates, if there are more than one - raise ValueError, otherwise - return the single
        template"""

        async def get_product_fulfillment_templates():
            return list(
                [
                    _["id"]
                    async for _ in self.client.products[product_id]
                    .templates.filter(type="fulfillment")
                    .values_list("id")
                ]
            )

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

        # Get the list of only the fulfillment params from incoming fulfillment request
        fulfillment_params: List = list(filter(lambda _: _["phase"] == "fulfillment", request["asset"]["params"]))

        for param in fulfillment_params:
            await self._fill_parameter(request_id, param)

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
