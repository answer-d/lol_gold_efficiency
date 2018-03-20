from django.db import models

# Create your models here.


class PatchVersion(models.Model):
    """パッチバージョン"""
    version_str = models.CharField(max_length=20)

    def __str__(self):
        return self.version_str


class Item(models.Model):
    """アイテム"""
    riot_item_id = models.PositiveIntegerField()
    name = models.CharField(max_length=50)
    base_cost = models.PositiveIntegerField()
    total_cost = models.PositiveIntegerField()
    is_purchasable = models.BooleanField()
    sell_gold = models.PositiveIntegerField()
    image_json = models.TextField()
    from_item_str = models.CharField(max_length=50, null=True)
    into_item_str = models.CharField(max_length=50, null=True)
    depth = models.PositiveIntegerField(null=True)
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Stats(models.Model):
    """アイテムに紐づくステータス"""
    # スタブモジュール
    STAB_STATS_BASE = {
        'AttackDamage': 350 / 10,
        'AbilityPower': 435 / 20,
        'Armor': 300 / 15,
        'MagicResistance': 450 / 25,
        'Health': 400 / 150,
        'Mana': 350 / 250,
        'HealthRegeneration': 150 / 50,  # HP5
        'ManaRegeneration': 125 / 25,  # MP5
        'CriticalStrikeChance': 400 / 10,
        'AttackSpeed': 300 / 12,
        'FlatMovementSpeed': 300 / 25,
    }
    # Tier2（これもスタブ）
    STAB_STATS_BASE['LifeSteal'] = (900 - 15 * STAB_STATS_BASE['AttackDamage']) / 10
    STAB_STATS_BASE['Lethality'] = (1100 - 25 * STAB_STATS_BASE['AttackDamage']) / 10
    STAB_STATS_BASE['MagicPenetration'] = (1100 - 45 * STAB_STATS_BASE['FlatMovementSpeed']) / 18
    STAB_STATS_BASE['OnhitDamage'] = (1000 - 25 * STAB_STATS_BASE['AttackSpeed']) / 15
    STAB_STATS_BASE['CooldownReduction'] = (800 - 200 * STAB_STATS_BASE['Health']) / 10
    STAB_STATS_BASE['PercentMovementSpeed'] = (850 - 30 * STAB_STATS_BASE['AbilityPower']) / 5
    STAB_STATS_BASE['HealAndShieldPower'] = (800 - 50 * STAB_STATS_BASE['ManaRegeneration'] -
                                             10 * STAB_STATS_BASE['CooldownReduction']) / 8

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    name = models.CharField(max_length=30, choices=map(lambda x: (x, x), STAB_STATS_BASE.keys()))
    amount = models.FloatField()

    def __str__(self):
        return self.item.name + '_' + self.stats.name


class Effect(models.Model):
    """アイテムに紐づく効果(passive/active)"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    is_evaluable = models.BooleanField()

    def __str__(self):
        return self.item.name + '_' + self.description


class TagMaster(models.Model):
    """タグのベース"""
    name = models.CharField(max_length=30)
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """アイテムに紐づくタグ"""
    # TAGS = {
    #     'GoldPer', 'Damage', 'Health', 'Stealth', 'Consumable', 'Mana', 'Slow',
    #     'NonbootsMovement', 'MagicPenetration', 'Armor', 'Tenacity', 'Boots',
    #     'ArmorPenetration', 'Trinket', 'Aura', 'SpellDamage', 'Vision', 'Jungle',
    #     'LifeSteal', 'Active', 'HealthRegen', 'AttackSpeed', 'Bilgewater', 'OnHit',
    #     'SpellVamp', 'SpellBlock', 'CooldownReduction', 'Lane', 'CriticalStrike',
    #     'ManaRegen'
    # }

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    tag = models.ForeignKey(TagMaster, on_delete=models.CASCADE)

    def __str__(self):
        return self.item.name + ':' + self.tag.name
