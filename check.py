from app import app, FileReader, Action, db
def check_integrity():
    with app.app_context():
        reader = FileReader.query.first()
        balance = reader.balance
        actions = Action.query.all()
        calculated_balance = 0
        for action in actions:
            if action.action_type == 'saldo':
                calculated_balance += float(action.details)
            elif action.action_type == 'zakup':
                _, price, quantity = action.details.split(',')
                calculated_balance -= float(price) * int(quantity)
            elif action.action_type == 'sprzedaż':
                _, price, quantity = action.details.split(',')
                calculated_balance += float(price) * int(quantity)
        if balance != calculated_balance:
            print("Błąd integralności danych: saldo nie zgadza się z historią operacji")
        else:
            print("Integralność danych została zachowana")

if __name__ == "__main__":
    with app.app_context():
        check_integrity()
        db.create_all()
    app.run(debug=True)
