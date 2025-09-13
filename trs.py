#!/home/eric/miniconda3/envs/learn/bin/python3
# -*- coding: UTF-8 -*-
import edge_tts
import warnings

import os

warnings.filterwarnings("ignore", category=DeprecationWarning)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import asyncio
import re
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
import pygame


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


def parse_bing_dict_entry(text):
    # 提取发音部分
    pronunciation_pattern = r"美\[([^]]+)]，英\[([^]]+)]"
    pronunciation_match = re.search(pronunciation_pattern, text)

    result = {}

    if pronunciation_match:
        result["us_pronunciation"] = pronunciation_match.group(1)
        result["uk_pronunciation"] = pronunciation_match.group(2)
        # 移除发音部分，以便后续处理
        text = text[pronunciation_match.end() :].strip()

    # 预定义的词性标签
    pos_tags = ["pron.", "adj.", "adv.", "conj.", "网络释义"]

    # 按分号分割字符串，但保留分割符？不，我们按分号分割，然后去掉每个片段前后的空格
    segments = [seg.strip() for seg in text.split("；") if seg.strip()]

    current_pos = None
    for seg in segments:
        # 检查当前片段是否以某个词性标签开头
        found = False
        for tag in pos_tags:
            if seg.startswith(tag):
                # 如果当前已经有一个词性在记录中，则先将之前的词性释义合并成字符串存入结果
                if current_pos is not None:
                    # 将当前词性的所有释义项用分号连接
                    result[current_pos] = "；".join(result[current_pos])
                current_pos = tag
                # 去掉标签，获取释义部分
                definition = seg[len(tag) :].strip()
                # 如果释义以冒号开头，去掉冒号
                if definition.startswith("："):
                    definition = definition[1:].strip()
                result[current_pos] = [definition]
                found = True
                break
        if not found and current_pos is not None:
            # 当前片段不是词性标签，则添加到当前词性的释义列表中
            result[current_pos].append(seg)

    # 处理最后一个词性
    if current_pos is not None:
        result[current_pos] = "；".join(result[current_pos])

    return result


def get_translation_from_bing(word: str):
    response = requests.get(
        f"https://cn.bing.com/dict/{word}?mkt=zh-CN&setlang=ZH"
    ).text
    soup = BeautifulSoup(response, "html.parser")
    metas = soup.find_all("meta")
    for meta in metas:
        if "name" in meta.attrs:
            if meta.attrs["name"] == "description":
                data = meta.attrs["content"]
                result = parse_bing_dict_entry(data)
                return result
    return dict()


def output_translation_from_bing(word: str, pos_def_list: Dict[str, str]):
    console = Console()
    title = (
        word
        + " 美: "
        + pos_def_list["us_pronunciation"]
        + " 英: "
        + pos_def_list["uk_pronunciation"]
    )
    table = Table(title=title, box=box.SQUARE_DOUBLE_HEAD)
    table.add_column("词性", justify="center", style="red")
    table.add_column("词义", justify="center", style="green")
    raw_trans = "词性,词义\n"

    del pos_def_list["uk_pronunciation"]
    del pos_def_list["us_pronunciation"]
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
  trs [-h] [-c] [-s] [-v] [text ...]

参数:
  text         要翻译的文本，可以是一个单词或一个句子，带引号或不带引号

选项:
  -h, --help   显示此帮助信息
  -c           拷贝
  -s           保存
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
    parser.add_argument("-v", "--voice", action="store_true", help="阅读当前文本")
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


async def synthesize_and_play(text, voice="en-US-GuyNeural"):
    """
    使用Edge-TTS将文本合成为语音并立即播放，使用临时文件自动清理。

    Args:
        text (str): 要合成的英文文本。
        voice (str): 选择的语音名称。
    """
    # 创建一个临时文件，'delete=False'意味着我们先不让系统自动删，等播放完再手动删。
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        temp_path = tmp_file.name

    try:
        # 1. 合成语音并写入临时文件
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_path)

        # 2. 初始化Pygame mixer并播放
        pygame.mixer.init()
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()

        # 3. 等待播放完毕
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        # 4. 无论成功与否，确保删除临时文件
        pygame.mixer.quit()  # 确保退出mixer，释放文件占用
        try:
            os.unlink(temp_path)
        except OSError as e:
            print(f"删除文件时出错: {e}")


def handle_voice():
    synthesize_and_play()


async def main():
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

    raw_content = ""
    if arg_num == 1 and is_a_single_word(args.text[0]):
        raw_content = args.text[0]
        translation = process_word(args.text[0])
    else:
        raw_content = " ".join(args.text)
        translation = process_sentence(" ".join(args.text))
    if args.copy:
        handle_copy()
    if args.save:
        handle_save()
    if args.voice and not raw_content == "":
        await synthesize_and_play(raw_content)


if __name__ == "__main__":
    asyncio.run(main())
