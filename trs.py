#!/home/eric/miniconda3/envs/learn/bin/python3
# -*- coding: UTF-8 -*-
import os
import sys
from typing import Dict
from openai.resources.chat.completions.messages import Messages
import requests
from openai import OpenAI
from rich.panel import Panel
from rich import box
from rich.table import Table
from rich.console import Console
from bs4 import BeautifulSoup


def get_translation_from_bing(word: str):
    response = requests.get(
        f"https://cn.bing.com/dict/{word}?mkt=zh-CN&setlang=ZH"
    ).text
    soup = BeautifulSoup(response, "html.parser")
    spans = soup.find_all("span", class_=["pos", "def b_regtxt"])
    pos_list = []
    def_list = []
    cnt = 0
    for span in spans:
        if cnt == 0:
            pos_list.append(span.get_text())
            cnt = 1
        else:
            def_list.append(span.get_text())
            cnt = 0
    return dict(zip(pos_list, def_list))


def output_translation_from_bing(word: str, pos_def_list: Dict[str, str]):
    console = Console()
    table = Table(title=word, box=box.SQUARE_DOUBLE_HEAD)
    table.add_column("词性", justify="center", style="red")
    table.add_column("词义", justify="center", style="green")
    for pos, define in pos_def_list.items():
        table.add_row(pos, define)
    console.print(table)


def process_word(word: str):
    pos_def_list = get_translation_from_bing(word)
    output_translation_from_bing(word, pos_def_list)


def check_api_key_exists():
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("请先配置好DASHSCOPE_API_KEY")
        exit(0)


def get_translation_from_ai(sentence: str):
    client = OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    messages = [{"role": "user", "content": sentence}]
    translation_options = {"source_lang": "auto", "target_lang": "Chinese"}
    translation = client.chat.completions.create(
        model="qwen-mt-turbo",
        messages=messages,
        extra_body={"translation_options": translation_options},
    )
    return translation.choices[0].message.content


def output_translation_from_ai(translation: str):
    console = Console()
    panel = Panel(f"[green]{translation}[/green]", title="[red]译文[/red]")
    console.print(panel)


def process_sentence(sentence: str):
    check_api_key_exists()
    translation = get_translation_from_ai(sentence)
    output_translation_from_ai(translation)


def main():
    arg_num = len(sys.argv) - 1
    if arg_num == 0:
        print("请输入要翻译的内容")
        sys.exit(0)
    if arg_num == 1 and " " not in sys.argv[1]:
        process_word(sys.argv[1])
    else:
        process_sentence(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()
