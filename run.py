from app import create_app, db
from app.models import User, ApiKey, Trade, ScanSession, Coin, Prediction, Outcome  # noqa

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, ApiKey=ApiKey, Trade=Trade,
                ScanSession=ScanSession, Coin=Coin, Prediction=Prediction, Outcome=Outcome)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
