# -*- coding: utf-8 -*-
# @Time: 2023/7/2 20:48
# @FileName: Tool.py
# @Software: PyCharm
# @GitHub: KimmyXYC
import hashlib


def cal_md5(string):
    md5_hash = hashlib.md5()
    md5_hash.update(string.encode('utf-8'))
    return md5_hash.hexdigest()
