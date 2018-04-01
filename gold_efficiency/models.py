import re
import json
from functools import reduce
from django.db import models

# Create your models here.


class PatchVersion(models.Model):
    """パッチバージョン"""
    version_str = models.CharField(max_length=20)

    def __str__(self):
        return self.version_str


class Tag(models.Model):
    """アイテムに紐づくタグ"""
    name = models.CharField(max_length=30)
    verbose_name = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    """アイテム"""
    name = models.CharField(max_length=50)
    riot_item_id = models.PositiveIntegerField()
    base_cost = models.PositiveIntegerField()
    total_cost = models.PositiveIntegerField()
    is_purchasable = models.BooleanField()
    sell_gold = models.PositiveIntegerField()
    img = models.CharField(max_length=100, null=True, blank=True)
    from_item_str = models.CharField(max_length=200, null=True, blank=True)
    into_item_str = models.CharField(max_length=200, null=True, blank=True)
    depth = models.PositiveIntegerField(null=True, blank=True)
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE, null=True, related_name="item_set")
    tags = models.ManyToManyField(Tag)

    def __str__(self):
        return self.name

    def get_gold_value(self, **kwargs):
        """アイテムの金銭価値を取得する"""
        # アイテムに紐づく効果の金銭価値を全て評価して足し合わせる
        gold_value_list = [x.get_gold_value(**kwargs) for x in self.effect_set.all()]
        if len(gold_value_list) > 0:
            gold_value = reduce(lambda x, y: x + y, gold_value_list)
        else:
            gold_value = 0
        return gold_value

    def get_gold_efficiency(self, **kwargs):
        """アイテムの金銭効率を取得する"""
        try:
            gold_efficiency = 100 * self.get_gold_value(**kwargs) / self.total_cost
        except ZeroDivisionError:
            gold_efficiency = 0
        return gold_efficiency

    def _get_from_items(self):
        """from_itemをItemオブジェクトのリストとして返す"""
        from_items = []
        if self.from_item_str is not None:
            for from_item_id in eval(self.from_item_str):
                if self.patch_version.item_set.filter(riot_item_id=from_item_id).exists():
                    from_items.append(self.patch_version.item_set.get(riot_item_id=from_item_id))
        return from_items
    from_items = property(_get_from_items)

    def _get_into_items(self):
        """into_itemをItemオブジェクトのリストとして返す"""
        into_items = []
        if self.into_item_str is not None:
            for into_item_id in eval(self.into_item_str):
                if self.patch_version.item_set.filter(riot_item_id=into_item_id).exists():
                    into_items.append(self.patch_version.item_set.get(riot_item_id=into_item_id))
        return into_items
    into_items = property(_get_into_items)


class StatsBase(models.Model):
    """ステータスの種類と金銭価値"""
    name = models.CharField(max_length=30)
    gold_value_per_amount = models.FloatField()
    patch_version = models.ForeignKey(PatchVersion, on_delete=models.CASCADE, related_name="stats_base_set")

    def __str__(self):
        return self.name


class Effect(models.Model):
    """アイテムに紐づく効果（一対多）"""
    description = models.TextField()
    verbose_description = models.TextField(null=True, blank=True)
    is_unique = models.BooleanField()
    formula = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)
    min_input = models.TextField(null=True, blank=True)
    max_input = models.TextField(null=True, blank=True)
    calc_priority = models.PositiveSmallIntegerField()
    is_updated_in_current_patch = models.BooleanField()
    is_checked_evaluation = models.BooleanField()
    ambiguous_type = models.CharField(max_length=30, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="effect_set")

    def __str__(self):
        return self.description

    def get_gold_value(self, **kwargs) -> float:
        """金銭価値を計算して返す"""
        self._validation_check_input(**kwargs)

        if self.is_evaluable(**kwargs):
            formula = self.formula
            for k, v in kwargs.items():
                formula = formula.replace("{" + k + "}", v)
            for stats_base in self.item.patch_version.stats_base_set.all():
                formula = formula.replace("[" + stats_base.name + "]", str(stats_base.gold_value_per_amount))

            return eval(formula)
        else:
            return 0

    # TODO:formulaセット時にヴァリデーションチェックする仕組み入れる

    def get_min_gold_value(self):
        """金銭価値の最小値を取得する"""
        return self.get_gold_value(**json.loads(self.min_input))

    def get_max_gold_value(self):
        """金銭価値の最大値を取得する"""
        return self.get_gold_value(**json.loads(self.max_input))

    def get_input_keys(self) -> list:
        """get_gold_value()を呼ぶ時に渡すべきキーのリストを返す"""
        if self.formula is not None:
            return self._deduplication(re.findall(r"{(.*?)}", self.formula))
        else:
            return []

    def get_stats_base_names(self) -> list:
        """formulaにかかれているStatsBaseの名前のリストを返す"""
        if self.formula is not None:
            return self._deduplication(re.findall(r"\[(.*?)\]", self.formula))
        else:
            return []

    def is_evaluable(self, **kwargs) -> bool:
        """kwargsが与えられた時評価可能かどうかを返す"""
        if self.formula is not None:
            required_keys = self.get_input_keys()
            if len(required_keys) > 0:
                if len(kwargs) > 0:
                    return reduce(lambda x, y: x and y, [x in required_keys for x in kwargs])
                else:
                    return False
            else:
                return True
        else:
            return False

    def _validation_check_formula(self, formula):
        """formulaセット時に実施するヴァリデーションチェック"""
        # ホワイトリスト方式で実装します
        pass

    def _validation_check_input(self, **kwargs):
        """金銭価値算出の引数に対して実施するヴァリデーションチェック"""
        # ホワイトリスト方式で実装します
        pass

    def _deduplication(self, obj: list) -> list:
        """リストから重複要素を排除して返す"""
        seen = set()
        seen_add = seen.add
        return [x for x in obj if x not in seen and not seen_add(x)]
