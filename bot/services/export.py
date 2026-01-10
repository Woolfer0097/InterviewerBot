from datetime import datetime
from typing import List
from io import StringIO
import csv
from bot.db.models import UserQuestion


def export_to_markdown(user_questions: List[UserQuestion], user_name: str = "Пользователь") -> str:
    """
    Экспортирует вопросы и ответы в красивый Markdown формат.
    
    Args:
        user_questions: Список UserQuestion с загруженными вопросами
        user_name: Имя пользователя для заголовка
        
    Returns:
        Markdown строка
    """
    md_lines = [
        f"# Интервью: {user_name}",
        "",
        f"*Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "---",
        "",
    ]
    
    for idx, uq in enumerate(user_questions, 1):
        question = uq.question
        md_lines.extend([
            f"## Вопрос {idx}",
            "",
            f"**Вопрос:** {question.question}",
            "",
            f"*Частота вопроса: {question.freq_score}/9*",
            "",
        ])
        
        if uq.answer_text:
            md_lines.extend([
                "### Ответ пользователя",
                "",
                uq.answer_text,
                "",
            ])
        
        if uq.feedback_text:
            md_lines.extend([
                "### Фидбек ИИ",
                "",
                uq.feedback_text,
                "",
            ])
        
        if uq.hint_text:
            md_lines.extend([
                "### Подсказка ИИ",
                "",
                uq.hint_text,
                "",
            ])
        
        if uq.answered_at:
            md_lines.append(f"*Дата ответа: {uq.answered_at.strftime('%Y-%m-%d %H:%M:%S')}*")
            md_lines.append("")
        
        md_lines.append("---")
        md_lines.append("")
    
    md_lines.append(f"\n*Всего вопросов: {len(user_questions)}*")
    
    return "\n".join(md_lines)


def export_to_csv(user_questions: List[UserQuestion]) -> str:
    """
    Экспортирует вопросы и ответы в CSV формат.
    
    Args:
        user_questions: Список UserQuestion с загруженными вопросами
        
    Returns:
        CSV строка (с BOM для Excel)
    """
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    # Заголовки
    writer.writerow([
        "Номер",
        "Вопрос",
        "Частота вопроса",
        "Ответ пользователя",
        "Фидбек ИИ",
        "Подсказка ИИ",
        "Дата ответа",
    ])
    
    # Данные
    for idx, uq in enumerate(user_questions, 1):
        question = uq.question
        writer.writerow([
            idx,
            question.question,
            question.freq_score,
            uq.answer_text or "",
            uq.feedback_text or "",
            uq.hint_text or "",
            uq.answered_at.strftime('%Y-%m-%d %H:%M:%S') if uq.answered_at else "",
        ])
    
    csv_string = output.getvalue()
    output.close()
    
    # Добавляем BOM для правильного отображения в Excel
    return '\ufeff' + csv_string

