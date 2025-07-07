from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        # Import here to avoid circular imports
        from .views import startup
        import threading
        
        # Start the startup process in a separate thread
        startup_thread = threading.Thread(target=startup)
        startup_thread.daemon = True
        startup_thread.start()
