#!/usr/bin/python3

from PyQt5.QtSql import QSqlDatabase, QSqlQuery
from PyQt5.QtWidgets import (QApplication, QDialog, QTableWidgetItem, QPushButton, QMessageBox, QTreeWidget, QTreeWidgetItem, QGridLayout, QWidget, QVBoxLayout, QHBoxLayout, QLayout, QBoxLayout, QSizePolicy, QSplitter, QCalendarWidget, QAbstractItemView, QSpacerItem)
from PyQt5.QtCore import (QDateTime, QDate, QTime, Qt, QItemSelectionModel)
from PyQt5.QtGui import (QTextCharFormat, QFont, QColor, QBrush)

from PyQt5 import uic
import sys

try:
    database = sys.argv[1]
except:
    database = 'database.sqlite'

db = QSqlDatabase.addDatabase("QSQLITE")
db.setDatabaseName(database)
db.open()

def check(widget, to_check):
    values = []
    for i, name in enumerate(to_check):
        item = widget.item(0, i)
        if not item or not item.text():
            QMessageBox.critical(widget, "Ошибка", f'Вы забыли указать "{name}"')
            return False
        values.append(item.text())
        item.setText("")
    return values


def get_count(text):
    query = QSqlQuery(text, db)
    query.first()
    count = 0
    try:
        count = int(query.value(0))
    except:
        pass
    return count


class EditButton(QPushButton):
    def __init__(self, id, row, widget):
        super().__init__('Обновить', clicked=self.on_click)
        self.id = id
        self.row = row
        self.widget = widget

    def on_click(self):
        pass


class ClubSchedule(QWidget):
    def __init__(self, id):
        super().__init__()

        self.club_id = int(id)
        self.calendar = QCalendarWidget()
        self.widget = QTreeWidget()
        self.widget.setHeaderLabels(["Название корта/ФИО", "Забронированное время"])
        self.widget.setColumnCount(2)

        q = QSqlQuery(f'select date(t.datetime), count(*) from timetable as t join places as p on (t.place_id=p.id) WHERE place_id={self.club_id} GROUP BY date(t.datetime)')
        while q.next():
            format = QTextCharFormat()
            format.setFontWeight(QFont.Black)
            format.setToolTip(f'Всего забронировано: {q.value(1)}')
            format.setBackground(QColor(245, 246, 193))

            dt = QDate.fromString(q.value(0), Qt.ISODate)
            self.calendar.setDateTextFormat(dt, format)

        self.calendar.selectionChanged.connect(self.reload)

        self.reload()

        layout = QVBoxLayout()
        layout.addWidget(self.calendar)
        layout.addWidget(self.widget)
        self.setLayout(layout)

    def reload(self):
        self.widget.clear()
        date = self.calendar.selectedDate().toString('yyyy-MM-dd')

        odd_even = True
        odd_color = QColor(240, 240, 240)

        clients = {}
        q = QSqlQuery('select id, name, family from players')
        while q.next():
            clients[q.value(0)] = f'{q.value(1)} {q.value(2)}'

        places_query = QSqlQuery(f'select id, name from places where club_id={self.club_id}')
        while places_query.next():
            place_item = QTreeWidgetItem(self.widget, [places_query.value(1)])
            self.widget.expandItem(place_item)

            tt_query = QSqlQuery(f'select datetime, player_id from timetable where place_id={places_query.value(0)} and date(datetime) == "{date}" order by player_id, datetime')
            player = None
            dt = None
            dates = []
            while tt_query.next():
                if player is None:
                    player = tt_query.value(1)

                datetime = QDateTime.fromString(tt_query.value(0), Qt.ISODate)

                if dt is None:
                    dt = datetime

                if player != tt_query.value(1) or abs(dt.toSecsSinceEpoch() - datetime.toSecsSinceEpoch()) > 1800:
                    player_item = QTreeWidgetItem(place_item, [clients[player], ', '.join(dates)])
                    if odd_even:
                        player_item.setBackground(0, odd_color)
                        player_item.setBackground(1, odd_color)
                    player = tt_query.value(1)
                    dates = []
                    odd_even = not odd_even

                dates.append(datetime.toString('HH:mm'))

            if len(dates):
                player_item = QTreeWidgetItem(place_item, [clients[player], ', '.join(dates)])
                if odd_even:
                    player_item.setBackground(0, odd_color)
                    player_item.setBackground(1, odd_color)

