#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 iOS 快捷方式「小宇宙 → RSS」。

设计（最简、最不易出错）：
  1. 读取剪贴板（用户在小宇宙里已复制链接）
  2. 询问确认链接（可编辑）
  3. URL 编码
  4. 打开  <转换页>?url=<编码后的链接>
  5. 转换页自动开始转换并显示 RSS 地址
"""
import plistlib
import os

OUT = "/var/minis/workspace/xiaoyuzhou_rss/dist/小宇宙转RSS.shortcut"
PAGE = "https://q1ngyunn.github.io/xyz2rss/"


def act(ident, **params):
    return {"WFWorkflowActionIdentifier": ident, "WFWorkflowActionParameters": params}


def build():
    actions = [
        # 1) 取剪贴板里的小宇宙链接
        act("is.workflow.actions.getclipboard"),

        # 2) 让用户确认/修改（默认值 = 剪贴板内容）
        act("is.workflow.actions.ask",
            WFAskActionPrompt="确认小宇宙播客链接",
            WFInputType="Text",
            WFAskActionDefaultAnswer={
                "Value": {"Type": "ExtensionInput"},
                "WFSerializationType": "WFTextTokenString",
            }),

        # 3) URL 编码，便于放进查询参数
        act("is.workflow.actions.urlencode", WFEncodeMode="Encode"),

        # 4) 与转换页地址拼接（上一步的输出作为此动作的输入变量）
        act("is.workflow.actions.text",
            WFTextActionText={
                "Value": {
                    "string": PAGE + "?url=\ufffc",
                    "attachmentsByRange": {
                        "{8, 1}": {
                            "Type": "ActionOutput",
                            "OutputName": "URL 编码的文本",
                            "OutputUUID": "__ENC__",
                        }
                    },
                },
                "WFSerializationType": "WFTextTokenString",
            }),

        # 5) 打开转换页
        act("is.workflow.actions.openurl"),
    ]

    # 给编码动作一个固定 UUID，供上面引用
    for a in actions:
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.urlencode":
            a["WFWorkflowActionParameters"]["UUID"] = "__ENC__"

    return {
        "WFWorkflowClientVersion": "1146.14",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowName": "小宇宙 → RSS",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 4282601983,
            "WFWorkflowIconGlyphNumber": 59511,
        },
        "WFWorkflowInputContentItemClasses": [
            "WFURLContentItem", "WFStringContentItem", "WFRichTextContentItem",
        ],
        "WFWorkflowTypes": ["NCWidget"],
        "WFWorkflowActions": actions,
    }


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        plistlib.dump(build(), f, fmt=plistlib.FMT_BINARY)
    print("written:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
