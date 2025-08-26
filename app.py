from flask import Flask, jsonify, request
from flask_cors import CORS
from extensions import db, migrate, jwt
from config import Config
from routes.auth import auth_bp
from routes.hotels import hotels_bp
from routes.sync import sync_bp
from flask import send_from_directory
import os

def create_app():
    app = Flask(
        __name__,
        static_folder="dist",      # <-- This tells Flask where to find static files
        static_url_path=""         # <-- This makes static files available at root
    )
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
    
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_react(path):
        # Serve API routes as normal
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        # Serve static files if they exist
        file_path = os.path.join(app.static_folder, path)
        if path != "" and os.path.exists(file_path):
            return send_from_directory(app.static_folder, path)
        # Otherwise, serve index.html (for React Router)
        return send_from_directory(app.static_folder, "index.html")

    return app


# if __name__ == '__main__':
#     app = create_app()
#     app.run(debug=True)



# from flask import Flask, jsonify
# from flask_cors import CORS
# from extensions import db, migrate, jwt
# from config import Config
# from routes.auth import auth_bp
# from routes.hotels import hotels_bp
# from routes.sync import sync_bp

# def create_app():
#     app = Flask(__name__)
#     app.config.from_object(Config)

#     # Extensions
#     db.init_app(app)
#     migrate.init_app(app, db)
#     jwt.init_app(app)

#     # ✅ CORS - allow only your deployed frontend + localhost for testing
#     CORS(app, resources={r"/api/*": {"origins": [
#         "https://hhs-hotel-demo-7fhz3.ondigitalocean.app",
#         "http://localhost:3000"
#     ]}}, supports_credentials=True)

#     # Blueprints
#     app.register_blueprint(auth_bp, url_prefix='/api/auth')
#     app.register_blueprint(hotels_bp, url_prefix='/api/hotels')
#     app.register_blueprint(sync_bp, url_prefix='/api/sync')

#     @app.route('/api/health')
#     def health():
#         return jsonify(status='ok')

#     return app