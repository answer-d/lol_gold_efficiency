# -*- encoding: utf-8 -*-

import sys
import re
import json
from copy import copy
from tqdm import tqdm
from riotwatcher import RiotWatcher

from ..models import PatchVersion, Item, StatsBase, Effect, Tag
from .constant_values import *
from .parsed_effect import ParsedEffect


class RiotStaticData(object):

    """
    コンストラクタ
    """
    def __init__(self, api_key=None, region="jp1", locale="ja_JP"):
        self.api_key = api_key
        self.region = region
        self.locale = locale

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
                effects = self._parse_description(item["description"])

                # 金銭効率ベース計算
                # 1. アイテムのトータル金額を取得して評価額としてセット
                # 2. Statsの中に既に金銭効率が決まっているものがあれば金銭価値算出して評価額から引く
                # 3. 2を繰り返し、Statsが単一になるまでやる
                # 4. 最終的に残った単一のStatsが計算しようとしているStatsのキーと一致する(はず)
                # 5. 得られたStatsのamountで評価額を割った値が金銭効率ベースになる
                all_stats = {
                    stats.stats_pair[0]: stats.stats_pair[1]
                    for stats in effects if stats.formula is not None
                }
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

        for id in tqdm(items["data"].keys()):
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
                    parsed_effects = self._parse_description(item["description"])

                    # EffectAmountの挿入
                    parsed_effects = [
                        self._insert_effect_amount(effect, item)
                        for effect in parsed_effects
                    ]

                    # 登録
                    for effect in parsed_effects:
                        if effect.formula is None:
                            is_checked_evaluation = False
                        else:
                            is_checked_evaluation = True
                        Effect.objects.update_or_create(
                            description=effect.description,
                            verbose_description=effect.verbose_description,
                            is_unique=effect.is_unique,
                            formula=effect.formula,
                            name=effect.unique_name,
                            is_updated_in_current_patch=False,
                            is_checked_evaluation=is_checked_evaluation,
                            item=item_record,
                            calc_priority=1
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
        splitted_desc = description.split("<br><br>")

        # <br><br>で区切られたやつを頑張ってつなげたりする
        concated_desc = list()
        index = 0
        for desc in splitted_desc:
            tags = self._get_contain_tags(desc)
            if (
                "stats" not in tags
                and "active" not in tags
                and "passive" not in tags
                and "unique" not in tags
                and index > 0
            ):
                concated_desc[index - 1] += desc
            else:
                concated_desc.append(desc)
                index += 1

        # <br>で区切る
        raw_description = list()
        for desc in concated_desc:
            splitted = desc.split("<br>")
            raw_description.extend(splitted)

        # タグを消したりなんだり
        description = [re.sub("<.*?>", "", line) for line in raw_description]

        # 中身を見始める
        parsed_effect_list = list()
        for line, raw_line in zip(description, raw_description):
            parsed_effect = ParsedEffect()
            parsed_effect.description = line
            parsed_effect.verbose_description = raw_line

            if line.find(": ") >= 0:
                header, effect = line.split(": ", 1)
                effect_type = self._get_effect_type(header)

                # ユニーク判定
                if effect_type == EFFECT_TYPES.UNIQUE:
                    parsed_effect.is_unique = True

                # 固有名存在判定
                if header.find("-") >= 0:
                    _, unique_name = header.split("-")
                    parsed_effect.unique_name = unique_name.strip()

                # スタッツ判定
                if self._is_stats(effect):
                    name, amount = self._convert_stats(effect)
                    formula = "{} * [{}]".format(str(amount), name)
                    parsed_effect.formula = formula
                    parsed_effect.stats_pair = (name, amount)
            else:
                # スタッツ判定
                if self._is_stats(line):
                    name, amount = self._convert_stats(line)
                    formula = "{} * [{}]".format(str(amount), name)
                    parsed_effect.formula = formula
                    parsed_effect.stats_pair = (name, amount)

            parsed_effect_list.append(parsed_effect)

        return parsed_effect_list

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

    """
    effectの行頭を見て種類を判定する
    あんまり使ってない
    """
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
    def _insert_effect_amount(self, effect, item):
        if not "effect" in item:
            return effect

        for amount in re.findall(r"@[^@@]*@", effect.description):
            stripped = amount.strip("@")

            # 掛け算があるのである
            if stripped.find("*") >= 0:
                key, times = stripped.split("*")
                value = float(item["effect"][key]) * int(times)
                effect.description = effect.description.replace(
                    amount, str(value)
                )
            # ゴールド袋は許さない
            elif stripped.find("Value") >= 0:
                    lower_value = item["effect"]["Effect1Amount"]
                    upper_value = item["effect"]["Effect2Amount"]
                    effect.description = effect.description.replace(
                        "@Value@",
                        "{} - {}".format(lower_value, upper_value)
                    )
            # 一般的な場合
            else:
                effect.description = effect.description.replace(
                    amount, item["effect"][stripped]
                )

        return effect

    def _get_contain_tags(self, sentence):
        tags = list()

        for tag in re.findall(r"<[^<>]*>", sentence):
            tag_name = tag.strip("<").strip(">")
            tags.append(tag_name)

        return tags



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
