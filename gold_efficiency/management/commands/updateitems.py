# -*- encoding:utf-8 -*-

from django.core.management.base import BaseCommand
from ...backends.riot_static_data import RiotStaticData
from django.conf import settings


class Command(BaseCommand):
    """
    引数で指定されたバージョンのアイテムデータを取ってきて登録する
    ファイルパスを指定するとその中身を指定されたバージョンとして登録する

    ※注※：バージョンチェックとアイテム取得で2回リクエストを送るのでRateLimitに注意すること
    """

    help = "引数で指定されたバージョンのアイテムデータをアップデートするよ。\n" \
        "-fが与えられた場合はパッチバージョンの指定は不要だよ。\n" \
        "Usage: python manage.py updateitems [%パッチバージョン%] [-f %ファイルパス%]"

    def add_arguments(self, parser):
        parser.add_argument(
            "-p", "--patch_version", type=str, required=False, default=None
        )
        parser.add_argument(
            "-f", "--file", type=str, required=False, default=None
        )

    def handle(self, *args, **options):
        static_data = RiotStaticData(api_key=settings.RIOT_API_KEY)
        available_versions = static_data.fetch_patch_versions()

        file_path = options["file"]

        if file_path:
            items = static_data.load_from_json(file_path)
            version = items["version"]
        else:
            version = options["patch_version"] if options["patch_version"] else available_versions[0]
            items = static_data.fetch_items(version)

        if version not in available_versions:
            print("(version:{})ないです。".format(version))
            return

        print("version:{} detected".format(version))

        print("Item update start.")
        static_data.update_versions(version)
        static_data.update_stats_base(items, version)
        static_data.update_items(items, version)
        print("Item update done.")
