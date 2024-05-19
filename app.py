from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class FileReader(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, nullable=False, default=0)
    warehouse = db.relationship('Product', backref='file_reader', lazy=True)
    actions = db.relationship('Action', backref='file_reader', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    file_reader_id = db.Column(db.Integer, db.ForeignKey('file_reader.id'), nullable=False)

class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.String(200), nullable=False)
    file_reader_id = db.Column(db.Integer, db.ForeignKey('file_reader.id'), nullable=False)

class FileReaderHandler:
    def __init__(self):
        self.load_data()

    def save_data(self):
        db.session.commit()

    def load_data(self):
        with app.app_context():
            reader = FileReader.query.first()
            if not reader:
                reader = FileReader(balance=0)
                db.session.add(reader)
                db.session.commit()
            self.balance = reader.balance
            self.warehouse = {product.name: {'price': product.price, 'quantity': product.quantity} for product in Product.query.all()}
            self.actions = [(action.action_type, action.details) for action in Action.query.all()]

    def modify(self, changes_list):
        with app.app_context():
            for change in changes_list:
                x, y, value = map(str.strip, change.split(','))
                x, y = int(x), int(y)
                product = Product.query.filter_by(name=y).first()
                if x == 'price':
                    product.price = float(value)
                elif x == 'quantity':
                    product.quantity = int(value)
            self.save_data()

    def display(self):
        if not self.warehouse:
            print("Brak danych do wyświetlenia")
            return
        for row in self.warehouse:
            print(','.join(map(str, row)))

    def save(self):
        self.save_data()

class Manager:
    def __init__(self):
        self.reader = FileReaderHandler()

    def assign(self, command):
        with app.app_context():
            if command.startswith('saldo'):
                amount = float(command.split(',')[1])
                reader = FileReader.query.first()
                reader.balance += amount
                action = Action(action_type='saldo', details=str(amount), file_reader_id=reader.id)
                db.session.add(action)
            elif command.startswith('sprzedaż'):
                parts = command.split(',')
                name = parts[1]
                price = float(parts[2])
                quantity = int(parts[3])
                product = Product.query.filter_by(name=name).first()
                if product.quantity < quantity:
                    print("Brak wystarczającej liczby sztuk w magazynie!")
                    return
                total_price = price * quantity
                product.quantity -= quantity
                reader = FileReader.query.first()
                reader.balance += total_price
                action = Action(action_type='sprzedaż', details=f"{name},{price},{quantity}", file_reader_id=reader.id)
                db.session.add(action)
            elif command.startswith('zakup'):
                parts = command.split(',')
                name = parts[1]
                price = float(parts[2])
                quantity = int(parts[3])
                product = Product.query.filter_by(name=name).first()
                reader = FileReader.query.first()
                if product:
                    product.quantity += quantity
                else:
                    product = Product(name=name, price=price, quantity=quantity, file_reader_id=reader.id)
                    db.session.add(product)
                total_price = price * quantity
                reader.balance -= total_price
                action = Action(action_type='zakup', details=f"{name},{price},{quantity}", file_reader_id=reader.id)
                db.session.add(action)
            elif command.startswith('konto'):
                print("Stan konta: ", FileReader.query.first().balance)
            elif command.startswith('lista'):
                self.reader.display()
            elif command.startswith('magazyn'):
                name = command.split(',')[1]
                product = Product.query.filter_by(name=name).first()
                if product:
                    print(f"Stan magazynu dla produktu {name}: Cena: {product.price}, Ilość: {product.quantity}")
                else:
                    print("Produkt nie istnieje w magazynie!")
            elif command.startswith('przegląd'):
                parts = command.split(',')
                start = int(parts[1]) if len(parts) > 1 else 0
                end = int(parts[2]) if len(parts) > 2 else len(self.reader.actions) - 1
                if start < 0 or end >= len(self.reader.actions):
                    print(f"Podano nieprawidłowy zakres, dostępne indeksy od 0 do {len(self.reader.actions)-1}")
                    return
                print("Historia operacji:")
                for i in range(start, end + 1):
                    print(self.reader.actions[i])
            else:
                print("Nieprawidłowa komenda!")

    def execute(self):
        while True:
            print("\nDostępne komendy: saldo, sprzedaż, zakup, konto, lista, magazyn, przegląd, koniec")
            command = input("Podaj komendę: ").lower()
            if command.startswith('koniec'):
                print("Koniec działania programu.")
                break
            self.assign(command)
            self.reader.save()

manager = Manager()

@app.route('/')
def index():
    global manager
    with app.app_context():
        balance = FileReader.query.first().balance
        warehouse = {product.name: {'price': product.price, 'quantity': product.quantity} for product in Product.query.all()}
    return render_template('index.html', balance=balance, warehouse=warehouse)

@app.route('/purchase', methods=['POST'])
def purchase():
    global manager
    name = request.form['name']
    price = float(request.form['price'])
    quantity = int(request.form['quantity'])
    with app.app_context():
        manager.assign(f'zakup,{name},{price},{quantity}')
    return redirect(url_for('index'))

@app.route('/sale', methods=['POST'])
def sale():
    global manager
    name = request.form['name']
    quantity = int(request.form['quantity'])
    with app.app_context():
        manager.assign(f'sprzedaż,{name},0,{quantity}')
    return redirect(url_for('index'))

@app.route('/change_balance', methods=['POST'])
def change_balance():
    global manager
    amount = float(request.form['amount'])
    with app.app_context():
        manager.assign(f'saldo,{amount}')
    return redirect(url_for('index'))

@app.route('/history/')
def history():
    global manager
    with app.app_context():
        actions = [(action.action_type, action.details) for action in Action.query.all()]
    return render_template('history.html', actions=actions)

@app.route('/history/<int:start>/<int:end>')
def history_range(start, end):
    global manager
    with app.app_context():
        total_actions = Action.query.count()
        if start < 0 or end >= total_actions or start > end:
            return "Nieprawidłowy zakres indeksów"
        actions = [(action.action_type, action.details) for action in Action.query.offset(start).limit(end-start+1)]
    return render_template('history.html', actions=actions)

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
