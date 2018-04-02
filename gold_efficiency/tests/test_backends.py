# -*- encoding: utf-8 -*-

import os
from django.test import TestCase
from ..backends import RiotStaticData


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
                stats, effect, unique_stats, unique_effects, other =\
                    rsd._parse_description(item["description"])
                print(other)
