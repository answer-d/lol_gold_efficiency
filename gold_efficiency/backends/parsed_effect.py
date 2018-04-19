# -*- encoding: utf-8 -*-
from ..logger import *


"""
アイテムのStats/Effect/Descriptionなどを格納するデータクラス
パーサの返り値が鬱陶しいので作成
"""
class ParsedEffect(object):
    __verbose_description = None
    __description = None
    __is_unique = False
    __formula = None
    __unique_name = None
    __FIELD_LIST = [
        "verbose_description",
        "description",
        "is_unique",
        "formula",
        "unique_name",
    ]

    def __init__(
        self,
        verbose_description=None,
        description=None,
        is_unique=False,
        formula=None,
        unique_name=None,
        stats_pair=None,
    ):
        self.__verbose_description = verbose_description
        self.__description = description
        self.__is_unique = is_unique
        self.__formula = formula
        self.__unique_name = unique_name

    @property
    def verbose_description(self):
        return self.__verbose_description

    @verbose_description.setter
    def verbose_description(self, value):
        self.__verbose_description = value

    @property
    def description(self):
        return self.__description

    @description.setter
    def description(self, value):
        self.__description = value

    @property
    def is_unique(self):
        return self.__is_unique

    @is_unique.setter
    def is_unique(self, value):
        self.__is_unique = value

    @property
    def formula(self):
        return self.__formula

    @formula.setter
    def formula(self, value):
        self.__formula = value

    @property
    def unique_name(self):
        return self.__unique_name

    @unique_name.setter
    def unique_name(self, value):
        self.__unique_name = value

    @property
    def stats_pair(self):
        return self.__stats_pair

    @stats_pair.setter
    def stats_pair(self, value):
        self.__stats_pair = value

    def getall(self):
        out = dict()
        for field_name in self.__FIELD_LIST:
            out[field_name] = getattr(self, field_name)

        return out
