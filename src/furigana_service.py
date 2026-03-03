"""
振假名服务 - 处理日文文本的振假名标注
"""

from typing import Dict, List, Optional
from pathlib import Path
import json
import re


class FuriganaService:
    """振假名服务类"""
    
    def __init__(self, dict_path: Path):
        self.dict_path = dict_path
        self.dictionary = {}
        self.load_dictionary()
    
    def load_dictionary(self) -> bool:
        """
        加载振假名字典
        
        Returns:
            是否加载成功
        """
        try:
            if not self.dict_path.exists():
                print(f"振假名字典不存在: {self.dict_path}")
                return False
            
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                self.dictionary = json.load(f)
            
            print(f"振假名字典加载成功，共 {len(self.dictionary)} 个词条")
            return True
        except Exception as e:
            print(f"加载振假名字典失败: {e}")
            return False
    
    def add_furigana(self, text: str) -> str:
        """
        为文本添加振假名标记
        
        Args:
            text: 原始日文文本
            
        Returns:
            带振假名标记的文本（HTML ruby 标签）
        """
        if not text or not self.dictionary:
            return text
        
        result = text
        
        # 按词长度从长到短排序，优先匹配长词
        sorted_words = sorted(self.dictionary.items(), key=lambda x: len(x[0]), reverse=True)
        
        for word, reading in sorted_words:
            if word in result:
                # 生成 ruby 标签
                ruby_tag = f'<ruby>{word}<rt>{reading}</rt></ruby>'
                result = result.replace(word, ruby_tag)
        
        return result
    
    def add_furigana_to_exam(self, exam_data: Dict) -> Dict:
        """
        为整个试卷添加振假名
        
        Args:
            exam_data: 试卷数据
            
        Returns:
            处理后的试卷数据
        """
        if not exam_data or "exam_info" not in exam_data:
            return exam_data
        
        exam_info = exam_data["exam_info"]
        
        # 处理每个章节
        for section in exam_info.get("sections", []):
            # 处理章节标题
            if "section_title" in section:
                section["section_title"] = self.add_furigana(section["section_title"])
            
            # 处理段落
            for passage in section.get("passages", []):
                # 处理段落文本
                if "passage" in passage:
                    passage_data = passage["passage"]
                    if isinstance(passage_data, dict) and passage_data.get("type") == "text":
                        passage_data["value"] = self.add_furigana(passage_data["value"])
                
                # 处理题目
                for question in passage.get("questions", []):
                    # 处理题干
                    if "question_text" in question:
                        question["question_text"] = self.add_furigana(question["question_text"])
                    
                    # 处理选项
                    for option in question.get("options", []):
                        if "text" in option:
                            option["text"] = self.add_furigana(option["text"])
                    
                    # 处理解析
                    if "explanation" in question:
                        question["explanation"] = self.add_furigana(question["explanation"])
        
        return exam_data
    
    def extract_kanji(self, text: str) -> List[str]:
        """
        提取文本中的汉字
        
        Args:
            text: 文本
            
        Returns:
            汉字列表
        """
        # 匹配汉字的正则表达式
        kanji_pattern = re.compile(r'[\u4e00-\u9fff]+')
        return kanji_pattern.findall(text)
    
    def get_reading(self, word: str) -> Optional[str]:
        """
        获取单词的读音
        
        Args:
            word: 单词
            
        Returns:
            读音，如果不存在返回 None
        """
        return self.dictionary.get(word)
    
    def add_word(self, word: str, reading: str) -> bool:
        """
        添加新词到字典
        
        Args:
            word: 单词
            reading: 读音
            
        Returns:
            是否添加成功
        """
        try:
            self.dictionary[word] = reading
            
            # 保存到文件
            with open(self.dict_path, 'w', encoding='utf-8') as f:
                json.dump(self.dictionary, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"添加词条失败: {e}")
            return False
