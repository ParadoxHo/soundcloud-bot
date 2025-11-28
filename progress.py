import time
from typing import List

class ProgressBar:
    def __init__(self, total_steps: int, width: int = 10):
        self.total_steps = total_steps
        self.width = width
        self.current_step = 0
        self.start_time = time.time()
    
    def get_bar(self, step: int = None) -> str:
        """Возвращает строку прогресс-бара"""
        if step is not None:
            self.current_step = step
        
        progress = min(self.current_step / self.total_steps, 1.0)
        filled = int(self.width * progress)
        empty = self.width - filled
        
        elapsed = time.time() - self.start_time
        elapsed_str = f"{elapsed:.1f}с"
        
        return f"[{'█' * filled}{'░' * empty}] {int(progress * 100)}% ({elapsed_str})"
    
    def get_stage_text(self, stage: int, stage_name: str) -> str:
        """Возвращает текст для этапа с прогресс-баром"""
        stages = {
            1: "🔍 Анализ запроса...",
            2: "🎵 Поиск трека...", 
            3: "⏬ Скачивание...",
            4: "📤 Отправка..."
        }
        
        stage_text = stages.get(stage, stage_name)
        return f"{self.get_bar(stage)}\n{stage_text}"

# Предопределенные прогресс-бары для разных операций
class ProgressManager:
    @staticmethod
    def search_progress():
        return ProgressBar(total_steps=4, width=8)
    
    @staticmethod
    def download_progress():
        return ProgressBar(total_steps=3, width=6)
