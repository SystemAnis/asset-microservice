"""
Microservizio API REST per la gestione degli asset.
Flask applicazione ottimizzata con:
- Configurazione basata su variabili d'ambiente
- Logging strutturato
- Gestione errori uniforme
- Paginazione e filtraggio
- Supporto per CRUD completi
- Health check endpoint
"""

import os
import logging
from flask import Flask, jsonify, request, abort, make_response

# ---------------------------------------------------------------------------
# Configurazione logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configurazione applicazione da variabili d'ambiente
# ---------------------------------------------------------------------------
class Config:
    """Carica la configurazione dalle variabili d'ambiente."""
    DEBUG = os.getenv("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    PORT = int(os.getenv("FLASK_PORT", 5000))
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    # Paginazione default
    DEFAULT_PER_PAGE = int(os.getenv("DEFAULT_PER_PAGE", 10))


app = Flask(__name__)
app.config.from_object(Config)

# ---------------------------------------------------------------------------
# Database simulato (in-memory)
# ---------------------------------------------------------------------------
assets = [
    {"id": 1, "hostname": "srv-web-01", "status": "active"},
    {"id": 2, "hostname": "db-prod-01", "status": "maintenance"},
]

# ---------------------------------------------------------------------------
# Helper: generazione ID univoco
# ---------------------------------------------------------------------------
def _next_id() -> int:
    """Restituisce il prossimo ID disponibile."""
    return max((a["id"] for a in assets), default=0) + 1


# ---------------------------------------------------------------------------
# Helper: response di successo standardizzato
# ---------------------------------------------------------------------------
def success_response(
    data=None,
    message: str = "Success",
    status_code: int = 200,
) -> tuple:
    """
    Restituisce un JSON di successo coerente.

    Esempio:
        {
            "status": "success",
            "message": "Success",
            "data": {...}
        }
    """
    payload = {"status": "success", "message": message}
    if data is not None:
        payload["data"] = data
    return make_response(jsonify(payload), status_code)


# ---------------------------------------------------------------------------
# Helper: risposta errore standardizzata
# ---------------------------------------------------------------------------
def error_response(message: str, status_code: int) -> tuple:
    """
    Restituisce un JSON di errore coerente.

    Esempio:
        {
            "status": "error",
            "message": "Bad request"
        }
    """
    logger.warning("Errore %d: %s", status_code, message)
    return make_response(jsonify({"status": "error", "message": message}), status_code)


# ---------------------------------------------------------------------------
# Error handlers globali
# ---------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request(error):
    return error_response("Richiesta non valida", 400)


@app.errorhandler(404)
def not_found(error):
    return error_resource_not_found(error)


@app.errorhandler(405)
def method_not_allowed(error):
    return error_response("Metodo non ammesso per questa risorsa", 405)


@app.errorhandler(500)
def internal_server_error(error):
    return error_response("Errore interno al server", 500)


def error_resource_not_found(resource: str = "Risorsa") -> tuple:
    """Handler 404 personalizzato con payload coerente."""
    return error_response(f"{resource} non trovata", 404)


# ---------------------------------------------------------------------------
# Route: Asset CRUD
# ---------------------------------------------------------------------------

@app.route("/api/assets", methods=["GET"])
def get_assets():
    """
    Ottieni l'elenco degli asset con paginazione e filtraggio opzionale.

    Query parameters:
        page      (int): numero di pagina, default 1
        per_page  (int): elementi per pagina, default CONFIG['DEFAULT_PER_PAGE']
        status    (str): filtra per stato (es. 'active', 'maintenance')
    """
    try:
        page = request.args.get("page", type=int, default=1)
        per_page = request.args.get(
            "per_page", type=int, default=app.config["DEFAULT_PER_PAGE"]
        )
        status_filter = request.args.get("status", type=str)

        # Filtramento in memoria
        queryset = assets
        if status_filter:
            queryset = [a for a in queryset if a.get("status") == status_filter]

        # Paginazione
        total = len(queryset)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = queryset[start:end]

        # Metadati paginazione
        pages = (total + per_page - 1) // per_page if per_page else 1

        meta = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        }

        return success_response(
            data={"items": page_items, "meta": meta},
            message="Asset list retrieved",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Errore durante il recupero degli asset")
        abort(500)


@app.route("/api/assets/<int:asset_id>", methods=["GET"])
def get_asset(asset_id: int):
    """Ottieni un singolo asset per ID."""
    asset = next((a for a in assets if a["id"] == asset_id), None)
    if asset is None:
        abort(404)
    return success_response(data=asset, message="Asset retrieved", status_code=200)


@app.route("/api/assets", methods=["POST"])
def create_asset():
    """
    Crea un nuovo asset.

    Body JSON atteso:
        {
            "hostname": "string",
            "status": "string (opzionale)"
        }
    """
    try:
        if not request.is_json:
            abort(400, description="Content-Type must be application/json")

        data = request.get_json()

        hostname = data.get("hostname")
        if not hostname or not isinstance(hostname, str):
            abort(400, description="Field 'hostname' is required and must be a string")

        status = data.get("status", "active")

        new_asset = {
            "id": _next_id(),
            "hostname": hostname,
            "status": status,
        }
        assets.append(new_asset)

        logger.info("Asset creato: id=%s, hostname=%s", new_asset["id"], hostname)
        return success_response(
            data=new_asset,
            message="Asset creato con successo",
            status_code=201,
        )
    except Exception as e:
        logger.exception("Errore durante la creazione dell'asset")
        abort(500)


@app.route("/api/assets/<int:asset_id>", methods=["PUT"])
def update_asset(asset_id: int):
    """Aggiorna un asset esistente parzialmente."""
    asset = next((a for a in assets if a["id"] == asset_id), None)
    if asset is None:
        abort(404)

    try:
        if not request.is_json:
            abort(400, description="Content-Type must be application/json")

        data = request.get_json()

        if "hostname" in data:
            if not isinstance(data["hostname"], str) or not data["hostname"]:
                abort(400, description="Field 'hostname' must be a non-empty string")
            asset["hostname"] = data["hostname"]

        if "status" in data:
            if not isinstance(data["status"], str) or not data["status"]:
                abort(400, description="Field 'status' must be a non-empty string")
            asset["status"] = data["status"]

        logger.info("Asset aggiornato: id=%s", asset_id)
        return success_response(data=asset, message="Asset aggiornato", status_code=200)
    except Exception as e:
        logger.exception("Errore durante l'aggiornamento dell'asset")
        abort(500)


@app.route("/api/assets/<int:asset_id>", methods=["DELETE"])
def delete_asset(asset_id: int):
    """Rimuovi un asset per ID."""
    global assets
    asset = next((a for a in assets if a["id"] == asset_id), None)
    if asset is None:
        abort(404)

    try:
        assets = [a for a in assets if a["id"] != asset_id]
        logger.info("Asset rimosso: id=%s", asset_id)
        return success_response(
            data={"id": asset_id}, message="Asset rimosso", status_code=200
        )
    except Exception as e:
        logger.exception("Errore durante la rimozione dell'asset")
        abort(500)


# ---------------------------------------------------------------------------
# Route: Health Check
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint per Docker/Kubernetes."""
    return success_response(
        data={
            "status": "healthy",
            "service": "asset-management-api",
            "version": "1.0.0",
        },
        message="Service OK",
        status_code=200,
    )


@app.route("/api/status", methods=["GET"])
def service_status():
    """Endpoint di stato servizio (monitoraggio)."""
    return success_response(
        data={
            "service": "asset-management-api",
            "version": "1.0.0",
            "running": True,
            "assets_total": len(assets),
        },
        message="Service status",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info(
        "Avviando %s su %s:%s (debug=%s)",
        app.name,
        app.config["HOST"],
        app.config["PORT"],
        app.config["DEBUG"],
    )
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
