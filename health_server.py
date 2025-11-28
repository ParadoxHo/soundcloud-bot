from aiohttp import web
import threading
import asyncio
import psutil
import time

class HealthServer:
    def __init__(self, bot_instance=None, port=8080):
        self.bot = bot_instance
        self.port = port
        self.app = web.Application()
        self.start_time = time.time()
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/metrics', self.metrics)
        self.app.router.add_get('/', self.root)
    
    async def health_check(self, request):
        """Простая проверка здоровья"""
        return web.json_response({
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": round(time.time() - self.start_time, 2)
        })
    
    async def metrics(self, request):
        """Метрики для мониторинга"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        metrics = {
            "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
            "memory_percent": round(process.memory_percent(), 2),
            "cpu_percent": round(process.cpu_percent(), 2),
            "active_threads": process.num_threads(),
            "uptime_seconds": round(time.time() - self.start_time, 2)
        }
        
        return web.json_response(metrics)
    
    async def root(self, request):
        """Корневой endpoint"""
        return web.Response(text="Music Bot Health Server")
    
    def start(self):
        """Запускает сервер в отдельном потоке"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            web.run_app(self.app, port=self.port, host='0.0.0.0')
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        print(f"✅ Health server запущен на порту {self.port}")
