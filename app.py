from flask import Flask, jsonify, request
from flask_cors import CORS
from extensions import db, migrate, jwt
from config import Config
from routes.auth import auth_bp
from routes.hotels import hotels_bp
from routes.sync import sync_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, supports_credentials=True)

    # Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(hotels_bp, url_prefix='/api/hotels')
    app.register_blueprint(sync_bp, url_prefix='/api/sync')

    
    # @app.route('/webhook/bookings', methods=['POST'])
    # def bookings_webhook():
    #     data = request.get_json()
    #     hotel = Hotel.query.get_or_404(hotel_id)
    #     print(data)
    
    @app.route('/api/health')
    def health():
        return jsonify(status='ok')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)