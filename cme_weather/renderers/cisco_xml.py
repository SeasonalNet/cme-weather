from __future__ import annotations

import html

from flask import Response


def escape_xml(value: str) -> str:
    return html.escape(value or "", quote=False)


def xml_response(xml: str) -> Response:
    body = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml
    return Response(body, status=200, mimetype="text/xml")


def text_page(*, title: str, prompt: str, text: str) -> str:
    return f"""
<CiscoIPPhoneText>
  <Title>{escape_xml(title)}</Title>
  <Prompt>{escape_xml(prompt)}</Prompt>
  <Text>{escape_xml(text)}</Text>
</CiscoIPPhoneText>
""".strip()


def input_page(*, title: str, prompt: str, url: str, default_value: str) -> str:
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
  </InputItem>
</CiscoIPPhoneInput>
""".strip()
