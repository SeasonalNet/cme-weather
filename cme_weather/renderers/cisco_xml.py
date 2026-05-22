from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Iterable

from flask import Response


@dataclass(frozen=True)
class SoftKeyItem:
    name: str
    url: str
    position: int
    url_down: str | None = None


def escape_xml(value: str) -> str:
    return html.escape(value or "", quote=False)


def xml_response(xml: str) -> Response:
    body = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
    return Response(body, status=200, mimetype="text/xml")


def soft_key_item(item: SoftKeyItem) -> str:
    url_down = f"\n    <URLDown>{escape_xml(item.url_down)}</URLDown>" if item.url_down else ""
    return f"""
  <SoftKeyItem>
    <Name>{escape_xml(item.name)}</Name>
    <URL>{escape_xml(item.url)}</URL>{url_down}
    <Position>{item.position}</Position>
  </SoftKeyItem>
""".rstrip()


def soft_key_items(items: Iterable[SoftKeyItem] | None) -> str:
    if items is None:
        return ""
    rendered = [soft_key_item(item) for item in items]
    if not rendered:
        return ""
    return "\n" + "\n".join(rendered)


def text_page(*, title: str, prompt: str, text: str, softkeys: Iterable[SoftKeyItem] | None = None) -> str:
    return f"""
<CiscoIPPhoneText>
  <Title>{escape_xml(title)}</Title>
  <Prompt>{escape_xml(prompt)}</Prompt>
  <Text>{escape_xml(text)}</Text>{soft_key_items(softkeys)}
</CiscoIPPhoneText>
""".strip()


def input_page(
    *,
    title: str,
    prompt: str,
    url: str,
    default_value: str,
    softkeys: Iterable[SoftKeyItem] | None = None,
) -> str:
    return f"""
<CiscoIPPhoneInput>
  <Title>{escape_xml(title)}</Title>
  <Prompt>{escape_xml(prompt)}</Prompt>
  <URL>{escape_xml(url)}</URL>
  <InputItem>
    <DisplayName>Location</DisplayName>
    <QueryStringParam>q</QueryStringParam>
    <DefaultValue>{escape_xml(default_value)}</DefaultValue>
    <InputFlags>A</InputFlags>
  </InputItem>{soft_key_items(softkeys)}
</CiscoIPPhoneInput>
""".strip()
