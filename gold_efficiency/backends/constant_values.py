# -*- encoding: utf-8

from enum import Enum


class EFFECT_TYPES(Enum):
    NORMAL = 1  # センスの無い命名
    UNIQUE = 2
    OTHER = 3


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

USELESS_TAGS = [
    "rules",
    "groupLimit"
]

MAPID_SUMMONERS_RIFT = "11"

ITEMIMG_BASE_URL = r"http://ddragon.leagueoflegends.com/cdn/{}/img/item/{}.png"
