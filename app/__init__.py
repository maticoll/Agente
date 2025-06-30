from flask import Flask
from .config import load_configurations, configure_logging
from .services.scheduler_service import init_scheduler
from .views import webhook_blueprint, debug_bp


def create_app():
    # Configuración de logging y variables de entorno
    configure_logging()
    app = Flask(__name__)
    load_configurations(app)

    # Inicializar scheduler con la instancia de la app
    init_scheduler(app)

    # Registrar blueprints
    app.register_blueprint(webhook_blueprint)
    app.register_blueprint(debug_bp)

    return app
