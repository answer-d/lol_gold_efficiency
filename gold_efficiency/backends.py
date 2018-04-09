# -*- encoding: utf-8 -*-

import re
import json
import logging
from enum import Enum
import lxml.html
import lxml.etree
from .models import PatchVersion, Item, StatsBase, Effect, Tag
from riotwatcher import RiotWatcher
from tqdm import tqdm


class EFFECT_TYPES(Enum):
    NORMAL = 1  # センスの無い命名
    UNIQUE = 2
    REWARD = 3
    QUEST = 4
    OTHER = 5


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

    USELESS_TAGS = [
        "//a",
        "//u",
        "//font",
        "//scalelevel",
        "//mana",
        "//unlockedpassive"
    ]

    """
    コンストラクタ
    """
    def __init__(self, api_key=None, region="jp1", locale="ja_JP"):
        self.api_key = api_key
        self.region = region
        self.locale = locale

        # ロガー（今は使ってない）
        # ファイルハンドラのログはmanage.pyと同階層に生成される
        self.logger = logging.getLogger()
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
        for base_items in self.BASE_ITEMS_LIST:
            for key, value in base_items.items():
                if StatsBase.objects.filter(patch_version=version, name=key).exists():
                    continue

                item = items['data'][value]

                # サモリフ以外除外
                if item["maps"][self.MAPID_SUMMONERS_RIFT] is False:
                    continue

                # アイテムデータの取得
                item_data = self._parse_item(item, version)
                stats, effects, unique_stats, unique_effects =\
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

        for id in tqdm(items["data"].keys()):
            item = items["data"][id]

            # サモリフ以外除外
            if item["maps"][self.MAPID_SUMMONERS_RIFT] is False:
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
                    stats, effects, unique_stats, unique_effects =\
                        self._parse_description(item["description"])

                    # EffectAmountの挿入
                    effects = self._insert_effect_amount(effects, item)
                    unique_effects = self._insert_effect_amount(
                        unique_effects,
                        item
                    )

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

        # effectの個別formula投入
        # とりあえず入れるため用なので、いずれ消す予定
        self._set_formula("自動効果(重複不可) - 素早さ:このアイテムが追加で10%のクールダウン短縮を獲得。", "10 * [CooldownReduction]")
        self._set_formula("自動効果(重複不可) - 畏怖:最大マナの3%に等しい魔力を得る。消費マナの25%を回復。", "{MAX_MANA} * 0.03 * [AbilityPower]")  # 更にambiguousにもしたい（消費マナの25%回復効果もあるので）
        self._set_formula("自動効果(重複不可) - マナチャージ:マナ消費ごとに最大マナが8増加(最大750マナ)。この効果は12秒につき最大3回まで発生。", "{STACK} * 8 * [Mana]")
        self._set_formula("自動効果(重複不可) - マナチャージ:マナ消費ごとに最大マナが12増加(最大750マナ)。この効果は12秒につき最大3回まで発生。", "{STACK} * 12 * [Mana]")
        self._set_formula("自動効果(重複不可):通常攻撃ごとに、攻撃速度 +8%、増加攻撃力 +4%、魔力 +4%を得る。効果は5秒間持続する(効果は最大6回までスタック)。最大スタックで「グインソーの憤怒」が発生する。", "{STACK} * ({AS} * 8 * [AttackSpeed] + {ADDITIONAL_AD} * 0.04 * [AttackDamage] + {AP} * 0.04 * [AbilityPower])")
        self._set_formula("発動効果(重複不可):1チャージ消費して体力125とマナ75を12秒間かけて回復する。さらに効果時間中穢れの接触を付与する。最大3チャージで、ショップを訪れることで補充できる。", "3 * (125 * [Health] + 75 * [Mana])")  # ambiguous
        self._set_formula("自動効果(重複不可):ユニット1体をキルするごとに物理防御と魔力がそれぞれ0.5増加する。この効果は最大30回までスタックする。", "{STACK} * 0.5 * ([Armor] + [AbilityPower])")
        self._set_formula("自動効果(重複不可) :ユニット1体をキルするごとに最大体力が5増加する。このボーナスは最大20回までスタックする。", "{STACK} * 5 * [Health]")
        self._set_formula("自動効果(重複不可):基本攻撃力 +50%", "{BASE_AD} * 0.5 * [AttackDamage]")
        self._set_formula("自動効果(重複不可) - ドレッド:栄光1スタックごとに魔力3を得る。", "{STACK} * 3 * [AbilityPower]")
        self._set_formula("自動効果:5秒毎に体力を6回復。", "6 * [HealthRegeneration]")
        self._set_formula("自動効果(重複不可) - 畏怖:最大マナの2%に等しい増加攻撃力を得る。消費マナの15%を回復。", "{MAX_MANA} * 0.02 * [AttackDamage]")
        self._set_formula("自動効果(重複不可) - マナチャージ:通常攻撃かマナを消費するごとに最大マナが5増加(最大750マナ)。この効果は12秒につき最大3回まで発生する。", "{STACK} * 5 * [Mana]")
        self._set_formula("自動効果(重複不可) - マナチャージ:通常攻撃かマナを消費するごとに最大マナが6増加(最大750マナ)。この効果は12秒につき最大3回まで発生する。", "{STACK} * 6 * [Mana]")
        self._set_formula("自動効果(重複不可) - 調和:基本マナ自動回復の上昇率が、基本体力自動回復の上昇率にも適用される。", "{MANA_REG_MOD} * [HealthRegeneration]")
        self._set_formula("自動効果(重複不可) - ドレッド:栄光1スタックごとに5の魔力を得る。栄光スタックが15以上になると、移動速度が10%増加する。", "{STACK} * 5 * [AbilityPower] + {STACK}//15 * 10 * [PercentMovementSpeed]")
        self._set_formula("自動効果(重複不可): 魔力を40 % 増加させる。", "{AP} * 0.4 * [AbilityPower]")
        self._set_formula("自動効果:1スタックごとに体力 +20、マナ +10、魔力 +4を獲得 (最大で体力 +200、マナ +100、魔力 +40)。1分ごとに1スタックを獲得 (最大10スタック)。", "{STACK} * (20 * [Health] + 10 * [Mana] + 4 * [AbilityPower])")
        self._set_formula("自動効果(重複不可) - マナチャージ:マナ消費ごとに最大マナが4増加(12秒につき最大3回まで)。", "{STACK} * 4 * [Mana]")
        self._set_formula("自動効果(重複不可) - マナチャージ:マナ消費ごとに最大マナが6増加(12秒につき最大3回まで)。", "{STACK} * 6 * [Mana]")
        self._set_formula("発動効果(重複不可) :1チャージ消費して体力125を12秒間かけて回復する。最大2チャージで、ショップを訪れることで補充できる。", "2 * (125 * [Health])")

    @staticmethod
    def _set_formula(effect_description, formula):
        for effect in Effect.objects.filter(description__contains=effect_description):
            effect.formula = formula
            effect.save()
            print("[{}] {} : {}".format(effect.item.name, effect_description, formula))

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
    def _parse_description(self, description):
        body = lxml.html.fromstring(description)
        stats = dict()
        effects = list()
        unique_stats = dict()
        unique_effects = list()

        # いらないタグを除去
        useless_tags = "|".join(self.USELESS_TAGS)
        for element in body.xpath(useless_tags):
            element.drop_tag()

        # <stats></stats>内のパラメータ
        for stats_set in body.xpath("//stats/text()"):
            stats_list = stats_set.split("\n")

            for s in stats_list:
                if self._is_stats(s):
                    key, value = self._convert_stats(s)
                    stats[key] = value

        # Effect周り全部
        effect_tags = "//active|//passive|//unique"
        quest = ""
        reward = ""
        for effect in body.xpath(effect_tags):
            if effect.tail is not None:
                effect_type = self._get_effect_type(effect)

                if effect_type == EFFECT_TYPES.UNIQUE:
                    if self._is_stats(effect.tail):
                        key, value = self._convert_stats(effect.tail)
                        unique_stats[key] = value
                    else:
                        unique_effects.append(
                            effect.text.strip() + effect.tail.strip()
                        )
                elif effect_type == EFFECT_TYPES.NORMAL:
                    if self._is_stats(effect.tail):
                        key, value = self._convert_stats(effect.tail)
                        stats[key] = value
                    else:
                        effects.append(
                            effect.text.strip() + effect.tail.strip()
                        )
                elif effect_type == EFFECT_TYPES.QUEST:
                    quest = effect.text.strip() + effect.tail.strip()
                elif effect_type == EFFECT_TYPES.REWARD:
                    reward = effect.text.strip() + effect.tail.strip()
                    reward_effect = effect.getnext()
                    reward += reward_effect.text.strip() + reward_effect.tail.strip()
                    break
                else:
                    effects.append(effect.text.strip() + effect.tail.strip())
        if quest != "" and reward != "":
            effects.append(quest + reward)

        return stats, effects, unique_stats, unique_effects

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
            if key in self.PERCENT_STATS_KEYS.keys():
                return True
            else:
                return False
        elif key in self.FLAT_STATS_KEYS.keys():
            return True
        else:
            return False

    def _get_effect_type(self, element):
        header = element.text.strip()

        if header.find("重複不可") >= 0:
            return EFFECT_TYPES.UNIQUE
        elif (header.find("発動効果") >= 0) or (header.find("自動効果") >= 0):
            return EFFECT_TYPES.NORMAL
        elif header.find("クエスト") >= 0:
            return EFFECT_TYPES.QUEST
        elif header.find("報酬") >= 0:
            return EFFECT_TYPES.REWARD
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
