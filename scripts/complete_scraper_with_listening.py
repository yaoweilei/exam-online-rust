#!/usr/bin/env python3
"""
完整的爬虫脚本 - 整合所有功能
包括：题目爬取 + 听力材料完整处理
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 从jlpt_struct.json加载JLPT结构定义
def load_jlpt_structure():
    """从jlpt_struct.json加载JLPT结构定义，构建section_name映射"""
    struct_file = Path(__file__).parent.parent / "data" / "paper" / "jlpt_struct.json"
    if not struct_file.exists():
        logger.warning(f"未找到JLPT结构文件: {struct_file}，使用默认配置")
        return {}
    
    try:
        with open(struct_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 构建section名称映射: {level: {section_id: section_name}}
        section_names = {}
        for level_data in data['JLPT_Exam_Structure']:
            level = level_data['level']
            section_names[level] = {}
            
            # N3/N4/N5特殊处理：需要累计问题编号
            # N3有两个section：文字・語彙(1-5) 和 言語知識・読解(1-7)
            # 实际的section_id应该是连续的：1.01-1.12
            question_offset = 0  # 问题编号偏移量
            
            for section_idx, section_data in enumerate(level_data['sections']):
                section_name = section_data['section_name']
                
                # 确定section前缀（1=言語知識・読解, 2=聴解）
                if '聴解' in section_name or '聴' in section_name:
                    section_prefix = '2'
                    question_offset = 0  # 听力题重新从1开始
                else:
                    section_prefix = '1'
                
                # 处理subsections
                if 'subsections' in section_data and section_data['subsections']:
                    for subsection in section_data['subsections']:
                        for q in subsection['questions']:
                            # 使用累计的问题编号
                            actual_q_number = q['q_number'] + question_offset
                            section_id = f"{section_prefix}.{actual_q_number:02d}"
                            # 使用 q_type 作为 section_name
                            section_names[level][section_id] = f"問題{actual_q_number} - {q['q_type']}"
                
                # 处理直接的questions
                if 'questions' in section_data:
                    for q in section_data['questions']:
                        # 使用累计的问题编号
                        actual_q_number = q['q_number'] + question_offset
                        section_id = f"{section_prefix}.{actual_q_number:02d}"
                        # 使用 q_type 作为 section_name
                        section_names[level][section_id] = f"問題{actual_q_number} - {q['q_type']}"
                
                # 更新偏移量：如果是非听力section，累加当前section的最大问题编号
                if section_prefix == '1':
                    # 找到当前section的最大问题编号
                    max_q_num = 0
                    if 'subsections' in section_data and section_data['subsections']:
                        for subsection in section_data['subsections']:
                            for q in subsection['questions']:
                                max_q_num = max(max_q_num, q['q_number'])
                    if 'questions' in section_data:
                        for q in section_data['questions']:
                            max_q_num = max(max_q_num, q['q_number'])
                    question_offset += max_q_num
        
        logger.info(f"✓ 已从jlpt_struct.json加载section名称定义")
        return section_names
    except Exception as e:
        logger.error(f"加载JLPT结构文件失败: {e}")
        return {}


# 从jlpt_struct.json加载section名称
JLPT_SECTION_NAMES = load_jlpt_structure()

# 如果加载失败，使用备用配置
if not JLPT_SECTION_NAMES:
    logger.warning("使用备用section名称配置")
    JLPT_SECTION_NAMES = {
        'N1': {
            # 言語知識（文字・語彙・文法）
            '1.01': '問題1 - 漢字読み',
            '1.02': '問題2 - 文脈規定',
            '1.03': '問題3 - 言い換え類義',
            '1.04': '問題4 - 用法',
            '1.05': '問題5 - 文の文法1(文法形式の判断)',
            '1.06': '問題6 - 文の文法2(文の組み立て)',
            '1.07': '問題7 - 文章の文法',
            # 読解
            '1.08': '問題8 - 内容理解(短文)',
            '1.09': '問題9 - 内容理解(中文)',
            '1.10': '問題10 - 内容理解(長文)',
            '1.11': '問題11 - 統合理解',
            '1.12': '問題12 - 主張理解(長文)',
            '1.13': '問題13 - 情報検索',
            # 聴解
            '2.01': '問題1 - 課題理解',
            '2.02': '問題2 - ポイント理解',
            '2.03': '問題3 - 概要理解',
            '2.04': '問題4 - 即時応答',
            '2.05': '問題5 - 統合理解',
        },
        'N2': {
            # 言語知識（文字・語彙・文法）
            '1.01': '問題1 - 漢字読み',
            '1.02': '問題2 - 表記',
            '1.03': '問題3 - 語形成',
            '1.04': '問題4 - 文脈規定',
            '1.05': '問題5 - 言い換え類義',
            '1.06': '問題6 - 用法',
            '1.07': '問題7 - 文の文法1(文法形式の判断)',
            '1.08': '問題8 - 文の文法2(文の組み立て)',
            '1.09': '問題9 - 文章の文法',
            # 読解
            '1.10': '問題10 - 内容理解(短文)',
            '1.11': '問題11 - 内容理解(中文)',
            '1.12': '問題12 - 統合理解',
            '1.13': '問題13 - 主張理解(長文)',
            '1.14': '問題14 - 情報検索',
            # 聴解
            '2.01': '問題1 - 課題理解',
            '2.02': '問題2 - ポイント理解',
            '2.03': '問題3 - 概要理解',
            '2.04': '問題4 - 即時応答',
            '2.05': '問題5 - 統合理解',
        },
        'N3': {
            # 言語知識（文字・語彙・文法）
            '1.01': '問題1 - 漢字読み',
            '1.02': '問題2 - 表記',
            '1.03': '問題3 - 文脈規定',
            '1.04': '問題4 - 言い換え類義',
            '1.05': '問題5 - 用法',
            '1.06': '問題6 - 文の文法1(文法形式の判断)',
            '1.07': '問題7 - 文の文法2(文の組み立て)',
            '1.08': '問題8 - 文章の文法',
            # 読解
            '1.09': '問題9 - 内容理解(短文)',
            '1.10': '問題10 - 内容理解(中文)',
            '1.11': '問題11 - 内容理解(長文)',
            '1.12': '問題12 - 情報検索',
            # 聴解
            '2.01': '問題1 - 課題理解',
            '2.02': '問題2 - ポイント理解',
            '2.03': '問題3 - 発話表現',
            '2.04': '問題4 - 即時応答',
            '2.05': '問題5 - 統合理解',
        }
    }

# 听力section完整模板
# 注意：section_name会在运行时从题型定义中获取，这里保留其他配置
LISTENING_SECTIONS = {
    "2.01": {
        "section_title": "問題1  では、まず質問を聞いてください。それから話を聞いて、用紙の１から４の中から、最もよいものを一つ選びなさい。",
        "description": "课题理解题",
        "passage_count": 6
    },
    "2.02": {
        "section_title": "問題2  では、まず質問を聞いてください。そのあと、用紙のせんたくしを読んでください。読む時間があります。それから話を聞いて、１から４の中から、最もよいものを一つ選びなさい。",
        "description": "要点理解题",
        "passage_count": 6
    },
    "2.03": {
        "section_title": "問題3  では、用紙に何も印刷されていません。この問題は、全体としてどんな内容かを聞く問題です。話の前に質問はありません。まず話を聞いてください。それから、質問と選択肢を聞いて、１から４の中から、最もよいものを一つ選びなさい。",
        "description": "概要理解题",
        "passage_count": 5
    },
    "2.04": {
        "section_title": "問題4  では、問題用紙に何も印刷されていません。まず文を聞いてください。それから、それに対する返事を聞いて、１から３の中から、最もよいものを一つ選びなさい。",
        "description": "即时应答题",
        "passage_count": 14,
        "options_count": 3
    },
    "2.05": {
        "section_title": "問題5  では長めの話を聞きます。この問題には練習はありません。問題用紙に、メモをとってもかまいません。",
        "description": "综合理解题",
        "passage_count": 3,
        "questions_per_passage": 2
    }
}


class CompleteScraper:
    """完整的爬虫 - 包含听力材料处理"""
    
    def __init__(self, exam_date: str, level: str, headless=False):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.exam_date = exam_date
        self.level = level.lower()
        
        self.sections = []
        self.current_section = None
        self.current_passage = None
        
        # 目录设置 - 音频和图片按照层级结构存放
        base_dir = Path(__file__).parent.parent
        # 音频路径: data/audio/jlpt/n1/2024_12/ (保持日期子目录)
        self.audio_dir = base_dir / "data" / "audio" / "jlpt" / self.level / self.exam_date
        # 图片路径: data/image/jlpt/n1/ (直接在级别目录下，不要日期子目录)
        self.image_dir = base_dir / "data" / "image" / "jlpt" / self.level
        # 试卷路径: data/paper/jlpt/n1/ (直接在级别目录下)
        self.paper_dir = base_dir / "data" / "paper" / "jlpt" / self.level
        
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.paper_dir.mkdir(parents=True, exist_ok=True)
        
        self.setup_driver()
    
    def setup_driver(self):
        """配置浏览器"""
        logger.info("正在初始化浏览器...")
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        logger.info("✓ 浏览器初始化成功")

    def get_section_id(self, section_type: str, problem_number: int) -> str:
        """生成section_id（字符串格式）"""
        if section_type == "listening":
            return f"2.{problem_number:02d}"
        else:
            return f"1.{problem_number:02d}"
    
    def get_section_name(self, section_id: str) -> str:
        """根据section_id获取标准的section_name"""
        # 使用题型定义中的标准名称
        level = self.level.upper()
        if level in JLPT_SECTION_NAMES:
            section_name = JLPT_SECTION_NAMES[level].get(section_id)
            if section_name:
                return section_name
        
        # 如果未找到，返回默认格式
        problem_num = section_id.split('.')[1]
        return f"問題{problem_num}"
    
    def get_section_type_by_id(self, section_id: str) -> str:
        """
        根据section_id获取section_type
        统一分为三类：vocabulary（词汇语法）、reading（读解）、listening（听力）
        """
        # 听力题：2.xx
        if section_id.startswith('2.'):
            return 'listening'
        
        # 词汇语法和读解：1.xx
        # 根据级别和section_id判断
        level = self.level.upper()
        
        if level == 'N1':
            # N1: 1.01-1.07 vocabulary, 1.08-1.13 reading
            section_num = int(section_id.split('.')[1])
            return 'vocabulary' if section_num <= 7 else 'reading'
        elif level == 'N2':
            # N2: 1.01-1.09 vocabulary, 1.10-1.14 reading
            section_num = int(section_id.split('.')[1])
            return 'vocabulary' if section_num <= 9 else 'reading'
        else:  # N3
            # N3: 1.01-1.08 vocabulary, 1.09-1.12 reading
            section_num = int(section_id.split('.')[1])
            return 'vocabulary' if section_num <= 8 else 'reading'
    
    def detect_section_info(self) -> Optional[Dict[str, Any]]:
        """检测section信息"""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r'(問題\d+[^\n]{10,200})', body_text)
            if match:
                section_title = match.group(1).strip()
                problem_match = re.search(r'問題(\d+)', section_title)
                if problem_match:
                    problem_number = int(problem_match.group(1))
                    # 根据标题和problem_number判断类型
                    section_type = self.detect_section_type(section_title, problem_number)
                    return {
                        "title": section_title,
                        "number": problem_number,
                        "type": section_type
                    }
            return None
        except:
            return None
    
    def detect_section_type(self, title: str, problem_number: int = 0) -> str:
        """检测section类型"""
        # 优先根据标题判断（最准确）
        if "聴解" in title or "聞" in title or "聴" in title or "では、まず質問を聞いてください" in title:
            return "listening"
        
        # 检查是否是情報検索题（包含"右のページ"或"みぎのページ"关键词）
        if "情報検索" in title or "右のページ" in title or "みぎのページ" in title:
            return "reading"
        
        # 根据problem_number判断（最可靠）
        # N1: 1-7: vocabulary, 8-13: reading, 14+: listening
        # N2: 1-7: vocabulary, 8-14: reading, 15+: listening
        # N3: 1-5: vocabulary, 6-8: grammar, 9-12: reading, 13+: listening
        if problem_number <= 7:
            # 問題1-7都是vocabulary/grammar
            return "vocabulary"
        elif problem_number <= 14:
            # 問題8-14都是reading
            return "reading"
        else:
            return "listening"
    
    def find_or_create_section(self, section_info: Dict[str, Any]):
        """查找或创建section"""
        section_title = section_info["title"]
        detected_type = section_info["type"]  # 从页面检测到的类型
        problem_number = section_info["number"]
        
        for section in self.sections:
            if section["section_title"] == section_title:
                self.current_section = section
                return
        
        # 计算正确的section_id（考虑已有的sections）
        section_id = self.calculate_next_section_id(detected_type)
        
        # 根据section_id获取标准的section_name和section_type
        section_name = self.get_section_name(section_id)
        section_type = self.get_section_type_by_id(section_id)  # 使用统一的类型
        
        self.current_section = {
            "section_id": section_id,
            "section_title": section_title,
            "section_name": section_name,
            "section_type": section_type,  # 统一的类型：vocabulary/reading/listening
            "description": section_title,
            "passages": []
        }
        self.sections.append(self.current_section)
        self.current_passage = None
        logger.info(f"  🆕 创建section {section_id}: {section_name} ({section_type})")
    
    def calculate_next_section_id(self, section_type: str) -> str:
        """
        计算下一个section_id
        根据已有的sections和section_type，计算正确的编号
        """
        if section_type == "listening":
            # 听力题：找到最大的2.xx编号，然后+1
            listening_sections = [s for s in self.sections if s.get("section_id", "").startswith("2.")]
            if listening_sections:
                max_num = max([int(s["section_id"].split(".")[1]) for s in listening_sections])
                return f"2.{max_num + 1:02d}"
            else:
                return "2.01"
        else:
            # 词汇语法/读解题：找到最大的1.xx编号，然后+1
            vocab_reading_sections = [s for s in self.sections if s.get("section_id", "").startswith("1.")]
            if vocab_reading_sections:
                max_num = max([int(s["section_id"].split(".")[1]) for s in vocab_reading_sections])
                return f"1.{max_num + 1:02d}"
            else:
                return "1.01"

    def extract_passage_text(self, container) -> Optional[str]:
        """提取阅读材料文本（包括完形填空的文章）"""
        try:
            # 方法1: 查找标准的阅读材料容器
            passage_selectors = [".passage", ".reading-text", ".article", "[class*='passage']"]
            for selector in passage_selectors:
                try:
                    passage_elem = container.find_element(By.CSS_SELECTOR, selector)
                    passage_text = passage_elem.text.strip()
                    if len(passage_text) > 50:
                        logger.info(f"  ✓ 找到阅读材料 ({len(passage_text)} 字符)")
                        return passage_text
                except:
                    continue
            
            # 方法2: 查找"文章"标识（完形填空）或带题号的文章
            try:
                page_text = container.text
                
                # 检查是否是問題7（完形填空）
                is_mondai7 = self.current_section and self.current_section.get("section_id") == "1.07"
                
                if "文章" in page_text:
                    # 提取"文章"后面的内容
                    match = re.search(r'文章\s*\n+(.*?)(?:\n\s*\([^\)]+による\)|$)', page_text, re.DOTALL)
                    
                    if match:
                        article_text = match.group(1).strip()
                        
                        # 清理题目内容（如"45. 筆者によると...\n1.xxx\n2.xxx\n..."）
                        # 匹配模式：\n数字. 题目文本\n选项列表
                        article_text = re.sub(r'\n\d+\.\s*[^\n]+\n(?:\d+\.[^\n]+\n)+', '\n', article_text)
                        
                        # 清理末尾的题目（如果文章最后有题目）
                        article_text = re.sub(r'\n\d+\.\s*[^\n]+(?:\n\d+\.[^\n]+)*$', '', article_text)
                        
                        # 清理页面元素和解析内容
                        # 1. 清理"收藏"、"纠错"、"解析"及其后面的所有内容
                        article_text = re.sub(r'\n*(?:收藏|纠错|解析).*$', '', article_text, flags=re.DOTALL)
                        
                        # 2. 清理其他常见的页面元素
                        article_text = re.sub(r'\n*(?:显示答案|隐藏答案|查看解析|提交答案).*$', '', article_text, flags=re.DOTALL)
                        
                        # 保留题号，不替换为___
                        # （题号格式如：（41）、（42）等应该保留）
                        
                        # 清理末尾多余的空白
                        article_text = article_text.strip()
                        
                        if len(article_text) > 50:
                            logger.info(f"  ✓ 找到完形填空文章 ({len(article_text)} 字符)")
                            return article_text
                
                # 方法2b: 查找以（1）、（2）等开头的段落（問題8/9）
                if not is_mondai7:
                    match = re.search(r'([（\(]\s*\d+\s*[）\)]\s*\n.*?)(?:\n\s*\n|$)', page_text, re.DOTALL)
                    if match:
                        article_text = match.group(1).strip()
                        
                        # 清理题目内容
                        article_text = re.sub(r'\n\d+\.\s*[^\n]+\n(?:\d+\.[^\n]+\n)+', '\n', article_text)
                        article_text = re.sub(r'\n\d+\.\s*[^\n]+(?:\n\d+\.[^\n]+)*$', '', article_text)
                        
                        # 清理页面元素和解析内容
                        article_text = re.sub(r'\n*(?:収藏|纠错|解析).*$', '', article_text, flags=re.DOTALL)
                        article_text = re.sub(r'\n*(?:显示答案|隐藏答案|查看解析|提交答案).*$', '', article_text, flags=re.DOTALL)
                        
                        article_text = article_text.strip()
                        
                        if len(article_text) > 50:
                            logger.info(f"  ✓ 找到带题号的文章 ({len(article_text)} 字符)")
                            return article_text
            except Exception as e:
                logger.debug(f"方法2失败: {e}")
            
            # 方法3: 查找长文本段落
            try:
                is_mondai7 = self.current_section and self.current_section.get("section_id") == "1.07"
                paragraphs = container.find_elements(By.TAG_NAME, "p")
                for para in paragraphs:
                    text = para.text.strip()
                    if len(text) > 200:
                        # 清理题目内容（如"45. 筆者によると...\n1.xxx\n2.xxx\n..."）
                        text = re.sub(r'\n\d+\.\s*[^\n]+\n(?:\d+\.[^\n]+\n)+', '\n', text)
                        
                        # 清理末尾的题目
                        text = re.sub(r'\n\d+\.\s*[^\n]+(?:\n\d+\.[^\n]+)*$', '', text)
                        
                        # 清理页面元素和解析内容
                        text = re.sub(r'\n*(?:収藏|纠错|解析).*$', '', text, flags=re.DOTALL)
                        text = re.sub(r'\n*(?:显示答案|隐藏答案|查看解析|提交答案).*$', '', text, flags=re.DOTALL)
                        
                        # 保留题号，不替换为___
                        # （题号格式如：（41）、（42）等应该保留）
                        
                        # 清理末尾多余的空白
                        text = text.strip()
                        
                        if len(text) > 50:
                            logger.info(f"  ✓ 找到长段落文章 ({len(text)} 字符)")
                            return text
            except:
                pass
            
            return None
        except Exception as e:
            logger.debug(f"提取阅读材料失败: {e}")
            return None
    
    def extract_audio_url(self, container) -> Optional[str]:
        """提取音频URL"""
        try:
            # 方法1: 优先在整个页面中查找audio标签（支持多种结构）
            try:
                # 等待audio标签加载（增加等待时间）
                time.sleep(1.0)
                
                # 方法1a: 查找 span.suspend-player-audio 内的 audio 标签
                try:
                    span_elems = self.driver.find_elements(By.CSS_SELECTOR, "span.suspend-player-audio")
                    logger.info(f"  🔍 找到 {len(span_elems)} 个 span.suspend-player-audio 元素")
                    for span in span_elems:
                        audio_elems = span.find_elements(By.TAG_NAME, "audio")
                        for audio in audio_elems:
                            url = audio.get_attribute("src")
                            # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                            if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                                logger.info(f"  ✓ 找到音频URL（span.suspend-player-audio > audio）: {url[:80]}...")
                                return url
                except:
                    pass
                
                # 方法1b: 直接查找带有suspend-player-audio类的audio标签
                audio_elems = self.driver.find_elements(By.CSS_SELECTOR, "audio.suspend-player-audio")
                logger.info(f"  🔍 找到 {len(audio_elems)} 个 audio.suspend-player-audio 元素")
                
                if audio_elems:
                    for idx, elem in enumerate(audio_elems):
                        url = elem.get_attribute("src")
                        logger.info(f"  🔍 audio元素 {idx}: src={url}")
                        # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                        if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                            logger.info(f"  ✓ 找到音频URL（audio.suspend-player-audio）: {url[:80]}...")
                            return url
                
                # 方法1c: 查找任何带src的audio标签
                audio_elems = self.driver.find_elements(By.CSS_SELECTOR, "audio[src]")
                logger.info(f"  🔍 找到 {len(audio_elems)} 个 audio[src] 元素")
                
                if audio_elems:
                    for idx, elem in enumerate(audio_elems):
                        url = elem.get_attribute("src")
                        logger.info(f"  🔍 audio[src]元素 {idx}: src={url}")
                        # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                        if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                            logger.info(f"  ✓ 找到音频URL（audio[src]）: {url[:80]}...")
                            return url
                
                # 方法1d: 查找所有audio标签（不管有没有src）
                audio_elems = self.driver.find_elements(By.TAG_NAME, "audio")
                logger.info(f"  🔍 找到 {len(audio_elems)} 个 audio 元素")
                
                if audio_elems:
                    for idx, elem in enumerate(audio_elems):
                        url = elem.get_attribute("src")
                        logger.info(f"  🔍 audio元素 {idx}: src={url}")
                        # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                        if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                            logger.info(f"  ✓ 找到音频URL（audio）: {url[:80]}...")
                            return url
                        
            except Exception as e:
                logger.debug(f"方法1失败: {e}")
            
            # 方法2: 在container中查找audio标签
            try:
                audio_elems = container.find_elements(By.TAG_NAME, "audio")
                for elem in audio_elems:
                    url = elem.get_attribute("src")
                    # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                    if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                        logger.info(f"  ✓ 找到音频URL（container-audio）: {url[:80]}...")
                        return url
            except Exception as e:
                logger.debug(f"方法2失败: {e}")
            
            # 方法3: 查找source标签
            try:
                source_elems = self.driver.find_elements(By.TAG_NAME, "source")
                for elem in source_elems:
                    url = elem.get_attribute("src")
                    # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                    if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                        logger.info(f"  ✓ 找到音频URL（source）: {url[:80]}...")
                        return url
            except Exception as e:
                logger.debug(f"方法3失败: {e}")
            
            # 方法4: 从带时间轴的元素中查找音频URL
            try:
                script_elements = container.find_elements(By.CSS_SELECTOR, "[data-starttime][data-endtime]")
                if script_elements:
                    # 查找这些元素的父容器
                    parent = script_elements[0].find_element(By.XPATH, "..")
                    # 尝试从父容器中查找audio标签
                    try:
                        audio_elem = parent.find_element(By.CSS_SELECTOR, "audio")
                        url = audio_elem.get_attribute("src")
                        # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                        if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                            logger.info(f"  ✓ 找到音频URL（时间轴父容器）: {url[:80]}...")
                            return url
                    except:
                        pass
                    
                    # 尝试从data属性中获取
                    for attr in ["data-audio", "data-src", "data-url", "data-audio-url"]:
                        url = parent.get_attribute(attr)
                        # 检查URL是否包含音频特征：.mp3后缀 或 /mp3/路径
                        if url and (".mp3" in url.lower() or "/mp3/" in url.lower()):
                            logger.info(f"  ✓ 找到音频URL（{attr}）: {url[:80]}...")
                            return url
            except Exception as e:
                logger.debug(f"方法4失败: {e}")
            
            return None
        except Exception as e:
            logger.error(f"提取音频URL异常: {e}")
            return None
    
    def download_audio(self, url: str, section_id: str, passage_id: int) -> Optional[str]:
        """下载音频"""
        try:
            # 处理http://开头的URL，转换为https://
            if url.startswith("http://"):
                logger.info(f"  🔄 检测到http://，尝试转换为https://")
                https_url = url.replace("http://", "https://", 1)
                
                # 先尝试https
                try:
                    response = requests.get(https_url, timeout=30)
                    if response.status_code == 200:
                        url = https_url
                        logger.info(f"  ✓ https://访问成功")
                    else:
                        logger.info(f"  ⚠️  https://访问失败 (HTTP {response.status_code})，回退到http://")
                except:
                    logger.info(f"  ⚠️  https://访问异常，回退到http://")
            
            year = self.exam_date[:4]
            month = self.exam_date[5:7]
            filename = f"{year}年{month}月{self.level.upper()}真题_{section_id}_{passage_id:02d}.mp3"
            filepath = self.audio_dir / filename
            
            logger.info(f"  ⏬ 下载音频: {url[:80]}...")
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                logger.info(f"  ✓ 音频已下载: {filename} ({len(response.content)} bytes)")
                # 返回层级化的音频路径: /data/audio/jlpt/n1/2024_12/xxx.mp3
                return f"/data/audio/jlpt/{self.level}/{self.exam_date}/{filename}"
            else:
                logger.warning(f"  ✗ 音频下载失败: HTTP {response.status_code}")
            return None
        except Exception as e:
            logger.warning(f"  ✗ 音频下载失败: {e}")
            return None
    
    def download_question_image(self, container, question_number: int) -> Optional[str]:
        """下载question级别的图片（例如1.12节第74题的表格）"""
        try:
            # 等待图片加载
            time.sleep(0.5)
            
            # 查找图片
            images = container.find_elements(By.TAG_NAME, "img")
            
            # 找到题目相关的图片（通常是第二张图片，第一张是passage的）
            # 或者找到包含 /picture/ 路径的图片
            target_img = None
            
            for idx, img in enumerate(images):
                try:
                    src = img.get_attribute("src")
                    if not src or "data:image" in src:
                        continue
                    
                    # 跳过小图标
                    if any(keyword in src.lower() for keyword in ['logo', 'icon', 'avatar']):
                        continue
                    
                    width = img.size.get('width', 0)
                    height = img.size.get('height', 0)
                    size = width * height
                    
                    # 优先选择包含 /picture/ 路径的图片
                    is_exam_picture = "/picture/" in src.lower()
                    
                    if is_exam_picture and size > 0:
                        # 如果已经有一张图片了（passage的），这是第二张
                        if target_img is None:
                            target_img = (img, src, width, height)
                        else:
                            # 找到第二张图片，这应该是question的图片
                            target_img = (img, src, width, height)
                            break
                except:
                    continue
            
            if not target_img:
                return None
            
            img_elem, img_url, width, height = target_img
            
            # 清理URL参数
            clean_url = img_url.split('?')[0]
            
            # 下载图片
            year = self.exam_date[:4]
            month = self.exam_date[5:7]
            section_id = self.current_section.get("section_id", "unknown")
            
            # 获取扩展名
            original_ext = clean_url.split('.')[-1].lower()
            if original_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = original_ext
            else:
                ext = 'jpg'
            
            # question图片文件名格式: YYYY_MM_N3_1.12_Q74.jpg
            filename = f"{year}_{month}_{self.level.upper()}_{section_id}_Q{question_number}.{ext}"
            filepath = self.image_dir / filename
            
            logger.info(f"  ⏬ 下载question图片: {filename}")
            response = requests.get(clean_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                logger.info(f"  ✓ question图片已下载: {filename} ({len(response.content)} bytes)")
                return f"/data/image/jlpt/{self.level}/{filename}"
            else:
                logger.warning(f"  ✗ question图片下载失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"  ✗ question图片下载异常: {e}")
            return None
    
    def download_listening_image(self, container, section_id: str, question_number: int) -> Optional[str]:
        """下载听力题的图片"""
        try:
            # 等待图片加载
            time.sleep(0.5)
            
            # 查找图片
            images = container.find_elements(By.TAG_NAME, "img")
            
            # 找到最大的图片（通常是题目图）
            largest_img = None
            max_size = 0
            
            for idx, img in enumerate(images):
                try:
                    src = img.get_attribute("src")
                    if not src or "data:image" in src:
                        continue
                    
                    # 跳过小图标
                    if any(keyword in src.lower() for keyword in ['logo', 'icon', 'avatar']):
                        continue
                    
                    width = img.size.get('width', 0)
                    height = img.size.get('height', 0)
                    size = width * height
                    
                    # 优先选择包含 /picture/ 路径的图片
                    is_exam_picture = "/picture/" in src.lower()
                    
                    if is_exam_picture and size > 0:
                        largest_img = (img, src, width, height)
                        break
                    elif size > max_size and size > 2500:
                        max_size = size
                        largest_img = (img, src, width, height)
                except:
                    continue
            
            if not largest_img:
                return None
            
            img_elem, img_url, width, height = largest_img
            
            # 清理URL参数（移除OSS签名等参数）
            clean_url = img_url.split('?')[0]
            
            # 下载图片
            year = self.exam_date[:4]
            month = self.exam_date[5:7]
            
            # 获取扩展名
            original_ext = clean_url.split('.')[-1].lower()
            if original_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = original_ext
            else:
                ext = 'jpg'
            
            # 听力题图片文件名格式: YYYY_MM_N3_2.04_Q01.jpg
            filename = f"{year}_{month}_{self.level.upper()}_{section_id}_Q{question_number:02d}.{ext}"
            filepath = self.image_dir / filename
            
            logger.info(f"  ⏬ 下载听力题图片: {filename}")
            # 使用清理后的URL下载（不需要OSS参数）
            response = requests.get(clean_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                logger.info(f"  ✓ 图片已下载: {filename} ({len(response.content)} bytes)")
                return f"/data/image/jlpt/{self.level}/{filename}"
            else:
                logger.warning(f"  ✗ 图片下载失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"  ✗ 听力题图片下载异常: {e}")
            return None
    
    def download_image(self, container, section_id: str) -> Optional[str]:
        """下载图片 - 只为特定section下载"""
        try:
            # 定义应该有图片的section白名单
            # N1: 問題13（1.13）是图片题
            # N2: 問題14（1.14）是图片题
            # N3: 問題12（1.12）可能有图片（信息检索题，有时有海报/传单图片）
            # 听力题: 2.01（課題理解）每题有场景图，2.04（即時応答）选项是图片
            if self.level.lower() == 'n1':
                IMAGE_SECTIONS = ["1.13"]
            elif self.level.lower() == 'n2':
                IMAGE_SECTIONS = ["1.14"]
            else:  # N3
                IMAGE_SECTIONS = ["1.12", "2.01", "2.04"]
            
            # 检查当前section是否在白名单中
            if section_id not in IMAGE_SECTIONS:
                logger.debug(f"  ⏭️  Section {section_id} 不需要图片，跳过")
                return None
            
            # 对于N3的1.12，如果没有找到图片也不报错（因为有些年份可能没有图片）
            is_optional_image = (self.level.lower() == 'n3' and section_id == "1.12")
            
            # 滚动到container位置，确保图片加载（懒加载）
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", container)
                time.sleep(1)  # 等待滚动和图片加载
                logger.info(f"  📜 已滚动到题目位置，等待图片加载")
            except Exception as e:
                logger.debug(f"  ⚠️  滚动失败: {e}")
            
            # 等待图片加载
            time.sleep(1)
            
            # 方法1: 在整个页面中查找图片（问题13的图片可能在container外）
            all_images = self.driver.find_elements(By.TAG_NAME, "img")
            logger.info(f"  🔍 页面中找到 {len(all_images)} 个图片元素")
            
            # 方法2: 在container中查找图片
            container_images = container.find_elements(By.TAG_NAME, "img")
            logger.info(f"  🔍 container中找到 {len(container_images)} 个图片元素")
            
            # 优先使用container中的图片，如果没有则使用页面中的
            images = container_images if container_images else all_images
            
            # 找到最大的图片（通常是内容图）
            largest_img = None
            max_size = 0
            
            for idx, img in enumerate(images):
                try:
                    src = img.get_attribute("src")
                    if not src:
                        logger.info(f"  🔍 图片 {idx}: 无src属性")
                        continue
                    
                    # 跳过base64图片
                    if "data:image" in src:
                        logger.info(f"  🔍 图片 {idx}: base64图片，跳过")
                        continue
                    
                    # 跳过小图标（通常是logo或icon）
                    if any(keyword in src.lower() for keyword in ['logo', 'icon', 'avatar']):
                        logger.info(f"  🔍 图片 {idx}: 图标类图片，跳过 - {src[:60]}")
                        continue
                    
                    width = img.size.get('width', 0)
                    height = img.size.get('height', 0)
                    size = width * height
                    
                    logger.info(f"  🔍 图片 {idx}: {width}x{height} (size={size}), src={src[:80]}...")
                    
                    # 优先选择包含 /picture/ 路径的图片（题目图片）
                    is_exam_picture = "/picture/" in src.lower()
                    
                    # 如果是题目图片，优先级更高
                    if is_exam_picture:
                        logger.info(f"  ✓ 发现题目图片（/picture/路径）")
                        if size > 0:  # 只要有尺寸就选择
                            largest_img = (img, src, width, height)
                            break  # 找到题目图片就停止搜索
                    # 否则按尺寸选择（至少50x50）
                    elif size > max_size and size > 2500:
                        max_size = size
                        largest_img = (img, src, width, height)
                except Exception as e:
                    logger.debug(f"  🔍 图片 {idx} 处理失败: {e}")
                    continue
            
            if not largest_img:
                if is_optional_image:
                    logger.info(f"  ℹ️  Section {section_id} 未找到图片（此section图片为可选）")
                else:
                    logger.warning(f"  ⚠️  未找到合适的图片（需要至少50x50）")
                return None
            
            img_elem, img_url, width, height = largest_img
            logger.info(f"  ✓ 选择最大图片: {width}x{height}, URL: {img_url[:80]}...")
            
            # 清理URL参数（移除OSS签名等参数）
            # 例如: https://oss.mojidict.com/.../xxx.png?OSSAccessKeyId=...&Expires=...&Signature=...
            # 清理后: https://oss.mojidict.com/.../xxx.png
            clean_url = img_url.split('?')[0]
            logger.info(f"  🔧 清理后的URL: {clean_url}")
            
            # 下载图片
            year = self.exam_date[:4]
            month = self.exam_date[5:7]
            
            # 根据清理后URL的扩展名决定文件格式
            original_ext = clean_url.split('.')[-1].lower()
            if original_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = original_ext
            else:
                ext = 'jpg'  # 默认使用jpg
            
            filename = f"{year}_{month}_{self.level.upper()}_{section_id}.{ext}"
            filepath = self.image_dir / filename
            
            logger.info(f"  ⏬ 开始下载图片: {filename}")
            # 使用清理后的URL下载（不需要OSS参数）
            response = requests.get(clean_url, timeout=30)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                logger.info(f"  ✓ 图片已下载: {filename} ({len(response.content)} bytes)")
                # 返回层级化的图片路径: /data/image/jlpt/n1/xxx.jpg (不包含日期子目录)
                return f"/data/image/jlpt/{self.level}/{filename}"
            else:
                logger.warning(f"  ✗ 图片下载失败: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"  ✗ 图片下载异常: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def extract_listening_script_from_audio_src(self, container) -> Optional[str]:
        """从audio标签的src属性中提取听力原文URL"""
        try:
            # 查找audio标签
            audio_elem = container.find_element(By.CSS_SELECTOR, "audio")
            src = audio_elem.get_attribute("src")
            if src and ".mp3" in src:
                # 尝试获取对应的文本文件URL（通常是.txt或.vtt）
                # 这里假设文本文件与音频文件在同一目录
                text_url = src.replace(".mp3", ".txt")
                logger.info(f"  ✓ 找到音频URL，推测文本URL: {text_url}")
                return text_url
        except:
            pass
        return None
    
    def extract_listening_script(self, container) -> Optional[List[Dict]]:
        """提取听力文字（原文）- 包含时间轴信息"""
        try:
            scripts = []
            
            # 方法0: 从HTML元素中提取（包含时间信息）⭐ 最佳方法
            try:
                # 查找包含时间信息的元素
                # <p class="moji-content" data-starttime="00:00:04,000" data-endtime="00:00:08,600">
                script_elements = container.find_elements(By.CSS_SELECTOR, "[data-starttime][data-endtime]")
                
                if script_elements:
                    logger.info(f"  ✓ 找到 {len(script_elements)} 个带时间轴的元素")
                    
                    script_id = 0
                    for idx, elem in enumerate(script_elements):
                        try:
                            text = elem.text.strip()
                            start_time = elem.get_attribute("data-starttime")
                            end_time = elem.get_attribute("data-endtime")
                            
                            # 跳过包含"解析"的元素（这是解析内容，不是听力原文）
                            if "解析" in text:
                                continue
                            
                            if text and start_time and end_time:
                                # 提取说话人（字符串格式）
                                speaker = None
                                
                                # 尝试提取说话人（格式：女：内容 或 店長：内容）
                                speaker_match = re.match(r'^([^：:]+)[：:]\s*(.*)', text)
                                if speaker_match:
                                    potential_speaker = speaker_match.group(1).strip()
                                    potential_text = speaker_match.group(2).strip()
                                    if len(potential_speaker) <= 5 and potential_text:
                                        speaker = potential_speaker
                                
                                # 创建script项
                                script_item = {
                                    "id": script_id,
                                    "text": text,  # 保留完整文本（包含speaker）
                                    "start": start_time,
                                    "end": end_time
                                }
                                
                                if speaker:
                                    script_item["speaker"] = speaker
                                
                                scripts.append(script_item)
                                script_id += 1
                        except Exception as e:
                            logger.debug(f"处理元素 {idx} 失败: {e}")
                            continue
                    
                    if scripts:
                        logger.info(f"  ✓ 提取了 {len(scripts)} 条听力文字（含时间轴）")
                        return scripts
            except Exception as e:
                logger.debug(f"方法0失败: {e}")
            
            # 方法1: 从页面文本中查找"原文"部分（备用方法）
            try:
                page_text = container.text
                
                if "原文" in page_text:
                    # 提取"原文"后面的内容，直到遇到"解析"或空行
                    # 匹配模式: 原文\n内容1\n内容2\n...\n\n解析
                    match = re.search(r'原文\s*\n+(.*?)(?:\n\s*\n+解析|\n\s*\n+$|$)', page_text, re.DOTALL)
                    
                    if match:
                        original_text = match.group(1).strip()
                        
                        # 按行分割，过滤空行
                        lines = [line.strip() for line in original_text.split('\n') if line.strip()]
                        
                        logger.info(f"  ✓ 找到原文，共 {len(lines)} 行")
                        
                        for idx, line in enumerate(lines):
                            speaker = None
                            
                            # 尝试提取说话人（格式：女：内容 或 店長：内容）
                            # 匹配中文冒号或英文冒号
                            speaker_match = re.match(r'^([^：:]+)[：:]\s*(.*)', line)
                            if speaker_match:
                                potential_speaker = speaker_match.group(1).strip()
                                potential_text = speaker_match.group(2).strip()
                                
                                # 验证说话人是否合理（通常是1-5个字符）
                                if len(potential_speaker) <= 5 and potential_text:
                                    speaker = potential_speaker
                            
                            # 不跳过任何内容，保留所有文本（包括选项）
                            script_item = {
                                "id": idx,
                                "text": line,  # 保留完整文本
                                "start": "00:00:00,000",
                                "end": "00:00:00,000"
                            }
                            
                            if speaker:
                                script_item["speaker"] = speaker
                            
                            scripts.append(script_item)
                        
                        if scripts:
                            logger.info(f"  ✓ 提取了 {len(scripts)} 条听力文字")
                            return scripts
            except Exception as e:
                logger.debug(f"方法1失败: {e}")
            
            # 方法2: 查找包含"原文"的元素
            try:
                # 查找包含"原文"文本的元素
                original_elements = container.find_elements(By.XPATH, ".//*[contains(text(), '原文')]")
                
                for elem in original_elements:
                    try:
                        # 获取该元素的父容器
                        parent = elem.find_element(By.XPATH, "..")
                        full_text = parent.text.strip()
                        
                        if "原文" in full_text and len(full_text) > 10:
                            # 移除"原文"标题
                            full_text = re.sub(r'^原文\s*\n+', '', full_text)
                            
                            # 提取到"解析"之前的内容
                            if "解析" in full_text:
                                full_text = full_text.split("解析")[0].strip()
                            
                            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                            
                            for idx, line in enumerate(lines):
                                speaker = None
                                
                                speaker_match = re.match(r'^([^：:]+)[：:]\s*(.*)', line)
                                if speaker_match:
                                    potential_speaker = speaker_match.group(1).strip()
                                    potential_text = speaker_match.group(2).strip()
                                    if len(potential_speaker) <= 5 and potential_text:
                                        speaker = potential_speaker
                                
                                # 保留所有内容（包括选项）
                                script_item = {
                                    "id": idx,
                                    "text": line,  # 保留完整文本
                                    "start": "00:00:00,000",
                                    "end": "00:00:00,000"
                                }
                                
                                if speaker:
                                    script_item["speaker"] = speaker
                                
                                scripts.append(script_item)
                            
                            if scripts:
                                logger.info(f"  ✓ 从元素提取了 {len(scripts)} 条听力文字")
                                return scripts
                    except:
                        continue
            except Exception as e:
                logger.debug(f"方法2失败: {e}")
            
            # 方法3: 查找特定的CSS类
            try:
                script_selectors = [
                    ".script-content",
                    ".original-text",
                    "[class*='script']",
                    "[class*='original']"
                ]
                
                for selector in script_selectors:
                    try:
                        script_elem = container.find_element(By.CSS_SELECTOR, selector)
                        full_text = script_elem.text.strip()
                        
                        if full_text and len(full_text) > 10:
                            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                            
                            for idx, line in enumerate(lines):
                                if "原文" in line or "解析" in line:
                                    continue
                                
                                speaker = None
                                
                                speaker_match = re.match(r'^([^：:]+)[：:]\s*(.*)', line)
                                if speaker_match:
                                    potential_speaker = speaker_match.group(1).strip()
                                    potential_text = speaker_match.group(2).strip()
                                    if len(potential_speaker) <= 5 and potential_text:
                                        speaker = potential_speaker
                                
                                # 保留所有内容（包括选项）
                                script_item = {
                                    "id": idx,
                                    "text": line,  # 保留完整文本
                                    "start": "00:00:00,000",
                                    "end": "00:00:00,000"
                                }
                                
                                if speaker:
                                    script_item["speaker"] = speaker
                                
                                scripts.append(script_item)
                            
                            if scripts:
                                logger.info(f"  ✓ 从CSS类提取了 {len(scripts)} 条听力文字")
                                return scripts
                    except:
                        continue
            except Exception as e:
                logger.debug(f"方法3失败: {e}")
            
            return None
            
        except Exception as e:
            logger.debug(f"提取听力文字失败: {e}")
            return None

    def click_show_answer(self):
        """点击显示答案"""
        try:
            buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '显示答案')]")
            if buttons:
                buttons[0].click()
                time.sleep(1)
                return True
            return False
        except:
            return False
    
    def extract_correct_answer(self, container) -> int:
        """提取正确答案"""
        try:
            options = container.find_elements(By.CSS_SELECTOR, ".option-item")
            for i, opt in enumerate(options, 1):
                class_attr = opt.get_attribute("class") or ""
                if any(k in class_attr.lower() for k in ['correct', 'right', 'active']):
                    return i
            return 0
        except:
            return 0
    
    def collect_underlined_texts(self, container, include_page: bool = False) -> List[str]:
        """收集题目或整页内带下划线的文本
        方法1: 使用JavaScript直接检测computedStyle中的text-decoration（最可靠）
        方法2: 使用CSS选择器（备用方案）
        """
        texts: List[str] = []
        seen = set()
        
        # 方法1: JavaScript检测 - 直接获取所有实际渲染为下划线的元素
        try:
            js_code = """
            const container = arguments[0];
            const includeBody = arguments[1];
            const roots = includeBody ? [container, document.body] : [container];
            const results = [];
            const seen = new Set();
            
            roots.forEach(root => {
                const walker = document.createTreeWalker(
                    root,
                    NodeFilter.SHOW_ELEMENT,
                    null
                );
                
                let node;
                while (node = walker.nextNode()) {
                    const style = window.getComputedStyle(node);
                    const textDec = style.textDecoration || style.textDecorationLine || '';
                    
                    // 检查是否有下划线样式
                    if (textDec.includes('underline')) {
                        // 只取当前元素的直接文本，不包含子元素
                        let text = '';
                        for (let child of node.childNodes) {
                            if (child.nodeType === Node.TEXT_NODE) {
                                text += child.textContent;
                            }
                        }
                        
                        // 如果没有直接文本节点，才使用innerText（但排除长文本）
                        if (!text.trim() && node.innerText) {
                            text = node.innerText;
                        }
                        
                        text = text.trim();
                        if (text && !seen.has(text) && text.length > 0 && text.length < 50) {
                            seen.add(text);
                            results.push(text);
                        }
                    }
                }
            });
            
            return results;
            """
            js_results = self.driver.execute_script(js_code, container, include_page)
            if js_results:
                for text in js_results:
                    if text and text not in seen:
                        seen.add(text)
                        texts.append(text)
                logger.info(f"  ✓ JavaScript检测到 {len(texts)} 个下划线词")
                return texts
        except Exception as e:
            logger.warning(f"  ⚠️  JavaScript检测失败: {e}")
        
        # 方法2: CSS选择器（备用）
        selectors = [
            "[style*='text-decoration: underline']",
            "[style*='text-decoration:underline']",
            "[style*='underline']",
            "[style*='border-bottom']",
            ".underline",
            ".under-line",
            ".underLine",
            ".underlined",
            "[class*='underline']",
            "[class*='underlined']",
            "u",
            "ins",
            "span[data-underline]",
            "[data-underline]"
        ]
        
        roots = [container]
        if include_page:
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                if body:
                    roots.append(body)
            except Exception:
                pass

        for root in roots:
            for selector in selectors:
                try:
                    elements = root.find_elements(By.CSS_SELECTOR, selector)
                except Exception:
                    continue
                for elem in elements:
                    text = (elem.text or "").strip()
                    if not text or len(text) >= 200:
                        continue
                    if text not in seen:
                        seen.add(text)
                        texts.append(text)
        
        if texts:
            logger.info(f"  ✓ CSS选择器检测到 {len(texts)} 个下划线词")
        return texts

    def extract_target_words(self, container, section_id: str, passage_text: str = "", is_passage_level: bool = False):
        """
        提取target_words（测试词/下划线词）
        参数：
            is_passage_level: True表示提取passage级别的target_words（从文章中提取所有下划线词）
                            False表示提取question级别的target_words（从题干中提取带圈数字标记的词）
        优先级：真实下划线 > 正则提取
        
        支持的题型：
        N1: 问题1、问题3、问题4（题干）+ 问题8-问题13（阅读题）
        N2: 问题1、问题2、问题5、问题6（题干）+ 问题10-问题14（阅读题）
        N3: 问题1、问题2、问题4、问题5（题干）+ 问题9-问题11（阅读题）
        """
        try:
            level = self.level.upper()
            
            # 定义需要记录下划线的阅读题section（按级别）
            # N1: 1.08-1.13 (问题8-13)
            # N2: 1.10-1.14 (问题10-14)
            # N3: 1.09-1.11 (问题9-11)
            reading_sections = {
                'N1': {'1.08', '1.09', '1.10', '1.11', '1.12', '1.13'},
                'N2': {'1.10', '1.11', '1.12', '1.13', '1.14'},
                'N3': {'1.09', '1.10', '1.11'}
            }
            
            current_reading = reading_sections.get(level, set())
            
            # 处理阅读题的passage级别target_words
            if is_passage_level and section_id in current_reading:
                # 使用更广泛的搜索范围提取passage中的所有下划线词
                underlined_words = self.collect_underlined_texts(container, include_page=True)
                if underlined_words:
                    logger.info(f"  ✓ 从passage提取target_words: {', '.join(underlined_words)}")
                    return underlined_words
                else:
                    logger.info(f"  ⚠️  passage中未找到下划线词")
                    return None

            # 处理阅读题的question级别target_words
            if section_id in current_reading and not is_passage_level:
                # 重要：只在题干文本元素本身查找，不在整个container查找
                # container可能包含passage区域，导致提取到passage中的所有下划线词
                try:
                    # 查找题干元素（.SQTitle）
                    title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                    # 只在题干元素中查找下划线词
                    underlined_in_question = self.collect_underlined_texts(title_elem, include_page=False)
                    if underlined_in_question:
                        # 过滤出带圈数字标记的词（①-⑩开头的）
                        circled_words = [w for w in underlined_in_question if w and len(w) > 0 and w[0] in '①②③④⑤⑥⑦⑧⑨⑩']
                        if circled_words:
                            # 去掉圈数字标记，只保留词本身
                            cleaned = [w[1:].strip() for w in circled_words]
                            logger.info(f"  ✓ 从题干提取target_words: {', '.join(cleaned)}")
                            return cleaned
                        else:
                            # 如果下划线词中没有圈数字标记，直接返回所有下划线词
                            logger.info(f"  ✓ 从题干提取target_words: {', '.join(underlined_in_question)}")
                            return underlined_in_question
                except Exception as e:
                    logger.warning(f"  ⚠️  查找题干元素失败: {e}")

                # 没有找到就返回None
                logger.info(f"  ⚠️  题干中未找到下划线词")
                return None

            # 其他section：优先使用HTML元素的下划线样式（从题干中提取）
            underlined_words = self.collect_underlined_texts(container, include_page=False)
            if underlined_words:
                logger.info(f"  ✓ 找到target_words: {', '.join(underlined_words)}")
                return underlined_words

            # 問題1（漢字読み）：提取划线的汉字词
            if section_id == "1.01":
                title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                text = title_elem.text
                text = re.sub(r'^\d+[\.\．]\s*', '', text)
                matches = re.findall(r'([一-龯]{2,4})(?:した|する|な|の|を|に|が|は|へ|と|から|まで|より|で|って)', text)
                if matches:
                    word = matches[-1]
                    logger.info(f"  ✓ 从文本提取target_words: {word}")
                    return [word]

            # 問題2（漢字書き/表記）：提取划线的平假名词
            elif section_id == "1.02":
                title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                text = title_elem.text
                text = re.sub(r'^\d+[\.\．]\s*', '', text)
                matches = re.findall(r'([ぁ-ん]{3,})', text)
                if matches:
                    word = matches[0]
                    logger.info(f"  ✓ 从文本提取target_words: {word}")
                    return [word]

            # 問題3（文脈規定）：提取划线的词
            elif section_id == "1.03":
                title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                text = title_elem.text
                text = re.sub(r'^\d+[\.\．]\s*', '', text)
                matches = re.findall(r'([一-龯]{2,4})', text)
                if matches:
                    word = matches[0]
                    logger.info(f"  ✓ 从文本提取target_words: {word}")
                    return [word]

            # 問題4（類義語/言い換え類義）：题目为空仍需返回整句
            elif section_id == "1.04":
                title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                question_text = title_elem.text
                question_text = re.sub(r'^\d+[\.\．]\s*', '', question_text).strip()
                if question_text:
                    logger.info(f"  ✓ 使用整句作为target_words: {question_text}")
                    return [question_text]

            # 問題5（語彙用法/言い換え類義）：题目本身就是要测试的词
            elif section_id == "1.05":
                title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                question_text = title_elem.text
                question_text = re.sub(r'^\d+[\.\．]\s*', '', question_text).strip()
                if question_text:
                    logger.info(f"  ✓ 找到target_words: {question_text}")
                    return [question_text]
            
            # 問題6（用法）：题目本身就是要测试的词（N2）
            elif section_id == "1.06":
                title_elem = container.find_element(By.CSS_SELECTOR, ".SQTitle")
                question_text = title_elem.text
                question_text = re.sub(r'^\d+[\.\．]\s*', '', question_text).strip()
                if question_text:
                    logger.info(f"  ✓ 找到target_words: {question_text}")
                    return [question_text]

            return None
        except Exception as e:
            logger.debug(f"提取target_words失败: {e}")
            return None

    def detect_passage_type(self, container) -> str:
        """检测passage类型（text或image）"""
        try:
            # 优先级1: 检查当前section_id（最可靠的判断方式）
            # 情報検索题可能有图片
            if self.current_section:
                section_id = self.current_section.get("section_id", "")
                # N1的問題13（1.13）是图片题
                # N2的問題14（1.14）是图片题
                # N3的問題7（1.12）是图片题（情報検索）
                if (self.level.lower() == 'n1' and section_id == "1.13") or \
                   (self.level.lower() == 'n2' and section_id == "1.14") or \
                   (self.level.lower() == 'n3' and section_id == "1.12"):
                    logger.info(f"  ✓ 检测到图片类型（{section_id} - 情報検索）")
                    return "image"
                # 其他所有阅读section都是文本类型
                elif section_id in ["1.08", "1.09", "1.10", "1.11", "1.13", "1.14"]:
                    logger.info(f"  ✓ 检测到文本类型（{section_id}）")
                    return "text"
            
            # 优先级2: 检查section标题中是否明确提到图片
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                # 只有明确提到"右のページ"才是图片题
                if "右のページ" in body_text:
                    logger.info(f"  ✓ 检测到图片类型（标题中有'右のページ'）")
                    return "image"
            except:
                pass
            
            # 优先级3: 检查是否有 /picture/ 路径的图片（题目专用图片）
            images = container.find_elements(By.TAG_NAME, "img")
            for img in images:
                src = img.get_attribute("src") or ""
                # 只有包含 /picture/ 路径的才是题目图片
                if "/picture/" in src.lower():
                    logger.info(f"  ✓ 检测到图片类型（/picture/路径）")
                    return "image"
            
            # 默认返回文本类型
            logger.info(f"  ✓ 检测到文本类型（默认）")
            return "text"
        except Exception as e:
            logger.debug(f"检测passage类型失败: {e}")
            return "text"
    
    def extract_single_question(self, index: int) -> Optional[Dict]:
        """提取题目"""
        try:
            logger.info(f"\n提取第 {index} 题...")
            time.sleep(1)
            
            section_info = self.detect_section_info()
            if section_info:
                self.find_or_create_section(section_info)
            elif not self.current_section:
                self.find_or_create_section({"title": "問題1", "number": 1, "type": "vocabulary"})
            
            title_elem = self.driver.find_element(By.CSS_SELECTOR, ".SQTitle")
            question_text = title_elem.text
            container = title_elem.find_element(By.XPATH, "../..")
            
            # 调试：输出原始题目文本（检查换行符）
            if self.current_section and '組み立て' in self.current_section.get('section_name', ''):
                logger.info(f"  🔍 原始题目文本: {repr(question_text)}")
                logger.info(f"  🔍 包含换行符: {chr(10) in question_text}")
            
            # 移除题号前缀
            clean_question = re.sub(r'^\d+[\.\．]\s*', '', question_text)
            
            # 处理排序题（文の組み立て）：标准化空白占位符
            # 排序题的特征是有多个连续空格、下划线和★符号
            if self.current_section and '組み立て' in self.current_section.get('section_name', ''):
                # 排序题有4个选项，需要填入4个位置，其中一个是★
                # 标准格式：文本 ___ ___ _★_ ___ 文本
                
                # 先找到★的位置
                star_pos = clean_question.find('★')
                if star_pos >= 0:
                    # 分割为★前和★后的部分
                    before_star = clean_question[:star_pos]
                    after_star = clean_question[star_pos+1:]
                    
                    # 计算★前后有多少个空白位置
                    # 网页模式：每个占位符+分隔符 = 6个空格（4个空格的占位符 + 2个空格的分隔符）
                    # 例如：[4空格][2空格][4空格][2空格]★[2空格][4空格]
                    # ★前：12个空格 / 6 = 2个占位符
                    # ★后：6个空格 / 6 = 1个占位符
                    # 应该处理为：___ ___ _★_ ___
                    
                    # 统计★前后的连续空格数量
                    # 查找★前的所有连续空格
                    before_space_match = re.search(r'\s+$', before_star)
                    before_space_count = len(before_space_match.group()) if before_space_match else 0
                    
                    # 查找★后的所有连续空格
                    after_space_match = re.search(r'^\s+', after_star)
                    after_space_count = len(after_space_match.group()) if after_space_match else 0
                    
                    # 每6个空格代表1个占位符
                    blanks_before = before_space_count // 6
                    blanks_after = after_space_count // 6
                    
                    # 排序题总共有4个选项，需要4个位置（包括★）
                    # 如果检测到的空白数量不足3个，补齐到3个
                    total_blanks = blanks_before + blanks_after
                    if total_blanks < 3:
                        # 如果★在开头，所有空白都在后面
                        if blanks_before == 0:
                            blanks_after = 3
                        # 如果★在结尾，所有空白都在前面
                        elif blanks_after == 0:
                            blanks_before = 3
                        # 否则平均分配
                        else:
                            blanks_after = 3 - blanks_before
                    
                    # 移除所有空白占位符（下划线和空格）
                    before_star = re.sub(r'_{2,}', ' ', before_star)  # 先处理下划线
                    before_star = re.sub(r'\s{2,}', ' ', before_star).rstrip()  # 再处理空格
                    after_star = re.sub(r'_{2,}', ' ', after_star)
                    after_star = re.sub(r'\s{2,}', ' ', after_star).lstrip()
                    
                    # 重新构建question
                    placeholders_before = (' ___ ' * blanks_before) if blanks_before > 0 else ''
                    placeholders_after = (' ___ ' * blanks_after) if blanks_after > 0 else ''
                    
                    clean_question = f"{before_star}{placeholders_before} _★_{placeholders_after} {after_star}"
                    clean_question = clean_question.strip()
                    # 清理多余的空格
                    clean_question = re.sub(r'\s+', ' ', clean_question)
            
            # 提取阅读材料（完形填空的文章）
            passage_text = self.extract_passage_text(container)
            
            # 始终检测passage类型（图片题可能没有passage_text）
            passage_type = self.detect_passage_type(container)
            
            # 等待音频加载（如果是听力题）
            section_type = self.current_section.get("section_type") if self.current_section else None
            if section_type == "listening":
                time.sleep(1)  # 给音频元素加载时间
            
            audio_url = self.extract_audio_url(container)
            if not audio_url and section_type == "listening":
                logger.warning(f"  ⚠️  听力题但未找到音频URL")
            listening_scripts = self.extract_listening_script(container)
            
            option_elements = container.find_elements(By.CSS_SELECTOR, ".option-item")
            options = [opt.text for opt in option_elements]
            
            self.click_show_answer()
            correct_answer = self.extract_correct_answer(container)
            
            explanation = ""
            try:
                explanation_elem = container.find_element(By.CSS_SELECTOR, ".explanation, .analysis")
                explanation = explanation_elem.text
            except:
                pass
            
            question_data = {
                "id": index,
                "question": clean_question,
                "options": options,
                "correct_answer": correct_answer,
                "explanation": explanation
            }
            
            # 检查question是否有独立的图片（例如1.12节的题目）
            # 1.12节的题目可能有question级别的图片（表格、图表等）
            if self.current_section and self.current_section.get("section_id") == "1.12":
                # 检查container中是否有多张图片
                # 如果有多张图片，第一张是passage的，后面的是question的
                try:
                    images = container.find_elements(By.TAG_NAME, "img")
                    # 过滤掉小图标和data:image
                    valid_images = []
                    for img in images:
                        src = img.get_attribute("src")
                        if src and "data:image" not in src and "/picture/" in src.lower():
                            width = img.size.get('width', 0)
                            height = img.size.get('height', 0)
                            if width * height > 1000:  # 过滤掉太小的图片
                                valid_images.append(img)
                    
                    # 如果有2张或以上的有效图片，说明有question级别的图片
                    if len(valid_images) >= 2:
                        question_image_url = self.download_question_image(container, index)
                        if question_image_url:
                            # 使用passage字段格式（与听力题图片格式一致）
                            question_data["passage"] = {
                                "type": "image",
                                "url": question_image_url
                            }
                            logger.info(f"  ✓ 已添加question图片到passage字段: {question_image_url}")
                except Exception as e:
                    logger.warning(f"  ⚠️  检查question图片失败: {e}")
            
            logger.info(f"  ✓ 题目: {clean_question[:30]}...")
            logger.info(f"  ✓ 答案: {correct_answer if correct_answer > 0 else '未识别'}")
            
            return {
                "question": question_data,
                "passage_text": passage_text,
                "passage_type": passage_type,
                "audio_url": audio_url,
                "listening_scripts": listening_scripts,
                "_container": container  # 保存container用于下载图片
            }
        except Exception as e:
            logger.error(f"提取题目失败: {e}")
            return None

    def add_question_to_section(self, question_data: Dict):
        """添加题目到section"""
        if not self.current_section:
            return
        
        question = question_data["question"]
        passage_text = question_data.get("passage_text")
        passage_type = question_data.get("passage_type", "text")
        audio_url = question_data.get("audio_url")
        listening_scripts = question_data.get("listening_scripts")
        
        # 调试：检查question对象是否包含passage字段（question级别的图片）
        if "passage" in question and isinstance(question["passage"], dict):
            logger.info(f"  🔍 DEBUG: question对象包含passage字段: {question['passage']}")
        
        section_type = self.current_section.get("section_type")
        
        # 听力题处理（如果有audio或script，就按听力题处理）
        is_listening = (section_type == "listening") or (audio_url is not None) or (listening_scripts is not None)
        
        if is_listening and (audio_url or listening_scripts):
            # 特殊处理問題5：根据音频文件分组
            # N1的問題5：综合理解题，一段听力材料可能有多个问题（質問1、質問2）
            # N2/N3的問題5：即时应答题，每题一个音频（类似問題4）
            section_id = self.current_section.get("section_id", "")
            # 只有N1的問題5才是综合理解题
            is_mondai5 = (section_id == "2.05" and self.level.lower() == 'n1')
            
            # 检查是否需要创建新的passage
            need_new_passage = False
            if not self.current_passage:
                need_new_passage = True
            elif is_mondai5:
                # 問題5：检查题目文本，如果包含"質問1"则创建新passage
                question_text = question.get("question", "")
                if "質問1" in question_text or "1番" in question_text:
                    need_new_passage = True
            
            if need_new_passage:
                passage_id = len(self.current_section["passages"]) + 1
                # 問題5需要passage结构
                if is_mondai5:
                    # 根据passage_id生成说明文字
                    if passage_id == 1:
                        description = "1番 \n問題用紙に何も印刷されていません。まず話を聞いてください。それから、質問と選択肢を聞いて、１から４の中から、最もよいものを一つ選んでください。"
                    else:
                        description = f"{passage_id}番 \nまず話を聞いてください。それから、二つの質問を聞いて、それぞれ問題用紙の１から４の中から、最もよいものを一つ選んでください。"
                    
                    self.current_passage = {
                        "id": passage_id,
                        "passage": {
                            "type": "text",
                            "value": description
                        },
                        "questions": [],
                        "script": []  # 問題5的script放在passage级别
                    }
                else:
                    # 其他听力题不需要passage内容
                    self.current_passage = {
                        "id": passage_id,
                        "questions": []
                    }
                self.current_section["passages"].append(self.current_passage)
                logger.info(f"  ✓ 创建新的听力passage {passage_id}")
            
            # 创建听力题对象
            # question id应该是当前passage内的序号（从1开始）
            question_id_in_passage = len(self.current_passage["questions"]) + 1
            listening_question = {
                "id": question_id_in_passage,  # 使用passage内的序号
                "question": "",  # 听力题question字段为空
                "options": question["options"],
                "correct_answer": question["correct_answer"],
                "explanation": question["explanation"]
            }
            
            # 添加音频路径
            if audio_url:
                # 問題5使用passage的id，其他使用question的序号
                if is_mondai5:
                    audio_passage_id = self.current_passage["id"]
                else:
                    audio_passage_id = len(self.current_passage["questions"]) + 1
                audio_path = self.download_audio(audio_url, section_id, audio_passage_id)
                if audio_path:
                    listening_question["audio"] = audio_path
            
            # 2.01和2.04：下载图片并添加到question的passage字段中
            if section_id in ["2.01", "2.04"]:
                container = question_data.get("_container")
                if container:
                    # 计算题目的全局序号
                    total_questions = sum(len(p["questions"]) for p in self.current_section["passages"])
                    question_number = total_questions + 1
                    image_url = self.download_listening_image(container, section_id, question_number)
                    if image_url:
                        listening_question["passage"] = {
                            "type": "image",
                            "url": image_url
                        }
                        logger.info(f"  ✓ 添加听力题图片: {image_url}")

            
            # 处理script
            if is_mondai5:
                # 問題5：script放在passage级别，多个问题共享
                if listening_scripts and not self.current_passage.get("script"):
                    # 只在第一个问题时设置script
                    self.current_passage["script"] = listening_scripts
                # 不在question级别添加script
            else:
                # 其他听力题：script放在question级别
                if listening_scripts:
                    listening_question["script"] = listening_scripts
                else:
                    listening_question["script"] = [{
                        "id": 0,
                        "text": "（听力文字稿待补充）",
                        "start": "00:00:00,000",
                        "end": "00:00:00,000"
                    }]
            
            self.current_passage["questions"].append(listening_question)
        # 有阅读材料的题目（完形填空、阅读理解）或图片题
        elif passage_text or passage_type == "image":
            # 检查是否与当前passage的材料相同（使用更宽松的匹配）
            need_new_passage = True
            if self.current_passage and "passage" in self.current_passage:
                current_content = self.current_passage["passage"].get("value", "")
                current_type = self.current_passage["passage"].get("type", "text")
                
                # 特殊处理：如果是图片类型，同一个section的题目应该合并
                if passage_type == "image" and current_type == "image":
                    # 图片题通常共享同一张图片
                    need_new_passage = False
                    logger.info(f"  ✓ 合并到当前passage（同一图片）")
                # 比较前100个字符，如果相同则认为是同一篇文章
                elif len(current_content) > 50 and len(passage_text) > 50:
                    if current_content[:100] == passage_text[:100]:
                        need_new_passage = False
                        logger.info(f"  ✓ 合并到当前passage（相同文章）")
                elif current_content == passage_text:
                    need_new_passage = False
                    logger.info(f"  ✓ 合并到当前passage（完全相同）")
            
            if need_new_passage:
                passage_id = len(self.current_section["passages"]) + 1
                
                # 如果是图片类型，使用不同的结构
                if passage_type == "image":
                    # 下载图片并获取URL
                    section_id = self.current_section.get("section_id", "")
                    
                    # 从question_data中获取container来下载图片
                    container = question_data.get("_container")
                    image_url = None
                    if container:
                        image_url = self.download_image(container, section_id)
                    
                    # 检查是否是可选图片的section（N3的1.12）
                    is_optional_image = (self.level.lower() == 'n3' and section_id == "1.12")
                    
                    # 如果下载失败
                    if not image_url:
                        if is_optional_image:
                            # 对于可选图片的section，如果没有图片就使用文本类型
                            logger.info(f"  ℹ️  Section {section_id} 没有图片，使用文本类型passage")
                            passage_type = "text"
                            # 继续执行下面的文本类型处理
                        else:
                            # 对于必须有图片的section，使用默认路径
                            year = self.exam_date[:4]
                            month = self.exam_date[5:7]
                            image_filename = f"{year}_{month}_{self.level.upper()}_{section_id}.webp"
                            # 图片直接放在级别目录下，不需要年份子目录
                            image_url = f"/data/image/jlpt/{self.level}/{image_filename}"
                            logger.warning(f"  ⚠️  图片下载失败，使用默认路径: {image_url}")
                    
                    # 如果有图片URL，创建图片类型的passage
                    if image_url:
                        self.current_passage = {
                            "id": passage_id,
                            "passage": {
                                "type": "image",
                                "url": image_url,
                                "alt_text": ""
                            },
                            "questions": []
                        }
                        logger.info(f"  ✓ 添加图片URL: {image_url}")
                
                # 文本类型的passage（包括原本是image但没有图片的情况）
                if passage_type != "image":
                    # 文本类型的passage
                    self.current_passage = {
                        "id": passage_id,
                        "passage": {
                            "type": passage_type,
                            "value": passage_text
                        },
                        "questions": []
                    }
                    
                    # 对于阅读题，提取passage级别的target_words
                    # N1: 1.08-1.13, N2: 1.10-1.14, N3: 1.09-1.11
                    section_id = self.current_section.get("section_id", "")
                    level = self.level.upper()
                    reading_sections = {
                        'N1': {'1.08', '1.09', '1.10', '1.11', '1.12', '1.13'},
                        'N2': {'1.10', '1.11', '1.12', '1.13', '1.14'},
                        'N3': {'1.09', '1.10', '1.11'}
                    }
                    if section_id in reading_sections.get(level, set()):
                        container = question_data.get("_container")
                        if container:
                            passage_target_words = self.extract_target_words(
                                container, section_id, passage_text, is_passage_level=True
                            )
                            if passage_target_words:
                                self.current_passage["passage"]["target_words"] = passage_target_words
                
                self.current_section["passages"].append(self.current_passage)
                logger.info(f"  ✓ 创建新passage（含阅读材料，类型：{passage_type}）")
        # 普通题目（无材料）
        elif not self.current_passage:
            passage_id = len(self.current_section["passages"]) + 1
            self.current_passage = {
                "id": passage_id,
                "questions": []
            }
            self.current_section["passages"].append(self.current_passage)
        
        # 只有非听力题才添加到questions数组
        if section_type != "listening":
            # 提取question级别的target_words（根据section和级别控制）
            # N1: 1.01, 1.03, 1.04, 1.08-1.13
            # N2: 1.01, 1.02, 1.05, 1.06, 1.10-1.14
            # N3: 1.01, 1.02, 1.04, 1.05, 1.09-1.11
            section_id = self.current_section.get("section_id", "")
            level = self.level.upper()
            
            # 定义需要提取target_words的section
            target_sections_map = {
                'N1': {'1.01', '1.03', '1.04', '1.08', '1.09', '1.10', '1.11', '1.12', '1.13'},
                'N2': {'1.01', '1.02', '1.05', '1.06', '1.10', '1.11', '1.12', '1.13', '1.14'},
                'N3': {'1.01', '1.02', '1.04', '1.05', '1.09', '1.10', '1.11'}
            }
            target_sections = target_sections_map.get(level, set())
            
            if section_id in target_sections:
                container = question_data.get("_container")
                if container:
                    question_target_words = self.extract_target_words(
                        container, section_id, passage_text or "", is_passage_level=False
                    )
                    if question_target_words:
                        question["target_words"] = question_target_words
                        logger.info(f"  ✓ 题目target_words: {', '.join(question_target_words)}")
            
            # 调试：在添加到passage前检查question对象
            if "passage" in question and isinstance(question["passage"], dict):
                logger.info(f"  🔍 DEBUG: 准备添加到passage的question包含passage字段: {question['passage']}")
            
            self.current_passage["questions"].append(question)
    
    def click_next_question(self) -> bool:
        """点击下一题"""
        try:
            next_btn = self.driver.find_element(By.CSS_SELECTOR, ".button.next.item")
            classes = next_btn.get_attribute("class") or ""
            if "disable" in classes:
                return False
            next_btn.click()
            time.sleep(2)
            return True
        except:
            return False

    def scrape_all_questions(self, url: str, max_questions: int = 200):
        """爬取所有题目"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始爬取: {url}")
        logger.info(f"{'='*60}\n")
        
        try:
            self.driver.get(url)
            logger.info("✓ 页面加载完成")
            time.sleep(5)
            
            question_index = 1
            consecutive_failures = 0
            
            while question_index <= max_questions:
                logger.info(f"\n--- 第 {question_index} 题 ---")
                
                question_data = self.extract_single_question(question_index)
                
                if question_data:
                    self.add_question_to_section(question_data)
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.info("连续失败3次，停止爬取")
                        break
                
                if not self.click_next_question():
                    logger.info("无法点击下一题，已到最后一题")
                    break
                
                question_index += 1
                time.sleep(0.5)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"✓ 爬取完成！")
            logger.info(f"{'='*60}\n")
            
            return self.sections
        except Exception as e:
            logger.error(f"爬取失败: {e}")
            return self.sections
    
    def create_listening_passage(self, passage_id: int, section_id: str, options_count: int = 4) -> Dict:
        """创建听力passage"""
        year = self.exam_date[:4]
        month = self.exam_date[5:7]
        filename = f"{year}年{month}月{self.level.upper()}真题_{section_id}_{passage_id:02d}.mp3"
        # 使用层级化的音频路径: /data/audio/jlpt/n1/2024_12/xxx.mp3
        audio_path = f"/data/audio/jlpt/{self.level}/{self.exam_date}/{filename}"
        
        if section_id == "2.04":
            passage_value = f"{passage_id}番 \n問題用紙に何も印刷されていません。まず文を聞いてください。それから、それに対する返事を聞いて、１から３の中から、最もよいものを一つ選びなさい。"
        else:
            passage_value = f"{passage_id}番 \n問題用紙に何も印刷されていません。まず話を聞いてください。それから、質問と選択肢を聞いて、１から４の中から、最もよいものを一つ選んでください。"
        
        options = [f"{i}. {i}" for i in range(1, options_count + 1)]
        
        passage = {
            "id": passage_id,
            "audio": audio_path,
            "topic": "",
            "passage": {
                "type": "text",
                "value": passage_value
            },
            "questions": [{
                "id": passage_id,
                "question": "",
                "options": options,
                "correct_answer": 0,
                "explanation": ""
            }],
            "script": [{
                "id": 0,
                "text": "（听力文字稿待补充）",
                "start": "00:00:00,000",
                "end": "00:00:00,000"
            }]
        }
        
        return passage

    def complete_listening_sections(self):
        """补全听力sections - 保留已爬取的内容"""
        logger.info(f"\n{'='*60}")
        logger.info("补全听力sections")
        logger.info(f"{'='*60}\n")
        
        # 检查已爬取的听力sections
        existing_listening = {s["section_id"]: s for s in self.sections if s.get("section_type") == "listening"}
        
        if existing_listening:
            logger.info(f"✓ 已爬取 {len(existing_listening)} 个听力section，将保留其内容")
        
        # 移除爬取的听力sections（稍后会重新添加完整版本）
        self.sections = [s for s in self.sections if s.get("section_type") != "listening"]
        
        # 创建或补全听力sections
        for section_id, template in LISTENING_SECTIONS.items():
            # 检查是否已经爬取了这个section
            if section_id in existing_listening:
                existing_section = existing_listening[section_id]
                logger.info(f"✓ Section {section_id}: 使用已爬取的内容 ({len(existing_section.get('passages', []))} passages)")
                
                # 使用已爬取的section，但确保结构完整
                section = existing_section
                
                # 补充缺失的passages（如果需要）
                passage_count = template["passage_count"]
                existing_passage_count = len(section.get("passages", []))
                
                if existing_passage_count < passage_count:
                    logger.info(f"  ⚠️  补充缺失的passages ({existing_passage_count}/{passage_count})")
                    options_count = template.get("options_count", 4)
                    
                    for i in range(existing_passage_count + 1, passage_count + 1):
                        passage = self.create_listening_passage(i, section_id, options_count)
                        section["passages"].append(passage)
                
                self.sections.append(section)
            else:
                # 创建新的section（如果没有爬取到）
                logger.info(f"创建 Section {section_id}: {template['section_name']}")
                
                section = {
                    "section_id": section_id,
                    "section_title": template["section_title"],
                    "section_name": template["section_name"],
                    "section_type": "listening",
                    "description": template["description"],
                    "passages": []
                }
                
                passage_count = template["passage_count"]
                options_count = template.get("options_count", 4)
                
                for i in range(1, passage_count + 1):
                    passage = self.create_listening_passage(i, section_id, options_count)
                    
                    # 問題5特殊处理
                    if section_id == 2.05:
                        questions_per_passage = template.get("questions_per_passage", 2)
                        passage["questions"] = []
                        for q in range(1, questions_per_passage + 1):
                            question_id = (i - 1) * questions_per_passage + q
                            passage["questions"].append({
                                "id": question_id,
                                "question": "",
                                "options": [f"{j}. {j}" for j in range(1, 5)],
                                "correct_answer": 0,
                                "explanation": ""
                            })
                    
                    section["passages"].append(passage)
                
                self.sections.append(section)
                logger.info(f"  ✓ 创建了 {len(section['passages'])} 个passage")
        
        # 按section_id排序（确保按照1.01, 1.02, ..., 2.01, 2.02的顺序）
        def section_sort_key(section):
            section_id = section.get("section_id", "0.00")
            # 分割为主号和副号，例如 "1.01" -> (1, 1)
            parts = section_id.split(".")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
            return (0, 0)
        
        self.sections.sort(key=section_sort_key)
    
    def save_to_exam_format(self, output_path: Path, title: str):
        """保存为exam格式 - 使用标准化的字段顺序"""
        from collections import OrderedDict
        
        # 从exam_date中提取年月和级别
        # exam_date格式: "2024_12" 或 "2024_12_N1"
        parts = self.exam_date.split("_")
        year_month = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 else self.exam_date
        exam_id = self.exam_date if len(parts) >= 3 else f"{self.exam_date}_{self.level.upper()}"
        
        # 标准化字段顺序
        def order_question(q):
            """统一question对象的字段顺序"""
            ordered = OrderedDict()
            ordered['id'] = q['id']
            ordered['question'] = q['question']
            ordered['options'] = q['options']
            ordered['correct_answer'] = q['correct_answer']
            ordered['explanation'] = q['explanation']
            # 支持新的target_words数组格式（放在explanation之后）
            if 'target_words' in q:
                ordered['target_words'] = q['target_words']
            # 兼容旧的target_word单数格式
            elif 'target_word' in q:
                ordered['target_word'] = q['target_word']
            if 'correct_order' in q:
                ordered['correct_order'] = q['correct_order']
            # 听力题和question级别图片的特殊字段
            if 'audio' in q:
                ordered['audio'] = q['audio']
            if 'passage' in q:
                ordered['passage'] = q['passage']
            if 'script' in q:
                ordered['script'] = q['script']
            return ordered
        
        def order_passage(p):
            """统一passage对象的字段顺序"""
            ordered = OrderedDict()
            ordered['id'] = p['id']
            if 'passage' in p:
                ordered['passage'] = p['passage']
            # 听力题passage级别的audio字段（如2.05）
            if 'audio' in p:
                ordered['audio'] = p['audio']
            ordered['questions'] = [order_question(q) for q in p['questions']]
            # 听力题passage级别的script字段（如2.05）
            if 'script' in p:
                ordered['script'] = p['script']
            return ordered
        
        def order_section(s):
            """统一section对象的字段顺序"""
            ordered = OrderedDict()
            ordered['section_id'] = s['section_id']
            ordered['section_title'] = s['section_title']
            ordered['section_name'] = s['section_name']
            ordered['section_type'] = s['section_type']
            if 'description' in s:
                ordered['description'] = s['description']
            ordered['passages'] = [order_passage(p) for p in s['passages']]
            return ordered
        
        def order_exam_info(info):
            """统一exam_info对象的字段顺序"""
            ordered = OrderedDict()
            ordered['title'] = info['title']
            ordered['exam_date'] = info['exam_date']
            ordered['exam_level'] = info['exam_level']
            ordered['exam_id'] = info['exam_id']
            ordered['sections'] = [order_section(s) for s in info['sections']]
            return ordered
        
        # 确保sections按正确顺序排列
        def section_sort_key(section):
            section_id = section.get("section_id", "0.00")
            parts = section_id.split(".")
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
            return (0, 0)
        
        sorted_sections = sorted(self.sections, key=section_sort_key)
        
        exam_info = {
            "title": title,
            "exam_date": year_month,
            "exam_level": self.level.upper(),
            "exam_id": exam_id,
            "sections": sorted_sections
        }
        
        exam_data = OrderedDict()
        exam_data['exam_info'] = order_exam_info(exam_info)
        
        # 如果文件已存在，先备份
        if output_path.exists():
            backup_path = output_path.with_suffix('.json.backup')
            import shutil
            shutil.copy2(output_path, backup_path)
            logger.info(f"  ⚠️  文件已存在，已备份到: {backup_path.name}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(exam_data, f, ensure_ascii=False, indent=2)
        
        # 计算题目总数（听力题和非听力题结构不同）
        total_questions = 0
        for section in self.sections:
            for passage in section.get("passages", []):
                if "questions" in passage:
                    # 非听力题：有questions数组
                    total_questions += len(passage["questions"])
                else:
                    # 听力题：每个passage就是一道题
                    total_questions += 1
        
        logger.info(f"\n✓ 试卷已保存: {output_path}")
        logger.info(f"  - Section数: {len(self.sections)}")
        logger.info(f"  - 题目数: {total_questions}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            logger.info("✓ 浏览器已关闭")


def main():
    """主函数 - 从配置文件读取试卷列表并批量下载"""
    print("\n" + "="*60)
    print("完整爬虫 - 批量下载试卷（从配置文件）")
    print("="*60)
    print("\n✨ 功能:")
    print("  1. 从配置文件读取试卷列表")
    print("  2. 批量爬取所有题目（词汇、语法、阅读、听力）")
    print("  3. 自动下载音频和图片")
    print("  4. 提取听力文字稿（含时间轴）")
    print("  5. 🔥 共享浏览器会话 - 只需登录一次！")
    print("="*60 + "\n")
    
    # 读取配置文件
    config_file = Path(__file__).parent / "complete_scraper_config.json"
    
    if not config_file.exists():
        logger.error(f"配置文件不存在: {config_file}")
        return
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return
    
    exam_list = config.get("exam_info", [])
    
    if not exam_list:
        logger.error("配置文件中没有试卷信息")
        return
    
    print(f"📋 找到 {len(exam_list)} 个试卷待下载:\n")
    for idx, exam in enumerate(exam_list, 1):
        print(f"  {idx}. {exam.get('title')} - {exam.get('url')}")
    print()
    
    # 创建一个共享的浏览器实例
    print("🌐 初始化浏览器（只需登录一次）...")
    shared_scraper = None
    
    try:
        # 使用第一个试卷的信息初始化浏览器
        first_exam = exam_list[0]
        exam_date = first_exam.get("exam_date", "").replace("/", "_")
        level = first_exam.get("exam_level", "N1").lower()
        shared_scraper = CompleteScraper(exam_date=exam_date, level=level, headless=False)
        print("✓ 浏览器已初始化，请在浏览器中登录网站")
        print("⏳ 等待10秒让你完成登录...")
        time.sleep(10)
        
    except Exception as e:
        logger.error(f"初始化浏览器失败: {e}")
        return
    
    # 批量处理每个试卷
    success_count = 0
    failed_count = 0
    
    try:
        for idx, exam in enumerate(exam_list, 1):
            title = exam.get("title", "")
            url = exam.get("url", "")
            exam_date = exam.get("exam_date", "").replace("/", "_")  # 2022/12 -> 2022_12
            level = exam.get("exam_level", "N1").lower()
            
            print("\n" + "="*60)
            print(f"[{idx}/{len(exam_list)}] 开始处理: {title}")
            print("="*60)
            
            try:
                # 更新scraper的exam_date和level（用于文件命名）
                shared_scraper.exam_date = exam_date
                shared_scraper.level = level
                
                # 更新音频和图片目录
                base_dir = Path(__file__).parent.parent
                shared_scraper.audio_dir = base_dir / "data" / "audio" / "jlpt" / level / exam_date
                shared_scraper.image_dir = base_dir / "data" / "image" / "jlpt" / level
                shared_scraper.audio_dir.mkdir(parents=True, exist_ok=True)
                shared_scraper.image_dir.mkdir(parents=True, exist_ok=True)
                
                # 重置sections（准备新试卷）
                shared_scraper.sections = []
                shared_scraper.current_section = None
                shared_scraper.current_passage = None
                
                # 爬取题目
                shared_scraper.scrape_all_questions(url, max_questions=200)
                
                # 保存结果 - 直接保存到对应级别目录
                output_dir = Path(__file__).parent.parent / "data" / "paper" / "jlpt" / level.lower()
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"{level.upper()}_{exam_date}.json"
                
                shared_scraper.save_to_exam_format(output_file, title)
                
                print("\n" + "="*60)
                print(f"✓ [{idx}/{len(exam_list)}] 完成: {title}")
                print("="*60)
                print(f"\n📊 统计:")
                listening_sections = [s for s in shared_scraper.sections if s.get("section_type") == "listening"]
                other_sections = [s for s in shared_scraper.sections if s.get("section_type") != "listening"]
                print(f"  - 非听力section: {len(other_sections)}")
                print(f"  - 听力section: {len(listening_sections)}")
                print(f"  - 输出文件: {output_file}")
                
                success_count += 1
                
                # 等待一下再处理下一个试卷
                if idx < len(exam_list):
                    print("\n⏳ 等待3秒后处理下一个试卷...")
                    time.sleep(3)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断，停止批量处理")
                raise
            except Exception as e:
                logger.error(f"\n✗ 处理失败: {title}")
                logger.error(f"错误: {e}")
                import traceback
                traceback.print_exc()
                failed_count += 1
                
                # 继续处理下一个试卷
                if idx < len(exam_list):
                    print("\n⏳ 等待3秒后继续处理下一个试卷...")
                    time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    finally:
        # 最后关闭浏览器
        if shared_scraper:
            shared_scraper.close()
    
    # 最终统计
    print("\n" + "="*60)
    print("📊 批量处理完成")
    print("="*60)
    print(f"  ✅ 成功: {success_count} 个")
    print(f"  ❌ 失败: {failed_count} 个")
    print(f"  📝 总计: {len(exam_list)} 个")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