class Places(QWidget):
    def __init__(self, id, name):
        super().__init__()

        self.club_id = int(id)

        uic.loadUi('places.ui', self)
        self.title.setText(f'Площадки для клуба "{name}"')
        self.places.setColumnCount(2)

        self.places.setHorizontalHeaderLabels(["Название", ""])
        self.update()

    def update(self):
        self.places.clear()

        id = self.club_id

        self.places.setRowCount(get_count(f'SELECT count(*) FROM places WHERE club_id={int(id)}') + 1)

        button = QPushButton("Добавить")
        button.clicked.connect(self.on_add)
        self.places.setCellWidget(0, 1, button)

        q = QSqlQuery(f'SELECT id, name FROM places WHERE club_id={int(id)}', db)
        row = 1
        while q.next():
            item = QTableWidgetItem(q.value(1))
            self.places.setItem(row, 0, item)
            row += 1

    def on_add(self):
        place_title = ''
        item = self.places.item(0, 0)
        if item:
            place_title = item.text()
        if not len(place_title):
            QMessageBox.critical(self.places, 'Ошибка', 'Вы забыли указать название корта')

        q = QSqlQuery()
        q.prepare('INSERT INTO places (club_id, name) VALUES (:club_id, :name)')
        q.bindValue(':club_id', self.club_id)
        q.bindValue(':name', place_title)
        q.exec()

        self.update()


class Clubs:
    class Values:
        def __init__(self, values):
            self.values = values

        def value(self, idx):
            return self.values[idx]

    class ClubPlacesButton(QPushButton):
        def __init__(self, club_name, club_id, clubs):
            super().__init__('Корты')
            self.clubs = clubs
            self.club_name = club_name
            self.club_id = club_id
            self.clicked.connect(self.on_click)

            self.places = Places(self.club_id, self.club_name)

        def on_click(self):
            tabs = self.clubs.tab_widget
            index = tabs.indexOf(self.places)
            if index == -1:
                index = tabs.addTab(self.places, f'Корты для клуба "{self.club_name}"')
            tabs.setCurrentIndex(index)

    class ClubScheduleButton(QPushButton):
        def __init__(self, club_name, club_id, clubs):
            super().__init__('Расписание')
            self.clubs = clubs
            self.club_name = club_name
            self.club_id = club_id
            self.clicked.connect(self.on_click)
            self.schedule = ClubSchedule(club_id)

        def on_click(self):
            tabs = self.clubs.tab_widget
            index = tabs.indexOf(self.schedule)
            if index == -1:
                index = tabs.addTab(self.schedule, f'Расписание для клуба "{self.club_name}"')
            tabs.setCurrentIndex(index)

    class ClubEditButton(EditButton):
        def on_click(self):
            v = []
            for col in range(0, 3):
                item = self.widget.item(self.row, col)
                if not item or not item.text():
                    QMessageBox.critical(self.widget, 'Ошибка', 'пустое поле недопустимо')
                    return
                v.append(item.text())
            query = QSqlQuery(db)
            query.exec(f"update clubs set name='{v[0]}', address='{v[1]}', phone='{v[2]}' WHERE id={self.id}")

    def __init__(self, widget, tab_widget):
        self.widget = widget
        self.tab_widget = tab_widget
        self.widget.setColumnCount(4)
        self.widget.setRowCount(1)
        button = QPushButton("Добавить")
        button.clicked.connect(self.on_new)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(button)
        layout.addStretch()

        widget = QWidget()
        widget.setLayout(layout)
        self.widget.setCellWidget(0, 3, widget)
        self.update()

    def show_item(self, query):
        row = self.widget.rowCount()
        self.widget.setRowCount(row + 1)

        for j in range(0, 3):
            item = QTableWidgetItem(query.value(j))
            self.widget.setItem(row, j, item)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.setContentsMargins(0, 0, 0, 0)
        buttonsLayout.addWidget(Clubs.ClubEditButton(query.value(3), row, self.widget))
        buttonsLayout.addWidget(Clubs.ClubPlacesButton(query.value(0), query.value(3), self))
        buttonsLayout.addWidget(Clubs.ClubScheduleButton(query.value(0), query.value(3), self))
        buttonsLayout.addStretch()

        buttonsWidget = QWidget()
        buttonsWidget.setLayout(buttonsLayout)
        self.widget.setCellWidget(row, 3, buttonsWidget)

    def on_new(self):
        v = check(self.widget, ["название клуба", "адрес", "телефон"])
        if not v:
            return

        query = QSqlQuery(db)
        query.exec(f"insert into clubs (name, address, phone) values ('{v[0]}', '{v[1]}', '{v[2]}')")
        v.append(query.lastInsertId())
        self.show_item(Clubs.Values(v))

    def update(self):
        query = QSqlQuery('select name, address, phone, id from clubs', db)
        while query.next():
            self.show_item(query)

        for col in range(0, 3):
            self.widget.setItem(0, col, None)

