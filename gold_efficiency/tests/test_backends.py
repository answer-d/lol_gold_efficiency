# -*- encoding: utf-8 -*-

import os
from django.test import TestCase
from ..backends.riot_static_data import RiotStaticData


ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_ITEMS_FILE = "test_items.json"


class RiotStaticDataTest(TestCase):

    """
    テストメソッドという名のデバッグ用メソッド
    （Modelsのimportでエラー吐くから普通にデバッグがめんどい）
    """
    def test_description_parser(self):
        rsd = RiotStaticData(None)
        file_path = os.path.join(ROOT, TEST_ITEMS_FILE)
        items = rsd.load_from_json(file_path)

        for id in items["data"].keys():
            item = items["data"][id]

            if "description" in item:
                parsed_effects = rsd._parse_description(item["description"])
                parsed_effects = [
                    rsd._insert_effect_amount(effect, item)
                    for effect in parsed_effects
                ]
