# -*- encoding: utf-8 -*-

import re
import json
from tqdm import tqdm
from riotwatcher import RiotWatcher

from ..models import PatchVersion, Item, StatsBase, Effect, Tag
from .constant_values import *
from .parsed_effect import ParsedEffect
from ..logger import *


@logging_class
class RiotStaticData(object):
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

        for id in tqdm(items["data"].keys()):
            item = items["data"][id]

            # サモリフ以外除外
            if item["maps"][MAPID_SUMMONERS_RIFT] is False:
                continue

            # 対象のアイテムが登録されてたらスキップ
            if Item.objects.filter(patch_version=version, riot_item_id=id).exists():
                continue

            # アイテム登録
            item_data = self._parse_item(item, version)
            item_record, _ = Item.objects.update_or_create(**item_data)

            # タグ登録
            if "tags" in item:
                for tag in item["tags"]:
                    tag_record, _ = Tag.objects.get_or_create(name=tag)
                    item_record.tags.add(tag_record)

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

        # effectの個別formula投入
        # とりあえず入れるため用なので、いずれ消す予定
        self._set_formula("自動効果(重複不可) - 素早さ: このアイテムが追加で10%のクールダウン短縮を獲得。",
                          "10 * [CooldownReduction]")
        self._set_formula("自動効果(重複不可) - 畏怖: 最大マナの3%に等しい魔力を得る。消費マナの25%を回復。",
                          "{MAX_MANA} * 0.03 * [AbilityPower]")  # 更にambiguousにもしたい（消費マナの25%回復効果もあるので）
        self._set_formula("マナチャージ: マナ消費ごとに最大マナが8増加(最大750マナ)。この効果は12秒につき最大3回まで発生。",
                          "{STACK} * 8 * [Mana]")
        self._set_formula("自動効果(重複不可) - マナチャージ: マナ消費ごとに最大マナが12増加(最大750マナ)。この効果は12秒につき最大3回まで発生。",
                          "{STACK} * 12 * [Mana]")
        self._set_formula("自動効果(重複不可): 通常攻撃ごとに、攻撃速度 +8%、増加攻撃力 +4%、魔力 +4%を得る。効果は5秒間持続する(効果は最大6回までスタック)。",
                          "{STACK} * ({AS} * 8 * [AttackSpeed] + {ADDITIONAL_AD} * 0.04 * [AttackDamage] + {AP} * 0.04 * [AbilityPower])")
        self._set_formula("発動効果(重複不可): 1チャージ消費して体力125とマナ75を12秒間かけて回復する。",
                          "3 * (125 * [Health] + 75 * [Mana])")  # ambiguous
        self._set_formula("自動効果(重複不可): ユニット1体をキルするごとに物理防御と魔力がそれぞれ0.5増加する。この効果は最大30回までスタックする。",
                          "{STACK} * 0.5 * ([Armor] + [AbilityPower])")
        self._set_formula("自動効果(重複不可) : ユニット1体をキルするごとに最大体力が5増加する。このボーナスは最大20回までスタックする。",
                          "{STACK} * 5 * [Health]")
        self._set_formula("自動効果(重複不可) - ドレッド: 栄光1スタックごとに魔力3を得る。",
                          "{STACK} * 3 * [AbilityPower]")
        self._set_formula("自動効果: 5秒毎に体力を6回復。",
                          "6 * [HealthRegeneration]")
        self._set_formula("自動効果(重複不可) - 畏怖: 最大マナの2%に等しい増加攻撃力を得る。消費マナの15%を回復。",
                          "{MAX_MANA} * 0.02 * [AttackDamage]")
        self._set_formula("自動効果(重複不可) - マナチャージ: 通常攻撃かマナを消費するごとに最大マナが5増加(最大750マナ)。この効果は12秒につき最大3回まで発生する。",
                          "{STACK} * 5 * [Mana]")
        self._set_formula("自動効果(重複不可) - マナチャージ: 通常攻撃かマナを消費するごとに最大マナが6増加(最大750マナ)。この効果は12秒につき最大3回まで発生する。",
                          "{STACK} * 6 * [Mana]")
        self._set_formula("自動効果(重複不可) - 調和: 基本マナ自動回復の上昇率が、基本体力自動回復の上昇率にも適用される。",
                          "{MANA_REG_MOD} * [HealthRegeneration]")
        self._set_formula("自動効果(重複不可) - ドレッド: 栄光1スタックごとに5の魔力を得る。栄光スタックが15以上になると、移動速度が10%増加する。",
                          "{STACK} * 5 * [AbilityPower] + {STACK}//15 * 10 * [PercentMovementSpeed]")
        self._set_formula("自動効果(重複不可) : 魔力を40%増加させる。",
                          "{AP} * 0.4 * [AbilityPower]")
        self._set_formula("自動効果: 1スタックごとに体力 +20、マナ +10、魔力 +4を獲得 (最大で体力 +200、マナ +100、魔力 +40)。1分ごとに1スタックを獲得 (最大10スタック)。",
                          "{STACK} * (20 * [Health] + 10 * [Mana] + 4 * [AbilityPower])")
        self._set_formula("自動効果(重複不可) - マナチャージ: マナ消費ごとに最大マナが4増加(12秒につき最大3回まで)。",
                          "{STACK} * 4 * [Mana]")
        self._set_formula("自動効果(重複不可) - マナチャージ: マナ消費ごとに最大マナが6増加(12秒につき最大3回まで)。",
                          "{STACK} * 6 * [Mana]")
        self._set_formula("発動効果(重複不可) : 1チャージ消費して体力125を12秒間かけて回復する。最大2チャージで、ショップを訪れることで補充できる。",
                          "2 * (125 * [Health])")

    @staticmethod
    def _set_formula(effect_description, formula):
        for effect in Effect.objects.filter(description__contains=effect_description):
            effect.formula = formula
            effect.save()
            print("[{}] {} : {}".format(effect.item.name, effect_description, formula))

    """
    StatsBaseを計算して、指定されたバージョンとしてDBに登録する
    """
    def update_stats_base(self, items, version):
        version = PatchVersion.objects.get(version_str=version)

        # 金銭効率ベースになるアイテムをtier順に処理
        for base_items in BASE_ITEMS_LIST:
            for key, value in base_items.items():
                item = items['data'][value]

                # サモリフ以外除外
                if item["maps"][MAPID_SUMMONERS_RIFT] is False:
                    continue

                # 既に登録されてるStatsBaseだったらスキップ
                if StatsBase.objects.filter(patch_version=version, name=key).exists():
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
    バージョンをDBに登録する
    """
    @staticmethod
    def update_versions(versions):
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
    @staticmethod
    def load_from_json(json_path):
    # def load_from_json(self, json_path):
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
        # いらないタグと中身を消す
        for tag in USELESS_TAGS:
            description = self._drop_tag(description, tag)

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
                concated_desc[index - 1] += "\n" + desc
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
            # 空白行はスルー
            if line == "":
                continue

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

    def _drop_tag(self, description, tag):
        return re.sub(r"<{}>.*?</{}>".format(tag, tag), "", description)


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
