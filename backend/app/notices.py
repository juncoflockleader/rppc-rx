"""Disclaimers + copyright notices (design §19.2-19.3).

The interpretive-persona disclaimer must appear in every transcript/export.
"""
from __future__ import annotations

DISCLAIMER_EN = (
    "This episode uses interpretive AI-generated personas based on selected "
    "sources and editorial design. It does not represent the actual historical "
    "figures."
)
DISCLAIMER_ZH = (
    "本内容使用基于选定资料和编辑设定生成的解释性 AI 角色，不代表真实历史人物本人。"
)
SOURCE_COPYRIGHT = (
    "Generated from user-supplied material. Please ensure you have the right to "
    "use any uploaded sources; generated outputs may be restricted if sources "
    "contain copyrighted material."
)


def notices() -> dict:
    return {"disclaimer_en": DISCLAIMER_EN, "disclaimer_zh": DISCLAIMER_ZH,
            "source_copyright": SOURCE_COPYRIGHT}
