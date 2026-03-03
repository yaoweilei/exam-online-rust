"""
JLPT考试结构加载器
用于加载和验证JLPT考试结构，配合爬虫使用
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class QuestionInfo:
    """题目信息"""
    q_number: int
    q_type: str
    q_count: int
    objective: str
    has_image: bool = False  # 是否有图片（如発話表現、情報検索）


@dataclass
class SectionInfo:
    """Section信息"""
    section_name: str
    section_time: str
    questions: List[QuestionInfo]
    subsections: List[str] = None  # 子section名称（如文字・語彙、文法、読解）


@dataclass
class LevelStructure:
    """级别结构"""
    level: str
    total_time: str
    sections: List[SectionInfo]


class JLPTStructureLoader:
    """JLPT结构加载器"""
    
    def __init__(self, struct_file: str = "data/paper/jlpt_struct.json"):
        self.struct_file = Path(struct_file)
        self.structures: Dict[str, LevelStructure] = {}
        self.load_structure()
    
    def load_structure(self):
        """加载JLPT结构文件"""
        if not self.struct_file.exists():
            raise FileNotFoundError(f"结构文件不存在: {self.struct_file}")
        
        with open(self.struct_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for level_data in data['JLPT_Exam_Structure']:
            level = level_data['level']
            sections = []
            
            for section_data in level_data['sections']:
                questions = []
                subsections = []
                
                # 处理subsections（如果有）
                if 'subsections' in section_data and section_data['subsections']:
                    for subsection in section_data['subsections']:
                        subsections.append(subsection['subsection'])
                        for q in subsection['questions']:
                            questions.append(QuestionInfo(
                                q_number=q['q_number'],
                                q_type=q['q_type'],
                                q_count=q['q_count'],
                                objective=q['objective'],
                                has_image=self._check_has_image(q['q_type'])
                            ))
                
                # 处理直接的questions（如聴解）
                if 'questions' in section_data:
                    for q in section_data['questions']:
                        questions.append(QuestionInfo(
                            q_number=q['q_number'],
                            q_type=q['q_type'],
                            q_count=q['q_count'],
                            objective=q['objective'],
                            has_image=self._check_has_image(q['q_type'])
                        ))
                
                sections.append(SectionInfo(
                    section_name=section_data['section_name'],
                    section_time=section_data['section_time'],
                    questions=questions,
                    subsections=subsections if subsections else None
                ))
            
            self.structures[level] = LevelStructure(
                level=level,
                total_time=level_data['total_time'],
                sections=sections
            )
    
    def _check_has_image(self, q_type: str) -> bool:
        """检查题型是否需要图片"""
        image_types = ['発話表現', '情報検索']
        return q_type in image_types
    
    def get_structure(self, level: str) -> Optional[LevelStructure]:
        """获取指定级别的结构"""
        return self.structures.get(level.upper())
    
    def get_total_questions(self, level: str) -> int:
        """获取指定级别的总题数"""
        structure = self.get_structure(level)
        if not structure:
            return 0
        
        total = 0
        for section in structure.sections:
            for q in section.questions:
                total += q.q_count
        return total
    
    def get_section_info(self, level: str, section_name: str) -> Optional[SectionInfo]:
        """获取指定section的信息"""
        structure = self.get_structure(level)
        if not structure:
            return None
        
        for section in structure.sections:
            if section_name in section.section_name:
                return section
        return None
    
    def validate_exam_structure(self, exam_data: Dict, level: str) -> Dict:
        """
        验证爬取的exam数据结构是否正确
        
        返回验证结果：
        {
            'valid': bool,
            'total_questions': int,
            'expected_questions': int,
            'missing_questions': int,
            'extra_questions': int,
            'section_details': [...]
        }
        """
        structure = self.get_structure(level)
        if not structure:
            return {'valid': False, 'error': f'未找到{level}级别的结构定义'}
        
        expected_total = self.get_total_questions(level)
        actual_total = 0
        section_details = []
        
        # 统计实际题目数
        for section in exam_data.get('exam_info', {}).get('sections', []):
            section_questions = 0
            for passage in section.get('passages', []):
                section_questions += len(passage.get('questions', []))
            
            actual_total += section_questions
            
            # 查找对应的结构定义
            section_info = self.get_section_info(level, section['section_name'])
            expected_count = sum(q.q_count for q in section_info.questions) if section_info else 0
            
            section_details.append({
                'section_id': section.get('section_id'),
                'section_name': section.get('section_name'),
                'expected': expected_count,
                'actual': section_questions,
                'match': expected_count == section_questions
            })
        
        return {
            'valid': actual_total == expected_total,
            'total_questions': actual_total,
            'expected_questions': expected_total,
            'missing_questions': max(0, expected_total - actual_total),
            'extra_questions': max(0, actual_total - expected_total),
            'section_details': section_details
        }
    
    def print_structure(self, level: str):
        """打印指定级别的结构信息"""
        structure = self.get_structure(level)
        if not structure:
            print(f"未找到{level}级别的结构定义")
            return
        
        print(f"\n{'='*60}")
        print(f"JLPT {structure.level} 考试结构")
        print(f"{'='*60}")
        print(f"总时间: {structure.total_time}")
        print(f"总题数: {self.get_total_questions(level)}")
        print()
        
        for section in structure.sections:
            print(f"\n【{section.section_name}】 ({section.section_time})")
            if section.subsections:
                print(f"  子部分: {', '.join(section.subsections)}")
            
            section_total = sum(q.q_count for q in section.questions)
            print(f"  题目数: {section_total}")
            print()
            
            for q in section.questions:
                image_mark = " 📷" if q.has_image else ""
                print(f"  問題{q.q_number}: {q.q_type}{image_mark}")
                print(f"    题数: {q.q_count}")
                print(f"    目标: {q.objective}")
                print()
    
    def get_section_mapping(self, level: str) -> Dict[str, str]:
        """
        获取section编号到名称的映射
        用于爬虫识别section
        
        返回: {'1.01': '漢字読み', '1.02': '表記', ...}
        """
        structure = self.get_structure(level)
        if not structure:
            return {}
        
        mapping = {}
        question_counter = 1
        
        for section in structure.sections:
            for q in section.questions:
                # 生成section_id (如 1.01, 1.02, 2.01, 2.02)
                if '聴解' in section.section_name:
                    section_prefix = '2'
                else:
                    section_prefix = '1'
                
                section_id = f"{section_prefix}.{q.q_number:02d}"
                mapping[section_id] = q.q_type
                question_counter += 1
        
        return mapping


def main():
    """测试程序"""
    loader = JLPTStructureLoader()
    
    # 打印所有级别的结构
    for level in ['N1', 'N2', 'N3', 'N4', 'N5']:
        loader.print_structure(level)
        print(f"\nSection映射:")
        mapping = loader.get_section_mapping(level)
        for section_id, q_type in sorted(mapping.items()):
            print(f"  {section_id}: {q_type}")
        print("\n" + "="*60 + "\n")
    
    # 测试验证功能（示例）
    print("\n测试验证功能:")
    print("加载一个json文件进行验证...")
    
    exam_file = Path("data/paper/jlpt/n3/N3_2010_07.json")
    if exam_file.exists():
        with open(exam_file, 'r', encoding='utf-8') as f:
            exam_data = json.load(f)
        
        result = loader.validate_exam_structure(exam_data, 'N3')
        print(f"\n验证结果:")
        print(f"  有效: {result['valid']}")
        print(f"  实际题数: {result['total_questions']}")
        print(f"  期望题数: {result['expected_questions']}")
        print(f"  缺失题数: {result['missing_questions']}")
        print(f"  多余题数: {result['extra_questions']}")
        print(f"\nSection详情:")
        for detail in result['section_details']:
            match_mark = "✓" if detail['match'] else "✗"
            print(f"  {match_mark} {detail['section_id']} {detail['section_name']}: "
                  f"{detail['actual']}/{detail['expected']}")


if __name__ == '__main__':
    main()
