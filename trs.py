#!/home/eric/miniconda3/envs/learn/bin/python3
# -*- coding: UTF-8 -*-
import os
import sys
import pyperclip
import tempfile
import argparse
from typing import Dict
from openai.resources.chat.completions.messages import Messages
import requests
from openai import OpenAI
from rich.panel import Panel
from rich import box
from rich.table import Table
from rich.console import Console
from bs4 import BeautifulSoup


def is_a_single_word(content: str):
    if " " not in content.strip():
        return True
    return False


def save_translation(translation: str):
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, "last_translation.txt")
    with open(file_path, "w", encoding="UTF-8") as f:
        f.write(translation)


def handle_copy():
    copy_to_the_clipboard(get_last_translation())
    print("已将上一次翻译的结果拷贝到剪切板")


def handle_save():
    save_to_the_local(get_last_translation())
    print("已将上一次翻译的结果存储到本地")


def copy_to_the_clipboard(words: str):
    pyperclip.copy(words)


def save_to_the_local(words: str):
    default_path = "./translation.txt"
    user_path = input("请您选择保存路径(默认./translation.txt):")
    if user_path == "":
        user_path = default_path
    try:
        with open(user_path, "w") as f:
            f.write(words)
    except:
        print("请输入正确路径")
        exit(0)


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
    raw_trans = "词性,词义\n"
    for pos, define in pos_def_list.items():
        table.add_row(pos, define)
        raw_trans += pos + "," + define + "\n"
    console.print(table)
    return raw_trans


def process_word(word: str):
    word = word.strip()
    pos_def_list = get_translation_from_bing(word)
    raw_trans = output_translation_from_bing(word, pos_def_list)
    save_translation(raw_trans)
    return raw_trans


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
    save_translation(translation)
    return translation


def print_help():
    help_text = """
翻译工具 (trs)

使用方法:
  trs [-h] [-c] [-s] [text ...]

参数:
  text         要翻译的文本，可以是一个单词或一个句子，带引号或不带引号

选项:
  -h, --help   显示此帮助信息
  -c           启用某种功能
  -s           启用另一种功能

示例:
  trs what is your position
  trs "what is your position"
  trs what
  trs "what"
  trs -c
  trs -s
  trs -c hello world
  trs -s hello world
    """
    print(help_text)


def args_init():
    parser = argparse.ArgumentParser(
        description="trs翻译工具", add_help=False, usage="trs [-h] [-c] [-s] [text ...]"
    )
    parser.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="若当前有待翻译文本输入，则将当前文本翻译的结果拷贝到剪切板，否则将上一次翻译的结果拷贝到剪切板",
    )
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="若当前有待翻译文本输入，则将当前文本翻译的结果保存到本地，否则将上一次翻译的结果保存到本地",
    )
    parser.add_argument(
        "-x", "--translate_clip", action="store_true", help="直接翻译剪切板"
    )
    parser.add_argument("-h", "--help", action="store_true", help="显示帮助信息")
    parser.add_argument("text", nargs="*", help="待翻译文本")
    return parser.parse_args()


def get_last_translation():
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, "last_translation.txt")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines)
    except:
        print("没有历史翻译")
        exit(0)


def handle_translate_clip():
    content = pyperclip.paste()
    if is_a_single_word(content):
        translation = process_word(content)
    else:
        translation = process_sentence(content)
    return translation


def main():
    args = args_init()
    arg_num = len(args.text)
    if args.help:
        print_help()
        exit(0)
    if arg_num == 0:
        if args.translate_clip:
            handle_translate_clip()
            if not args.copy and not args.save:
                exit(0)
        if args.copy and not args.save:
            handle_copy()
            exit(0)
        if args.save and not args.copy:
            handle_save()
            exit(0)
        if args.copy and args.save:
            handle_copy()
            handle_save()
            exit(0)
        print("请输入要翻译的内容")
        sys.exit(0)
    if arg_num == 1 and is_a_single_word(args.text[0]):
        translation = process_word(args.text[0])
    else:
        translation = process_sentence(" ".join(args.text))
    if args.copy:
        handle_copy()
    if args.save:
        handle_save()


if __name__ == "__main__":
    main()