class Players:
    class PlayerEditButton(EditButton):
        def on_click(self):
            v = []
            for col in range(0, 3):
                item = self.widget.item(self.row, col)
                if not item or not item.text():
                    QMessageBox.critical(self.widget, 'Ошибка', 'пустое поле недопустимо')
                    return
                v.append(item.text())
            query = QSqlQuery(db)
            query.exec(f"update players set name='{v[0]}', family='{v[1]}', phone='{v[2]}' WHERE id={self.id}")

    def __init__(self, widget):
        self.widget = widget

        self.widget.setColumnCount(4)
        self.widget.setRowCount(1)
        self.widget.setHorizontalHeaderLabels(["Имя", "Фамилия", "Телефон", ""])
        button = QPushButton("добавить")
        button.clicked.connect(self.on_new)
        self.widget.setCellWidget(0, 3, button)
        self.update()

    def on_new(self):
        v = check(self.widget, ["имя", "фамилия", "телефон"])
        if not v:
            return

        query = QSqlQuery(db)
        query.exec(f"insert into players (name, family, phone) values ('{v[0]}', '{v[1]}', '{v[2]}')")
        self.update()

    def update(self):
        count = get_count('select count(*) from players')
        # +1 нужен что бы добавить 0ю строчку для нового клуба
        self.widget.setRowCount(count + 1)

        query = QSqlQuery('select name, family, phone, id from players', db)
        i = 1
        while query.next():
            for j in range(0, 3):
                item = QTableWidgetItem(query.value(j))
                self.widget.setItem(i, j, item)

            buttonsLayout = QBoxLayout(QBoxLayout.LeftToRight, self.widget)
            buttonsLayout.addWidget(Players.PlayerEditButton(query.value(3), i, self.widget))
            buttonsWidget = QWidget()
            buttonsWidget.setLayout(buttonsLayout)

            self.widget.setCellWidget(i, 3, buttonsWidget)
            i += 1

        for col in range(0, 3):
            self.widget.setItem(0, col, None)

class ManagerWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModal)

        uic.loadUi('manager.ui', self)

        self.players = Players(self.players_widget)
        self.clubs = Clubs(self.clubs_widget, self.tab_widget)

        self.show()


class TimeButton(QPushButton):
    def __init__(self, datetime, place_id, client_id, selected, enabled):
        super().__init__(datetime.toString('HH:mm'))
        self.datetime = datetime
        self.place_id = place_id
        self.client_id = client_id
        self.setCheckable(True)
        self.setEnabled(enabled)
        self.setChecked(selected)

        self.toggled.connect(self.on_selected)

    def on_selected(self, toggled):
        if toggled:
            query = QSqlQuery(db)
            query.prepare('INSERT INTO timetable (place_id, datetime, player_id) VALUES (:place_id, :datetime, :player_id)')
            query.bindValue(':datetime', self.datetime.toString(Qt.ISODate))
            query.bindValue(':place_id', self.place_id)
            query.bindValue(':player_id', self.client_id)
            query.exec()
        else:
            query = QSqlQuery(db)
            query.prepare('DELETE FROM timetable WHERE place_id=:place_id AND datetime=:datetime')
            query.bindValue(':datetime', self.datetime.toString(Qt.ISODate))
            query.bindValue(':place_id', self.place_id)
            query.exec()


