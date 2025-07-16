"""
Django settings for WebSocket Message Counter project.
"""
import os
import logging.config
from pathlib import Path
import structlog
import logging_loki

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,nginx,app_blue,app_green,host.docker.internal').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'channels',
    'chat',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'core.middleware.RequestIDMiddleware',
    'core.middleware.StructuredLoggingMiddleware',
]

ROOT_URLCONF = 'config.urls'

ASGI_APPLICATION = 'config.asgi.application'

# Redis for channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.environ.get('REDIS_HOST', 'redis'), 6379)],
        },
    },
}

# Database (required by Django, using SQLite in-memory for minimal setup)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Logging configuration
LOGGING_CONFIG = None

# Loki configuration - make it optional for development
LOKI_URL = os.environ.get('LOKI_URL', 'http://loki:3100')
LOKI_ENABLED = os.environ.get('LOKI_ENABLED', 'false').lower() == 'true'

# Structured logging with structlog
timestamper = structlog.processors.TimeStamper(fmt="iso")

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure logging handlers
console_handler = {
    'class': 'logging.StreamHandler',
    'formatter': 'json',
}

handlers_config = {'console': console_handler}

# Add Loki handler if enabled
if LOKI_ENABLED:
    try:
        import logging_loki
        loki_handler = {
            'class': 'logging_loki.LokiHandler',
            'url': f"{LOKI_URL}/loki/api/v1/push",
            'tags': {
                'service': 'websocket-message-counter',
                'environment': 'production' if not DEBUG else 'development',
            },
            'version': '1',
        }
        handlers_config['loki'] = loki_handler
        print(f"Loki handler configured for {LOKI_URL}")
    except (ImportError, Exception) as e:
        print(f"Warning: Loki handler not available: {e}")
        pass

# Determine which handlers to use
active_handlers = ['console']
if 'loki' in handlers_config:
    active_handlers.append('loki')

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'format': '%(message)s',
        },
    },
    'handlers': handlers_config,
    'root': {
        'handlers': active_handlers,
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': active_handlers,
            'level': os.environ.get('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'chat': {
            'handlers': active_handlers,
            'level': 'DEBUG',
            'propagate': False,
        },
        'core': {
            'handlers': active_handlers,
            'level': 'DEBUG',
            'propagate': False,
        },
    }
})

# WebSocket settings
WEBSOCKET_HEARTBEAT_INTERVAL = int(os.environ.get('WEBSOCKET_HEARTBEAT_INTERVAL', '30'))
GRACEFUL_SHUTDOWN_TIMEOUT = int(os.environ.get('GRACEFUL_SHUTDOWN_TIMEOUT', '10'))

# Concurrency settings
# CPU cores for determining optimal worker count
import multiprocessing
CPU_COUNT = multiprocessing.cpu_count()

# Health check settings
HEALTH_CHECK_STARTUP_DELAY = int(os.environ.get('HEALTH_CHECK_STARTUP_DELAY', '3'))
