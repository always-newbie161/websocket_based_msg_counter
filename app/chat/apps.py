from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    
    def ready(self):
        # Start the heartbeat service
        from .heartbeat import start_heartbeat_service
        start_heartbeat_service()
        
        # Set up signal handlers for graceful shutdown
        from .signals import setup_signal_handlers
        setup_signal_handlers()