class ClientWindow(QDialog):
    def __init__(self, parent, client_id):
        super().__init__(parent)

        self.client_id = client_id

        self.setGeometry(0, 0, 800, 600)

        self.splitter = QSplitter(Qt.Vertical)
        self.calendar = QCalendarWidget()
        self.schedule = QTreeWidget()
        self.splitter.addWidget(self.calendar)
        self.splitter.addWidget(self.schedule)

        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

        self.schedule.setColumnCount(1)
        self.schedule.setHeaderLabels(["Расписание"])
        self.schedule.setSelectionMode(QAbstractItemView.NoSelection)
        self.schedule.setFocusPolicy(Qt.NoFocus)

        self.calendar.selectionChanged.connect(self.reload)

        self.reload()
        self.show()

    def reload(self):
        self.schedule.clear()

        timetable = {}

        query = QSqlQuery('select id, name from clubs', db)
        while query.next():
            item = timetable[int(query.value(0))] = QTreeWidgetItem(self.schedule, [query.value(1)])
            self.schedule.expandItem(item)

        query = QSqlQuery('select id, club_id, name from places', db)
        while query.next():
            place_id = int(query.value(0))
            club_id = int(query.value(1))
            name = query.value(2)

            place_item = QTreeWidgetItem(timetable[club_id], [name])
            self.schedule.expandItem(place_item)
            timetable_item = QTreeWidgetItem(place_item, [])
            self.schedule.expandItem(timetable_item)

            layout = QGridLayout()
            row = 0
            col = 0
            t = QTime(9, 0, 0)
            while t.hour() <= 21:
                time = QDateTime(self.calendar.selectedDate(), t)
                q = QSqlQuery(db)
                q.prepare('SELECT player_id FROM timetable WHERE place_id=:place_id AND datetime=:datetime')
                q.bindValue(':place_id', place_id)
                q.bindValue(':datetime', time.toString(Qt.ISODate))
                q.exec()

                selected = False
                enabled = True

                if q.next():
                    if int(q.value(0)) == self.client_id:
                        selected = True
                    else:
                        enabled = False

                layout.addWidget(TimeButton(time, place_id, self.client_id, selected, enabled), row, col)
                col += 1
                if col > 4:
                    col = 0
                    row += 1
                t = t.addSecs(60 * 30)

            timeItem = QTreeWidgetItem(place_item)
            widget = QWidget()
            widget.setLayout(layout)
            self.schedule.setItemWidget(timetable_item, 0, widget)


class ChooseWindow(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi('chooser.ui', self)

        self.clients.currentIndexChanged.connect(self.on_client_index_changed)
        self.update_clients()

        self.manager.clicked.connect(self.manager_window)
        self.client.clicked.connect(self.client_window)

        self.show()

    def update_clients(self):
        self.clients.clear()
        q = QSqlQuery('SELECT id, name, family FROM players', db)
        while q.next():
            self.clients.addItem(f'{q.value(1)} {q.value(2)}', q.value(0))

    def on_client_index_changed(self, index):
        if index >= 0:
            self.client.setEnabled(True)
        else: self.client.setEnabled(False)

    def manager_window(self):
        win = ManagerWindow(self)
        win.finished.connect(self.update_clients)

    def client_window(self):
        win = ClientWindow(self, int(self.clients.currentData()))


if __name__ == '__main__':
    tables = [
        ('clubs', 'CREATE TABLE clubs (id INTEGER NOT NULL PRIMARY KEY, name varchar(100), address varchar(100), phone varchar(100))'),
        ('places', 'CREATE TABLE places (id INTEGER NOT NULL PRIMARY KEY, club_id integer not null, name varchar(100))'),
        ('players', 'CREATE TABLE players (id INTEGER NOT NULL PRIMARY KEY, name varchar(100), family varchar(100), phone varchar(100))'),
        ('timetable', 'CREATE TABLE timetable (place_id int not null, datetime text not null, player_id int not null)')
    ]
    exist_tables = set(db.tables())
    for table_name, schema in tables:
        if table_name not in exist_tables:
            q = QSqlQuery(schema)
            q.exec()

    app = QApplication(sys.argv)
    win = ChooseWindow()
    app.exec_()
