import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
                               QLabel, QLineEdit, QTableWidget, QTableWidgetItem, QComboBox,
                               QMessageBox, QHBoxLayout, QDialog, QFormLayout, QDialogButtonBox, QDateEdit)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QDate
from sqlalchemy import (create_engine, Column, Integer, String, Date, ForeignKey, select, distinct)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

DB_URI = 'postgresql+psycopg2://postgres@localhost:5432/database'
engine = create_engine(DB_URI)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Person(Base):
    __tablename__ = 'persons'
    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    passport_series = Column(String)
    passport_number = Column(String)
    address = Column(String)
    positions = relationship("Position", back_populates="person", cascade="all, delete")

class Company(Base):
    __tablename__ = 'companies'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    positions = relationship("Position", back_populates="company", cascade="all, delete")

class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    start_date = Column(Date)
    person_id = Column(Integer, ForeignKey('persons.id'))
    company_id = Column(Integer, ForeignKey('companies.id'))

    person = relationship("Person", back_populates="positions")
    company = relationship("Company", back_populates="positions")

Base.metadata.create_all(engine)

class EmployeeDialog(QDialog):
    def __init__(self, data=None):
        super().__init__()
        self.setWindowTitle("Форма сотрудника")
        layout = QFormLayout()
        self.setWindowIcon(QIcon('./logo.ico'))
        self.full_name = QLineEdit()
        self.passport_series = QLineEdit()
        self.passport_number = QLineEdit()
        self.address = QLineEdit()
        self.company = QLineEdit()
        self.position = QLineEdit()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())

        if data:
            self.full_name.setText(data['full_name'])
            self.passport_series.setText(data['passport_series'])
            self.passport_number.setText(data['passport_number'])
            self.address.setText(data['address'])
            self.company.setText(data['company'])
            self.position.setText(data['position'])
            self.start_date.setDate(QDate(data['start_date'].year, data['start_date'].month, data['start_date'].day))

        layout.addRow("ФИО:", self.full_name)
        layout.addRow("Серия паспорта:", self.passport_series)
        layout.addRow("Номер паспорта:", self.passport_number)
        layout.addRow("Адрес:", self.address)
        layout.addRow("Компания:", self.company)
        layout.addRow("Должность:", self.position)
        layout.addRow("Дата начала:", self.start_date)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        self.setLayout(layout)

    def get_data(self):
        return {
            'full_name': self.full_name.text(),
            'passport_series': self.passport_series.text(),
            'passport_number': self.passport_number.text(),
            'address': self.address.text(),
            'company': self.company.text(),
            'position': self.position.text(),
            'start_date': self.start_date.date().toPython()
        }

