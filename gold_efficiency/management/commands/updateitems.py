# -*- encoding:utf-8 -*-

from django.core.management.base import BaseCommand
from ...backends import RiotStaticData

APIKEY = "hoge"


"""
引数で指定されたバージョンのアイテムデータを取ってきて登録する
ファイルパスを指定するとその中身を指定されたバージョンとして登録する

※注※：バージョンチェックとアイテム取得で2回リクエストを送るのでRateLimitに注意すること
"""
class Command(BaseCommand):
    help = "引数で指定されたバージョンのアイテムデータをアップデートするよ。\n" \
        "Usage: python manage.py updateitems %パッチバージョン% -f %ファイルパス(オプション)%"

    def add_arguments(self, parser):
        parser.add_argument("patch_version", type=str)
        parser.add_argument(
            "-f", "--file", type=str, required=False, default=None
        )

    def handle(self, *args, **options):
        static_data = RiotStaticData(APIKEY)
        version = options["patch_version"]
        file_path = options["file"]

        if file_path is not None:
            items = static_data.load_from_json(file_path)
        else:
            available_versions = static_data.fetch_patch_versions()
            if version not in available_versions:
                print("(そんなバージョン)ないです。")
                return

            items = static_data.fetch_items(version)

        static_data.update_versions(version)
        static_data.update_stats_base(items, version)
        static_data.update_items(items, version)

        print("Update Done.")
