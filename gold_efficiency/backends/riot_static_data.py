# -*- encoding: utf-8 -*-

import sys
import re
import json
import logging
import lxml.html
import lxml.etree
from riotwatcher import RiotWatcher
from ..models import PatchVersion, Item, StatsBase, Effect, Tag
from .constant_values import *


class RiotStaticData(object):

    """
    コンストラクタ
    """
    def __init__(self, api_key=None, region="jp1", locale="ja_JP"):
        self.api_key = api_key
        self.region = region
        self.locale = locale

        # ロガー（今は使ってない）
        # ファイルハンドラのログはmanage.pyと同階層に生成される
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        # handler = logging.FileHandler(filename="backends.log", encoding="utf-8", mode="w")
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        self.logger.addHandler(handler)

    """
    StatsBaseを計算して、指定されたバージョンとしてDBに登録する
    """
    def update_stats_base(self, items, version):
        version = PatchVersion.objects.get(version_str=version)

        # 金銭効率ベースになるアイテムをtier順に処理
        for base_items in BASE_ITEMS_LIST:
            for key, value in base_items.items():
                if StatsBase.objects.filter(patch_version=version, name=key).exists():
                    continue

                item = items['data'][value]

                # サモリフ以外除外
                if item["maps"][MAPID_SUMMONERS_RIFT] is False:
                    continue

                # アイテムデータの取得
                item_data = self._parse_item(item, version)
                stats, effects, unique_stats, unique_effects, other =\
                    self._parse_description(item["description"])

                # 金銭効率ベース計算
                # 1. アイテムのトータル金額を取得して評価額としてセット
                # 2. Statsの中に既に金銭効率が決まっているものがあれば金銭価値算出して評価額から引く
                # 3. 2を繰り返し、Statsが単一になるまでやる
                # 4. 最終的に残った単一のStatsが計算しようとしているStatsのキーと一致する(はず)
                # 5. 得られたStatsのamountで評価額を割った値が金銭効率ベースになる
                all_stats = stats.copy()
                all_stats.update(unique_stats)
                valuation_gold = item_data["total_cost"]

                while 1 < len(all_stats):
                    for stats_name, stats_amount in list(all_stats.items()):
                        existing_stats_base = StatsBase.objects.filter(name=stats_name, patch_version=version)

                        if len(existing_stats_base) == 1:
                            valuation_gold -= existing_stats_base[0].gold_value_per_amount * int(stats_amount)
                            del all_stats[stats_name]

                # キー一致してるかチェック
                # TODO : エラー処理
                if key not in all_stats.keys():
                    print("＼(^o^)／ｵﾜﾀ")
                    break

                # 金銭効率ベースの計算
                gold_value_per_amount = valuation_gold / int(all_stats[key])

                # DB登録
                StatsBase.objects.update_or_create(
                    name=key,
                    gold_value_per_amount=gold_value_per_amount,
                    patch_version=version
                )

    """
    itemsのjsonデータを指定されたバージョンとしてDBに登録する
    """
    def update_items(self, items, version):
        version = PatchVersion.objects.get(version_str=version)

        # StatsBaseが登録されてなかったら先に登録する
        if not StatsBase.objects.filter(patch_version=version).exists():
            self.update_stats_base(items, version)

        n_item = len(items["data"])
        for i, id in enumerate(items["data"].keys()):
            sys.stdout.write("\r{} / {}".format(i + 1, n_item))
            item = items["data"][id]

            # サモリフ以外除外
            if item["maps"][MAPID_SUMMONERS_RIFT] is False:
                continue

            # アイテム登録
            if not Item.objects.filter(patch_version=version, riot_item_id=id).exists():
                item_data = self._parse_item(item, version)
                item_record, _ = Item.objects.update_or_create(**item_data)

                # タグ登録
                if "tags" in item:
                    for tag in item["tags"]:
                        Tag.objects.update_or_create(
                            name=tag,
                        )
                        item_record.tags.add(Tag.objects.get(name=tag))

                # スタッツ/エフェクト登録
                if "description" in item:
                    # パース
                    stats, effects, unique_stats, unique_effects, other =\
                        self._parse_description(item["description"])

                    # EffectAmountの挿入
                    effects = self._insert_effect_amount(effects, item)
                    unique_effects = self._insert_effect_amount(
                        unique_effects,
                        item
                    )
                    other = self._insert_effect_amount(other, item)

                    # 登録
                    for name, amount in stats.items():
                        Effect.objects.update_or_create(
                            description=str(amount)+name,
                            is_unique=False,
                            formula="{} * [{}]".format(str(amount), name),
                            calc_priority=1,
                            is_updated_in_current_patch=False,
                            is_checked_evaluation=True,
                            item=item_record,
                        )
                    for effect in effects:
                        Effect.objects.update_or_create(
                            description=effect,
                            is_unique=False,
                            calc_priority=1,
                            is_updated_in_current_patch=False,
                            is_checked_evaluation=False,
                            item=item_record,
                        )
                    for name, amount in unique_stats.items():
                        Effect.objects.update_or_create(
                            description=str(amount) + name,
                            is_unique=True,
                            formula="{} * [{}]".format(str(amount), name),
                            calc_priority=1,
                            is_updated_in_current_patch=False,
                            is_checked_evaluation=True,
                            item=item_record,
                        )
                    for effect in unique_effects:
                        Effect.objects.update_or_create(
                            description=effect,
                            is_unique=True,
                            calc_priority=1,
                            is_updated_in_current_patch=False,
                            is_checked_evaluation=False,
                            item=item_record,
                        )
                    for effect in other:
                        Effect.objects.update_or_create(
                            description=effect,
                            is_unique=False,
                            calc_priority=1,
                            is_updated_in_current_patch=False,
                            is_checked_evaluation=False,
                            item=item_record,
                        )

    """
    バージョンをDBに登録する
    """
    def update_versions(self, versions):
        if not isinstance(versions, list):
            versions = [versions]

        for version in versions:
            PatchVersion.objects.update_or_create(version_str=version)

    """
    利用可能なバージョンをString Listとして取得する
    """
    def fetch_patch_versions(self):
        watcher = RiotWatcher(self.api_key)
        return watcher.static_data.versions(self.region)

    """
    対象verのitemsを取得する
    """
    def fetch_items(self, version):
        watcher = RiotWatcher(self.api_key)
        return watcher.static_data.items(
            region=self.region,
            locale=self.locale,
            version=version,
            tags="all"
        )

    """
    ローカルファイルから読み込み
    """
    @classmethod
    def load_from_json(self, json_path):
        with open(json_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data


# --- Private Method -----------------------------------------------------------

    """
    itemの基本データをパース
    """
    def _parse_item(self, item, patch_version):
        version_str = str(patch_version)

        item_data = dict(
            name=item["name"],
            riot_item_id=item["id"],
            base_cost=item["gold"]["base"],
            total_cost=item["gold"]["total"],
            is_purchasable=item["gold"]["purchasable"],
            sell_gold=item["gold"]["sell"],
            img=ITEMIMG_BASE_URL.format(version_str, item["id"]),
            patch_version=patch_version,
        )

        # 存在しないキーはNoneに
        for key, value in NOATTR_ITEM_KEYS.items():
            if key in item:
                item_data[value] = item[key]
            else:
                item_data[value] = None

        return item_data

    """
    description内のstatsおよびeffectのパース
    """
    def _parse_description(self, description):
        description = description.replace("<br>", "\n")
        description = re.sub("<.*?>", "", description)
        description = description.split("\n")
        description = [line for line in description if line.strip() != ""]

        stats = dict()
        effects = list()
        unique_stats = dict()
        unique_effects = list()
        other = list()

        for line in description:
            if line.find(": ") >= 0:
                header, effect = line.split(": ", 1)
                effect_type = self._get_effect_type(header)

                if effect_type == EFFECT_TYPES.UNIQUE:
                    if self._is_stats(effect):
                        key, value = self._convert_stats(effect)
                        unique_stats[key] = value
                    else:
                        unique_effects.append(
                            header.strip() + effect.strip()
                        )
                elif effect_type == EFFECT_TYPES.NORMAL:
                    if self._is_stats(effect):
                        key, value = self._convert_stats(effect)
                        stats[key] = value
                    else:
                        effects.append(
                            header.strip() + effect.strip()
                        )
                elif effect_type == EFFECT_TYPES.QUEST:
                    quest = header.strip() + effect.strip()
                elif effect_type == EFFECT_TYPES.REWARD:
                    reward = header.strip() + effect.strip()
                    reward_effect = effect.getnext()
                    reward += reward_header.strip() + reward_effect.strip()
                    break
                else:
                    effects.append(header.strip() + effect.strip())
            else:
                if self._is_stats(line):
                    key, value = self._convert_stats(line)
                    stats[key] = value
                else:
                    other.append(line.strip())

        return stats, effects, unique_stats, unique_effects, other

    """
    取り出したものがstatsかeffectかを判定
    """
    def _is_stats(self, contents):
        contents = contents.strip()
        splitted = contents.split(" ")
        if len(splitted) != 2:
            return False

        key, value = splitted
        if value.find("%") >= 0:
            if key in PERCENT_STATS_KEYS.keys():
                return True
            else:
                return False
        elif key in FLAT_STATS_KEYS.keys():
            return True
        else:
            return False

    def _get_effect_type(self, header):
        if header.find("重複不可") >= 0:
            return EFFECT_TYPES.UNIQUE
        elif (header.find("発動効果") >= 0) or (header.find("自動効果") >= 0):
            return EFFECT_TYPES.NORMAL
        else:
            return EFFECT_TYPES.OTHER

    """
    statsを切り分ける.
    その際データベースに登録可能なキー名に変換する.

    ex.)
    stats, value = "スタッツ value"
    """
    def _convert_stats(self, contents):
        contents = contents.strip()
        contents = contents.replace("+", "")
        key, value = contents.split(" ")

        if value.find("%") >= 0:
            return PERCENT_STATS_KEYS[key], value.replace("%", "")
        else:
            return FLAT_STATS_KEYS[key], value

    """
    item["effect"]内に格納された@Effect*Amount@でeffectの中身を置換する
    """
    def _insert_effect_amount(self, effects, item):
        if not "effect" in item:
            return effects

        for i, effect in enumerate(effects):
            for amount in re.findall(r"@[^@@]*@", effect):
                stripped = amount.strip("@")

                if stripped.find("*") >= 0:
                    key, value = stripped.split("*")
                    effects[i] = effects[i].replace(
                        amount,
                        str(float(item["effect"][key]) * int(value))
                    )
                elif stripped.find("Value") >= 0:
                    lower_value = item["effect"]["Effect1Amount"]
                    upper_value = item["effect"]["Effect2Amount"]
                    effects[i] = effects[i].replace(
                        "@Value@",
                        "{} - {}".format(lower_value, upper_value)
                    )
                else:
                    print(stripped)
                    effects[i] = effects[i].replace(amount, item["effect"][stripped])
        return effects

# --- テスト -------------------------------------------------------------------

    def _get_available_versions(self):
        return ["8.6.1", "8.5.1", "8.4.1"]

    def _save_to_json(self):
        import json

        watcher = RiotWatcher(self.api_key)

        versions = watcher.static_data.versions(region=self.region)
        with open("versions_{}.json".format(self.region), "w") as fp:
            json.dump(versions, fp)

        for version in versions:
            items = watcher.static_data.items(
                region=self.region,
                locale=self.locale,
                version=version,
                tags="all",
            )
            with open("items_ver.{}_{}.json".format(version, self.region), "w") as fp:
                json.dump(items, fp)
