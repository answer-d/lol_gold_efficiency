# -*- encoding:utf-8 -*-

from django.core.management.base import BaseCommand
from ...backends.riot_static_data import RiotStaticData
from django.conf import settings
from ...logger import *


class Command(BaseCommand):
    """
    引数で指定されたバージョンのアイテムデータを取ってきて登録する
    ファイルパスを指定するとその中身を指定されたバージョンとして登録する

    ※注※：バージョンチェックとアイテム取得で2回リクエストを送るのでRateLimitに注意すること
    """

    help = "引数で指定されたバージョンのアイテムデータをアップデートするよ。\n" \
        "-fが与えられた場合はパッチバージョンの指定は不要だよ。\n" \
        "Usage: python manage.py updateitems [%パッチバージョン%] [-f %ファイルパス%]"

    @logging
    def add_arguments(self, parser):
        parser.add_argument(
            "-p", "--patch_version", type=str, required=False, default=None
        )
        parser.add_argument(
            "-f", "--file", type=str, required=False, default=None
        )

    @logging
    def handle(self, *args, **options):
        static_data = RiotStaticData(api_key=settings.RIOT_API_KEY)
        file_path = options["file"]

        if file_path:
            logger.debug("file_pathが与えられているよぉ～ : {}".format(file_path))

            items = static_data.load_from_json(file_path)
            version = items["version"]
        else:
            logger.debug("RiotAPIをコールするよぉ～")

            available_versions = static_data.fetch_patch_versions()
            version = options["patch_version"] if options["patch_version"] else available_versions[0]
            if version not in available_versions:
                logger.error("(version:{}が)ないです。".format(version))
                return
            items = static_data.fetch_items(version)

        logger.info("Item update start (version={}).".format(version))
        static_data.update_versions(version)
        static_data.update_stats_base(items, version)
        static_data.update_items(items, version)
        logger.info("Item update done.")