class EmployeeWindow(QWidget):
    def __init__(self, role):
        super().__init__()
        self.role = role
        self.setWindowIcon(QIcon('./logo.ico'))
        self.setWindowTitle("Мои сотрудники")
        self.layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по имени...")
        self.search_input.textChanged.connect(self.load_data)
        self.filter_company = QComboBox()
        self.filter_company.currentTextChanged.connect(self.load_data)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.filter_company)
        self.layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ФИО", "Серия", "Номер", "Адрес", "Компания", "Должность", "Дата начала"
        ])
        self.layout.addWidget(self.table)

        if self.role in ('Администратор', 'Менеджер'):
            add_btn = QPushButton("Добавить сотрудника")
            add_btn.clicked.connect(self.add_employee)
            self.layout.addWidget(add_btn)

        if self.role == 'Администратор':
            edit_btn = QPushButton("Редактировать")
            edit_btn.clicked.connect(self.edit_employee)
            delete_btn = QPushButton("Удалить")
            delete_btn.clicked.connect(self.delete_employee)
            self.layout.addWidget(edit_btn)
            self.layout.addWidget(delete_btn)

        self.setLayout(self.layout)
        self.load_companies()
        self.load_data()

    def load_companies(self):
        session = Session()
        self.filter_company.clear()
        self.filter_company.addItem("Все компании")
        try:
            companies = session.query(Company).order_by(Company.name).all()
            for c in companies:
                self.filter_company.addItem(c.name)
        finally:
            session.close()

    def load_data(self):
        session = Session()
        self.table.setRowCount(0)
        try:
            query = session.query(Position).join(Person).join(Company)
            if name := self.search_input.text().strip().lower():
                query = query.filter(Person.full_name.ilike(f"%{name}%"))
            company = self.filter_company.currentText()
            if company != "Все компании":
                query = query.filter(Company.name == company)

            positions = query.all()
            self.table.setRowCount(len(positions))
            for i, pos in enumerate(positions):
                p = pos.person
                c = pos.company
                values = [
                    p.full_name, p.passport_series, p.passport_number,
                    p.address, c.name, pos.title, pos.start_date.strftime("%Y-%m-%d")
                ]
                for j, val in enumerate(values):
                    self.table.setItem(i, j, QTableWidgetItem(str(val)))
        finally:
            session.close()

    def add_employee(self):
        dialog = EmployeeDialog()
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            session = Session()
            try:
                person = Person(
                    full_name=data['full_name'],
                    passport_series=data['passport_series'],
                    passport_number=data['passport_number'],
                    address=data['address']
                )
                company = session.query(Company).filter_by(name=data['company']).first()
                if not company:
                    company = Company(name=data['company'])
                position = Position(
                    title=data['position'],
                    start_date=data['start_date'],
                    person=person,
                    company=company
                )
                session.add_all([person, company, position])
                session.commit()
                self.load_companies()
                self.load_data()
            finally:
                session.close()

    def get_selected_data(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите сотрудника.")
            return None
        return [self.table.item(row, i).text() for i in range(7)]

    def edit_employee(self):
        old = self.get_selected_data()
        if not old:
            return
        data_dict = {
            'full_name': old[0], 'passport_series': old[1], 'passport_number': old[2],
            'address': old[3], 'company': old[4], 'position': old[5],
            'start_date': datetime.strptime(old[6], "%Y-%m-%d").date()
        }
        dialog = EmployeeDialog(data_dict)
        if dialog.exec() == QDialog.Accepted:
            new = dialog.get_data()
            session = Session()
            try:
                person = session.query(Person).filter_by(
                    full_name=old[0],
                    passport_series=old[1],
                    passport_number=old[2]
                ).first()
                if not person:
                    return
                person.full_name = new['full_name']
                person.passport_series = new['passport_series']
                person.passport_number = new['passport_number']
                person.address = new['address']

                position = person.positions[0]
                position.title = new['position']
                position.start_date = new['start_date']

                company = session.query(Company).filter_by(name=new['company']).first()
                if not company:
                    company = Company(name=new['company'])
                    session.add(company)
                position.company = company

                session.commit()
                self.load_companies()
                self.load_data()
            finally:
                session.close()

    def delete_employee(self):
        data = self.get_selected_data()
        if not data:
            return
        reply = QMessageBox.question(self, "Удалить", f"Удалить сотрудника {data[0]}?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            session = Session()
            try:
                person = session.query(Person).filter_by(
                    full_name=data[0],
                    passport_series=data[1],
                    passport_number=data[2]
                ).first()
                if person:
                    session.delete(person)
                    session.commit()
                    self.load_data()
                    self.load_companies()
            finally:
                session.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('./logo.ico'))
        self.setWindowTitle("Главное меню")
        layout = QVBoxLayout()
        label = QLabel("Выберите роль:")
        layout.addWidget(label)

        for role in ("Администратор", "Менеджер"):
            btn = QPushButton(role)
            btn.clicked.connect(lambda _, r=role: self.open_role_window(r))
            layout.addWidget(btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def open_role_window(self, role):
        self.emp_win = EmployeeWindow(role)
        self.emp_win.show()
        self.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
