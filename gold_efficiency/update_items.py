import json
from riotwatcher import RiotWatcher
from .models import PatchVersion, Item, StatsMaster, Stats, Effect, TagMaster, Tag


# やりたいこと
# ・パッチバージョンを確認して、最新版がDBになかったらレコードを作る
# stats_masterは再計算する(もしかしたらベースになっているアイテムに変更が入るかもしれないので)


def set_patch_version(patch_version):
    record = PatchVersion(version_str=patch_version)
    record.save()


def set_stats_master(name, patch_version):
    gold_value_per_amount = calc_gold_value_per_amount(name, patch_version)

    record = StatsMaster.objects.create(
        name=name, gold_value_per_amount=gold_value_per_amount, patch_version=patch_version
    )
    record.save()


def set_tag_master(name, patch_version):
    pass


def calc_gold_value_per_amount(name, patch_version) -> float:
    return 1.0


def update_items_database(items_json):
    # PatchVersion
    set_patch_version(items_json['version'])

    # TagMaster

    # StatsMaster
        # Tier 1 (...)
        # Tier 2 (...)

    # Item
        # Item (main)
        # Stats
        # Effect

    pass


def update_items_main():
    # init riotwatcher

    # get json

    # version check
        # if True: update db -> set visible
        # if False: end
