# -*- encoding: utf-8 -*-

import re
import json
import lxml.html
from .models import PatchVersion, Item, Stats, Effect, Tag
from riotwatcher import RiotWatcher


class RiotStaticData(object):

    NOATTR_ITEM_KEYS = {
        "from": "from_item_str",
        "into": "into_item_str",
        "depth": "depth",
    }

    FLAT_STATS_KEYS = {
        "攻撃力": "AttackDamage",
        "魔力": "AbilityPower",
        "物理防御": "Armor",
        "魔法防御": "MagicResistance",
        "体力": "Health",
        "マナ": "Mana",
        "移動速度": "FlatMovementSpeed",
        "脅威": "Lethality",
        "魔法防御貫通": "MagicPenetration"
    }
    PERCENT_STATS_KEYS = {
        "クールダウン短縮": "CooldownReduction",
        "ライフスティール": "LifeSteal",
        "移動速度": "PercentMovementSpeed",
        "クリティカル率": "CriticalStrikeChance",
        "基本マナ自動回復": "ManaRegeneration",
        "基本体力自動回復": "HealthRegeneration",
        "攻撃速度": "AttackSpeed",
        "回復効果およびシールド量": "HealAndShieldPower",
    }

    MAPID_SUMMONERS_RIFT = "11"

    ITEMIMG_BASE_URL = r"http://ddragon.leagueoflegends.com/cdn/{}/img/item/{}.png"

    """
    コンストラクタ
    """
    def __init__(self, api_key=None, region="jp1", locale="ja_JP"):
        self.api_key = api_key
        self.region = region
        self.locale = locale

    """
    itemsのjsonデータを指定されたバージョンとしてDBに登録する
    """
    def update_items(self, items, version):
        version = PatchVersion.objects.get(version_str=version)

        for id in items["data"].keys():
            item = items["data"][id]

            # サモリフ以外除外
            if item["maps"][self.MAPID_SUMMONERS_RIFT] is False:
                continue

            # アイテム登録
            if not Item.objects.filter(patch_version=version, riot_item_id=id).exists():
                item_data = self._parse_item(item, version)
                item_record, _ = Item.objects.update_or_create(**item_data)

                # タグ登録
                if "tag" in item:
                    for tag in item["tags"]:
                        Tag.objects.update_or_create(
                            name=tag,
                            item=item_record
                        )

                # スタッツ/エフェクト登録
                if "description" in item:
                    # パース
                    stats, effects, unique_stats, unique_effects =\
                        self._parse_description(item["description"], version)

                    # EffectAmountの挿入
                    effects = self._insert_effect_amount(effects, item)
                    unique_effects = self._insert_effect_amount(
                        unique_effects,
                        item
                    )

                    # 登録
                    for name, amount in stats.items():
                        Stats.objects.update_or_create(
                            name=name,
                            amount=amount,
                            item=item_record
                        )
                    for effect in effects:
                        Effect.objects.update_or_create(
                            description=effect,
                            is_unique=False,
                            is_evaluable=False,
                            item=item_record,
                        )
                    for name, amount in unique_stats.items():
                        Stats.objects.update_or_create(
                            name=name,
                            amount=amount,
                            item=item_record
                        )
                    for effect in unique_effects:
                        Effect.objects.update_or_create(
                            description=effect,
                            is_unique=True,
                            is_evaluable=False,
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
            img=self.ITEMIMG_BASE_URL.format(version_str, item["id"]),
            patch_version=patch_version,
        )

        # 存在しないキーはNoneに
        for key, value in self.NOATTR_ITEM_KEYS.items():
            if key in item:
                item_data[value] = item[key]
            else:
                item_data[value] = None

        return item_data

    """
    description内のstatsおよびeffectのパース
    """
    def _parse_description(self, description, patch_version):
        body = lxml.html.fromstring(description)
        stats = {}
        effects = []
        unique_stats = {}
        unique_effects = []

        # いらないタグを除去
        for element in body.xpath("//font"):
            element.drop_tag()
        for element in body.xpath("//a"):
            element.drop_tag()
        for element in body.xpath("//unlockedPassive"):
            element.drop_tag()
        for element in body.xpath("//scaleLevel"):
            element.drop_tag()
        for element in body.xpath("//mana"):
            element.drop_tag()

        # <stats></stats>内のパラメータ
        for stats_set in body.xpath("//stats/text()"):
            stats_list = stats_set.split("\n")
            stats_list = map(lambda x: x.strip(), stats_list)
            stats_list = map(
                lambda x: x.replace("+", ""),
                stats_list
            )
            for s in stats_list:
                if self._is_stats(s):
                    key, value = self._convert_stats(s)
                    stats[key] = value

        # <active></active>と<passive></passive>
        reward = ""
        for effect in body.xpath("//active"):
            if effect.tail is not None:
                effect = effect.text.strip() + effect.tail.strip()
                effects.append(effect)
        for effect in body.xpath("//passive"):
            if effect.tail is not None:
                if effect.text == "報酬:":
                    reward = effect.text
                    continue
                effect = reward + effect.text.strip() + effect.tail.strip()
                effects.append(effect)

                if reward != "":
                    reward = ""

        # <unique></unique>内のパラメータ
        for unique in body.xpath("//unique"):
            if unique.tail is not None:
                unique_list = unique.tail.split("\n")
                unique_list = list(map(lambda x: x.strip().replace("+", ""), unique_list))
                for v in unique_list:
                    if self._is_stats(v):
                        key, value = self._convert_stats(v)
                        unique_stats[key] = value
                    else:
                        v = unique.text + v
                        unique_effects.append(v)
        unique_effects = [e for e in unique_effects if e != ""]

        return stats, effects, unique_stats, unique_effects

    """
    取り出したものがstatsかeffectかを判定
    """
    def _is_stats(self, contents):
        splitted = contents.split(" ")
        if len(splitted) != 2:
            return False

        key, value = splitted
        if value.find("%") >= 0:
            if key in self.PERCENT_STATS_KEYS.keys():
                return True
            else:
                return False
        elif key in self.FLAT_STATS_KEYS.keys():
            return True
        else:
            return False

    """
    statsを切り分ける.
    その際データベースに登録可能なキー名に変換する.

    ex.)
    stats, value = "スタッツ value"
    """
    def _convert_stats(self, contents):
        key, value = contents.split(" ")

        if value.find("%") >= 0:
            return self.PERCENT_STATS_KEYS[key], value.replace("%", "")
        else:
            return self.FLAT_STATS_KEYS[key], value

    """
    item["effect"]内に格納された@Effect*Amount@
    effectの中身を置換する
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
                else:
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
