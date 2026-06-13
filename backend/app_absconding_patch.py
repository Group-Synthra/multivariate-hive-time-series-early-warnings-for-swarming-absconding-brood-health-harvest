
# Add these two lines inside your existing backend/app.py

from backend.routes.absconding_routes import absconding_bp
app.register_blueprint(absconding_bp)

# Then run:
# python backend/scripts/run_absconding.py
# python backend/app.py
#
# Test:
# http://localhost:5000/api/absconding/summary
