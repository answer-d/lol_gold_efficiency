# -*- encoding: utf-8 -*-

import re
import json
import lxml.html
from .models import PatchVersion, Item, StatsBase, Stats, Effect, Tag
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
        "回復効果およびシールド量": "HealAndShieldPower"
    }

    # 金銭効率ベースには計算順序があるのでリスト管理
    # → 後ろのリストに入っているアイテムは前出のアイテムの金銭効率を参照する
    BASE_ITEMS_LIST = [
        {
            "AttackDamage": "1036",  # ロングソード
            "AbilityPower": "1052",  # 増魔の書
            "Armor": "1029",  # クロースアーマー
            "MagicResistance": "1033",  # ヌルマジックマント
            "Health": "1028",  # ルビークリスタル
            "Mana": "1027",  # サファイアクリスタル
            "HealthRegeneration": "1006",  # 再生の珠
            "ManaRegeneration": "1004",  # フェアリーチャーム
            "CriticalStrikeChance": "1051",  # 喧嘩屋のグローブ
            "AttackSpeed": "1042",  # ダガー
            "FlatMovementSpeed": "1001",  # ブーツ
        },
        {
            "LifeSteal": "1053",  # ヴァンパイアセプター
            "Lethality": "3134",  # セレイテッドダーク
            "MagicPenetration": "3020",  # ソーサラーシューズ
            # "OnhitDamage": "1043",  # リカーブボウ
            "CooldownReduction": "3067",  # キンドルジェム
            "PercentMovementSpeed": "3113",  # エーテルウィスプ
        },
        {
            "HealAndShieldPower": "3114",  # フォビドゥンアイドル
        }
    ]

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
    StatsBaseを計算して、指定されたバージョンとしてDBに登録する
    """
    def update_stats_base(self, items, version):
        version = PatchVersion.objects.get(version_str=version)

        # 金銭効率ベースになるアイテムをtier順に処理
        for base_items in self.BASE_ITEMS_LIST:
            for key, value in base_items.items():
                if StatsBase.objects.filter(patch_version=version, name=key):
                    #DEBUG
                    print("already created StatsBase : {}".format(key))
                    continue

                item = items['data'][value]

                # DEBUG
                print("loop for : {}".format(item['name']))

                # サモリフ以外除外
                if item["maps"][self.MAPID_SUMMONERS_RIFT] is False:
                    continue

                # アイテムデータの取得
                item_data = self._parse_item(item, version)
                stats, effects, unique_stats, unique_effects =\
                    self._parse_description(item["description"], version)

                # 金銭効率ベース計算
                # 1. アイテムのトータル金額を取得して評価額としてセット
                # 2. Statsの中に既に金銭効率が決まっているものがあれば金銭価値算出して評価額から引く
                # 3. 2を繰り返し、Statsが単一になるまでやる
                # 4. 最終的に残った単一のStatsが計算しようとしているStatsのキーと一致する(はず)
                # 5. 得られたStatsのamountで評価額を割った値が金銭効率ベースになる
                all_stats = stats.copy()
                all_stats.update(unique_stats)
                valuation_gold = item_data["total_cost"]

                # DEBUG
                print("evaluate gold efficiency base start")
                print("all_stats : {}".format(all_stats))

                while 1 < len(all_stats):
                    # DEBUG
                    print("len(all_stats):{} > 1".format(len(all_stats)))

                    for stats_name, stats_amount in list(all_stats.items()):
                        #DEBUG
                        print("stats_name:{}, stats_amount:{}".format(stats_name, stats_amount))

                        existing_stats_base = StatsBase.objects.filter(name=stats_name, patch_version=version)

                        #DEBUG
                        print(existing_stats_base)

                        if len(existing_stats_base) == 1:
                            valuation_gold -= existing_stats_base[0].gold_efficiency_per_amount * int(stats_amount)
                            del all_stats[stats_name]

                            #DEBUG
                            print("all_stats[{}] deleted".format(stats_name))

                if key not in all_stats.keys():
                    # DEBUG
                    print("＼(^o^)／ｵﾜﾀ")

                gold_efficiency_per_amount = valuation_gold / int(all_stats[key])

                # DEBUG
                print("[{}] gold_efficiency_per_amount = {}".format(key, gold_efficiency_per_amount))
                print("evaluate gold efficiency base end")

                # DB登録
                StatsBase.objects.update_or_create(
                    name=key,
                    gold_efficiency_per_amount=gold_efficiency_per_amount,
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
                            stats=StatsBase.objects.get(patch_version=version, name=name),
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
                            stats=StatsBase.objects.get(patch_version=version, name=name),
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
